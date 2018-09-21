__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main.logger_helper import L
import threading
import prctl

def thread_run():
    prctl.set_name("")
    threading.current_thread().name = "webui"
    L.l.debug('Processing webui_run')
    return 'Processed webui_run'