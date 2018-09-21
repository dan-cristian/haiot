from main.logger_helper import L
import threading
import prctl

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


def thread_run():
    prctl.set_name("")
    threading.current_thread().name = ""
    L.l.debug('Processing template_run')
    return 'Processed template_run'
