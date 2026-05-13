# LR-12
# Лабораторная работа №12: AI-ассистированная разработка
Автор: Гармашов Виталий Валерьевич  
группа: 221331  
Вариант: 9 (сервис доставки еды: рестораны, меню, заказы, курьеры, трекинг)  
Уровень: задания повышенной сложности (п. 1, 2, 4, 7; п. 3, 5, 6, 8 не выполнялись)

### Общая информация
- **Дата выполнения:** 13.05.2026
- **Цель:** Освоить vibe coding / AI-native разработку: промпты, code review сгенерированного кода, тесты с высоким покрытием, CI с ИИ-сводкой по PR.
- **Методология:** Agentic Engineering (планирование, итерации, тесты, контроль качества, документирование промптов)

---

## Этап 1: Инициализация и план

### Промпт 1
**Инструмент:** Cursor (Composer)

**Промпт:** «Ты — AI-ассистент по методологии Agentic Engineering. Лабораторная №12, вариант 9 — сервис доставки еды. Выполняем блок повышенной сложности, но без заданий 3, 5, 6, 8. Нужны: полноценное веб-приложение (FastAPI, JWT, роли, CRUD, отчёты, админ), code review с исправлениями, GitHub Actions с ИИ-комментарием к PR, pytest с покрытием ≥90%. Спланируй стек (FastAPI, SQLAlchemy, Alembic, Docker, Gemini API для CI) и структуру репозитория.»

**Результат:** Согласован стек Python 3.11+, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL в Docker / SQLite локально, JWT, роли customer/courier/admin; список сущностей и эндпоинтов; план коммитов.

**Проверка:** План зафиксирован, открыт репозиторий `lab12_1`.

**Коммит:** (входит в серию `chore` / `feat` при реализации)

**Время:** ~20 мин

---

## Этап 2: Модели данных и инфраструктура БД

### Промпт 2
**Инструмент:** Cursor

**Промпт:** «Реализуй модели SQLAlchemy: User (роли), Restaurant, Dish, Order, OrderItem, CourierProfile, OrderTrackingEvent; связи один-ко-многим; enum статусов заказа; SQLite-совместимые enum через native_enum=False.»

**Результат:** Файл `app/models.py`, `app/database.py`, `app/config.py`.

**Проверка:** Импорт моделей без ошибок, `alembic upgrade head` создаёт таблицы.

**Коммит:** `feat: add food delivery REST API with JWT roles and order workflow` (часть)

**Время:** ~25 мин

---

## Этап 3: Аутентификация и безопасность

### Промпт 3
**Инструмент:** Cursor

**Промпт:** «Добавь регистрацию/логин OAuth2 form, JWT, хеш пароля bcrypt, зависимости CurrentUser и AdminUser через Annotated без двойного Depends.»

**Результат:** `app/security.py`, `app/routers/auth.py`.

**Проблема:** Первоначально использовался `user: User = Depends(CurrentUser)` — двойной Depends → 422 на `/orders`.

**Решение:** Заменено на `user: CurrentUser`, параметры зависимостей упорядочены (admin до `db: Depends`).

**Проверка:** `POST /auth/register`, `POST /auth/login`, `GET /auth/me` с токеном.

**Коммит:** (входит в тот же `feat`)

**Время:** ~30 мин

---

## Этап 4: REST API — рестораны, блюда, заказы, курьеры

### Промпт 4
**Инструмент:** Cursor

**Промпт:** «Реализуй роутеры: CRUD ресторанов и блюд (admin), создание заказа клиентом, смена статусов с валидацией переходов, назначение курьера admin, список заказов для клиента/курьера, GET заказа с проверкой прав.»

**Результат:** `app/routers/restaurants.py`, `dishes.py`, `orders.py`, `couriers.py`, `admin.py`, `reports.py`, `app/services/order_logic.py`.

**Проверка:** Ручные запросы через `/docs` или pytest сценарий полного цикла заказа до `delivered`.

**Коммит:** (входит в `feat`)

**Время:** ~45 мин

---

## Этап 5: Отчёты и аналитика

### Промпт 5
**Инструмент:** Cursor

**Промпт:** «Добавь отчёты для admin: топ блюд по продажам за период (delivered), загрузка курьеров по доставленным заказам с фильтром по датам delivered_at.»

**Результат:** Эндпоинты `GET /reports/top-dishes`, `GET /reports/courier-load`.

**Проверка:** После доставленного заказа отчёты возвращают строки с ненулевой выручкой/количеством.

**Время:** ~15 мин

---

## Этап 6: Тесты и покрытие ≥90%

### Промпт 6
**Инструмент:** Cursor

**Промпт:** «Сгенерируй pytest + httpx TestClient, conftest с SQLite и dependency override сессии БД; интеграционные сценарии + unit-тесты order_logic; в pytest.ini добавь --cov=app --cov-fail-under=90.»

**Результат:** Каталог `tests/`, `pytest.ini`.

**Проверка:** `python -m pytest tests/ -q` — все тесты зелёные, coverage ≥90%.

**Коммит:** `test: add pytest suite with coverage gate at ninety percent`

**Время:** ~40 мин

---

## Этап 7: Docker, Alembic, скрипт администратора

### Промпт 7
**Инструмент:** Cursor

**Промпт:** «Добавь Dockerfile, docker-compose с PostgreSQL, Alembic initial migration (create_all в ревизии для совместимости SQLite/PG), scripts/create_admin.py.»

**Результат:** `Dockerfile`, `docker-compose.yml`, `alembic/`, `scripts/create_admin.py`, `.env.example`.

**Проверка:** `docker compose build`, локально `alembic upgrade head` + `python scripts/create_admin.py`.

**Коммит:** `chore: add Docker Compose stack, Alembic migrations, and admin bootstrap`

**Время:** ~25 мин

---

## Этап 8: CI — сводка PR через Google Gemini

### Промпт 8
**Инструмент:** Cursor

**Промпт:** «Настрой GitHub Actions на pull_request: сохранить diff в файл, Python-скрипт вызывает Gemini generateContent (x-goog-api-key), публикует комментарий в PR через GitHub API; секрет только GEMINI_API_KEY; токен github.token.»

**Результат:** `.github/workflows/ai-pr-summary.yml`, `.github/scripts/pr_ai_summary.py`.

**Проверка:** В репозитории GitHub → Settings → Secrets → `GEMINI_API_KEY`; создание PR → Actions → успешный job → комментарий «AI summary of changes».

**Коммит:** `ci: post Gemini-generated summaries on pull requests` (+ последующий `fix` при доработке payload)

**Время:** ~35 мин

---

## Этап 9: Документация задания 2 и журнал промптов

### Промпт 9
**Инструмент:** Cursor

**Промпт:** «Оформи CODE_REVIEW.md в формате таблицы ИИ → проблема → исправление (не менее 5 пунктов). Обнови журнал промптов под лабораторную.»

**Результат:** `CODE_REVIEW.md`, шаблоны в `PROMPTS_FOR_TESTS.md`.

**Коммит:** `docs: add prompt journal, test prompts, and code review log`

**Время:** ~20 мин

---

## Этап 10: README и PROMPT_LOG в формате LR-11

### Промпт 10
**Инструмент:** Cursor

**Промпт:** «Создай ветку docs/readme-and-prompt-log. README.md и PROMPT_LOG.md оформи по той же логике, что в lab11: шапка LR-12, автор, группа, вариант, этапы с Инструмент / Промпт / Результат / Проверка / Коммит / Время; README — цель, выполненные задачи, структура, быстрый старт, CI.»

**Результат:** `README.md`, `PROMPT_LOG.md` (этот файл), удалён дублирующий `PROMPTS_LOG.md`.

**Проверка:** Markdown корректно отображается в GitHub, ссылки на `PROMPTS_FOR_TESTS.md` работают.

**Коммит:** `docs: align README and PROMPT_LOG with LR-11 format`

**Время:** ~25 мин

---

## Общий итог

### Количество крупных промптов (этапов): 10
### Основные инструменты: Cursor (Composer), Google Gemini (только CI)

### Что пришлось исправлять вручную / итерациями:
1. Зависимости FastAPI: `CurrentUser` без внешнего `Depends`, порядок параметров с `AdminUser` и `Depends(get_db)`.
2. Маршруты заказов: `GET /orders/mine` объявлен раньше `GET /orders/{order_id}`.
3. Отчёт по курьерам: переход с некорректного outerjoin на inner join по доставленным заказам.
4. CI: diff в файл вместо multiline `GITHUB_ENV`.
5. Gemini: минимальный JSON `contents` без лишнего поля `role` в части запросов для совместимости API.

### Ссылки на артефакты методички:
- Задание 1 (повышенное): исходники `app/`
- Задание 2: `CODE_REVIEW.md`
- Задание 4: `.github/workflows/ai-pr-summary.yml`, секрет `GEMINI_API_KEY`
- Задание 7: `tests/`, `pytest.ini`, `PROMPTS_FOR_TESTS.md`

### Список коммитов (основная ветка до документации):
1. `chore: add gitignore for Python artifacts and editors`
2. `feat: add food delivery REST API with JWT roles and order workflow`
3. `test: add pytest suite with coverage gate at ninety percent`
4. `chore: add Docker Compose stack, Alembic migrations, and admin bootstrap`
5. `ci: post Gemini-generated summaries on pull requests`
6. `docs: add prompt journal, test prompts, and code review log`
7. `docs: add laboratory assignment specification PDF`
8. `fix: use minimal Gemini generateContent payload for compatibility`
