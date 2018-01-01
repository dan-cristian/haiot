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
from main.logger_helper import L
from main.admin import model_helper
from common import Constant

initialised = False
__observer = None

if __inotify_import_ok:
    class EventHandler(FileSystemEventHandler):
        def on_any_event(self, event):
            #Log.logger.info('File event={}'.format(event))
            dispatcher.send(Constant.SIGNAL_FILE_WATCH, event=event.event_type, file=event.src_path,
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


def unload():
    global __observer, initialised, __inotify_import_ok
    initialised = False

def init():
    global __observer, initialised, __inotify_import_ok
    if __inotify_import_ok:
        path = model_helper.get_param(Constant.P_MOTION_VIDEO_PATH)
        L.l.info('Initialising file watchdog for folder={}'.format(path))
        if os.path.exists(path):
            event_handler = EventHandler()
            __observer = Observer()
            __observer.schedule(event_handler, path, recursive=True)
            initialised = True
            __observer.start()
        else:
            L.l.warning('Filewatch not initialised watch path={} not found'.format(path))
    else:
        L.l.info('Inotify observer not available,  not initialising file watch')