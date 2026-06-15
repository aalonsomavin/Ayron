# Django HTMX Template

A production-ready Django template for new projects with HTMX, TailwindCSS, daisyUI, and Docker-first development.

## Stack

- Django 5.2 LTS
- HTMX (CDN)
- TailwindCSS + daisyUI
- PostgreSQL
- Docker Compose
- pytest + pytest-django

## Bootstrap (copy/paste)

```bash
git clone <this-repo> myproject
cd myproject
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000. You will be redirected to login. Create a superuser:

```bash
docker compose run --rm web python manage.py createsuperuser
```

Then log in with those credentials.

## Project Structure

```
project-root/
├── backend/
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── dev.py
│   │   │   ├── test.py
│   │   │   └── prod.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── apps/
│   │   ├── core/
│   │   └── accounts/
│   ├── templates/
│   ├── static/
│   │   └── s/
│   ├── manage.py
│   └── pytest.ini
├── frontend/
│   ├── package.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── src/
│       └── styles.css
├── docker/
│   ├── backend/Dockerfile
│   ├── tailwind/Dockerfile
│   └── entrypoint.sh
├── scripts/
│   ├── dev.sh
│   ├── test.sh
│   └── fmt.sh
├── compose.yml
├── .env.example
├── .dockerignore
├── .gitignore
└── README.md
```

## Commands

| Command | Description |
|---------|-------------|
| `docker compose up --build` | Start dev: Django + Postgres + Tailwind watch |
| `docker compose run --rm web python manage.py migrate` | Run migrations |
| `docker compose run --rm web python manage.py createsuperuser` | Create admin user |
| `docker compose run --rm web pytest` | Run tests |
| `docker compose run --rm web pytest --cov` | Run tests with coverage |
| `./scripts/dev.sh` | Alias for `docker compose up --build` |
| `./scripts/test.sh` | Alias for running tests |
| `./scripts/fmt.sh` | Run ruff check + format |

## Auth & Access Control

All pages require login by default. Public routes are configured in `apps.core.middleware.LoginRequiredMiddleware` via `PUBLIC_PATHS`:

- `/accounts/login/`
- `/accounts/logout/`
- `/admin/`
- `/static/`
j- `/health`

To add a public route, append to `PUBLIC_PATHS` in `backend/apps/core/middleware.py`.

## Tailwind & CSS

**Dev only:** The `tailwind` service runs `npm run dev:docker`, which uses a polling loop (rebuilt every 2s) to avoid Docker for Mac volume watch limitations. Output: `backend/static/css/app.css`. Django serves this via staticfiles. No manual steps needed except browser reload.

**Production:** Run `npm run build:local` once during deployment; do not run the tailwind container in prod.

For local dev without Docker:

```bash
cd frontend
npm install
npm run watch:local
```

## Test Database

Tests use SQLite in-memory for speed. No extra Postgres setup required for CI. Override in `config.settings.test` if you prefer Postgres.

## Environment

Copy `.env.example` to `.env`. Key variables:

- `DEBUG` – 1 for dev
- `SECRET_KEY` – required in prod
- `ALLOWED_HOSTS` – comma-separated
- `DATABASE_URL` – Postgres URL
