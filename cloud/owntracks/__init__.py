from main.logger_helper import L
import json
from main import thread_pool
from pydispatch import dispatcher
from common import Constant, get_json_param
from transport import mqtt_io


class P:
    initialised = False
    mqtt_topic_receive = None
    mqtt_topic_receive_prefix = None

    def __init__(self):
        pass


def mqtt_on_message(client, userdata, msg):
    try:
        item = msg.topic.split(P.mqtt_topic_receive_prefix)
        payload = msg.payload.decode('utf-8').lower()
        L.l.info('Got owncloud mqtt {}={}'.format(msg.topic, payload))
        json_obj = json.loads(payload)
        if json_obj['_type'] == 'location':
            lat = json_obj['lat']
            lon = json_obj['lon']
            alt = json_obj['alt']
            vel = json_obj['vel']
            bat = json_obj['batt']
            if 'inregions' in json_obj:
                for reg in json_obj['inregions']:
                    pass

    except Exception as ex:
        L.l.error('Error owntracks mqtt {} ex={}'.format(msg.payload, ex), exc_info=True)


def unload():
    L.l.info('Owntracks module unloading')
    #thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Owntracks module initialising')
    # rules.P.openhab_topic = get_json_param(Constant.P_MQTT_TOPIC_OPENHAB_SEND)
    P.mqtt_topic_receive = get_json_param(Constant.P_MQTT_TOPIC_OWNTRACKS_RECEIVE)
    P.mqtt_topic_receive_prefix = P.mqtt_topic_receive.replace('#', '')
    mqtt_io.P.mqtt_client.message_callback_add(P.mqtt_topic_receive, mqtt_on_message)
    mqtt_io.add_message_callback(P.mqtt_topic_receive, mqtt_on_message)
    P.initialised = True
