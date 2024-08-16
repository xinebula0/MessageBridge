from flask import Flask, g
from components.database import SessionLocal


app = Flask(__name__)


@app.before_request
def create_session():
    g.db_session = SessionLocal()


@app.teardown_request
def remove_session(exception=None):
    db_session = g.pop('db_session', None)
    if db_session is not None:
        db_session.remove()
