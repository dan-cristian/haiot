__author__ = 'Dan Cristian <dan.cristian@gmail.com>'


from main import Log
from main import thread_pool

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


def get_pin_value(pin_index=None, board_index=0):
    return pfio.digital_read(pin_num=pin_index, hardware_addr=board_index)


def set_pin_value(pin_index=None, pin_value=None, board_index=0):
    pfio.digital_write(pin_num=pin_index, value=pin_value, hardware_addr=board_index)
    return get_pin_value(pin_index=pin_index, board_index=board_index)


def switch_pressed(event):
    Log.logger.info('Piface input pressed, event={} chip={}'.format(event, event.chip))
    pin_num = event.pin_num


def switch_unpressed(event):
    Log.logger.info('Piface input released, event={} chip={}'.format(event, event.chip))


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
            for i in range(4):
                __listener.register(i, pfio.IODIR_ON, switch_pressed)
                __listener.register(i, pfio.IODIR_OFF, switch_unpressed)
            __listener.activate()
            Log.logger.info("Piface input listener activated")
            thread_pool.add_interval_callable(thread_run, run_interval_second=10)
            global initialised
            initialised = True
            Log.logger.info('Piface initialised OK')
        except Exception, ex:
            Log.logger.critical('Piface not initialised, err={}'.format(ex))
    else:
        Log.logger.info('Piface NOT initialised, module pifacedigitalio unavailable on this system')