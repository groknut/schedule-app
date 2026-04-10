# ГрафикПро — Work Schedule Planning System

Хакатон-проект для автоматизации планирования и учёта рабочего графика сотрудников.

## Стек

| Слой       | Технология                          |
|------------|-------------------------------------|
| Backend    | Python 3.10+ · FastAPI · SQLAlchemy |
| База данных| SQLite (легко сменить на PostgreSQL) |
| Фронтенд   | Vanilla HTML/CSS/JS (SPA)           |
| Экспорт    | openpyxl (.xlsx)                    |

---

## Быстрый старт

### 1. Установить зависимости
Используя `pip`
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Используя `uv`
```bash
uv sync
```
### 2. Запустить сервер
```bash
python backend/main.py
# или: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# или uv run backend/main.py
```

### 3. Открыть браузер
```
http://localhost:8000
```

> При первом запуске автоматически создаётся демо-организация с 5 сотрудниками и 50 плановыми сменами на 14 дней.

---

## Функциональность

### ✅ Реализовано (все пункты ТЗ кроме авторизации/ролей)

| Пункт                          | Статус | Где смотреть                    |
|-------------------------------|--------|---------------------------------|
| Индивидуальный график          | ✅     | Страница «Мой график»           |
| Визуализация день/неделя/месяц | ✅     | Три режима в календаре          |
| Хранение данных в БД           | ✅     | SQLite / SQLAlchemy ORM         |
| Ролевая модель (структура)     | ✅     | Поля в модели Employee          |
| Выгрузка в Excel               | ✅     | Страница «Выгрузка Excel»       |
| Подтверждение план/факт        | ✅     | Страница «Подтверждение»        |
| Отчёты план/факт               | ✅     | Страница «Отчёты»               |
| Несколько организаций          | ✅     | Страница «Организации»          |
| Вложенные команды              | ✅     | Team.parent_team_id             |
| График руководителя (нагрузка) | ✅     | Дашборд + «График команды»      |

---

## API (Swagger)

```
http://localhost:8000/docs
```

### Основные эндпоинты

```
GET/POST    /organizations
GET/POST    /teams
GET/POST    /employees
GET/POST    /shifts
PUT         /shifts/{id}
DELETE      /shifts/{id}
POST        /shifts/{id}/confirm      ← подтверждение план/факт
GET         /shifts/export/excel      ← Excel выгрузка
GET         /reports/plan-fact        ← отчёт план/факт
GET         /reports/workload         ← нагрузка по сотрудникам
```

### Пример: создать смену
```bash
curl -X POST http://localhost:8000/shifts \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 1,
    "date": "2025-06-10",
    "start_time": "09:00:00",
    "end_time": "18:00:00",
    "shift_type": "planned"
  }'
```

### Пример: экспорт в Excel
```
GET /shifts/export/excel?date_from=2025-06-01&date_to=2025-06-30&team_id=1
```

---

## Структура проекта

```
schedule-app/
├── backend/
│   ├── main.py         ← FastAPI приложение, все роуты
│   ├── models.py       ← SQLAlchemy ORM модели
│   ├── database.py     ← Engine, сессии, create_tables
│   ├── schemas.py      ← Pydantic схемы (валидация)
│   ├── requirements.txt
│   └── schedule.db     ← SQLite файл (создаётся автоматически)
└── frontend/
    └── index.html      ← SPA (Vanilla JS, без фреймворков)
```

---

## Смена БД на PostgreSQL

В `database.py` заменить строку:
```python
DATABASE_URL = "sqlite:///./schedule.db"
# на:
DATABASE_URL = "postgresql://user:password@localhost/scheduledb"
```
И добавить `psycopg2-binary` в requirements.txt.

---

## Команда

Авторизация и ролевая модель реализованы другим членом команды и подключаются через middleware.
