__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main.logger_helper import L
from main import thread_pool
import prctl
import threading
from music import mpd


class P:
    initialised = False

    def __init__(self):
        pass


def thread_run():
    prctl.set_name("music")
    threading.current_thread().name = "music"
    mpd.thread_run()
    L.l.debug('Processing music_run')
    return 'Processed music_run'


def unload():
    L.l.info('Music module unloading')
    # ...
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Music module initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=60)
    mpd.init()
    P.initialised = True
