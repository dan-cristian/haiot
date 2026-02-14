import datetime

from main.logger_helper import L
from main import thread_pool
from pydispatch import dispatcher
from common import Constant, get_json_param
from inspect import getmembers, isfunction
from transport import mqtt_io
import transport
import threading
import prctl
from storage.dicts.model import HADiscoverableDevice

class P:
    event_list = []
    func_list = None
    initialised = False
    ha_topic = None
    mqtt_topic_receive = None
    mqtt_topic_receive_prefix = None
    discovery_timestamps = {}
    discovery_resent_period = 60*60

    # https://www.home-assistant.io/integrations/mqtt/#sensors
    discovery_template_1=('{"unique_id":"<unique_id>",' +
                        '"device_class":"<device_class>",' +
                        '"unit_of_measurement":"<unit_of_measurement>",' +
                        '"state_topic":"<ha_mqtt_prefix><device_type>/<unique_id>/state",' +
                        '"value_template":"{{ value_json.<device_class> }}",' +
                        '"device":{"identifiers":["<device_identifier_name>"],' +
                         '"name":"<location_name>"}}')

    discovery_template = ('{"unique_id":"<unique_id>",' +
                            '"device_class":"<device_class>",' +
                            '"unit_of_measurement":"<unit_of_measurement>",' +
                            '"state_topic":"<ha_mqtt_prefix><device_type>/<unique_id>/state",' +
                            #'"enabled_by_default": true,' +
                            #'"value_template":"{{ value_json.<device_class> }}",' +
                            '"device":{"identifiers":["<unique_id>"],' +
                            '"name":"<unique_id>",' +
                            '"model":"haiot"}}')
    sensor_template = '{<device_class>:<sensor_value>}'

    def __init__(self):
        pass

def parse_rules(obj, change):
    """ running rule method corresponding with obj type """
    # executed on all db value changes
    if isinstance(obj, HADiscoverableDevice):
        device_name = type(obj).__name__ + "_" + "{}".format(getattr(obj, obj._main_key)).replace(":", "-")
        device_name = device_name.replace(' ', '_')
        # publish a discoverable package periodically
        # https://www.home-assistant.io/integrations/mqtt/#discovery-payload
        if hasattr(obj, "ha_device_type"):
            device_type = obj.ha_device_type
        else:
            device_type = "sensor"

        if device_name in P.discovery_timestamps.keys():
            last_discovery = P.discovery_timestamps[device_name]
        else:
            last_discovery = datetime.datetime.min
        if (datetime.datetime.now() - last_discovery).total_seconds() > P.discovery_resent_period:
            if hasattr(obj, "ha_device_class") and hasattr(obj, "ha_device_class_unit"):
                ha_field_list = obj.ha_fields.strip().split(',')
                device_class_list = obj.ha_device_class.strip().split(',')
                device_class_unit_list = obj.ha_device_class_unit.strip().split(',')
                index = 0
                for ha_field in ha_field_list:
                    device_class = device_class_list[index]
                    device_unit = device_class_unit_list[index]
                    device_unique_id = device_name + '_' + ha_field
                    subtopic = "{}/{}/config".format(device_type, device_unique_id)
                    payload = P.discovery_template.replace(
                        "<unique_id>", device_unique_id).replace(
                        "<device_class>", device_class).replace(
                        "<unit_of_measurement>", device_unit).replace(
                        "<ha_mqtt_prefix>", P.ha_topic).replace(
                        "<device_type>", device_type).replace(
                        "<device_identifier_name>", device_name).replace(
                        "<location_name>", device_name)
                    if '"device_class":"",' in payload:
                        payload = payload.replace('"device_class":"",','').replace(
                            '"unit_of_measurement":"",','')
                    send_mqtt_ha(subtopic=subtopic, payload=payload)
                    L.l.info("Published HA discovery to {}, payload={}".format(subtopic, payload))
                    index += 1
            #else:
            #    send_mqtt_ha(subtopic=subtopic, payload=payload)
            P.discovery_timestamps[device_name] = datetime.datetime.now()

        for item in change:
            if item != 'updated_on' and item != 'source_host':
                device_unique_id = device_name + '_' + item
                subtopic = "{}/{}/state".format(device_type, device_unique_id)
                value = "{}".format(getattr(obj, item))
                # payload = P.sensor_template.replace("<device_class>", item).replace("<sensor_value>", value)
                payload = value
                send_mqtt_ha(subtopic=subtopic, payload=payload)


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

def send_mqtt_ha(subtopic, payload):
    transport.send_message_topic(topic=P.ha_topic + subtopic, json=payload)

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