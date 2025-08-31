from decouple import config

MODE = config("MODE", default="development")

if MODE == "development":
    from .development import *
elif MODE == "production":
    from .production import *
else:
    raise ValueError(f"Unsupported MODE: {MODE}")