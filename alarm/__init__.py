__author__ = 'dcristian'
import alarm_loop
from main.admin import thread_pool

def init():
    print "Alarm module initialising"
    alarm_loop.init()
    thread_pool.add_callable(alarm_loop.thread_run)

if __name__ == '__main__':
    init()