import logging.config
from messagebus import create_app, MessageBus
from messagebus.mbc import ConnectorFactory
from flask import jsonify, g
from werkzeug.exceptions import HTTPException
import uuid
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import yaml

app = create_app()
logger = logging.getLogger('MBus')

class ConfigChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("messagebus.yaml"):
            logger.info("Config file modified, reloading...")
            with open('conf/messagebus.yaml', 'r') as f:
                config = yaml.safe_load(f)
                app.config.update(config)


def start_watching():
    event_handler = ConfigChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path='conf/', recursive=False)
    observer.start()
    return observer

@app.before_request
def generate_g():
    g.uuid = uuid.uuid4()
    g.mbus = MessageBus()
    channels = app.config.get("channels")
    for channel in channels["inuse"]:
        conf = channels[channel]["default"]
        conn = ConnectorFactory.get_connector(channel, **conf)
        g.mbus.register_connector(conn)

@app.teardown_request
def remove_session(exception=None):
    db_session = g.pop('db_session', None)
    if db_session is not None:
        db_session.remove()


@app.errorhandler(Exception)
def handle_exception(e):
    # 如果是HTTP异常，获取状态码和描述信息
    if isinstance(e, HTTPException):
        response = e.get_response()
        response.data = jsonify({
            "error": e.name,
            "description": e.description
        }).data
        response.content_type = "application/json"
        return response
    # 对于非HTTP异常，返回500状态码
    else:
        return jsonify({
            "error": "Internal Server Error",
            "description": "An unexpected error occurred."
        }), 500


if __name__ == '__main__':
    watcher = start_watching()
    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        watcher.stop()
    watcher.join()
