__author__ = 'dcristian'

import heat_loop
from main.admin import thread_pool

def init():
    print "Heat module initialising"
    thread_pool.add_callable(heat_loop.main)

def unload():
    pass

if __name__ == '__main__':
    init()