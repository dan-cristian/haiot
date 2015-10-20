__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

# http://abyz.co.uk/rpi/pigpio/download.html
# http://abyz.co.uk/rpi/pigpio/python.html

from pydispatch import dispatcher
from main import Log
from main import thread_pool
from common import Constant

__import_ok = False
initialised = False
__callback = []


try:
    import pigpio
    __import_ok = True
except Exception, ex:
    __import_ok = False
    Log.logger.info('Exception on importing pigpio, err={}'.format(ex))


def input_event(gpio, level, tick):
    Log.logger.info("Received pigpio input gpio={} level={} tick={}".format(gpio, level, tick))


def init():
    Log.logger.info('PiGpio initialising')
    if __import_ok:
        try:
            pi = pigpio.pi()
            global __callback, initialised
            for i in range(0, 40):
                __callback.append(pi.callback(user_gpio=i, edge=pigpio.EITHER_EDGE, func=input_event))
            initialised = True
            Log.logger.info('PiGpio initialised OK')
        except Exception, ex:
            Log.logger.info('Unable to initialise PiGpio, err={}'.format(ex))
            initialised = False
    else:
        Log.logger.info('PiGpio NOT initialised, module unavailable on this system')


