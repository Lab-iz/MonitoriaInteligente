import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _sqlite_uri(path):
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path.as_posix()}"


def _database_uri(default_path):
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql://", 1)
        return database_url
    return _sqlite_uri(os.environ.get("SQLITE_DB_PATH", default_path))


def _render_path(filename):
    if os.environ.get("RENDER"):
        return Path("/tmp") / filename
    return INSTANCE_DIR / filename


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "monitoria-inteligente-dev-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(BASE_DIR / "app" / "static" / "uploads"))
    REPORT_FOLDER = os.environ.get("REPORT_FOLDER", str(BASE_DIR / "instance" / "reports"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    AI_PROVIDER = os.environ.get("AI_PROVIDER", "mock")
    SEED_DEFAULT_PASSWORD = os.environ.get("SEED_DEFAULT_PASSWORD", "demo123")
    AUTO_INIT_DB = _env_bool("AUTO_INIT_DB")
    SEED_DEMO_DATA = _env_bool("SEED_DEMO_DATA")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}


class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = _sqlite_uri(INSTANCE_DIR / "monitoria.db")
    DEBUG = True


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = _database_uri(_render_path("monitoria.db"))
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", str(_render_path("uploads")))
    REPORT_FOLDER = os.environ.get("REPORT_FOLDER", str(_render_path("reports")))
    DEBUG = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
