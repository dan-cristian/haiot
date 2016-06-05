__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

from pydispatch import dispatcher
from main import Log
from main import thread_pool
from common import Constant

# https://piface.github.io/pifacedigitalio/example.html
__import_ok = False
__pfd = None
__listener = None
initialised = False

try:
    import pifacedigitalio as pfio

    __import_ok = True
except Exception, ex:
    __import_ok = False
    Log.logger.info('Exception on importing pifacedigitalio, err={}'.format(ex))


def format_pin_code(board_index, pin_direction, pin_index):
    return str(board_index) + ":" + str(pin_direction) + ":" + str(pin_index)


def get_pin_value(pin_index=None, board_index=0):
    return pfio.digital_read(pin_num=pin_index, hardware_addr=board_index)


def set_pin_value(pin_index=None, pin_value=None, board_index=0):
    pfio.digital_write(pin_num=pin_index, value=pin_value, hardware_addr=board_index)
    return get_pin_value(pin_index=pin_index, board_index=board_index)


def input_event(event):
    Log.logger.debug('Piface switch event={}'.format(event))
    pin_num = event.pin_num
    board_index = event.chip.hardware_addr
    direction = event.direction  # 0 for press/contact, 1 for release/disconnect
    gpio_pin_code = format_pin_code(board_index=board_index, pin_direction=Constant.GPIO_PIN_DIRECTION_IN,
                                    pin_index=pin_num)
    Log.logger.info('Event piface gpio={} direction={}'.format(gpio_pin_code, direction))
    dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=gpio_pin_code, direction=Constant.GPIO_PIN_DIRECTION_IN,
                    pin_value=direction, pin_connected=(direction == 0))


def thread_run():
    pass


def unload():
    Log.logger.info('Piface unloading')
    if __import_ok:
        pfio.deinit()


def init():
    Log.logger.info('Piface initialising')
    if __import_ok:
        try:
            pfio.init()
            global __pfd, __listener
            __pfd = pfio.PiFaceDigital()
            __listener = pfio.InputEventListener(chip=__pfd)
            for i in range(8):
                Log.logger.info("Piface registering pin {}".format(i))
                __listener.register(i, pfio.IODIR_ON, input_event)
                __listener.register(i, pfio.IODIR_OFF, input_event)
            __listener.activate()
            Log.logger.info("Piface input listener activated")
            thread_pool.add_interval_callable(thread_run, run_interval_second=10)
            global initialised
            initialised = True
            Log.logger.info('Piface initialised OK')
        except Exception, ex1:
            Log.logger.info('Piface not initialised, err={}'.format(ex1))
    else:
        Log.logger.info('Piface NOT initialised, module pifacedigitalio unavailable on this system')
