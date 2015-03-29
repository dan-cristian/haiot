__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
import datetime
import random
import sys
from main import dbcommit, dbadd, dbbegin
from main.admin import models
#https://learn.adafruit.com/setting-up-io-python-library-on-beaglebone-black/using-the-bbio-library
try:
    import Adafruit_BBIO.GPIO as GPIO
    import_module_exist = True
except:
    logging.critical('Module Adafruit_BBIO.GPIO is not installed, module will not be initialised')

import_module_exist = False

def register_gpios():
    #global zone_alarm_list
    zone_alarm_list = models.ZoneAlarm.query.all()
    for zonealarm in zone_alarm_list:
        try:
            GPIO.setup(zonealarm.gpio_pin_code, GPIO.IN)
            GPIO.add_event_detect(zonealarm.gpio_pin_code, GPIO.BOTH, callback=event_detected, bouncetime=300)
            logging.info('Enabled alarm on gpio {} zone {}'.format(zonealarm.gpio_pin_code, zonealarm.zone.name))
        except Exception, ex:
            logging.critical('Unable to setup GPIO {} zone {} '.format(zonealarm.gpio_pin_code,
                                                                      zonealarm.zone.name))

def event_detected(channel):
    try:
        zonealarm=models.ZoneAlarm.query.filter_by(gpio_pin_code=channel).first()
        global import_module_exist
        if import_module_exist:
            state = GPIO.input(zonealarm.gpio_pin_code)
            zonealarm.alarm_status = state
        else:
            state = random.randint(0,2)
        zonealarm.updated_on = datetime.datetime.now()
        zonealarm.notify_enabled_ = True
        dbcommit()
        logging.info('Event detected zone {} channel {} status {}'.format(zonealarm.zone.name, channel, state))
    except Exception, ex:
        logging.warning('Error alarm status save, err {}'.format(ex))


def check_for_events():
    global zone_alarm_list
    for zonealarm in zone_alarm_list:
        if GPIO.event_detected(zonealarm.gpio_pin_code):
            state = GPIO.input(zonealarm.gpio_pin_code)
            logging.info('Event detected gpio {} zone {}'.format(state, zonealarm.zone.name))

def init():
    register_gpios()

def thread_run():
    logging.debug('Processing Beaglebone IO')
    global import_module_exist
    if not import_module_exist:
        event_detected('P8_11')
    return 'Processed bbb_io'