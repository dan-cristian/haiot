__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import random

from pydispatch import dispatcher

from main.logger_helper import Log
from common import Constant
from main.admin import models
from relay import gpio_pi_bbb

__pool_pin_codes=[]

#https://learn.adafruit.com/setting-up-io-python-library-on-beaglebone-black/using-the-bbio-library

#IMPORTANT: installing PyBBIO enables all i/o pins as a dtc is installed
#https://github.com/graycatlabs/PyBBIO/wiki
try:
    import Adafruit_BBIO.GPIO as GPIO
    import_module_exist = True
except:
    Log.logger.info('Module Adafruit_BBIO.GPIO is not installed, module will not be initialised')
    import_module_exist = False

def register_gpios():
    global import_module_exist
    #global zone_alarm_list
    zone_alarm_list = models.ZoneAlarm.query.all()
    for zonealarm in zone_alarm_list:
        try:
            gpio_pin = models.GpioPin.query.filter_by(pin_code=zonealarm.gpio_pin_code,
                                                      host_name=Constant.HOST_NAME).first()
            if gpio_pin:
                #record this pin as used to enable clean shutdown
                if gpio_pin.pin_index_bcm != '':
                    gpio_pi_bbb.get_pin_bcm(gpio_pin.pin_index_bcm)
                GPIO.setup(zonealarm.gpio_pin_code, GPIO.IN)
                gpio_pi_bbb.set_pin_edge(gpio_pin.pin_index_bcm, 'both')
                try:
                    GPIO.add_event_detect(zonealarm.gpio_pin_code, GPIO.BOTH)#, callback=event_detected, bouncetime=300)
                    __pool_pin_codes.append(zonealarm.gpio_pin_code)
                    Log.logger.info('OK callback on gpio {} zone {}'.format(zonealarm.gpio_pin_code, zonealarm.zone_id))
                except Exception, ex:
                    Log.logger.warning('Unable to add event callback pin {} zone {}'.format(zonealarm.gpio_pin_code,
                                                                                        zonealarm.zone_id))
                    try:
                        GPIO.add_event_detect(zonealarm.gpio_pin_code, GPIO.FALLING)
                        Log.logger.info('OK pooling on gpio {} err='.format(zonealarm.gpio_pin_code, ex))
                        __pool_pin_codes.append(zonealarm.gpio_pin_code)
                    except Exception, ex:
                        Log.logger.warning('Unable to add pooling on pin {} err={}'.format(zonealarm.gpio_pin_code, ex))


                #Log.logger.info('Testing an input read on this gpio pin')
                #event_detected(zonealarm.gpio_pin_code)
                import_module_exist = True
            else:
                Log.logger.warning('Unable to find gpio for zonealarm pin {}'.format(zonealarm.alarm_pin_name))
        except Exception, ex:
            Log.logger.critical('Unable to setup GPIO {} zone {} err={}'.format(zonealarm.gpio_pin_code,
                                                                      zonealarm.zone_id, ex))

def event_detected(channel):
    try:
        global import_module_exist
        if import_module_exist:
            state = GPIO.input(channel)
        else:
            #FOR TESTING PURPOSES
            state = random.randint(0,2)
        Log.logger.info('IO input detected channel {} status {}'.format(channel, state))
        dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=channel, direction='in', pin_value=state)
    except Exception, ex:
        zonealarm = None
        Log.logger.warning('Error io event detected, err {}'.format(ex))

#check for events on pins not setup with callback event
def __check_for_events():
    global __pool_pin_codes
    for pin_code in __pool_pin_codes:
        if GPIO.event_detected(pin_code):
            state = GPIO.input(pin_code)
            #Log.logger.info('Pooling event detected gpio {} val {}'.format(pin_code, state))
            dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=pin_code, direction='in', pin_value=state)

def init():
    register_gpios()

def thread_run():
    Log.logger.debug('Processing Beaglebone IO')
    global import_module_exist
    if not import_module_exist:
        Log.logger.info('Simulating motion detection for test purposes')
        event_detected('P8_11')
    else:
        __check_for_events()
    return 'Processed bbb_io'