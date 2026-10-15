import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

ADMIN_URL = os.environ.get("HC_TEST_ADMIN_URL", "postgresql://hc:hc@localhost:5432/hc_pms")
TEST_DB = "hc_pms_test"
TEST_URL = ADMIN_URL.rsplit("/", 1)[0] + f"/{TEST_DB}"
os.environ["HC_DATABASE_URL"] = TEST_URL  # must be set before hc_pms.config is imported

from fastapi.testclient import TestClient  # noqa: E402

from hc_pms.load import load  # noqa: E402
from hc_pms.main import app  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
KEY = {"X-HC-ApiKey": "dev-hc-key"}


@pytest.fixture(scope="session", autouse=True)
def test_database() -> Iterator[None]:
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
        conn.execute(f"CREATE DATABASE {TEST_DB}")
    load(TEST_URL, FIXTURES / "universe.csv", FIXTURES, reset=True)
    yield


@pytest.fixture(scope="session")
def client(test_database: None) -> Iterator[TestClient]:
    with TestClient(app) as c:  # runs lifespan → opens the DB pool
        yield c


@pytest.fixture
def db() -> Iterator[psycopg.Connection]:
    with psycopg.connect(TEST_URL) as conn:
        yield conn
