__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
import time
#https://learn.adafruit.com/setting-up-io-python-library-on-beaglebone-black/using-the-bbio-library
import Adafruit_BBIO.GPIO as GPIO

def register_gpios():
    GPIO.add_event_detect('P8_11', GPIO.FALLING)

def check_for_events():
    if GPIO.event_detected('P8_11'):
        logging.info('Event detected {}'.format(GPIO.input('P8_11')))

def init():
    register_gpios()

def thread_run():
    logging.info('Processing Beaglebone IO')
    check_for_events()
    return 'Processed bbb_io'