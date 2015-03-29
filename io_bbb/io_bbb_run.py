__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
import time
from main.admin import models
#https://learn.adafruit.com/setting-up-io-python-library-on-beaglebone-black/using-the-bbio-library
try:
    import Adafruit_BBIO.GPIO as GPIO
except:
    logging.critical('Module Adafruit_BBIO.GPIO is not installed, module will not be initialised')

zone_alarm_list = None

def register_gpios():
    global zone_alarm_list
    zone_alarm_list = models.ZoneAlarm.query.all()
    for zonealarm in zone_alarm_list:
        logging.info('Enabling alarm on gpio {} zone {}'.format(zonealarm.gpio_pin_code, zonealarm.zone.name))
        try:
            GPIO.setup(zonealarm.gpio_pin_code, GPIO.IN)
            GPIO.add_event_detect(zonealarm.gpio_pin_code, GPIO.FALLING, callback=event_detected, bouncetime=300)
        except Exception, ex:
            logging.critical('Unable to setup GPIO {} zone {}'.format(zonealarm.gpio_pin_code, zonealarm.zone.name))

def event_detected(channel):
    logging.info('Event detected channel {}'.format(channel))

def check_for_events():
    global zone_alarm_list
    for zonealarm in zone_alarm_list:
        if GPIO.event_detected(zonealarm.gpio_pin_code):
            state = GPIO.input(zonealarm.gpio_pin_code)
            logging.info('Event detected gpio {} zone {}'.format(state, zonealarm.zone.name))

def init():
    register_gpios()

def thread_run():
    logging.info('Processing Beaglebone IO')
    #check_for_events()
    return 'Processed bbb_io'