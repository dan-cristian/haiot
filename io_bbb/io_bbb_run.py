__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
import datetime
import random
import sys
import time
from main import db
from main.admin import models
#https://learn.adafruit.com/setting-up-io-python-library-on-beaglebone-black/using-the-bbio-library
try:
    import Adafruit_BBIO.GPIO as GPIO
except:
    logging.critical('Module Adafruit_BBIO.GPIO is not installed, module will not be initialised')

import_module_psutil_exist = False

def register_gpios():
    global import_module_psutil_exist
    #global zone_alarm_list
    zone_alarm_list = models.ZoneAlarm.query.all()
    for zonealarm in zone_alarm_list:
        try:
            GPIO.setup(zonealarm.gpio_pin_code, GPIO.IN)
            GPIO.add_event_detect(zonealarm.gpio_pin_code, GPIO.BOTH, callback=event_detected, bouncetime=300)
            logging.info('Enabled alarm on gpio {} zone {}'.format(zonealarm.gpio_pin_code, zonealarm.zone_id))
            import_module_exist = True
        except Exception, ex:
            logging.critical('Unable to setup GPIO {} zone {} '.format(zonealarm.gpio_pin_code,
                                                                      zonealarm.zone_id))

def event_detected(channel):
    try:
        zonealarm=models.ZoneAlarm.query.filter_by(gpio_pin_code=channel).first()
        global import_module_psutil_exist
        if import_module_exist:
            state = GPIO.input(zonealarm.gpio_pin_code)
        else:
            state = random.randint(0,2)
        zonealarm.alarm_status = state
        zonealarm.updated_on = datetime.datetime.now()
        zonealarm.notify_enabled_ = True
        time.sleep(1)
        db.session.commit()
        logging.info('Event detected zone {} channel {} status {}'.format(zonealarm.zone_id, channel, state))
    except Exception, ex:
        zonealarm = None
        logging.warning('Error alarm status save, err {}'.format(ex))


def check_for_events():
    global zone_alarm_list
    for zonealarm in zone_alarm_list:
        if GPIO.event_detected(zonealarm.gpio_pin_code):
            state = GPIO.input(zonealarm.gpio_pin_code)
            logging.info('Event detected gpio {} zone {}'.format(state, zonealarm.zone_id))

def init():
    register_gpios()

def thread_run():
    logging.debug('Processing Beaglebone IO')
    global import_module_psutil_exist
    if not import_module_exist:
        logging.info('Simulating motion detection for test purposes')
        event_detected('P8_11')
    return 'Processed bbb_io'