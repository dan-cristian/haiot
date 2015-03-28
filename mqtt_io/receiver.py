__author__ = 'dcristian'
import socket
import logging
import datetime
import sys
from pydispatch import dispatcher
from common.utils import json2obj
from common import constant


def on_subscribe(client, userdata, mid, granted_qos):
    logging.info('Subscribed to client {} user {} mid {} qos {}'.format(
        str(client), str(userdata), str(mid), str(granted_qos)))


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    logging.debug('Received from client [{}] userdata [{}] msg [{}] at {} '.format(client._client_id,
                                                                                         userdata, msg.topic,
                                                                                          datetime.datetime.now()))
    try:
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