__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

import random
import threading
from pydispatch import dispatcher
from main import thread_pool
from main.logger_helper import L
from common import Constant
from main.admin import models
from gpio import std_gpio

initialised = False
__pool_pin_codes = []

# https://learn.adafruit.com/setting-up-io-python-library-on-beaglebone-black/using-the-bbio-library
# IMPORTANT: installing PyBBIO enables all i/o pins as a dtc is installed
# https://github.com/graycatlabs/PyBBIO/wiki
try:
    import Adafruit_BBIO.GPIO as GPIO

    import_module_exist = True
except:
    L.l.info('Module Adafruit_BBIO.GPIO is not installed, module will not be initialised')
    import_module_exist = False


def event_detected(channel):
    try:
        global import_module_exist
        if import_module_exist:
            state = GPIO.input(channel)
        else:
            # FOR TESTING PURPOSES
            state = random.randint(0, 2)
        L.l.info('IO input detected channel {} status {}'.format(channel, state))
        dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=channel, direction='in',
                        pin_value=state, pin_connected=(state == 0))
    except Exception, ex:
        zonealarm = None
        L.l.warning('Error io event detected, err {}'.format(ex))


# check for events on pins not setup with callback event
def __check_for_events():
    global __pool_pin_codes
    for pin_code in __pool_pin_codes:
        if GPIO.event_detected(pin_code):
            state = GPIO.input(pin_code)
            # Log.logger.info('Pooling event detected gpio {} val {}'.format(pin_code, state))
            dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=pin_code, direction='in',
                            pin_value=state, pin_connected=(state == 0))


def setup_in_ports(gpio_pin_list):
    for gpio_pin in gpio_pin_list:
        if gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_BBB:
            L.l.info('Set pincode={} type={} index={} as input'.format(gpio_pin.pin_code, gpio_pin.pin_type,
                                                                       gpio_pin.pin_index_bcm))
            GPIO.setup(gpio_pin.pin_code, GPIO.IN)
            std_gpio.set_pin_edge(gpio_pin.pin_index_bcm, 'both')
            try:
                GPIO.add_event_detect(gpio_pin.pin_code, GPIO.BOTH)  # , callback=event_detected, bouncetime=300)
                __pool_pin_codes.append(gpio_pin.pin_code)
                L.l.info('OK callback on gpio'.format(gpio_pin.pin_code))
            except Exception, ex:
                L.l.warning('Unable to add event callback pin={} err={}'.format(gpio_pin.pin_code, ex))
                try:
                    GPIO.add_event_detect(gpio_pin.pin_code, GPIO.FALLING)
                    L.l.info('OK pooling on gpio {} err='.format(gpio_pin.pin_code, ex))
                    __pool_pin_codes.append(gpio_pin.pin_code)
                except Exception, ex:
                    L.l.warning('Unable to add pooling on pin {} err={}'.format(gpio_pin.pin_code, ex))


def thread_run():
    threading.current_thread().name = "bbbio"
    global initialised
    if initialised:
        L.l.debug('Processing Beaglebone IO')
        global import_module_exist
        if not import_module_exist:
            L.l.info('Simulating motion detection for test purposes')
            event_detected('P8_11')
        else:
            __check_for_events()
        return 'Processed bbb_io'


def unload():
    # ...
    thread_pool.remove_callable(thread_run)
    global initialised
    initialised = False


def init():
    L.l.info('Beaglebone IO module initialising')
    try:
        dispatcher.connect(setup_in_ports, signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, sender=dispatcher.Any)
        thread_pool.add_interval_callable(thread_run, run_interval_second=10)
        global initialised
        initialised = True
    except Exception, ex:
        L.l.critical('Module io_bbb not initialised, err={}'.format(ex))
