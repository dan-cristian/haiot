from main.logger_helper import L
from main.admin import models
from common import Constant
from gpio import io_common


class P:
    pcf = None
    i2c_port_num = 1
    pcf_address = 0x24
    import_module_exist = None
    initialised = False

    def __init__(self):
        pass


try:
    from pcf8574 import PCF8574
    P.import_module_exist = True
except ImportError:
    L.l.info('Module PCF8574 is not installed, module will not be initialised')


def _not_initialised(message):
    L.l.error('Module PCF8574 is not initialised for {}'.format(message))
    return None


def get_pin(pin_index):
    if P.initialised:
        if pin_index in range(0, 8):
            L.l.info('Getting pcf pin {}'.format(pin_index))
            return P.pcf.port[pin_index]
        else:
            L.l.error('PCF pin index must be between 0 and 7, unexpected val {}'.format(pin_index))
            return None
    else:
        return _not_initialised('get_pin')


def set_pin_value(pin_index, pin_value):
    if P.initialised:
        L.l.info('Setting pcf pin {}={}'.format(pin_index, pin_value))
        P.pcf.port[pin_index] = bool(pin_value)
    else:
        return _not_initialised('set_pin_value')


def post_init():
    if P.initialised:
        L.l.info('Running post_init pcf')
        relays = models.ZoneCustomRelay.query.filter_by(
            gpio_host_name=Constant.HOST_NAME, relay_type=Constant.GPIO_PIN_TYPE_PI_PCF8574).all()
        for relay in relays:
            L.l.info('Reading pcf pin {}'.format(relay.gpio_pin_code))
            pin_index = int(relay.gpio_pin_code)
            pin_val = get_pin(pin_index)
            io_common.update_custom_relay(pin_code=pin_index, pin_value=pin_val, notify=True)
    else:
        return _not_initialised('post_init')


def init():
    if P.import_module_exist:
        L.l.info('Initialising PCF8574')
        P.pcf = PCF8574(P.i2c_port_num, P.pcf_address)
        P.initialised = True
        L.l.info('Initialising PCF8574 OK, state= {}'.format(P.pcf.port))

