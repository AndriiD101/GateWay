from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _parse_connection_string(raw_connection: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for segment in raw_connection.split(";"):
        if not segment.strip() or "=" not in segment:
            continue
        key, value = segment.split("=", 1)
        parts[key.strip().lower()] = value.strip()
    return parts


def _normalize_odbc_bool(value: str | None, default: str) -> str:
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"true", "yes", "y", "1"}:
        return "yes"
    if normalized in {"false", "no", "n", "0"}:
        return "no"

    # Keep valid ODBC 18 encrypt values if already provided.
    if normalized in {"mandatory", "optional", "strict"}:
        return normalized

    return default


def _adonet_to_odbc(raw_connection: str) -> str:
    parts = _parse_connection_string(raw_connection)
    if not parts:
        return raw_connection

    server = parts.get("server") or parts.get("data source")
    database = parts.get("initial catalog") or parts.get("database")
    user = parts.get("user id") or parts.get("uid")
    password = parts.get("password") or parts.get("pwd")

    driver = parts.get("driver", "{ODBC Driver 18 for SQL Server}")
    encrypt = _normalize_odbc_bool(parts.get("encrypt"), default="yes")
    trust_cert = _normalize_odbc_bool(parts.get("trustservercertificate"), default="no")
    timeout = parts.get("connection timeout", "30")

    odbc_parts = [
        f"DRIVER={driver}",
        f"SERVER={server}",
        f"DATABASE={database}",
        f"UID={user}",
        f"PWD={password}",
        f"Encrypt={encrypt}",
        f"TrustServerCertificate={trust_cert}",
        f"Connection Timeout={timeout}",
    ]

    return ";".join(item for item in odbc_parts if not item.endswith("=None")) + ";"


def _build_database_url(raw_connection: str) -> str:
    if not raw_connection:
        raise ValueError("AZURE_SQL_CONNECTION_STRING is required.")

    if raw_connection.startswith(("mssql+pyodbc://", "sqlite:///", "postgresql://")):
        return raw_connection

    odbc_connection = _adonet_to_odbc(raw_connection)
    return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_connection)}"


DATABASE_URL = _build_database_url(settings.azure_sql_connection_string)

engine_kwargs = {
    "pool_pre_ping": True,
    "future": True,
    "pool_recycle": 1800,
    "pool_size": 5,
    "max_overflow": 10,
}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
