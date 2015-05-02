__author__ = 'dcristian'
from main import app
from flask import request
from main import logger
from common import constant, utils
from main.admin import db, models
import relay_pi

initialised=False

def relay_update(gpio_pin_code='', pin_is_on=''):
    #return pin value after state set
    try:
        logger.debug('Received relay state update pin {}'.format(gpio_pin_code))
        gpiopin = models.GpioPin.query.filter_by(pin_code=gpio_pin_code).first()
        pin_value = -1
        if gpiopin:
            pin_value = relay_set(gpiopin.pin_code, pin_is_on, from_web=False)
            gpiopin.pin_value = pin_value
            gpiopin.notify_transport_enabled = False
            db.session.commit()
        else:
            logger.warning('Pin {} does not exists locally'.format(gpio_pin_code))
    except Exception, ex:
        logger.warning('Error updating relay state err={}'.format(ex))
    return -1

def relay_get(pin=None, from_web=False):
    message = 'Get relay state for pin {}'.format(pin)
    logger.info(message)
    if constant.HOST_MACHINE_TYPE == constant.MACHINE_TYPE_RASPBERRY:
        pin_value = relay_pi.get_pin_bcm(pin)
    else:
        message = message + '\n error not running on raspberry'
        pin_value = None

    if from_web:
        return return_web_message(pin_value=pin_value, ok_message=message, err_message=message)
    else:
        return pin_value

def relay_set(pin=None, value=None, from_web=False):
    value = int(value)
    message = 'Set relay state {} for pin {}'.format(value, pin)
    logger.info(message)
    if constant.HOST_MACHINE_TYPE == constant.MACHINE_TYPE_RASPBERRY:
        pin_value = relay_pi.set_pin_bcm(pin, value)
    else:
        message = message + '\n error not running on raspberry'
        pin_value = None

    if from_web:
        return return_web_message(pin_value=pin_value, ok_message=message, err_message=message)
    else:
        return pin_value

def return_web_message(pin_value, ok_message='', err_message=''):
    if pin_value:
        return ok_message + '\n' + constant.SCRIPT_RESPONSE_OK + '=' + pin_value
    else:
        return err_message + '\n'

def unload():
    global initialised
    if constant.HOST_MACHINE_TYPE == constant.MACHINE_TYPE_RASPBERRY:
         relay_pi.unload()
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
            response = relay_set(pin=pin, value=value, from_web=True)
        return response
    initialised = True


