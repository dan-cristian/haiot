__author__ = 'dcristian'

import datetime

from main import logger
import transport.mqtt_io


def send_message(txt):
    try:
        #logger.debug('Sending message at {} [{}] '.format(datetime.datetime.now(), txt))
        if transport.mqtt_io.client_connected:
            transport.mqtt_io.mqtt_client.publish(transport.mqtt_io.topic, txt)
        else:
            #logger.debug('MQTT client not connected, retrying connect, message to be discarded: {}'.format(txt))
            transport.mqtt_io.init()
    except Exception, ex:
        print ('Error sending mqtt message, {}'.format(ex))