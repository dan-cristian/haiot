__author__ = 'dcristian'
import socket
import logging
import datetime
import sys
from pydispatch import dispatcher
from common.utils import json2obj
from common import constant
import mqtt_io

last_message_received=datetime.datetime.now()

def on_subscribe(client, userdata, mid, granted_qos):
    logging.info('Subscribed to client {} user {} mid {} qos {}'.format(
        str(client), str(userdata), str(mid), str(granted_qos)))


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    try:
        global last_message_received
        last_message_received = datetime.datetime.now()
        logging.debug('Received from client [{}] userdata [{}] msg [{}] at {} '.format(client._client_id,
                                                                                         userdata, msg.topic,
                                                                                          datetime.datetime.now()))
        # locate json string
        start = msg.payload.find('{')
        end = msg.payload.find('}')
        json = msg.payload[start:end + 1]
        x = json2obj(json)
        logging.debug('Message received is {}'.format(json))
        dispatcher.send(signal=constant.SIGNAL_MQTT_RECEIVED, client=client, userdata=userdata, topic=msg.topic, obj=x)
        if hasattr(x, 'command') and hasattr(x, 'command_id') and hasattr(x, 'host_target'):
            if x.host_target == socket.gethostname():
                logging.info('Executing command {}'.format(x.command))
            else:
                print "Received command {} for other host {}".format(x, x.host_target)
    except AttributeError, ex:
        logging.warning('Unknown attribute error in msg {} err {}'.format(json, ex))
    except ValueError, e:
        logging.warning('Invalid JSON {} {}'.format(json, e))

def thread_run():
    logging.debug('Processing mqtt_io receiver')
    global last_message_received
    seconds_elapsed = (datetime.datetime.now()-last_message_received).total_seconds()
    if seconds_elapsed > 60:
        logging.warning('Last mqtt message was received {} seconds ago, unusually long'.format(seconds_elapsed))
    #mqtt_io.mqtt_client.loop(timeout=1)
    return 'Processed template_run'