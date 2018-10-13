__author__ = 'dcristian'
from datetime import datetime, timedelta
from main.logger_helper import L
from common import Constant, utils
from main.admin import models
from main.admin.model_helper import commit
from main import thread_pool
from sensor import zwave
import std_gpio
import piface
import threading
import prctl
# import bbb_io
# import pigpio_gpio
import rpi_gpio


class P:
    initialised = False
    expire_func_list = {}

    def __init__(self):
        pass


# update hardware pin state and record real pin value in local DB only
def relay_update(gpio_pin_code=None, pin_value=None, from_web=False):
    result = None
    # return pin value after state set
    try:
        L.l.debug('Received relay state update pin {}'.format(gpio_pin_code))
        gpiopin_list = models.GpioPin.query.filter_by(pin_code=gpio_pin_code, host_name=Constant.HOST_NAME).all()
        if gpiopin_list:
            if len(gpiopin_list) > 1:
                L.l.warning("Multiple records with same pin code {}".format(gpio_pin_code))
            for gpiopin in gpiopin_list:
                pin_value = relay_set(gpio_pin=gpiopin, value=pin_value, from_web=from_web)
                result = pin_value
                gpiopin.pin_value = pin_value
                gpiopin.notify_transport_enabled = False
                commit()
        else:
            L.l.warning('Pin {} does not exists locally, is db data correct?'.format(gpio_pin_code))
    except Exception as ex:
        L.l.error('Error updating relay state err={}'.format(ex), exc_info=True)
    return result


# parameter is GpioPin model, not the pin index!
def relay_get(gpio_pin_obj=None, from_web=False):
    message = 'Get relay state for pin {}'.format(gpio_pin_obj)
    if Constant.HOST_MACHINE_TYPE in [Constant.MACHINE_TYPE_RASPBERRY, Constant.MACHINE_TYPE_BEAGLEBONE]:
        if gpio_pin_obj.pin_type in [Constant.GPIO_PIN_TYPE_PI_STDGPIO, Constant.GPIO_PIN_TYPE_BBB]:
            if rpi_gpio.initialised:
                pin_value = rpi_gpio.get_pin_bcm(bcm_id=int(gpio_pin_obj.pin_index_bcm))
            else:
                pin_value = std_gpio.get_pin_bcm(bcm_id=gpio_pin_obj.pin_index_bcm)
        elif gpio_pin_obj.pin_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
            # todo: check if pin index is bcm type indeed for piface
            pin_value = piface.get_pin_value(pin_index=gpio_pin_obj.pin_index_bcm, board_index=gpio_pin_obj.board_index)
        else:
            L.l.warning('Cannot select gpio method for pin={}'.format(gpio_pin_obj))
            pin_value = None
    else:
        message += ' error not running on gpio enabled devices'
        pin_value = None
        L.l.warning(message)

    # if from_web:
    #    return return_web_message(pin_value=pin_value, ok_message=message, err_message=message)
    # else:
    return pin_value


# set gpio pin without updating DB, so make sure it's used only after DB update trigger
def relay_set(gpio_pin=None, value=None, from_web=False):
    pin_value = None
    value = int(value)
    message = 'Set relay state [{}] for pin [{}] from web=[{}]'.format(value, gpio_pin.pin_index_bcm, from_web)
    # L.l.info(message)
    if Constant.HOST_MACHINE_TYPE in [Constant.MACHINE_TYPE_RASPBERRY, Constant.MACHINE_TYPE_BEAGLEBONE]:
        if gpio_pin.pin_type in [Constant.GPIO_PIN_TYPE_PI_STDGPIO, Constant.GPIO_PIN_TYPE_BBB]:
            if rpi_gpio.initialised:
                pin_value = rpi_gpio.set_pin_bcm(bcm_id=int(gpio_pin.pin_index_bcm), pin_value=int(value))
            else:
                pin_value = std_gpio.set_pin_bcm(gpio_pin.pin_index_bcm, value)
        elif gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
            pin_value = piface.set_pin_value(pin_index=int(gpio_pin.pin_index_bcm), pin_value=int(value),
                                             board_index=int(gpio_pin.board_index))
        else:
            L.l.warning("Unknown pin type {}".format(gpio_pin.pin_type))
    else:
        message += ' error not running on gpio enabled devices'
        L.l.warning(message)

    # if from_web:
    #    return return_web_message(pin_value=pin_value, ok_message=message, err_message=message)
    # else:
    return pin_value


#  save relay io state to db, except for current node
#  carefull not to trigger infinite recursion updates
def gpio_record_update(json_object):
    try:
        host_name = utils.get_object_field_value(json_object, 'name')
        # L.l.info('Received gpio state update from {}'.format(host_name))
        if host_name != Constant.HOST_NAME:
            models.GpioPin().save_changed_fields_from_json_object(
                json_object=json_object, notify_transport_enabled=False, save_to_graph=False)
    except Exception as ex:
        L.l.warning('Error on gpio state update, err {}'.format(ex))


def zone_custom_relay_record_update(json_object):
    # save relay state to db, except for current node
    # carefull not to trigger infinite recursion updates
    try:
        host_name = utils.get_object_field_value(json_object, 'gpio_host_name')
        # L.l.info('Received custom relay state update for host {}'.format(host_name))
        if host_name == Constant.HOST_NAME:
            # execute local pin change related actions like turn on/off a relay
            if P.initialised:
                gpio_pin_code = utils.get_object_field_value(json_object, 'gpio_pin_code')
                relay_type = utils.get_object_field_value(json_object, 'relay_type')
                relay_is_on = utils.get_object_field_value(json_object, 'relay_is_on')
                expire = utils.get_object_field_value(json_object, 'expire')
                if relay_type == Constant.GPIO_PIN_TYPE_ZWAVE:
                    vals = gpio_pin_code.split('_')
                    if len(vals) == 2:
                        node_id = int(vals[1])
                        L.l.info('Received relay state update host {}, obj={}'.format(host_name, json_object))
                        # zwave switch name is not needed, identify device only by node_id
                        zwave.set_switch_state(node_id=node_id, state=relay_is_on)
                        if expire is not None:
                            # revert back to initial state
                            expire_time = datetime.now() + timedelta(seconds=expire)
                            func = (zwave.set_switch_state, node_id, not(bool(relay_is_on)))
                            if expire_time not in P.expire_func_list.keys():
                                P.expire_func_list[expire_time] = func
                            else:
                                L.l.error("Duplicate zwave key in list")
                                exit(999)
                    else:
                        L.l.error("Incorrect zwave switch format {}, must be <name>_<node_id>".format(gpio_pin_code))
                else:
                    gpio_record = models.GpioPin.query.filter_by(pin_code=gpio_pin_code,
                                                                 host_name=Constant.HOST_NAME).first()
                    if gpio_record:
                        value = 1 if relay_is_on else 0
                        relay_set(gpio_pin=gpio_record, value=value, from_web=False)
                        if expire is not None:
                            # revert back to initial state in x seconds
                            expire_time = datetime.now() + timedelta(seconds=expire)
                            func = (relay_set, gpio_record, not (bool(relay_is_on)), False)
                            if expire_time not in P.expire_func_list.keys():
                                P.expire_func_list[expire_time] = func
                            else:
                                L.l.error("Duplicate key in gpio list")
                                exit(999)
                    else:
                        L.l.warning('Could not find gpio record for custom relay pin code={}'.format(gpio_pin_code))
        # todo: check if for zwave we get multiple redundant db saves
        models.ZoneCustomRelay().save_changed_fields_from_json_object(
            json_object=json_object, notify_transport_enabled=False, save_to_graph=False)
    except Exception as ex:
        L.l.error('Error on zone custom relay update, err={}'.format(ex), exc_info=True)


# https://stackoverflow.com/questions/26881396/how-to-add-a-function-call-to-a-list
def _process_expire():
    for func_time in dict(P.expire_func_list).keys():
        if datetime.now() >= func_time:
            func = P.expire_func_list[func_time]
            L.l.info("Function expired, executing relay action func={}".format(func))
            func[0](*func[1:])
            del func


def thread_run():
    prctl.set_name("gpio")
    threading.current_thread().name = "gpio"
    # pigpio_gpio.thread_run()
    piface.thread_run()
    # bbb_io.thread_run()
    std_gpio.thread_run()
    rpi_gpio.thread_run()
    _process_expire()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def unload():
    if Constant.HOST_MACHINE_TYPE in [Constant.MACHINE_TYPE_RASPBERRY, Constant.MACHINE_TYPE_BEAGLEBONE]:
        L.l.info('Unloading gpio pins')
        std_gpio.unload()
        piface.unload()
        # bbb_io.unload()
        rpi_gpio.unload()
    P.initialised = False


def init():
    L.l.debug("GPIO initialising")
    if Constant.IS_MACHINE_RASPBERRYPI:
        piface.init()
        # pigpio_gpio.init()
        rpi_gpio.init()
    if Constant.IS_MACHINE_BEAGLEBONE:
        # bbb_io.init()
        std_gpio.init()
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    P.initialised = True
