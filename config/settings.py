from pathlib import Path

from django.contrib.messages import constants as message_constants
import environ

import pymysql

pymysql.version_info = (2, 2, 1, "final", 0)  # satisfy Django's mysqlclient version check
pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
environ.Env.read_env(BASE_DIR / ".env")

# Create env object with casting
env = environ.Env(
    DEBUG=(bool, False)
)

# NOTE: the Flask _env file had a typo (SECRET_KET); both are accepted here.
SECRET_KEY = env("SECRET_KEY", default="dev-only-insecure-key") or env("SECRET_KET", default="dev-only-insecure-key")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "accounts",
    "inventory",
    "rest_framework",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database configuration
# Try DATABASE_URL first (for Appliku), fallback to individual DB_* variables (for Docker/local)
if env.str("DATABASE_URL", default=""):
    DATABASES = {
        "default": env.db(),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env.str("DB_NAME", default="inventory"),
            "USER": env.str("DB_USERNAME", default="root"),
            "PASSWORD": env.str("DB_PASSWORD", default=""),
            "HOST": env.str("DB_HOST", default="localhost"),
            "PORT": env.str("DB_PORT", default="3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "accounts.backends.LegacyPasswordBackend",
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

SILENCED_SYSTEM_CHECKS = ["account.W004", "models.W036"]

# Django Allauth configuration
SITE_ID = 1
ACCOUNT_LOGIN_METHODS = {"username"}
ACCOUNT_SIGNUP_FIELDS = ["username", "password1", "password2"]
ACCOUNT_UNIQUE_EMAIL = False
ACCOUNT_LOGIN_ON_EMAIL_VERIFICATION = False
ACCOUNT_ADAPTER = "accounts.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.SocialAccountAdapter"

# Fresh, salted hashing for all new/rehashed passwords
PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "el"
TIME_ZONE = "Europe/Athens"
USE_I18N = True
USE_TZ = False  # the Flask app stored naive local datetimes

STATIC_URL = env.str("STATIC_URL", default="/static/")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = env.str("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))

MEDIA_URL = "/media/"
MEDIA_ROOT = "/app/media"  # Use Appliku volume mount point

# Session configuration
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400  # 24 hours

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Flask flashed "error"; Bootstrap's class is alert-danger.
MESSAGE_TAGS = {message_constants.ERROR: "danger"}
UPLOAD_MAX_BYTES = 16 * 1024 * 1024  # was MAX_CONTENT_LENGTH

# Email configuration for password reset
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env.str("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)
EMAIL_TIMEOUT = 30

# Social Auth configuration
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env.str("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", default="")
SOCIAL_AUTH_GOOGLE_CLIENT_ID = env.str("SOCIAL_AUTH_GOOGLE_CLIENT_ID", default="")
SOCIAL_AUTH_GOOGLE_CLIENT_SECRET = env.str("SOCIAL_AUTH_GOOGLE_CLIENT_SECRET", default="")
SOCIAL_AUTH_GOOGLE_SCOPE = ["profile", "email"]
SOCIAL_AUTH_GOOGLE_PROVIDER = "google"
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {
            "access_type": "offline",
        },
    }
}

# Anthropic API configuration
ANTHROPIC_API_KEY = env.str("ANTHROPIC_API_KEY", default="")

# Django REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# Required when running behind Appliku's reverse proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Logging configuration for Appliku
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"": {"handlers": ["console"], "level": env.str("LOG_LEVEL", default="INFO")}},
}
