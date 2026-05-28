# Backend

FastAPI backend for the Study Efficiency MVP. This milestone implements the core P0 data path only:

1. simple-login by nickname
2. start a study session
3. end a study session with self-report fields
4. abandon an unfinished study session without deleting it
5. list and inspect study sessions
6. upload and fetch aggregated motion features

No frontend, model training, prediction endpoints, dashboard endpoints, password login, or JWT auth are implemented in this milestone.

## Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   └── routers/
├── tests/
├── requirements.txt
└── .env.example
```

## Configuration

The app reads `DATABASE_URL` from the environment.

Example MySQL URL:

```text
mysql+pymysql://study_user:study_password@127.0.0.1:3306/study_efficiency?charset=utf8mb4
```

For tests, SQLite is used:

```text
sqlite://
```

Only `.env.example` is committed. Do not commit real `.env` files or database credentials.

## Local setup

Use a project-local virtual environment:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start the API:

```bash
export DATABASE_URL="sqlite:///./study_efficiency.db"
uvicorn app.main:app --reload
```

OpenAPI docs are available at:

```text
http://127.0.0.1:8000/docs
```

## MySQL development database

From the repository root:

```bash
docker compose up -d mysql
```

Then set:

```bash
export DATABASE_URL="mysql+pymysql://study_user:study_password@127.0.0.1:3306/study_efficiency?charset=utf8mb4"
```

The app currently creates tables on startup via SQLAlchemy metadata and performs a small idempotent schema upgrade for the `study_sessions` abandon fields. Alembic migrations can be added in a later milestone if schema evolution becomes more complex.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

The tests cover simple-login, session start/end/abandon/list/detail, motion feature upsert and 404 behavior.
