__author__ = 'Dan Cristian <dan.cristian@gmail.com>'


from main import Log
from main import thread_pool

# https://piface.github.io/pifacedigitalio/example.html
__import_ok = False
initialised = False

try:
    import pifacedigitalio as pfio
    __import_ok = True
except ImportError:
    __import_ok = False
    pass


def get_pin_value(pin_index=None, board_index=0):
    return pfio.digital_read(pin_num=pin_index, hardware_addr=board_index)


def set_pin_value(pin_index=None, pin_value=None, board_index=0):
    pfio.digital_write(pin_num=pin_index, value=pin_value, hardware_addr=board_index)
    return get_pin_value(pin_index=pin_index, board_index=board_index)


def thread_run():
    pass


def init():
    Log.logger.info('PiFace module initialising')
    if __import_ok:
        try:
            pfio.init()
            thread_pool.add_interval_callable(thread_run, run_interval_second=10)
            global initialised
            initialised = True
        except Exception, ex:
            Log.logger.critical('Module piface not initialised, err={}'.format(ex))
    else:
        Log.logger.info('Module pifacedigitalio not loaded')