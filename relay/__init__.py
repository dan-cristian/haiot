__author__ = 'dcristian'
from main import app
from flask import request
import logging
from common import constant
import relay_pi

initialised=False

def unload():
    global initialised
    if constant.HOST_MACHINE_TYPE == constant.MACHINE_TYPE_RASPBERRY:
         relay_pi.unload()
    initialised = False

def init():
    logging.info("Relay initialising")
    global initialised

    @app.route('/relay/get')
    def relay_get():
        pin=request.args.get('pin', '')
        message = 'Get relay state for pin {}'.format(pin)
        logging.info(message)
        if constant.HOST_MACHINE_TYPE == constant.MACHINE_TYPE_RASPBERRY:
            return message + '\n' + constant.SCRIPT_RESPONSE_OK + '=' + relay_pi.get_pin_bcm(pin)
        else:
            return message + ' error not running on raspberry'

    @app.route('/relay/set')
    def relay_set():
        pin=request.args.get('pin', '')
        value=request.args.get('value', '')
        message = 'Set relay state {} for pin {}'.format(value, pin)
        logging.info(message)
        if constant.HOST_MACHINE_TYPE == constant.MACHINE_TYPE_RASPBERRY:
            return message + '\n' + constant.SCRIPT_RESPONSE_OK + '=' + relay_pi.set_pin_bcm(pin, value)
        else:
            return message + ' error not running on raspberry'

    initialised = True


