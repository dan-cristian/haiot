__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import time
from pydispatch import dispatcher
from main import L
from main import thread_pool
from common import Constant


# https://piface.github.io/pifacedigitalio/example.html
class P:
    import_ok = False
    pfd = {}
    listener = None
    initialised = False
    pool_pin_codes = []

    def __init__(self):
        pass


try:
    import pifacedigitalio as pfio
    P.import_ok = True
except Exception as ex:
    P.import_ok = False
    L.l.info('Pifacedigitalio module not available')


def format_pin_code(board_index, pin_direction, pin_index):
    return str(board_index) + ":" + str(pin_direction) + ":" + str(pin_index)


def get_pin_value(pin_index=None, board_index=0):
    return pfio.digital_read(pin_num=pin_index, hardware_addr=board_index)


def _get_output_pin_value(pin_index=None, board_index=0):
    return P.pfd[board_index].output_pins[pin_index].value


# http://www.farnell.com/datasheets/1881551.pdf
def set_pin_value(pin_index=None, pin_value=None, board_index=0):
    L.l.info('Set piface pin {} value {} board {}'.format(pin_index, pin_value, board_index))
    pfio.digital_write(pin_num=pin_index, value=pin_value, hardware_addr=board_index)
    act_value = _get_output_pin_value(pin_index=pin_index, board_index=board_index)
    if pin_value != act_value:
        L.l.warning("Piface set pin {} failed, actual value={}".format(pin_index, act_value))
    return act_value


# not used
def set_relay(index, value):
    pfio.relays[index].value = value


def input_event(event):
    # L.l.info('Piface switch event={}'.format(event))
    pin_num = event.pin_num
    board_index = event.chip.hardware_addr
    direction = event.direction  # 0 for press/contact, 1 for release/disconnect
    gpio_pin_code = format_pin_code(board_index=board_index, pin_direction=Constant.GPIO_PIN_DIRECTION_IN,
                                    pin_index=pin_num)
    # if gpio_pin_code == 7:
    # L.l.info('Event piface gpio={} direction={}'.format(gpio_pin_code, direction))
    dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=gpio_pin_code, direction=Constant.GPIO_PIN_DIRECTION_IN,
                    pin_value=direction, pin_connected=(direction == 0))


def _read_default(pin, board_index=0):
    val = get_pin_value(pin_index=pin)
    gpio_pin_code = format_pin_code(board_index=board_index, pin_direction=Constant.GPIO_PIN_DIRECTION_IN,
                                    pin_index=pin)
    dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=gpio_pin_code, direction=Constant.GPIO_PIN_DIRECTION_IN,
                    pin_value=val, pin_connected=(val == 0))


#  define all ports that are used as read/input
#  port format is x:direction:y, e.g. 0:in:3, x=board, direction=in/out, y=pin index (0 based)
# !!! make sure piface listener is enabled in the same thread, and pin index is integer
def setup_in_ports_pif(gpio_pin_list):
    try:
        pfio.init()
        P.pfd[0] = pfio.PiFaceDigital(hardware_addr=0)
        P.listener = pfio.InputEventListener(chip=P.pfd[0])
        for gpio_pin in gpio_pin_list:
            if gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
                # Log.logger.info('Set piface code={} type={} index={}'.format(
                #    gpio_pin.pin_code,gpio_pin.pin_type, gpio_pin.pin_index_bcm))
                try:
                    # i = gpio_pin.pin_code.split(":")[2]
                    # Log.logger.info("Piface registering input pin {}".format(gpio_pin.pin_index_bcm))
                    pin = int(gpio_pin.pin_index_bcm)
                    P.listener.register(pin, pfio.IODIR_ON, input_event)
                    P.listener.register(pin, pfio.IODIR_OFF, input_event)
                    L.l.info('OK callback set on piface {} pin {}'.format(gpio_pin.pin_code, pin))
                    _read_default(pin=pin)
                except Exception as ex:
                    L.l.critical('Unable to setup piface listener pin={} err={}'.format(gpio_pin.pin_code, ex))
                P.pool_pin_codes.append(gpio_pin.pin_code)
        P.listener.activate()
    except Exception as ex:
        L.l.critical('Piface setup ports failed, err={}'.format(ex))


def thread_run():
    pass


def unload():
    L.l.info('Piface unloading')
    if P.import_ok:
        P.listener.deactivate()
        pfio.deinit_board()


def init():
    L.l.debug('Piface initialising')
    if P.import_ok:
        try:
            dispatcher.connect(setup_in_ports_pif, signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, sender=dispatcher.Any)
            thread_pool.add_interval_callable(thread_run, run_interval_second=10)
            P.initialised = True
            L.l.info('Piface initialised OK')
        except Exception as ex1:
            L.l.info('Piface not initialised, err={}'.format(ex1))
    else:
        L.l.info('Piface NOT initialised, module pifacedigitalio unavailable on this system')
