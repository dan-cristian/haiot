__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main.logger_helper import L
import threading

def thread_run():
    threading.current_thread().name = "webui"
    L.l.debug('Processing webui_run')
    return 'Processed webui_run'