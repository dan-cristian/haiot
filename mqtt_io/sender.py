__author__ = 'dcristian'

import logging
import sys
import mqtt_io
from main.admin import model_helper
from common import constant

def send_message(txt):
    try:
        if mqtt_io.client_connected:
            mqtt_io.mqtt_client.publish(mqtt_io.topic, txt)
        else:
            logging.warning('MQTT client not connected, message to be discarded: {}'.format(txt))
    except Exception:
        logging.critical('Error sending mqtt message, {}'.format(sys.exc_info()[0]))