import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.extensions import db
from app.services.seed_service import seed_demo_data


@pytest.fixture()
def app(tmp_path):
    app = create_app("testing")
    app.config.update(
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
        REPORT_FOLDER=str(tmp_path / "reports"),
    )

    with app.app_context():
        db.create_all()
        seed_demo_data()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


def login(client, username, password="demo123"):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
