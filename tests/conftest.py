"""Shared fixtures."""
import sys
from pathlib import Path

# Make `from src.* import ...` work without requiring PYTHONPATH=. on the CLI.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from src.whale_watching.database import WhaleDatabase


@pytest.fixture
def db(tmp_path):
    """Fresh SQLite DB per test."""
    path = tmp_path / "test_whales.db"
    inst = WhaleDatabase(str(path))
    yield inst
    inst.close()
