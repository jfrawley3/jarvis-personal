import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_USER_ID", "12345")


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Give every test its own SQLite file so connections don't share state.

    Must patch database.DATABASE_PATH directly — `from config import` creates
    a local binding that doesn't update when config.DATABASE_PATH changes.
    """
    import config
    import database

    db_file = str(tmp_path / "test.db")
    config.DATABASE_PATH = db_file
    database.DATABASE_PATH = db_file

    database.init_db()
    yield
