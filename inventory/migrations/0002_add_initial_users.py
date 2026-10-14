import os

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations

USERS = [
    {"username": "dimimour", "email": "user1@example.com"},
]


def add_users(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    for data in USERS:
        env_key = f"INITIAL_PASSWORD_{data['username'].upper()}"
        password = os.environ.get(env_key)
        User.objects.get_or_create(
            username=data["username"],
            defaults={
                **data,
                "password": make_password(password) if password else make_password(None),
            },
        )


def remove_users(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    User.objects.filter(username__in=[u["username"] for u in USERS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_users, remove_users),
    ]