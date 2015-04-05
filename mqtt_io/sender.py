__author__ = 'dcristian'

import logging
import sys
import datetime
import mqtt_io
from main.admin import model_helper
from common import constant

def send_message(txt):
    try:
        logging.debug('Sending message at {} [{}] '.format(datetime.datetime.now(), txt))
        if mqtt_io.client_connected:
            mqtt_io.mqtt_client.publish(mqtt_io.topic, txt)
        else:
            logging.debug('MQTT client not connected, retrying connect, message to be discarded: {}'.format(txt))
            mqtt_io.init()
    except Exception, ex:
        logging.critical('Error sending mqtt message, {}'.format(ex))