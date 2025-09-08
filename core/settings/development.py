from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

# django-debug-toolbar (imported below)
INTERNAL_IPS = [
    "127.0.0.1",
]

INSTALLED_APPS = ["debug_toolbar",] + INSTALLED_APPS
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware",] + MIDDLEWARE

# Debug Toolbar settings
# DEBUG_TOOLBAR_CONFIG = {
#     "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
# }