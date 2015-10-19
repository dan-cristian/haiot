__author__ = 'dcristian'

from main.logger_helper import Log
from common import Constant, utils
from main.admin import models
from main.admin.model_helper import commit

import std_gpio
import piface
import bbb_io

initialised=False


# update hardware pin state and record real pin value in local DB only
def relay_update(gpio_pin_code=None, pin_value=None, from_web=False):
    result = None
    #return pin value after state set
    try:
        Log.logger.debug('Received relay state update pin {}'.format(gpio_pin_code))
        gpiopin = models.GpioPin.query.filter_by(pin_code=gpio_pin_code, host_name=Constant.HOST_NAME).first()
        if gpiopin:
            pin_value = relay_set(gpio_pin=gpiopin, value=pin_value, from_web=from_web)
            result = pin_value
            gpiopin.pin_value = pin_value
            gpiopin.notify_transport_enabled = False
            commit()
        else:
            Log.logger.warning('Pin {} does not exists locally, is db data correct?'.format(gpio_pin_code))
    except Exception, ex:
        Log.logger.warning('Error updating relay state err={}'.format(ex))
    return result


#pin expected format is bcm
def relay_get(gpio_pin=None, from_web=False):
    message = 'Get relay state for pin {}'.format(gpio_pin.pin_index_bcm)
    if Constant.HOST_MACHINE_TYPE in [Constant.MACHINE_TYPE_RASPBERRY, Constant.MACHINE_TYPE_BEAGLEBONE]:
        if gpio_pin.pin_type in [Constant.GPIO_PIN_TYPE_PI, Constant.GPIO_PIN_TYPE_BBB]:
            pin_value = std_gpio.get_pin_bcm(gpio_pin.pin_index_bcm)
        elif gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_FACE:
            pin_value = piface.get_pin_value(pin_index=gpio_pin.pin_index_bcm, board_index=gpio_pin.board_index)
        #Log.logger.info(message + str(" val={}".format(pin_value)))
    else:
        message += ' error not running on gpio enabled devices'
        pin_value = None
        Log.logger.warning(message)

    #if from_web:
    #    return return_web_message(pin_value=pin_value, ok_message=message, err_message=message)
    #else:
    return pin_value


#set gpio pin without updating DB, so make sure it's used only after DB update trigger
def relay_set(gpio_pin=None, value=None, from_web=False):
    value = int(value)
    message = 'Set relay state [{}] for pin [{}] from web=[{}]'.format(value, gpio_pin.pin_index_bcm, from_web)
    Log.logger.info(message)
    if Constant.HOST_MACHINE_TYPE in [Constant.MACHINE_TYPE_RASPBERRY, Constant.MACHINE_TYPE_BEAGLEBONE]:
        if gpio_pin.pin_type in [Constant.GPIO_PIN_TYPE_PI, Constant.GPIO_PIN_TYPE_BBB]:
            pin_value = std_gpio.set_pin_bcm(gpio_pin.pin_index_bcm, value)
        elif gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_FACE:
            pin_value = piface.set_pin_value(pin_index=gpio_pin.pin_index_bcm, pin_value=value,
                                             board_index=gpio_pin.board_index)
    else:
        message += ' error not running on gpio enabled devices'
        pin_value = None
        Log.logger.warning(message)

    #if from_web:
    #    return return_web_message(pin_value=pin_value, ok_message=message, err_message=message)
    #else:
    return pin_value

#  save relay io state to db, except for current node
#  carefull not to trigger infinite recursion updates
def gpio_record_update(json_object):
    try:
        host_name = utils.get_object_field_value(json_object, 'name')
        Log.logger.info('Received gpio state update from {}'.format(host_name))
        if host_name != Constant.HOST_NAME:
            models.GpioPin().save_changed_fields_from_json_object(json_object=json_object,
                                                    notify_transport_enabled=False, save_to_graph=False)
    except Exception, ex:
        Log.logger.warning('Error on gpio state update, err {}'.format(ex))


def zone_custom_relay_record_update(json_object):
    #save relay state to db, except for current node
    #carefull not to trigger infinite recursion updates
    try:
        host_name = utils.get_object_field_value(json_object, 'gpio_host_name')
        Log.logger.info('Received custom relay state update from {}'.format(host_name))
        if host_name == Constant.HOST_NAME:
            #execute local pin change related actions like turn on/off a relay
            global initialised
            if initialised:
                gpio_pin_code = utils.get_object_field_value(json_object, 'gpio_pin_code')
                gpio_record = models.GpioPin.query.filter_by(pin_code=gpio_pin_code,
                                                             host_name=Constant.HOST_NAME).first()
                if gpio_record:
                    value = 1 if utils.get_object_field_value(json_object, 'relay_is_on') else 0
                    relay_set(gpio_pin=gpio_record, value=value, from_web=False)
                else:
                    Log.logger.warning('Could not find gpio record for custom relay pin code={}'.format(gpio_pin_code))

        else:
            models.ZoneCustomRelay().save_changed_fields_from_json_object(json_object=json_object,
                                                    notify_transport_enabled=False, save_to_graph=False)
    except Exception, ex:
        Log.logger.warning('Error on zone custom relay update, err {}'.format(ex))


def unload():
    global initialised
    if Constant.HOST_MACHINE_TYPE in [Constant.MACHINE_TYPE_RASPBERRY, Constant.MACHINE_TYPE_BEAGLEBONE]:
        Log.logger.info('Unloading gpio pins')
        std_gpio.unload()
        piface.un
    initialised = False


def init():
    Log.logger.info("GPIO initialising")
    if Constant.IS_MACHINE_RASPBERRYPI:
        piface.init()
    if Constant.IS_MACHINE_BEAGLEBONE:
        bbb_io.init()
    if Constant.IS_MACHINE_RASPBERRYPI or Constant.IS_MACHINE_BEAGLEBONE:
        std_gpio.init()
    global initialised
    initialised = True