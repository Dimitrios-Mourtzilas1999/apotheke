FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
EXPOSE 8001
# --fake-initial: creates tables on a fresh DB, adopts the existing Flask tables otherwise
CMD ["sh", "-c", "python manage.py migrate --fake-initial --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8001"]
