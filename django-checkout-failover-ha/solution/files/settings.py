import os
from pathlib import Path

BASE_DIR = Path(os.environ.get("HA_ROOT", "/app/ha")).resolve()
SECRET_KEY = "shopdesk-lab-not-for-production"
DEBUG = False
ALLOWED_HOSTS = ["*"]
AZ_ID = os.environ.get("HA_AZ_ID", "az-a")
AZ_WRITE_AFFINITY = False

INSTALLED_APPS = [
    "catalog",
    "identity",
    "inventory",
    "checkout",
    "fulfill",
    "controlplane",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "shopdesk.urls"
WSGI_APPLICATION = "shopdesk.wsgi.application"
TIME_ZONE = "UTC"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

PRIMARY_DB = str(BASE_DIR / "state" / "primary.sqlite")
REPLICA_DB = str(BASE_DIR / "state" / "standby.sqlite")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": PRIMARY_DB,
        "ATOMIC_REQUESTS": False,
    },
    "replica": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": REPLICA_DB,
        "ATOMIC_REQUESTS": False,
        "OPTIONS": {},
    },
}

DATABASE_ROUTERS = ["controlplane.router.ShopdeskRouter"]
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_COOKIE_NAME = "shopdesk_session"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": str(BASE_DIR / "state" / "default-cache"),
    },
    "pins": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": str(BASE_DIR / "state" / "pin-cache"),
    },
}

HA_CONFIG_PATH = str(BASE_DIR / "config" / "ha.json")
