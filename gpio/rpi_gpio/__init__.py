import time
from pydispatch import dispatcher
from main.logger_helper import L
from common import Constant
from main import sqlitedb
from gpio import io_common
from storage.model import m
__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


class P:
    initialised = False
    pool_pin_codes = []
    import_module_exist = None

    def __init__(self):
        pass


from common import fix_module
while True:
    try:
        if Constant.is_os_linux():
            import RPi.GPIO as GPIO
            P.import_module_exist = True
        break
    except ImportError as iex:
        if not fix_module(iex):
            break
    except Exception as ex:
        L.l.info('Error importing rpi-gpio, ex={}'.format(ex))
        break


# https://sourceforge.net/p/raspberry-gpio-python/wiki/Checking%20function%20of%20GPIO%20channels/
def __get_pin_function(bcm_id):
    res = GPIO.gpio_function(bcm_id)
    return res


# set gpio pin and return the actual pin state, LOW=0, HIGH=1
# https://sourceforge.net/p/raspberry-gpio-python/wiki/Outputs/
def set_pin_bcm(bcm_id=None, pin_value=None):
    L.l.info('Set rpi.gpio pin {} value {}'.format(bcm_id, pin_value))
    if Constant.debug_dummy: return pin_value
    try:
        # function does not detect well output status
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
    except Exception as ex:
        L.l.error("Error set_pin_bcm: {}".format(ex), exc_info=1)


def get_pin_bcm(bcm_id):
    try:
        res = GPIO.input(bcm_id)
    except RuntimeError as rex:
        L.l.warning('Error reading input rpi.gpio pin {} err={}'.format(bcm_id, rex))
        res = None
        # GPIO.setup(bcm_id, GPIO.OUT)
        # retry read
        # res = GPIO.input(bcm_id)
    return res


def _do_event(channel, state):
    try:
        dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=int(channel), direction='in',
                        pin_value=state, pin_connected=(state == 0))
    except Exception as ex:
        L.l.warning('Error rpi.gpio event detected, err {}'.format(ex))


def _check_event(channel, target_state):
    time.sleep(0.1)
    state = GPIO.input(channel)
    if state != target_state:
        L.l.info("False positive, channel {}, state {}".format(channel, state))
    else:
        _do_event(channel, state)


# https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/,  LOW=0, HIGH=1
def _event_detected_rising(channel):
    L.l.info("Rising event, channel {}, expect state {}".format(channel, GPIO.HIGH))
    _check_event(channel, GPIO.HIGH)


def _event_detected_falling(channel):
    L.l.info("Falling event, channel {},  expect state {}".format(channel, GPIO.LOW))
    _check_event(channel, GPIO.LOW)


def _event_detected_both(channel):
    now_state = GPIO.input(channel)
    L.l.info("Both event, channel {}, now_state={}".format(channel, now_state))
    # time.sleep(0.1)
    new_state = GPIO.input(channel)
    L.l.info("Both event, channel {}, NEW_state={}".format(channel, new_state))
    _do_event(channel, new_state)


def _event_detected_reversed_both(channel):
    now_state = GPIO.input(channel)
    L.l.info("Both event reversed, channel {}, now_state={}".format(channel, now_state))
    # time.sleep(0.1)
    new_state = GPIO.input(channel)
    # reverse state for normal open contacts
    L.l.info("State pin before reverse={}".format(new_state))
    rev_state = int(not new_state)
    L.l.info("State pin {} after reverse={}".format(channel, rev_state))
    _do_event(channel, rev_state)


#  define all ports that are used as read/input, BCM format
#  https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/
def setup_in_ports(gpio_pin_list):
    for gpio_pin in gpio_pin_list:
        if gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_STDGPIO:
            # L.l.info('Set rpi.gpio pincode={} type={} index={} as input'.format(
            #    gpio_pin.pin_code, gpio_pin.pin_type, gpio_pin.pin_index_bcm))
            try:
                # http://razzpisampler.oreilly.com/ch07.html
                # one wire connected to GPIO, another to GROUND. Use relays next to PI for long wires.
                GPIO.setwarnings(False)
                GPIO.setup(int(gpio_pin.pin_index_bcm), GPIO.IN, pull_up_down=GPIO.PUD_UP)  # PUD_DOWN:no contact detection
                GPIO.remove_event_detect(int(gpio_pin.pin_index_bcm))
                # GPIO.add_event_detect(int(gpio_pin.pin_code), GPIO.RISING, callback=_event_detected_rising,
                #                      bouncetime=500)
                # Log.logger.info('Added rising on rpi.gpio'.format(gpio_pin.pin_code))
                # GPIO.add_event_detect(int(gpio_pin.pin_code), GPIO.FALLING, callback=_event_detected_falling,
                #                      bouncetime=500)
                # Log.logger.info('Added falling on rpi.gpio'.format(gpio_pin.pin_code))
                if gpio_pin.contact_type == Constant.CONTACT_TYPE_NO:
                    # L.l.info("Added input with reverse contact (NO) on pin {}".format(gpio_pin))
                    GPIO.add_event_detect(
                        int(gpio_pin.pin_index_bcm), GPIO.BOTH, callback=_event_detected_reversed_both, bouncetime=500)
                    L.l.info('OK callback set on rpi {} pin {}'.format(gpio_pin.pin_code, gpio_pin.pin_index_bcm))
                    _event_detected_reversed_both(int(gpio_pin.pin_index_bcm))
                else:  # for PIR and CONTACT_NC
                    GPIO.add_event_detect(
                        int(gpio_pin.pin_index_bcm), GPIO.BOTH, callback=_event_detected_both, bouncetime=500)
                    L.l.info('OK callback rev set on rpi {} pin {}'.format(gpio_pin.pin_code, gpio_pin.pin_index_bcm))
                    _event_detected_both(int(gpio_pin.pin_index_bcm))
                # L.l.info('OK callback set on rpi.gpio'.format(gpio_pin.pin_code))
            except Exception as ex:
                L.l.critical('Unable to setup rpi.gpio callback pin={} err={}'.format(gpio_pin.pin_index_bcm, ex))
            P.pool_pin_codes.append(gpio_pin.pin_index_bcm)


def post_init_relay_value(gpio_pin_code):
    # avoid GPIO out init as will turn relay on

    # pin_index_bcm = int(gpio_pin_code)
    # GPIO.setup(pin_index_bcm, GPIO.OUT)
    # val = get_pin_bcm(pin_index_bcm)
    # reverse val to have relays off at init
    val = 0  # default off
    # set_pin_bcm(pin_index_bcm, val)
    return val


def post_init_alarm_value(gpio_pin_code):
    pin_index_bcm = int(gpio_pin_code)
    GPIO.setup(int(pin_index_bcm), GPIO.IN, pull_up_down=GPIO.PUD_UP)
    # fixme check pin_connected value
    pin_val = get_pin_bcm(pin_index_bcm)
    if pin_val is not None:
        return pin_val == 1
    else:
        return None


def post_init():
    if P.initialised:
        L.l.info('Running post_init rpi_gpio')
        relays = m.ZoneCustomRelay.find({m.ZoneCustomRelay.gpio_host_name: Constant.HOST_NAME,
                                         m.ZoneCustomRelay.relay_type: Constant.GPIO_PIN_TYPE_PI_STDGPIO})
        for relay in relays:
            L.l.info('Reading gpio pin {}'.format(relay.gpio_pin_code))
            if len(relay.gpio_pin_code) <= 2:  # run this only for gpio bcm pins (piface has longer size)
                pin_index_bcm = int(relay.gpio_pin_code)
                GPIO.setup(pin_index_bcm, GPIO.OUT)
                pin_val = get_pin_bcm(pin_index_bcm)
                io_common.update_custom_relay(pin_code=pin_index_bcm, pin_value=pin_val, notify=True)


def unload():
    for gpio_pin_index_bcm in P.pool_pin_codes:
        if isinstance(gpio_pin_index_bcm, int):
            GPIO.remove_event_detect(gpio_pin_index_bcm)
    time.sleep(0.1)
    GPIO.cleanup()
    P.initialised = False


def init():
    L.l.info('RPI.GPIO module initialising')
    try:
        GPIO.setmode(GPIO.BCM)
        dispatcher.connect(setup_in_ports, signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, sender=dispatcher.Any)
        P.initialised = True
    except Exception as ex:
        L.l.critical('Module rpi.gpio not initialised, err={}'.format(ex))
