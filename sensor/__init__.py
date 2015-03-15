__author__ = 'dcristian'

#! venv/bin/python


import threading
import datetime
import signal
import sys

from owsensor import loop_read, SensorOw

def init():
    print "Sensor module initialising"
    thread_list = []
    def signal_handler(signal, frame):
            print('You pressed Ctrl+C!')
            sys.exit(0)

    print ('Entering runserver, debug= ' + str(sys.flags.debug))

    if len(thread_list)==0:
        t=threading.Thread(target=loop_read)
        #t.name="Thread at " + str(datetime.datetime.now())
        t.daemon = True
        thread_list.append(t)
        t.start()

    else:
        print("Ignoring another entry in main program, len="+str(len(thread_list)))

    signal.signal(signal.SIGINT, signal_handler)


if __name__ == '__main__':
    init()