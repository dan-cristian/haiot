from pydispatch import dispatcher
from main import thread_pool
from main.logger_helper import L
from common import Constant
import time

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False
__pool_pin_codes = []

try:
    import RPi.GPIO as GPIO
    import_module_exist = True
except ImportError:
    L.l.info('Module RPI.GPIO is not installed, module will not be initialised')
    import_module_exist = False


# https://sourceforge.net/p/raspberry-gpio-python/wiki/Checking%20function%20of%20GPIO%20channels/
def __get_pin_function(bcm_id):
    res = GPIO.gpio_function(bcm_id)
    return res


# set gpio pin and return the actual pin state, LOW=0, HIGH=1
# https://sourceforge.net/p/raspberry-gpio-python/wiki/Outputs/
def set_pin_bcm(bcm_id=None, pin_value=None):
    L.l.info('Set rpi.gpio pin {} value {} function {}'.format(bcm_id, pin_value, __get_pin_function(bcm_id)))
    try:
        # if __get_pin_function(bcm_id) != GPIO.OUT:
        GPIO.setup(bcm_id, GPIO.OUT)
        if __get_pin_function(bcm_id) in {GPIO.OUT}:
            GPIO.output(bcm_id, pin_value)
            set_val = get_pin_bcm(bcm_id)
            if set_val != pin_value:
                L.l.critical('Rpi.gpio out value not OK, is {} but need {}'.format(bcm_id, set_val, pin_value))
            return set_val
        else:
            L.l.warning('Unable to setup rpi.gpio pin {} as OUT '.format(bcm_id))
    except Exception, ex:
        L.l.error("Error set_pin_bcm: {}".format(ex), exc_info=1)


def get_pin_bcm(bcm_id):
    try:
        res = GPIO.input(bcm_id)
    except RuntimeError, rex:
        L.l.warning('Error reading input rpi.gpio pin {} err={}. Setting as OUT and retry.'.format(bcm_id, rex))
        GPIO.setup(bcm_id, GPIO.OUT)
        # retry read
        res = GPIO.input(bcm_id)
    return res


def _do_event(channel, state):
    try:
        global import_module_exist
        if import_module_exist:
            state = GPIO.input(channel)
            L.l.debug('Event rpi.gpio input detected channel={} state={}'.format(channel, state))
            dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=channel, direction='in',
                            pin_value=state, pin_connected=(state == 0))
    except Exception, ex:
        L.l.warning('Error rpi.gpio event detected, err {}'.format(ex))


def _check_event(channel, target_state):
    time.sleep(0.1)
    state = GPIO.input(channel)
    if state != target_state:
        L.l.info("False positive, channel {}, state {}".format(channel, state))
    else:
        _do_event(channel, state)


#  https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/,  LOW=0, HIGH=1
def _event_detected_rising(channel):
    L.l.info("Rising event, channel {}, expect state {}".format(channel, GPIO.HIGH))
    _check_event(channel, GPIO.HIGH)


def _event_detected_falling(channel):
    L.l.info("Falling event, channel {},  expect state {}".format(channel, GPIO.LOW))
    _check_event(channel, GPIO.LOW)


def _event_detected_both(channel):
    now_state = GPIO.input(channel)
    #L.l.info("Both event, channel {}, now_state={}".format(channel, now_state))
    time.sleep(0.1)
    new_state = GPIO.input(channel)
    #L.l.info("Both event, channel {}, NEW_state={}".format(channel, new_state))
    _do_event(channel, new_state)


#  define all ports that are used as read/input, BCM format
#  https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/
def setup_in_ports(gpio_pin_list):
    for gpio_pin in gpio_pin_list:
        if gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_STDGPIO:
            L.l.info('Set rpi.gpio pincode={} type={} index={} as input'.format(
                gpio_pin.pin_code, gpio_pin.pin_type, gpio_pin.pin_index_bcm))
            try:
                # http://razzpisampler.oreilly.com/ch07.html
                GPIO.setup(int(gpio_pin.pin_code), GPIO.IN, pull_up_down=GPIO.PUD_UP)  # PUD_DOWN:no contact detection
                GPIO.remove_event_detect(int(gpio_pin.pin_code))
                # GPIO.add_event_detect(int(gpio_pin.pin_code), GPIO.RISING, callback=_event_detected_rising,
                #                      bouncetime=500)
                # Log.logger.info('Added rising on rpi.gpio'.format(gpio_pin.pin_code))
                # GPIO.add_event_detect(int(gpio_pin.pin_code), GPIO.FALLING, callback=_event_detected_falling,
                #                      bouncetime=500)
                # Log.logger.info('Added falling on rpi.gpio'.format(gpio_pin.pin_code))
                GPIO.add_event_detect(int(gpio_pin.pin_code), GPIO.BOTH, callback=_event_detected_both, bouncetime=500)
                L.l.info('OK callback set on rpi.gpio'.format(gpio_pin.pin_code))
            except Exception, ex:
                L.l.critical('Unable to setup rpi.gpio callback pin={} err={}'.format(gpio_pin.pin_code, ex))
            __pool_pin_codes.append(gpio_pin.pin_code)


def thread_run():
    pass


def unload():
    for gpio_pin in __pool_pin_codes:
        if isinstance(gpio_pin, int):
            GPIO.remove_event_detect(gpio_pin)
    time.sleep(1)
    GPIO.cleanup()
    thread_pool.remove_callable(thread_run)
    global initialised
    initialised = False


def init():
    L.l.debug('RPI.GPIO module initialising')
    try:
        GPIO.setmode(GPIO.BCM)
        dispatcher.connect(setup_in_ports, signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, sender=dispatcher.Any)
        thread_pool.add_interval_callable(thread_run, run_interval_second=10)
        global initialised
        initialised = True
    except Exception, ex:
        L.l.critical('Module rpi.gpio not initialised, err={}'.format(ex))
