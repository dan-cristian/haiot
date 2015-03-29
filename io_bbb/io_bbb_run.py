__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import logging
import time
from main import db
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
        try:
            GPIO.setup(zonealarm.gpio_pin_code, GPIO.IN)
            GPIO.add_event_detect(zonealarm.gpio_pin_code, GPIO.BOTH, callback=event_detected, bouncetime=300)
            logging.info('Enabled alarm on gpio {} zone {}'.format(zonealarm.gpio_pin_code, zonealarm.zone.name))
        except Exception, ex:
            logging.critical('Unable to setup GPIO {} zone {}'.format(zonealarm.gpio_pin_code, zonealarm.zone.name))

def event_detected(channel):
    zonealarm=models.ZoneAlarm.query.filter_by(gpio_pin_code=channel).all()
    if len(zonealarm)==1:
        state = GPIO.input(zonealarm[0].gpio_pin_code)
        zonealarm[0].alarm_status = state
        zonealarm[0].notify_enabled_ = True
        db.session.commit()
        logging.info('Event detected zone {} channel {} status {}'.format(zonealarm[0].zone.name, channel, state))
    else:
        logging.warning('Multiple zones defined with same gpio code {}'.format(channel))

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
    #check_for_events()
    return 'Processed bbb_io'