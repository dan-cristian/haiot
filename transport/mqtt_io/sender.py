__author__ = 'dcristian'

import datetime

from main import logger
import transport.mqtt_io
from common import utils

def send_message(txt):
    try:
        #logger.debug('Sending message at {} [{}] '.format(utils.get_base_location_now_date(), txt))
        if transport.mqtt_io.client_connected:
            transport.mqtt_io.mqtt_client.publish(transport.mqtt_io.topic, txt)
            return True
        else:
            #logger.debug('MQTT client not connected, retrying connect, message to be discarded: {}'.format(txt))
            elapsed = (utils.get_base_location_now_date() - transport.mqtt_io.last_connect_attempt).total_seconds()
            if elapsed > 10:
                transport.mqtt_io.init()
            return False
    except Exception, ex:
        print ('Error sending mqtt message, {}'.format(ex))
        return False