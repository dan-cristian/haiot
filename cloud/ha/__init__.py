import datetime

from main.logger_helper import L
from main import thread_pool
from pydispatch import dispatcher
from common import Constant, get_json_param
from inspect import getmembers, isfunction
from transport import mqtt_io
import threading
import prctl
from storage.dicts.model import HADiscoverableDevice

class P:
    event_list = []
    func_list = None
    initialised = False
    mqtt_topic_receive = None
    mqtt_topic_receive_prefix = None
    discovery_resent_period = 60*60

    def __init__(self):
        pass

def parse_rules(obj, change):
    """ running rule method corresponding with obj type """
    # executed on all db value changes
    if isinstance(obj, HADiscoverableDevice):
        # publish a discoverable package periodically
        if (datetime.datetime.now() - obj.ha_discovery_sent_on).total_seconds() > P.discovery_resent_period:
            for item in change:
                #if item in obj.get_device_class():
                #    obj.ha_device_class = item
                #else:
                #    obj.ha_device_class = "Generic"
                # obj.ha_unique_id = obj.get_ha_unique_id()
                pass


        L.l.debug('Received ha obj={} change={} for rule parsing'.format(obj, change))
        if hasattr(obj, Constant.JSON_PUBLISH_SOURCE_HOST):
            source = getattr(obj, Constant.JSON_PUBLISH_SOURCE_HOST)
        elif hasattr(obj, Constant.JSON_PUBLISH_SRC_HOST):
            source = getattr(obj, Constant.JSON_PUBLISH_SRC_HOST)
        else:
            source = 'unknown'
        # process all changes from all hosts
        # if source == Constant.HOST_NAME or source is None:
        try:
            # extract only changed fields
            if hasattr(obj, Constant.JSON_PUBLISH_FIELDS_CHANGED):
                change = obj.last_commit_field_changed_list
            else:
                change = change
            #generate standard messages for home_assistant
            #print(change)
        except Exception as ex:
            L.l.exception('Error parsing ha rules, ex={}'.format(ex))

def mqtt_on_message(client, userdata, msg):
    try:
        item = msg.topic.split(P.mqtt_topic_receive_prefix)
        payload = msg.payload.decode('utf-8').lower()
        # L.l.info('Got ha mqtt {}={}'.format(msg.topic, payload))
    except Exception as ex:
        L.l.error('Error ha mqtt {} ex={}'.format(msg.payload, ex), exc_info=True)

def thread_run():
    prctl.set_name("ha")
    threading.current_thread().name = "ha"
    prctl.set_name("idle_ha")
    threading.current_thread().name = "idle_ha"

def unload():
    L.l.info('HA module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False

def init():
    L.l.info('HA module initialising')
    P.ha_topic = get_json_param(Constant.P_MQTT_TOPIC_HA_SEND)
    P.mqtt_topic_receive = get_json_param(Constant.P_MQTT_TOPIC_HA_RECEIVE)
    P.mqtt_topic_receive_prefix = P.mqtt_topic_receive.replace('#', '')
    mqtt_io.P.mqtt_client.message_callback_add(P.mqtt_topic_receive, mqtt_on_message)
    mqtt_io.add_message_callback(P.mqtt_topic_receive, mqtt_on_message)
    thread_pool.add_interval_callable(thread_run, run_interval_second=1)
    dispatcher.connect(parse_rules, signal=Constant.SIGNAL_DB_CHANGE_FOR_RULES, sender=dispatcher.Any)
    P.initialised = True