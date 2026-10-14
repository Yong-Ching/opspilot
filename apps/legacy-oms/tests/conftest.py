import os
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import psycopg
import pytest

ADMIN_URL = os.environ.get("ACME_TEST_ADMIN_URL", "postgresql://acme:acme@localhost:5432/acme_oms")
TEST_DB = "acme_oms_test"
TEST_URL = ADMIN_URL.rsplit("/", 1)[0] + f"/{TEST_DB}"
os.environ["ACME_DATABASE_URL"] = TEST_URL  # must be set before acme_oms.config is imported

from fastapi.testclient import TestClient  # noqa: E402

from acme_oms.load import load  # noqa: E402
from acme_oms.main import app  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "olist"
KEY = {"X-Acme-Key": "dev-acme-key"}


@pytest.fixture(scope="session", autouse=True)
def test_database() -> Iterator[None]:
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {TEST_DB}")
    load(TEST_URL, FIXTURES, reset=True, shift_to=date(2026, 10, 10))
    yield


@pytest.fixture(scope="session")
def client(test_database: None) -> Iterator[TestClient]:
    with TestClient(app) as c:  # runs lifespan → opens the DB pool
        yield c


@pytest.fixture
def db() -> Iterator[psycopg.Connection]:
    with psycopg.connect(TEST_URL) as conn:
        yield conn
