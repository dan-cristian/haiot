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
__pin_tick_list = {}

try:
    import pigpio
    __import_ok = True
except Exception, ex:
    __import_ok = False
    Log.logger.info('Exception on importing pigpio, err={}'.format(ex))


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
    pin_tick = __pin_tick_list.get(gpio)
    if not pin_tick:
        __pin_tick_list[gpio] = tick
        pin_tick = 0
    if tick - pin_tick > 10000:
        Log.logger.info("Received pigpio input gpio={} level={} tick={}".format(gpio, level, tick))
        dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=gpio, direction=Constant.GPIO_PIN_DIRECTION_IN,
                    pin_value=level, pin_connected=(level == 0))
    else:
        # ignore bounce
        pass

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


