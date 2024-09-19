import logging
import logging.config
from messagebus import create_app
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import yaml

app = create_app(__name__)
logger = logging.getLogger('MBus')


class ConfigChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("messagebus.yaml"):
            logger.info("Config file modified, reloading...")
            with open('conf/messagebus.yaml', 'r', encoding="utf-8") as f:
                config = yaml.safe_load(f)
                app.config.update(config)

        if event.src_path.endswith("logging.yaml"):
            with open('conf/logging.yaml', 'r', encoding="utf-8") as f:
                log_config = yaml.safe_load(f)
                logging.config.dictConfig(log_config)


def start_watching():
    event_handler = ConfigChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path='conf/', recursive=False)
    observer.start()
    return observer


if __name__ == "__main__":
    logger.debug(app.url_map)
    watcher = start_watching()
    try:
        app.run(debug=False, host="0.0.0.0")
    except KeyboardInterrupt:
        watcher.stop()
    watcher.join()
