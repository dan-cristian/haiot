__author__ = 'dcristian'
import alarm_loop
from main.admin import thread_pool

initialised=False

def init():
    print "Alarm module initialising"
    alarm_loop.init()
    thread_pool.add_callable(alarm_loop.thread_run)
    global initialised
    initialised = True

if __name__ == '__main__':
    init()