__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

# http://abyz.co.uk/rpi/pigpio/download.html
# http://abyz.co.uk/rpi/pigpio/python.html
# https://ms-iot.github.io/content/images/PinMappings/RP2_Pinout.png

import socket
from pydispatch import dispatcher
from main import Log
from main import thread_pool
from main.admin import models
from main.admin.model_helper import commit
from common import Constant

__import_ok = False
initialised = False
__callback = []
__pi = None
__callback_thread = None
__pin_tick_list = {}  # {[pin_no, level, was_processed?]}

try:
    import pigpio
    __import_ok = True
except Exception, ex:
    __import_ok = False
    Log.logger.info('Exception on importing pigpio, err={}'.format(ex))

'''
http://abyz.co.uk/rpi/pigpio/index.html

ALL gpios are identified by their Broadcom number.  See elinux.org
There are 54 gpios in total, arranged in two banks.
Bank 1 contains gpios 0-31.  Bank 2 contains gpios 32-54.
A user should only manipulate gpios in bank 1.
There are at least three types of board.
Type 1

26 pin header (P1).
Hardware revision numbers of 2 and 3.
User gpios 0-1, 4, 7-11, 14-15, 17-18, 21-25.
Type 2

26 pin header (P1) and an additional 8 pin header (P5).
Hardware revision numbers of 4, 5, 6, and 15.
User gpios 2-4, 7-11, 14-15, 17-18, 22-25, 27-31.
Type 3

40 pin expansion header (J8).
Hardware revision numbers of 16 or greater.
User gpios 2-27 (0 and 1 are reserved).
It is safe to read all the gpios. If you try to write a system gpio or change its mode you can crash the Pi
or corrupt the data on the SD card.
'''


class InputEvent:
    def __init__(self, gpio, level, tick):
        self.tick = tick
        self.level = level
        self.gpio = gpio
        self.processed = False


def get_pin_value(pin_index_bcm=None):
    global __pi
    return __pi.read(pin_index_bcm)


def set_pin_value(pin_index_bcm=None, pin_value=None):
    global __pi
    __pi.write(pin_index_bcm, pin_value)
    return get_pin_value(pin_index_bcm=pin_index_bcm)


# tick = microseconds since boot
def input_event(gpio, level, tick):
    global __pi, __pin_tick_list
    # assumes pins are pull-up enabled
    pin_tick_event = __pin_tick_list.get(gpio)
    current = __pi.get_current_tick()
    delta = current - tick
    if pin_tick_event:
        last_tick = pin_tick_event.tick
    else:
        last_tick = 0
    if tick <= last_tick:
        # Log.logger.info("IN DUPLICATE gpio={} lvl={} tick={} current={} delta={}".format(gpio, level, tick, current, delta))
        pass
    else:
        # ignore record events in the past
        event = InputEvent(gpio, level, tick)
        __pin_tick_list[gpio] = event
        Log.logger.info("IN gpio={} lvl={} tick={} current={} delta={}".format(gpio, level, tick, current, delta))
    #dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=gpio, direction=Constant.GPIO_PIN_DIRECTION_IN,
    #                pin_value=level, pin_connected=(level == 0))


def setup_in_ports(gpio_pin_list):
    #global __callback_thread
    #Log.logger.info('Socket timeout={}'.format(socket.getdefaulttimeout()))
    # socket.setdefaulttimeout(None)
    #__callback_thread = Thread(target = setup_in_ports_and_wait, args=(gpio_pin_list, ))
    #__callback_thread.name = 'callback loop'
    #__callback_thread.start()
    global __callback, __pi
    Log.logger.info('Configuring {} gpio input ports'.format(len(gpio_pin_list)))
    if __pi:
        if socket.getdefaulttimeout() is not None:
            Log.logger.critical('PiGpio callbacks cannot be started as socket timeout is not None')
        else:
            for gpio_pin in gpio_pin_list:
                if gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_STDGPIO:
                    Log.logger.info('Set pincode={} type={} index={} as input'.format(gpio_pin.pin_code,
                                                                                      gpio_pin.pin_type,
                                                                                      gpio_pin.pin_index_bcm))
                    __pi.set_mode(int(gpio_pin.pin_index_bcm), pigpio.INPUT)
                    # https://learn.sparkfun.com/tutorials/pull-up-resistors
                    __pi.set_pull_up_down(int(gpio_pin.pin_index_bcm), pigpio.PUD_UP)
                    __callback.append(__pi.callback(user_gpio=int(gpio_pin.pin_index_bcm),
                                                    edge=pigpio.EITHER_EDGE, func=input_event))
                    gpio_pin_record = models.GpioPin().query_filter_first(
                        models.GpioPin.pin_code.in_([gpio_pin.pin_code]),
                        models.GpioPin.host_name.in_([Constant.HOST_NAME]))
                    gpio_pin_record.pin_direction = Constant.GPIO_PIN_DIRECTION_IN
                    commit()
                else:
                    Log.logger.info('Skipping PiGpio setup for pin {} with type {}'.format(gpio_pin.pin_code,
                                                                                           gpio_pin.pin_type))
        Log.logger.info('Exit gpio callback thread loop')
    else:
        Log.logger.critical('PiGpio not yet initialised but was asked to setup IN ports. Check module init order.')


def thread_run():
    global initialised, __pin_tick_list, __pi
    if initialised:
        for event in __pin_tick_list.values():
            if not event.processed:
                delta = __pi.get_current_tick() - event.tick
                if delta > 100000:
                    event.processed = True
                    dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=event.gpio,
                                    direction=Constant.GPIO_PIN_DIRECTION_IN,
                                    pin_value=event.level, pin_connected=(event.level == 0))

def unload():
    global __pi, __callback
    __callback = []
    __pi.stop()


def init():
    Log.logger.info('PiGpio initialising')
    if __import_ok:
        try:
            global __pi
            __pi = pigpio.pi()
            global initialised
            # setup this to receive list of ports that must be set as "IN" and have callbacks defined
            dispatcher.connect(setup_in_ports, signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, sender=dispatcher.Any)
            initialised = True
            Log.logger.info('PiGpio initialised OK')
        except Exception, ex:
            Log.logger.info('Unable to initialise PiGpio, err={}'.format(ex))
            initialised = False
    else:
        Log.logger.info('PiGpio NOT initialised, module unavailable on this system')


