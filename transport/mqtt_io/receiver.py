__author__ = 'dcristian'
import socket
import datetime
from pydispatch import dispatcher
from main import logger
from common.utils import json2obj
from common import constant, utils
import transport.mqtt_io


__last_message_received = utils.get_base_location_now_date()
__last_minute = 0




# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    try:
        global __last_message_received, __last_minute
        if utils.get_base_location_now_date().minute != __last_minute:
            __last_minute = utils.get_base_location_now_date().minute
            transport.mqtt_io.mqtt_msg_count_per_minute = 0

        transport.mqtt_io.mqtt_msg_count_per_minute += 1
        __last_message_received = utils.get_base_location_now_date()
        logger.debug('Received from client [{}] userdata [{}] msg [{}] at {} '.format(client._client_id,
                                                                                      userdata, msg.topic,
                                                                                      utils.get_base_location_now_date()))
        # locate json string
        start = msg.payload.find('{')
        end = msg.payload.find('}')
        json = msg.payload[start:end + 1]
        x = json2obj(json)
        logger.debug('Message received is {}'.format(json))
        start = utils.get_base_location_now_date()
        dispatcher.send(signal=constant.SIGNAL_MQTT_RECEIVED, client=client, userdata=userdata, topic=msg.topic, obj=x)
        elapsed = (utils.get_base_location_now_date() - start).total_seconds()
        if elapsed>5:
            logger.warning('Command received took {} seconds'.format(elapsed))
        if hasattr(x, 'command') and hasattr(x, 'command_id') and hasattr(x, 'host_target'):
            if x.host_target == socket.gethostname():
                logger.info('Executing command {}'.format(x.command))
            else:
                print "Received command {} for other host {}".format(x, x.host_target)
    except AttributeError, ex:
        logger.warning('Unknown attribute error in msg {} err {}'.format(json, ex))
    except ValueError, e:
        logger.warning('Invalid JSON {} {}'.format(json, e))


def thread_run():
    logger.debug('Processing mqtt_io receiver')
    global __last_message_received
    seconds_elapsed = (utils.get_base_location_now_date() - __last_message_received).total_seconds()
    if seconds_elapsed > 120:
        logger.warning('Last mqtt message was received {} seconds ago, unusually long'.format(seconds_elapsed))
        transport.mqtt_io.init()
    # mqtt_io.mqtt_client.loop(timeout=1)
    return 'Processed template_run'