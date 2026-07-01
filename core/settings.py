"""
Django settings for core project.
Django 5.2.x
"""

import os
from pathlib import Path

try:
    import ldap
    from django_auth_ldap.config import LDAPSearch
    _LDAP_DISPONIVEL = True
except ImportError:
    _LDAP_DISPONIVEL = False

# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# =============================================================================
# SECURITY
# =============================================================================

SECRET_KEY = "django-insecure-tv=yz++fhm@$vipya_&q0#5uh*8bp0-pk%!(a2jxa8yzy4ck#9"

DEBUG = True

ALLOWED_HOSTS = [
    "*",
]

CSRF_TRUSTED_ORIGINS = [
    "http://10.100.0.34",
    "http://localhost",
    "http://demeter.ciaer.interna",
    "https://escala.ciaer.interna",
    "https://*.replit.dev",
    "https://*.replit.app",
    "https://*.repl.co",
    "https://*.janeway.replit.dev",
    "https://*.kirk.replit.dev",
    "https://*.picard.replit.dev",
]

# =============================================================================
# AUTH
# =============================================================================

AUTH_USER_MODEL = "escalas.UsuarioCustomizado"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# =============================================================================
# APPLICATIONS
# =============================================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "escalas",
]

# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =============================================================================
# URLS / TEMPLATES
# =============================================================================

ROOT_URLCONF = "core.urls"

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
                "escalas.context_processors.om_context",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# =============================================================================
# DATABASE
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC FILES
# =============================================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# =============================================================================
# MEDIA FILES
# =============================================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

# =============================================================================
# DEFAULT PK
# =============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# LOGGING
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": (
                "{levelname} "
                "{asctime} "
                "{threadName} "
                "{module} "
                "{filename} "
                "{lineno} "
                "{funcName} "
                "{message}"
            ),
            "style": "{",
        },

        "simple": {
            "format": (
                "{levelname} "
                "{asctime} "
                "{module} "
                "{lineno} "
                "{message}"
            ),
            "style": "{",
        },
    },

    "handlers": {

        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },

        "django_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "django.log",
            "formatter": "verbose",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },

        "request_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "requests.log",
            "formatter": "simple",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },

    "loggers": {

        "django": {
            "handlers": ["console", "django_file"],
            "level": "ERROR",
            "propagate": False,
        },

        "django.request": {
            "handlers": ["request_file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# =============================================================================
# LDAP / ACTIVE DIRECTORY
# =============================================================================

if _LDAP_DISPONIVEL:
    # Produção (Linux / python-ldap instalado) — autentica via AD
    from django_auth_ldap.config import *

    AUTH_LDAP_SERVER_URI = "ldap://10.100.0.1:389"
    AUTH_LDAP_BIND_DN = "cn=django,ou=ciaer,dc=ciaer,dc=interna"
    AUTH_LDAP_BIND_PASSWORD = "P0rM41s7"

    AUTH_LDAP_USER_SEARCH = LDAPSearch(
        "ou=CIAER,dc=ciaer,dc=interna", ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)"
    )

    AUTH_LDAP_USER_ATTR_MAP = {
        "username": "sAMAccountName",
        "first_name": "name",
        "last_name": "physicalDeliveryOfficeName",
    }

    AUTHENTICATION_BACKENDS = [
        "core.backend.CustomLDAPBackend",
        "django.contrib.auth.backends.ModelBackend",
    ]

    AUTH_LDAP_ALWAYS_UPDATE_USER = True
    AUTH_LDAP_CACHE_TIMEOUT = 3600

else:
    # Teste local (Windows / sem python-ldap) — login local apenas
    AUTHENTICATION_BACKENDS = [
        "django.contrib.auth.backends.ModelBackend",
    ]

# =============================================================================
# SECURITY OPTIONS (opcional)
# =============================================================================

SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_HTTPONLY = False

X_FRAME_OPTIONS = "DENY"

SECURE_BROWSER_XSS_FILTER = True

SECURE_CONTENT_TYPE_NOSNIFF = True

# =============================================================================
# DEBUG TOOLBAR / DEV ONLY (opcional)
# =============================================================================

if DEBUG:
    INTERNAL_IPS = [
        "127.0.0.1",
    ]
