__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main.logger_helper import L
import threading


def thread_run():
    threading.current_thread().name = "music"
    L.l.debug('Processing music_run')
    return 'Processed music_run'
