__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import time
from pydispatch import dispatcher
from main import L
from main import thread_pool
from common import Constant
from main.admin import models
from main.admin.model_helper import commit
from gpio import io_common

# https://piface.github.io/pifacedigitalio/example.html
class P:
    import_ok = False
    pfd = {}
    listener = {}
    initialised = False
    board_init = False
    # pool_pin_codes = []

    def __init__(self):
        pass


try:
    import pifacedigitalio as pfio
    from pifacedigitalio.core import NoPiFaceDigitalDetectedError
    P.import_ok = True
except Exception as ex:
    P.import_ok = False
    L.l.info('Pifacedigitalio module not available')


def _format_pin_code(board_index, pin_direction, pin_index):
    return str(board_index) + ":" + str(pin_direction) + ":" + str(pin_index)


# To read the state of an input use the pfio.digital_read(pin) function. If a button is
# pressed the function returns a 1, otherwise it returns a 0.
def _get_in_pin_value(pin_index, board_index):
    return pfio.digital_read(pin_num=pin_index, hardware_addr=board_index)


def get_out_pin_value(pin_index, board_index):
    return P.pfd[board_index].output_pins[pin_index].value


# http://www.farnell.com/datasheets/1881551.pdf
def set_pin_value(pin_index, pin_value, board_index):
    L.l.info('Set piface pin {} value {} board {}'.format(pin_index, pin_value, board_index))
    pfio.digital_write(pin_num=pin_index, value=pin_value, hardware_addr=board_index)
    act_value = get_out_pin_value(pin_index=pin_index, board_index=board_index)
    if pin_value != act_value:
        L.l.warning("Piface set pin {} failed, actual value={}".format(pin_index, act_value))
    return act_value


def _input_event(event):
    # L.l.info('Piface switch event={}'.format(event))
    pin_num = event.pin_num
    board_index = event.chip.hardware_addr
    direction = event.direction  # 0 for press/contact, 1 for release/disconnect
    pin_val = _get_in_pin_value(pin_num, board_index)
    gpio_pin_code = _format_pin_code(board_index=board_index, pin_direction=Constant.GPIO_PIN_DIRECTION_IN,
                                     pin_index=pin_num)
    # if gpio_pin_code == 7:
    L.l.info('Event piface gpio={} direction={} altval={}'.format(gpio_pin_code, direction, pin_val))
    dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=gpio_pin_code, direction=Constant.GPIO_PIN_DIRECTION_IN,
                    pin_value=pin_val, pin_connected=(pin_val == 1))


#  define all ports that are used as read/input
#  port format is x:direction:y, e.g. 0:in:3, x=board, direction=in/out, y=pin index (0 based)
# !!! make sure piface listener is enabled in the same thread, and pin index is integer
def _setup_in_ports_pif(gpio_pin_list):
    for gpio_pin in gpio_pin_list:
        if gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
            # Log.logger.info('Set piface code={} type={} index={}'.format(
            #    gpio_pin.pin_code,gpio_pin.pin_type, gpio_pin.pin_index_bcm))
            try:
                # i = gpio_pin.pin_code.split(":")[2]
                # Log.logger.info("Piface registering input pin {}".format(gpio_pin.pin_index_bcm))
                pin = int(gpio_pin.pin_index_bcm)
                board = int(gpio_pin.board_index)
                if board in P.listener.keys():
                    P.listener[board].register(pin, pfio.IODIR_ON, _input_event)
                    P.listener[board].register(pin, pfio.IODIR_OFF, _input_event)
                    L.l.info('OK callback set on piface board {}, {} pin {}'.format(board, gpio_pin.pin_code, pin))
                    # _read_default(pin=pin, board_index=board)
            except Exception as ex:
                L.l.critical('Unable to setup piface listener board={} pin={} err={}'.format(
                    board, gpio_pin.pin_code, ex))
    for li in P.listener.values():
        li.activate()


def _setup_board():
    try:
        bus, chip = 0, 0
        try:
            for chip in [0, 1]:
                pfio.init(bus=bus, chip_select=chip)
                L.l.info("Initialised piface spi spidev{}.{}".format(bus, chip))
        except Exception as ex:
            pass
        for board in [0, 1, 2, 3]:
            try:
                pfd = pfio.PiFaceDigital(hardware_addr=board, init_board=True)
                P.pfd[board] = pfd
                P.listener[board] = pfio.InputEventListener(chip=P.pfd[board])
                L.l.info("Initialised piface listener board {}".format(board))
            except NoPiFaceDigitalDetectedError as ex:
                pass
        P.board_init = True
    except Exception as ex:
        L.l.critical('Piface setup board failed, err={}'.format(ex))


def unload():
    L.l.info('Piface unloading')
    if P.import_ok:
        pass
        # pfio.deinit_board()


def post_init():
    L.l.info('Running post_init piface')
    # read default values
    for board in P.pfd.keys():
        for pin in range(8):
            gpio_pin_code = _format_pin_code(board_index=board, pin_direction=Constant.GPIO_PIN_DIRECTION_OUT,
                                             pin_index=pin)
            pin_out_val = get_out_pin_value(pin_index=pin, board_index=board)
            io_common.update_custom_relay(pin_code=gpio_pin_code, pin_value=pin_out_val, notify=True)
            gpio_pin_code = _format_pin_code(board_index=board, pin_direction=Constant.GPIO_PIN_DIRECTION_IN,
                                             pin_index=pin)
            pin_in_val = _get_in_pin_value(pin_index=pin, board_index=board)
            alt_pin_in = P.pfd[board].input_pins[pin].value
            L.l.info('Read input pin {} value={} alt={}'.format(gpio_pin_code, pin_in_val, alt_pin_in))
            io_common.update_custom_relay(pin_code=gpio_pin_code, pin_value=pin_in_val, notify=True)
            # resend to ensure is received by other late init modules like openhab
            dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=gpio_pin_code, direction=Constant.GPIO_PIN_DIRECTION_IN,
                            pin_value=pin_in_val, pin_connected=(pin_in_val == 1))


def init():
    L.l.debug('Piface initialising')
    if P.import_ok:
        try:
            _setup_board()
            # thread_pool.add_interval_callable(thread_run, run_interval_second=10)
            dispatcher.connect(_setup_in_ports_pif, signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, sender=dispatcher.Any)
            P.initialised = True
            L.l.info('Piface initialised OK')
        except Exception as ex1:
            L.l.info('Piface not initialised, err={}'.format(ex1))
    else:
        L.l.info('Piface not initialised, module pifacedigitalio unavailable on this system')
