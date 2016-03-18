from pydispatch import dispatcher
from main import thread_pool
from main.logger_helper import Log
from common import Constant

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

initialised = False
__pool_pin_codes = []

try:
    import RPi.GPIO as GPIO
    import_module_exist = True
except:
    Log.logger.info('Module RPI.GPIO is not installed, module will not be initialised')
    import_module_exist = False


# https://sourceforge.net/p/raspberry-gpio-python/wiki/Checking%20function%20of%20GPIO%20channels/
def __get_pin_function(bcm_id=''):
    res = GPIO.gpio_function(bcm_id)
    return res


# set gpio pin and return the actual pin state, LOW=0, HIGH=1
# https://sourceforge.net/p/raspberry-gpio-python/wiki/Outputs/
def set_pin_bcm(bcm_id=None, pin_value=None):
    if __get_pin_function(bcm_id) != GPIO.OUT:
        GPIO.setup(bcm_id, GPIO.OUT)

    if __get_pin_function(bcm_id) == GPIO.OUT:
        GPIO.output(bcm_id, pin_value)
    else:
        Log.logger.warning('Unable to setup pin {} as OUT '.format(bcm_id))


def get_pin_bcm(bcm_id=''):
    if __get_pin_function(bcm_id) != GPIO.IN:
        Log.logger.warning('Trying to read a pin {} not set as IN'.format(bcm_id))
        res = -1
    else:
        res = GPIO.input(bcm_id)


#  https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/
def event_detected(channel):
    try:
        global import_module_exist
        if import_module_exist:
            state = GPIO.input(channel)
        Log.logger.info('IO input detected channel {} status {}'.format(channel, state))
        dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=channel, direction='in',
                        pin_value=state, pin_connected=(state == 0))
    except Exception, ex:
        zonealarm = None
        Log.logger.warning('Error io event detected, err {}'.format(ex))


#  define all ports that are used as read/input, BCM format
def setup_in_ports(gpio_pin_list):
    for gpio_pin in gpio_pin_list:
        if gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_STDGPIO:
            Log.logger.info('Set pincode={} type={} index={} as input'.format(gpio_pin.pin_code, gpio_pin.pin_type,
                                                                              gpio_pin.pin_index_bcm))
            GPIO.setup(gpio_pin.pin_code, GPIO.IN)
            try:
                GPIO.add_event_detect(gpio_pin.pin_code, GPIO.BOTH, callback=event_detected, bouncetime=300)
                __pool_pin_codes.append(gpio_pin.pin_code)
                Log.logger.info('OK callback on gpio'.format(gpio_pin.pin_code))
            except Exception, ex:
                Log.logger.warning('Unable to add event callback pin={} err={}'.format(gpio_pin.pin_code, ex))


def thread_run():
    global initialised
    if initialised:
        Log.logger.debug('Processing RPI.GPIO')
        global import_module_exist
        if not import_module_exist:
            Log.logger.info('Simulating motion detection for test purposes')
            event_detected('P8_11')
        #else:
        #    __check_for_events()
        return 'Processed rpi.gpio'


def unload():
    # todo: remove callbacks
    thread_pool.remove_callable(thread_run)
    global initialised
    initialised = False


def init():
    Log.logger.info('RPI.GPIO module initialising')
    try:
        GPIO.setmode(GPIO.BCM)
        dispatcher.connect(setup_in_ports, signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, sender=dispatcher.Any)
        thread_pool.add_interval_callable(thread_run, run_interval_second=10)
        global initialised
        initialised = True
    except Exception, ex:
        Log.logger.critical('Module rpi.gpio not initialised, err={}'.format(ex))
