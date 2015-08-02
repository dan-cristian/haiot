__author__ = 'dcristian'
from main import app
from flask import request
from main import logger
from common import constant, utils
from main.admin import db, models
from main.admin.model_helper import commit

import gpio_pi_bbb

initialised=False

def relay_update(gpio_pin_code=None, pin_value=None):
    #return pin value after state set
    try:
        logger.debug('Received relay state update pin {}'.format(gpio_pin_code))
        gpiopin = models.GpioPin.query.filter_by(pin_code=gpio_pin_code, host_name=constant.HOST_NAME).first()
        result = None
        if gpiopin:
            pin_value = relay_set(pin_bcm=gpiopin.pin_index_bcm, value=pin_value, from_web=False)
            result = pin_value
            gpiopin.pin_value = pin_value
            gpiopin.notify_transport_enabled = False
            commit()
        else:
            logger.warning('Pin {} does not exists locally, is db data correct?'.format(gpio_pin_code))
    except Exception, ex:
        logger.warning('Error updating relay state err={}'.format(ex))
    return result

#pin expected format is bcm
def relay_get(pin=None, from_web=False):
    message = 'Get relay state for pin {}'.format(pin)
    logger.info(message)
    if constant.HOST_MACHINE_TYPE in [constant.MACHINE_TYPE_RASPBERRY, constant.MACHINE_TYPE_BEAGLEBONE]:
        pin_value = gpio_pi_bbb.get_pin_bcm(pin)
    else:
        message += ' error not running on gpio enabled devices'
        pin_value = None
        logger.warning(message)

    if from_web:
        return return_web_message(pin_value=pin_value, ok_message=message, err_message=message)
    else:
        return pin_value

def relay_set(pin_bcm=None, value=None, from_web=False):
    value = int(value)
    message = 'Set relay state [{}] for pin [{}] from web=[]'.format(value, pin_bcm, from_web)
    logger.info(message)
    if constant.HOST_MACHINE_TYPE in [constant.MACHINE_TYPE_RASPBERRY, constant.MACHINE_TYPE_BEAGLEBONE]:
        pin_value = gpio_pi_bbb.set_pin_bcm(pin_bcm, value)
    else:
        message += ' error not running on gpio enabled devices'
        pin_value = None
        logger.warning(message)

    if from_web:
        return return_web_message(pin_value=pin_value, ok_message=message, err_message=message)
    else:
        return pin_value

def return_web_message(pin_value, ok_message='', err_message=''):
    if pin_value:
        return ok_message + '\n' + constant.SCRIPT_RESPONSE_OK + '=' + pin_value
    else:
        return err_message + '\n'

def gpio_record_update(json_object):
    #save relay io state to db, except for current node
    #carefull not to trigger infinite recursion updates
    try:
        host_name = utils.get_object_field_value(json_object, 'name')
        logger.info('Received gpio state update from {}'.format(host_name))
        if host_name != constant.HOST_NAME:
            id = utils.get_object_field_value(json_object, 'id')
            record = models.GpioPin(id=id)
            assert isinstance(record, models.GpioPin)
            record.pin_type = utils.get_object_field_value(json_object, 'pin_type')
            record.pin_code = utils.get_object_field_value(json_object, 'pin_code')
            record.pin_index_bcm = utils.get_object_field_value(json_object, 'pin_index_bcm')
            record.pin_value = utils.get_object_field_value(json_object, 'pin_value')
            record.pin_direction = utils.get_object_field_value(json_object, 'pin_direction')
            record.is_active = utils.get_object_field_value(json_object, 'is_active')
            record.updated_on = utils.get_base_location_now_date()
            current_record = models.GpioPin.query.filter_by(id=id).first()
            record.save_changed_fields(current_record=current_record, new_record=record, notify_transport_enabled=False,
                                       save_to_graph=False)
            db.session.commit()
    except Exception, ex:
        logger.warning('Error on gpio state update, err {}'.format(ex))
    pass

def zone_custom_relay_record_update(json_object):
    #save relay state to db, except for current node
    #carefull not to trigger infinite recursion updates
    try:
        host_name = utils.get_object_field_value(json_object, 'gpio_host_name')
        logger.info('Received custom relay state update from {}'.format(host_name))
        if host_name == constant.HOST_NAME:
            #execute local pin change related actions like turn on/off a relay
            global initialised
            if initialised:
                gpio_pin_code = utils.get_object_field_value(json_object, 'gpio_pin_code')
                gpio_record = models.GpioPin.query.filter_by(pin_code=gpio_pin_code,
                                                             host_name=constant.HOST_NAME).first()
                if gpio_record:
                    value = 1 if utils.get_object_field_value(json_object, 'relay_is_on') else 0
                    pin_bcm = gpio_record.pin_index_bcm
                    relay_set(pin_bcm=pin_bcm, value=value, from_web=False)
                else:
                    logger.warning('Could not find gpio record for custom relay pin code={}'.format(gpio_pin_code))

        else:
            id = utils.get_object_field_value(json_object, 'id')
            record = models.ZoneCustomRelay(id=id)
            assert isinstance(record, models.ZoneCustomRelay)
            record.relay_pin_name = utils.get_object_field_value(json_object, 'relay_pin_name')
            record.zone_id = utils.get_object_field_value(json_object, 'zone_id')
            record.gpio_pin_code = utils.get_object_field_value(json_object, 'gpio_pin_code')
            record.gpio_host_name = utils.get_object_field_value(json_object, 'gpio_host_name')
            record.relay_is_on = utils.get_object_field_value(json_object, 'relay_is_on')
            record.updated_on = utils.get_base_location_now_date()
            current_record = models.ZoneCustomRelay.query.filter_by(id=id).first()
            record.save_changed_fields(current_record=current_record, new_record=record, notify_transport_enabled=False,
                                       save_to_graph=False)
            db.session.commit()
    except Exception, ex:
        logger.warning('Error on zone custom relay update, err {}'.format(ex))

def unload():
    global initialised
    if constant.HOST_MACHINE_TYPE in [constant.MACHINE_TYPE_RASPBERRY, constant.MACHINE_TYPE_BEAGLEBONE]:
        logger.info('Unloading gpio pins')
        gpio_pi_bbb.unload()
    initialised = False

def init():
    logger.info("Relay initialising")
    global initialised

    @app.route('/relay/get')
    def relay_get_web():
        pin=request.args.get('pin', '').strip()
        if pin == '':
            response = return_web_message(pin_value=None, err_message='Argument [pin] not provided')
        else:
            response = relay_get(pin=pin, from_web=True)
        return response

    @app.route('/relay/set')
    def relay_set_web():
        pin=request.args.get('pin', '').strip()
        value=request.args.get('value', '').strip()
        if pin == '':
            response = return_web_message(pin_value=None, err_message='Argument [pin] not provided')
        elif value == '':
            response = return_web_message(pin_value=None, err_message='Argument [value] not provided')
        else:
            response = relay_set(pin_bcm=pin, value=value, from_web=True)
        return response
    initialised = True


