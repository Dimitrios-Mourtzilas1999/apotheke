# Apotheke – Flask → Django migration

Django project (`config/`) with two apps:
- `accounts` – `User`/`Role` on the existing `users`/`roles` tables, login, logout, change password
- `inventory` – `Category`, `Supplier`, `Product` on the existing tables; dashboard, CRUD views, JSON endpoints

URL paths are identical to the Flask app, so the existing JavaScript works unchanged.

## Run
    pip install -r requirements.txt
    cp .env.example .env              # fill DB_*; DB_ENGINE=sqlite for a quick try
    python manage.py migrate --fake-initial
    python manage.py createsuperuser  # creates an admin-role user (nobody in the old DB has a role)
    python manage.py runserver 8001
    python manage.py test             # 15 tests

## Using your existing MySQL database
The models match the existing tables/columns exactly (no `last_login` was added), so
`migrate --fake-initial` adopts them without touching your data and only creates Django's own
tables (sessions, migrations, ...). `alembic_version` is no longer used.
Back up first: this was verified against an emulation of your dump on SQLite, not on MySQL itself.

Existing MD5 passwords keep working and are re-hashed with PBKDF2 on first login. `nikosmour`
has a 64-char hash the Flask login could never match (it only compared MD5); set a new one with
`python manage.py changepassword nikosmour`.

## Files
Uploads and QR codes moved from `static/uploads|qrcodes` to `media/uploads|qrcodes` (copied here).
Django serves them behind login; use nginx/object storage for heavier use.
