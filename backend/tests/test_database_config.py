from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.settings.config import Settings


def test_cloudbase_mysql_fields_build_safe_sqlalchemy_url() -> None:
    settings = Settings(
        app_env="production",
        db_host="10.0.0.8",
        db_port=3306,
        db_user="root",
        db_password="special@:/#password",
        db_name="flask_demo",
    )

    url = make_url(settings.sqlalchemy_url_string())
    assert url.drivername == "mysql+pymysql"
    assert url.host == "10.0.0.8"
    assert url.port == 3306
    assert url.username == "root"
    assert url.password == "special@:/#password"
    assert url.database == "flask_demo"
    assert url.query["charset"] == "utf8mb4"


def test_production_rejects_sqlite_fallback() -> None:
    with pytest.raises(ValueError, match="生产环境必须配置 CloudBase MySQL"):
        Settings(app_env="production", database_url="sqlite:///./change_radar.db")


def test_partial_cloudbase_mysql_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="DB_PASSWORD"):
        Settings(db_host="10.0.0.8", db_user="root", db_name="flask_demo")


def test_initial_migration_compiles_for_mysql(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DB_HOST", "10.0.0.8")
    monkeypatch.setenv("DB_PORT", "3306")
    monkeypatch.setenv("DB_USER", "root")
    monkeypatch.setenv("DB_PASSWORD", "not-a-real-password")
    monkeypatch.setenv("DB_NAME", "flask_demo")

    alembic_config = Config(str(backend_dir / "alembic.ini"))
    command.upgrade(alembic_config, "head", sql=True)
    sql = capsys.readouterr().out

    assert "CREATE TABLE security_master" in sql
    assert "CREATE TABLE anomaly_event" in sql
    assert "CREATE TABLE watchlist" in sql
    assert "CREATE TABLE alert_setting" in sql
    assert "DEFAULT (CURRENT_TIMESTAMP)" not in sql
    assert "DEFAULT CURRENT_TIMESTAMP" in sql
