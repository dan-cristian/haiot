__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

from main import logger
import datetime
import random
import sys
import time
from main import db
from common import constant
from main.admin import models
from pydispatch import dispatcher

#https://learn.adafruit.com/setting-up-io-python-library-on-beaglebone-black/using-the-bbio-library
try:
    import Adafruit_BBIO.GPIO as GPIO
    import_module_exist = True
except:
    logger.info('Module Adafruit_BBIO.GPIO is not installed, module will not be initialised')
    import_module_exist = False

def register_gpios():
    global import_module_exist
    #global zone_alarm_list
    zone_alarm_list = models.ZoneAlarm.query.all()
    for zonealarm in zone_alarm_list:
        try:
            GPIO.setup(zonealarm.gpio_pin_code, GPIO.IN)
            GPIO.add_event_detect(zonealarm.gpio_pin_code, GPIO.BOTH, callback=event_detected, bouncetime=300)
            logger.info('Enabled alarm on gpio {} zone {}'.format(zonealarm.gpio_pin_code, zonealarm.zone_id))
            import_module_exist = True
        except Exception, ex:
            logger.critical('Unable to setup GPIO {} zone {} err={}'.format(zonealarm.gpio_pin_code,
                                                                      zonealarm.zone_id, ex))

def event_detected(channel):
    try:
        global import_module_exist
        if import_module_exist:
            state = GPIO.input(channel)
        else:
            #FOR TESTING PURPOSES
            state = random.randint(0,2)
        logger.info('IO input detected channel {} status {}'.format(channel, state))
        dispatcher.send(constant.SIGNAL_GPIO, gpio_pin_code=channel, direction='in', pin_value=state)
    except Exception, ex:
        zonealarm = None
        logger.warning('Error io event detected, err {}'.format(ex))


def check_for_events():
    global zone_alarm_list
    for zonealarm in zone_alarm_list:
        if GPIO.event_detected(zonealarm.gpio_pin_code):
            state = GPIO.input(zonealarm.gpio_pin_code)
            logger.info('Event detected gpio {} zone {}'.format(state, zonealarm.zone_id))

def init():
    register_gpios()

def thread_run():
    logger.debug('Processing Beaglebone IO')
    global import_module_exist
    if not import_module_exist:
        logger.info('Simulating motion detection for test purposes')
        event_detected('P8_11')
    return 'Processed bbb_io'