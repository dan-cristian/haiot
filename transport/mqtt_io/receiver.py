__author__ = 'dcristian'
import socket
import threading
import prctl
from pydispatch import dispatcher
from main.logger_helper import L
from common.utils import json2obj
from common import Constant, utils
import transport.mqtt_io

class P:
    last_rec = utils.get_base_location_now_date()
    last_minute = 0


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    json = msg
    try:
        if utils.get_base_location_now_date().minute != P.last_minute:
            P.last_minute = utils.get_base_location_now_date().minute
            transport.mqtt_io.mqtt_msg_count_per_minute = 0
        transport.mqtt_io.mqtt_msg_count_per_minute += 1
        P.last_rec = utils.get_base_location_now_date()
        #L.l.debug('Received from client [{}] userdata [{}] msg [{}] at {} '.format(client._client_id,
        #                                                                           userdata, msg.topic,
        #                                                                           utils.get_base_location_now_date()))
        # locate json string
        start = msg.payload.find('{')
        end = msg.payload.find('}')
        json = msg.payload[start:end + 1]
        if '"source_host_": "{}"'.format(Constant.HOST_NAME) not in json:
            # ignore messages send by this host
            x = json2obj(json)
            #if x[Constant.JSON_PUBLISH_SOURCE_HOST] != str(Constant.HOST_NAME):
            start = utils.get_base_location_now_date()
            dispatcher.send(signal=Constant.SIGNAL_MQTT_RECEIVED, client=client, userdata=userdata, topic=msg.topic, obj=x)
            elapsed = (utils.get_base_location_now_date() - start).total_seconds()
            if elapsed > 5:
                L.l.warning('Command received took {} seconds'.format(elapsed))
            if False:
                if hasattr(x, 'command') and hasattr(x, 'command_id') and hasattr(x, 'host_target'):
                    if x.host_target == Constant.HOST_NAME:
                        L.l.info('Executing command {}'.format(x.command))
                    else:
                        L.l.info("Received command {} for other host {}".format(x, x.host_target))
    except AttributeError as ex:
        L.l.warning('Unknown attribute error in msg {} err {}'.format(json, ex))
    except ValueError as e:
        L.l.warning('Invalid JSON {} {}'.format(json, e))


def thread_run():
    prctl.set_name("mqtt_receiver")
    threading.current_thread().name = "mqtt_receiver"
    # L.l.debug('Processing mqtt_io receiver')
    seconds_elapsed = (utils.get_base_location_now_date() - P.last_rec).total_seconds()
    if seconds_elapsed > 120:
        L.l.warning('Last mqtt message received {} seconds ago, unusually long'.format(seconds_elapsed))
        transport.mqtt_io.init()
    # mqtt_io.mqtt_client.loop(timeout=1)
    return 'Processed template_run'
