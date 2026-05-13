# LR-12
# Лабораторная работа №12: AI-ассистированная разработка
Автор: Гармашов Виталий Валерьевич  
группа: 221331  
Вариант: 9  

## Цель
Освоить эффективное использование ИИ-инструментов при разработке на Python: промпт-инжиниринг, критический разбор сгенерированного кода, автоматизированное тестирование с высоким покрытием и интеграцию ИИ в CI (сводка изменений по pull request).

## Выполненные задачи (повышенная сложность, без п. 3, 5, 6, 8)

### 1. Полноценное веб-приложение (REST API)
- **Стек:** FastAPI, SQLAlchemy 2.x, Pydantic v2, JWT, Alembic, SQLite (локально) / PostgreSQL (Docker).
- **Роли:** `customer`, `courier`, `admin` (регистрация по умолчанию — клиент; курьеры создаются админом).
- **Сущности:** рестораны, блюда (меню), заказы и позиции, профили курьеров, события трекинга статуса заказа.
- **Функции:** CRUD ресторанов и блюд (admin), оформление заказа, валидация переходов статусов, назначение курьера (admin), отчёты `top-dishes` и `courier-load` (admin), список пользователей и деактивация (admin).

### 2. Code review сгенерированного кода
- Оформлен отчёт в формате «ИИ → проблема → исправление» (не менее пяти пунктов): файл [`CODE_REVIEW.md`](CODE_REVIEW.md).

### 4. Интеграция ИИ в CI/CD
- Workflow GitHub Actions на событие `pull_request`: сборка diff, вызов **Google Gemini** (`generateContent`), публикация комментария в PR.
- Секрет репозитория: **`GEMINI_API_KEY`** (ключ из [Google AI Studio](https://aistudio.google.com/apikey)).
- Файлы: [`.github/workflows/ai-pr-summary.yml`](.github/workflows/ai-pr-summary.yml), [`.github/scripts/pr_ai_summary.py`](.github/scripts/pr_ai_summary.py).

### 7. Unit-тесты и покрытие ≥90%
- Pytest + `httpx` TestClient, отдельные unit-тесты бизнес-логики заказов.
- В [`pytest.ini`](pytest.ini) задано `--cov-fail-under=90`.
- Шаблоны промптов для генерации тестов: [`PROMPTS_FOR_TESTS.md`](PROMPTS_FOR_TESTS.md).

## Структура проекта

```text
lab12_1/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── security.py
│   ├── routers/          # auth, restaurants, dishes, orders, couriers, admin, reports
│   └── services/         # order_logic (переходы статусов, расчёт суммы заказа)
├── tests/
├── alembic/
├── scripts/
│   └── create_admin.py   # первый пользователь admin (после миграций)
├── .github/
│   ├── workflows/
│   └── scripts/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pytest.ini
├── PROMPT_LOG.md         # журнал промптов и этапов (как в LR-11)
├── PROMPTS_FOR_TESTS.md
└── CODE_REVIEW.md
```

## Быстрый старт (локально)

```powershell
cd d:\projects\lab12_1
python -m pip install -r requirements.txt
copy .env.example .env
# при необходимости отредактируйте .env (SECRET_KEY, DATABASE_URL)
python -m alembic upgrade head
$env:ADMIN_PASSWORD="your-secure-admin-password"
python scripts\create_admin.py
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Документация API: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
- В Swagger для логина поле **username** = email, **password** = пароль.

## Docker (PostgreSQL + API)

```powershell
docker compose up --build
```

Создайте в **корне репозитория** файл `.env` по образцу [`.env.example`](.env.example): для Docker нужны **`POSTGRES_USER`**, **`POSTGRES_DB`**, **`POSTGRES_PASSWORD`**, строка **`DATABASE_URL`** (хост `db` внутри compose-сети) и **`SECRET_KEY`**. В [`docker-compose.yml`](docker-compose.yml) для сервисов указан только **`env_file: .env`** — в репозитории нет строк вида `POSTGRES_PASSWORD: …`, на которые чаще всего ругаются сканеры секретов.

## Тесты и покрытие

```powershell
python -m pytest tests/ -q
```

Ожидается успешный прогон и покрытие пакета `app` не ниже 90% (см. `pytest.ini`).

## Проверка задания 4 (CI + Gemini)

1. Код запушен на GitHub, в репозитории есть workflow **AI PR summary**.
2. **Settings → Secrets and variables → Actions** — создан секрет **`GEMINI_API_KEY`**.
3. Создаётся **Pull Request** (например ветка `docs/...` → `main`), не только push в `main`.
4. Во вкладке **Actions** смотрите успешный запуск; в PR — комментарий **«AI summary of changes»** (скриншот для отчёта по методичке).

### Если workflow падает с HTTP 429 (Gemini)

Это **не ошибка Pull Request** — PR создан нормально, не сработал только лимит бесплатного тарифа Google (запросы или токены в минуту/день). Что можно сделать:

- Подождать **~1 минуту** и нажать **Re-run failed jobs** в Actions (в скрипте добавлены повторы с задержкой и укороченный diff).
- В **Settings → Variables → Actions** при желании задайте **`GEMINI_MODEL`** (переопределит значение по умолчанию в скрипте). Список имён моделей: [Gemini models](https://ai.google.dev/gemini-api/docs/models). Примеры для экономии квоты: `gemini-2.5-flash-lite` (по умолчанию в коде), `gemini-3.1-flash-lite`, `gemini-3.1-flash-lite-preview` — если конкретное имя не находится, замените на актуальное из консоли AI Studio.
- Уменьшить объём текста в запросе: переменная **`GEMINI_MAX_DIFF_CHARS`** (по умолчанию `24000`).
- Проверить квоту в [Google AI Studio](https://aistudio.google.com/) / при необходимости включить платный тариф.

### Если workflow падает с HTTP 502 / 503 / 504

Обычно это **временная перегрузка** API Google или GitHub. В скрипте включены повторы с паузой; чаще всего помогает **Re-run failed jobs** через минуту.

Предупреждение в логе про **Node.js 20** у `actions/checkout` — это плановая депрекация раннера GitHub, к падению шага с Gemini не относится.

## Дополнительные материалы

| Файл | Назначение |
|------|------------|
| [PROMPT_LOG.md](PROMPT_LOG.md) | Полный журнал промптов по этапам (формат LR-11) |
| [PROMPTS_FOR_TESTS.md](PROMPTS_FOR_TESTS.md) | Шаблоны промптов для задания 7 |
| [CODE_REVIEW.md](CODE_REVIEW.md) | Code review задания 2 |
# LR-12
