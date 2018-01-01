import socket
import time
from threading import Thread, Lock
from pydispatch import dispatcher
from main import L
from main import thread_pool
from main.admin import models
from main.admin.model_helper import commit
from common import Constant

__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

# http://abyz.co.uk/rpi/pigpio/download.html
# http://abyz.co.uk/rpi/pigpio/python.html
# https://ms-iot.github.io/content/images/PinMappings/RP2_Pinout.png


__import_ok = False
initialised = False
__callback = []
__pi = None
__callback_thread = None
__pin_tick_dict = {}  # {InputEvent}
__lock_dict = {}  # lock list for each gpio


class Logx:
    def __init__(self):
        pass

    class Logger:
        def __init__(self):
            pass

        @staticmethod
        def info(text):
            print(text)

    logger = Logger()


try:
    import pigpio
    __import_ok = True
except Exception, ex:
    __import_ok = False
    L.l.info('Not importing pigpio_gpio, message={}'.format(ex))

'''
http://abyz.co.uk/rpi/pigpio_gpio/index.html

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
        self.event_count = 0
        self.processed = False

    def __repr__(self):
        return 'gpio={} level={} tick={} count={} processed={}'.format(self.gpio, self.level, self.tick,
                                                                       self.event_count, self.processed)


def get_pin_value(pin_index_bcm=None):
    global __pi
    return __pi.read(pin_index_bcm)


def set_pin_value(pin_index_bcm=None, pin_value=None):
    global __pi
    __pi.write(pin_index_bcm, pin_value)
    return get_pin_value(pin_index_bcm=pin_index_bcm)


def announce_event(event):
    L.l.info("DISPATCH IN io={} lvl={} count={} tick={}".format(event.gpio, event.level, event.event_count,
                                                                event.tick))
    # pin connected state assumes pins are pull-up enabled
    dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=event.gpio,
                    direction=Constant.GPIO_PIN_DIRECTION_IN,
                    pin_value=event.level, pin_connected=(event.level == 0))


# executed by a haiot thread (not by gpiopd thread)
def check_notify_event(event):
    # print("Debounce thread started for event {}".format(event))
    global __pin_tick_dict, __pi, __callback_thread, __lock_dict
    all_events_processed = False
    while not all_events_processed:
        time.sleep(0.1)  # latency in detecting changes
        current_tick = __pi.get_current_tick()
        all_events_processed = True
        for event in __pin_tick_dict.values():
            lock = __lock_dict[event.gpio]
            lock.acquire()
            try:
                # debounce period
                if not event.processed and (current_tick - event.tick > 100000):
                    # event old enough to not be a noise event
                    announce_event(event)
                    event.processed = True
                if not event.processed:
                    all_events_processed = False
            finally:
                lock.release()
    # print("Debounce thread exit")
    __callback_thread = None


# executed by gpiopd thread
def input_event(gpio, level, tick):
    global __pi, __pin_tick_dict
    pin_tick_event = __pin_tick_dict.get(gpio)
    current = __pi.get_current_tick()
    delta = current - tick
    if pin_tick_event and pin_tick_event.processed:
        # reset event to initial state
        pin_tick_event.event_count = 0
        pin_tick_event.processed = False
    if not pin_tick_event or pin_tick_event.event_count == 0:
        pin_tick_event = InputEvent(gpio, level, tick)
        pin_tick_event.event_count += 1
        __pin_tick_dict[gpio] = pin_tick_event
        # anounce first state change
        announce_event(pin_tick_event)
    else:
        if tick < pin_tick_event.tick:
            # ignore record events in the past
            L.l.debug("Ignore old gpio={} lvl={} tick={} current={} delta={}".format(gpio, level, tick, current,
                                                                                     delta))
        else:
            global __lock_dict
            lock = __lock_dict.get(gpio)
            if not lock:
                lock = Lock()
                __lock_dict[gpio] = lock
            lock.acquire()
            try:
                pin_tick_event.level = level
                pin_tick_event.tick = tick
                pin_tick_event.event_count += 1
                # Log.logger.info("IN gpio={} lvl={} tick={} current={} delta={}".format(gpio, level, tick, current, delta))
                # start a thread if not already started to notify the event completion without bounce
                global __callback_thread
                if __callback_thread is None:
                    __callback_thread = Thread(target=check_notify_event, args=(pin_tick_event,))
                    __callback_thread.start()
            finally:
                lock.release()


def setup_in_ports(gpio_pin_list):
    # Log.logger.info('Socket timeout={}'.format(socket.getdefaulttimeout()))
    # socket.setdefaulttimeout(None)
    global __callback, __pi
    L.l.info('Configuring {} gpio input ports'.format(len(gpio_pin_list)))
    if __pi:
        if socket.getdefaulttimeout() is not None:
            L.l.critical('PiGpio callbacks cannot be started as socket timeout is not None')
        else:
            for gpio_pin in gpio_pin_list:
                if gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_STDGPIO:
                    try:
                        L.l.info('Set pincode={} type={} index={} as input'.format(gpio_pin.pin_code,
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
                    except Exception, ex1:
                        L.l.critical('Unable to setup pigpio_gpio pin, er={}'.format(ex1))
                else:
                    L.l.info('Skipping PiGpio setup for pin {} with type {}'.format(gpio_pin.pin_code,
                                                                                    gpio_pin.pin_type))
        L.l.info('Exit gpio callback thread loop')
    else:
        L.l.critical('PiGpio not yet initialised but was asked to setup IN ports. Check module init order.')


def thread_run():
    pass


def unload():
    global __pi, __callback
    __callback = []
    __pi.stop()


def init():
    L.l.info('PiGpio initialising')
    global initialised
    global __pi
    if __import_ok:
        try:
            __pi = pigpio.pi()
            # test if daemon is on
            __pi.get_current_tick()
            # setup this to receive list of ports that must be set as "IN" and have callbacks defined
            dispatcher.connect(setup_in_ports, signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, sender=dispatcher.Any)
            initialised = True
            L.l.info('PiGpio initialised OK')
        except Exception, ex1:
            L.l.info('Unable to initialise PiGpio, err={}'.format(ex1))
            __pi = None
            initialised = False
    else:
        L.l.info('PiGpio NOT initialised, module unavailable on this system')
