from main import sqlitedb
from main.logger_helper import L
if sqlitedb:
    from storage.sqalc import models
from common import Constant
from gpio import io_common
from storage.model import m


class P:
    pcf = None
    i2c_port_num = 1
    pcf_address = 0x24
    import_module_exist = None
    initialised = False

    def __init__(self):
        pass


from common import fix_module
while True:
    try:
        from pcf8574 import PCF8574
        P.import_module_exist = True
        break
    except ImportError as iex:
        if not fix_module(iex):
            break


def _not_initialised(message):
    L.l.error('Module PCF8574 is not initialised for {}'.format(message))
    return None


def get_pin(pin_index):
    if P.initialised:
        if 0 <= pin_index <= 7:
            val = P.pcf.port[int(pin_index)]
            L.l.info('Getting == PCF == pin {} val={}'.format(pin_index, val))
            return val
        else:
            L.l.error('PCF pin index must be between 0 and 7, unexpected val {}'.format(pin_index))
            return None
    else:
        return _not_initialised('get_pin')


def set_pin_value(pin_index, pin_value):
    if P.initialised:
        L.l.info('Setting == PCF == pin {} val={}'.format(pin_index, pin_value))
        P.pcf.port[int(pin_index)] = bool(pin_value)
        return get_pin(pin_index)
    else:
        return _not_initialised('set_pin_value')


def unload():
    pass


def post_init_relay_value(gpio_pin_code):
    if P.initialised:
        pin_index = int(gpio_pin_code)
        return get_pin(pin_index)
    else:
        return None


def post_init_alarm_value(gpio_pin_code):
    pin_index = int(gpio_pin_code)
    # fixme check pin_connected status
    return get_pin(pin_index) == 1


def post_init():
    if P.initialised:
        L.l.info('Running post_init pcf')
        if sqlitedb:
            relays = models.ZoneCustomRelay.query.filter_by(
                gpio_host_name=Constant.HOST_NAME, relay_type=Constant.GPIO_PIN_TYPE_PI_PCF8574).all()
        else:
            relays = m.ZoneCustomRelay.find({m.ZoneCustomRelay.gpio_host_name: Constant.HOST_NAME,
                                            m.ZoneCustomRelay.relay_type: Constant.GPIO_PIN_TYPE_PI_PCF8574})
        for relay in relays:
            L.l.info('Reading pcf pin {}'.format(relay.gpio_pin_code))
            pin_index = int(relay.gpio_pin_code)
            pin_val = get_pin(pin_index)
            io_common.update_custom_relay(pin_code=pin_index, pin_value=pin_val, notify=True)


def init():
    if P.import_module_exist:
        try:
            L.l.info('Initialising PCF8574')
            P.pcf = PCF8574(P.i2c_port_num, P.pcf_address)
            test_ok = P.pcf.port[0]  # try a read
            P.initialised = True
            L.l.info('Initialising PCF8574 OK, state= {}'.format(P.pcf.port))
        except Exception as ex:
            L.l.info('Unable to initialise PCF8574, ex={}'.format(ex))
