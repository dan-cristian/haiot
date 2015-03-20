__author__ = 'dcristian'
from main import app
from flask import request
import logging
from common import constant

initialised=False

def init():
    logging.info("Relay initialised")
    global initialised
    initialised = True

@app.route('/relay/get')
def relay_get():
    pin=request.args.get('pin', '')
    logging.info('Get relay state for pin ' + pin)
    return constant.SCRIPT_RESPONSE_OK + '=0'

@app.route('/relay/set')
def relay_set():
    pin=request.args.get('pin', '')
    value=request.args.get('value', '')
    logging.info('Set relay state for pin ' + pin)
    return constant.SCRIPT_RESPONSE_OK + '=' + value

