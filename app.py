import logging.config
from messagebus import create_app


app = create_app()
logger = logging.getLogger('MBus')


@app.teardown_request
def remove_session(exception=None):
    db_session = g.pop('db_session', None)
    if db_session is not None:
        db_session.remove()
