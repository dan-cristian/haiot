__author__ = 'dcristian'
from main import app
from flask import request
import logging
from common import constant, utils
from main.admin import db, models
import relay_pi

initialised=False

def relay_update(gpio_pin_code='', heat_is_on=''):
    #return pin value after state set
    try:
        logging.debug('Received relay state update pin {}'.format(gpio_pin_code))
        gpiopin = models.GpioPin.query.filter_by(pin_code=gpio_pin_code).first()
        pin_value = -1
        if gpiopin:
            pin_value = relay_set(gpiopin.pin_code, heat_is_on, from_web=False)
            gpiopin.pin_value = pin_value
            gpiopin.notify_transport_enabled = False
            db.session.commit()
        else:
            logging.warning('Pin {} does not exists locally'.format(gpio_pin_code))
    except Exception, ex:
        logging.warning('Error updating relay state')
    return -1

def relay_get(pin=None, from_web=False):
    message = 'Get relay state for pin {}'.format(pin)
    logging.info(message)
    if constant.HOST_MACHINE_TYPE == constant.MACHINE_TYPE_RASPBERRY:
        pin_value = relay_pi.get_pin_bcm(pin)
    else:
        pin_value = None
        message = message + ' error not running on raspberry'

    if from_web:
        if pin_value:
            return message + '\n' + constant.SCRIPT_RESPONSE_OK + '=' + pin_value
        else:
            return message #error case
    else:
        return pin_value

def relay_set(pin=None, value=None, from_web=False):
    value = int(value)
    message = 'Set relay state {} for pin {}'.format(value, pin)
    logging.info(message)
    if constant.HOST_MACHINE_TYPE == constant.MACHINE_TYPE_RASPBERRY:
        pin_value = relay_pi.set_pin_bcm(pin, value)
    else:
        message = message + ' error not running on raspberry'

    if from_web:
        if pin_value:
            return message + '\n' + constant.SCRIPT_RESPONSE_OK + '=' + pin_value
        else:
            return message #error case
    else:
        return pin_value

def unload():
    global initialised
    if constant.HOST_MACHINE_TYPE == constant.MACHINE_TYPE_RASPBERRY:
         relay_pi.unload()
    initialised = False

def init():
    logging.info("Relay initialising")
    global initialised

    @app.route('/relay/get')
    def relay_get_web():
        pin=request.args.get('pin', '')
        relay_get(pin=pin, from_web=True)

    @app.route('/relay/set')
    def relay_set_web():
        pin=request.args.get('pin', '')
        value=request.args.get('value', '')
        relay_set(pin=pin, value=value, from_web=True)


    initialised = True


