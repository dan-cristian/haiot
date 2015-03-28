__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
import time
import Adafruit_BBIO.GPIO as GPIO

def register_gpios():
    GPIO.add_event_detect("P8_08", GPIO.FALLING)

def check_for_events():
    if GPIO.event_detected("P8_08"):
        print "event detected!"

def thread_run():
    logging.debug('Processing Beaglebone IO')
    return 'Processed bbb_io'