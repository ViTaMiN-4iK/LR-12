"""Summarize a pull request diff with Google Gemini and post a GitHub comment.

Environment variables:
  GEMINI_API_KEY      — required to call Gemini (set as GitHub Actions secret).
  GEMINI_MODEL        — optional; default gemini-2.5-flash-lite (cost-oriented lite model, friendlier free-tier).
                        Override examples: gemini-3.1-flash-lite, gemini-3.1-flash-lite-preview (see Google model list).
  GEMINI_MAX_DIFF_CHARS — optional; default 24000 (large diffs hit free-tier token limits quickly).
  GITHUB_EVENT_PATH, GITHUB_REPOSITORY, GITHUB_TOKEN — provided in Actions.
  PR_DIFF_FILE        — path to diff text (default: pr.diff)

If GEMINI_API_KEY is unset, the script exits successfully without posting.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request


def _parse_retry_delay_sec(err_body: str) -> float | None:
    m = re.search(r"retry in ([0-9.]+)\s*s", err_body, re.I)
    if m:
        return min(120.0, float(m.group(1)) + 2.0)
    return None


def _gemini_generate_once(api_key: str, model: str, user_text: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [
            {
                "parts": [{"text": user_text}],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 2048,
            "temperature": 0.3,
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"No candidates in Gemini response: {data!r:.2000}")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    if not parts or "text" not in parts[0]:
        raise RuntimeError(f"Unexpected Gemini shape: {data!r:.2000}")
    return parts[0]["text"].strip()


def _gemini_transient_http(code: int) -> bool:
    """429 = quota; 5xx / 503 = temporary overload (retry with backoff)."""
    return code == 429 or code in (500, 502, 503, 504)


def _gemini_backoff_sec(attempt_index: int, err_body: str, http_code: int) -> float:
    if http_code == 429:
        return _parse_retry_delay_sec(err_body) or (15.0 * (attempt_index + 1))
    return min(60.0, 5.0 * (2**attempt_index))


def _gemini_generate_with_retries(api_key: str, model: str, user_text: str, attempts: int = 5) -> str:
    last_err = ""
    for i in range(attempts):
        try:
            return _gemini_generate_once(api_key, model, user_text)
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            last_err = err
            if not _gemini_transient_http(e.code):
                raise
            wait = _gemini_backoff_sec(i, err, e.code)
            label = "429 rate limit" if e.code == 429 else f"HTTP {e.code} (transient)"
            print(f"Gemini {label}, sleeping {wait:.1f}s before retry {i + 1}/{attempts}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Gemini failed after {attempts} attempts: {last_err[:1500]}")


_GH_COMMENT_RETRYABLE = (408, 429, 500, 502, 503, 504)


def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("GEMINI_API_KEY not set; skipping AI summary.")
        return

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("No GITHUB_EVENT_PATH; skipping.")
        return

    with open(event_path, encoding="utf-8") as f:
        event = json.load(f)
    pr = event.get("pull_request") or {}
    pr_number = pr.get("number")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = (os.environ.get("GITHUB_TOKEN") or "").strip()

    max_chars = int(os.environ.get("GEMINI_MAX_DIFF_CHARS") or "24000")
    diff_path = os.environ.get("PR_DIFF_FILE", "pr.diff")
    try:
        with open(diff_path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
            diff = raw[:max_chars]
            if len(raw) > max_chars:
                diff += f"\n\n… (diff truncated to {max_chars} chars for API quota; full diff in PR files tab)"
    except OSError:
        diff = ""
    if not diff.strip():
        diff = "(empty diff — possibly merge or no file changes)"

    model = (os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash-lite").strip()
    system_preamble = (
        "You are a concise senior engineer. Summarize the pull request diff in 5–10 bullet points "
        "for teammates. Focus on user-visible behavior, risks, and follow-ups. Use clear English.\n\n"
    )
    user_block = f"Repository: {repo}\n\nDiff:\n{diff}"
    text = _gemini_generate_with_retries(api_key, model, system_preamble + user_block)
    comment = "## AI summary of changes\n\n" + text

    if pr_number and token and repo:
        url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        body = json.dumps({"body": comment}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        for attempt in range(5):
            cr = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(cr, timeout=60) as r2:
                    print("Posted comment:", r2.status)
                break
            except urllib.error.HTTPError as e:
                err = e.read().decode("utf-8", errors="replace")
                if e.code not in _GH_COMMENT_RETRYABLE or attempt == 4:
                    raise
                wait = min(30.0, 3.0 * (2**attempt))
                print(f"GitHub comment HTTP {e.code}, retry in {wait:.1f}s: {err[:300]}", file=sys.stderr)
                time.sleep(wait)
    else:
        print("Would post comment (missing token/repo/pr):\n", comment[:500])


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print("HTTP error:", e.code, err[:2000], file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)
