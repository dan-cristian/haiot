import transport.mqtt_io
from common import utils
from main.logger_helper import Log

__author__ = 'dcristian'


def send_message(txt):
    try:
        # Log.logger.debug('Sending message at {} [{}] '.format(utils.get_base_location_now_date(), txt))
        if transport.mqtt_io.client_connected:
            transport.mqtt_io.mqtt_client.publish(transport.mqtt_io.topic, txt)
            return True
        else:
            # Log.logger.debug('MQTT client not connected, retrying connect, message to be discarded: {}'.format(txt))
            elapsed = (utils.get_base_location_now_date() - transport.mqtt_io.last_connect_attempt).total_seconds()
            if elapsed > 10:
                transport.mqtt_io.init()
            return False
    except Exception, ex:
        Log.logger.error('Error sending mqtt message, {}'.format(ex), exc_info=True)
        return False