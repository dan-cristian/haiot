__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import sys
import time
import os
try:
    from watchdog.observers import Observer
    from watchdog.events import LoggingEventHandler, FileSystemEventHandler
    __inotify_import_ok = True
except Exception, ex:
    __inotify_import_ok = False
from pydispatch import dispatcher
from main import logger
from main.admin import model_helper
from common import constant

initialised = False
__observer = None

class EventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        #logger.info('File event={}'.format(event))
        dispatcher.send(constant.SIGNAL_FILE_WATCH, event=event.event_type, file=event.src_path,
                        is_directory=event.is_directory)
        #print event
    def on_created(self, event):
        pass
    def on_modified(self, event):
        pass
    def on_deleted(self, event):
        pass
    def on_moved(self, event):
        pass

if __name__ == "__main__":
    #logging.basicConfig(level=logging.INFO,format='%(asctime)s - %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    event_handler = EventHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def unload():
    global __observer, initialised
    observer.stop()
    observer.join()
    initialised = False

def init():
    global __observer, initialised, __inotify_import_ok
    if __inotify_import_ok:
        path = model_helper.get_param(constant.P_MOTION_VIDEO_PATH)
        logger.info('Initialising file watchdog for folder={}'.format(path))
        if os.path.exists(path):
            event_handler = EventHandler()
            __observer = Observer()
            __observer.schedule(event_handler, path, recursive=True)
            initialised = True
            __observer.start()
        else:
            logger.warning('Filewatch not initialised watch path={} not found'.format(path))
    else:
        logger.info('Inotify observer not available,  not initialising file watch')