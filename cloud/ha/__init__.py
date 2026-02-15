import datetime

from main.logger_helper import L
from main import thread_pool
from pydispatch import dispatcher
from common import Constant, get_json_param
from transport import mqtt_io
import transport
import threading
import prctl
import common
from storage.dicts.model import HADiscoverableDevice
from storage.dicts import model

class P:
    event_list = []
    func_list = None
    initialised = False
    ha_topic = None
    mqtt_topic_receive = None
    mqtt_topic_receive_prefix = None
    discovery_timestamps = {}
    discovery_resent_period = 60*60
    availability_timestamps = {}

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

class TemplateSensorDiscovery:
    """{
    "name":"<sensor_name>",
    "unique_id":"<unique_sensor_id>",
    "availability_topic":"<availability_topic>",
    "state_topic":"<state_topic>",
    "device":{
        "name":"<device_name>",
        "identifiers":["<unique_device_id>"],
        "model":"haiot"
        }
    ,"device_class":"<device_class>",
    "unit_of_measurement":"<unit_of_measurement>"
    }"""
    availability_topic = '<ha_mqtt_prefix><device_name>/status'
    state_topic = '<ha_mqtt_prefix><device_type>/<unique_sensor_id>/state'

def _get_variables(obj):
    device_name = type(obj).__name__ + "_" + "{}".format(getattr(obj, obj._main_key)).replace(":", "-")
    device_name = device_name.replace(' ', '_')
    # https://www.home-assistant.io/integrations/mqtt/#discovery-payload
    if hasattr(obj, "ha_device_type"):
        device_type = obj.ha_device_type
    else:
        device_type = "sensor"
    availability_topic = TemplateSensorDiscovery.availability_topic.replace(
        "<ha_mqtt_prefix>", P.ha_topic).replace(
        "<device_name>", device_name)
    return device_name, device_type, availability_topic

def parse_rules(obj, change):
    """ running rule method corresponding with obj type """
    if issubclass(type(obj), HADiscoverableDevice):
        # executed on all db value changes
        device_name, device_type, availability_topic = _get_variables(obj)
        if device_name not in P.discovery_timestamps.keys():
            L.l.info("Detected realtime new object not in config, {}".format(device_name))
            announce_discovery(obj)
        for item in change:
            if item != 'updated_on' and item != 'source_host':
                sensor_unique_id = device_name + '_' + item
                topic = "{}{}/{}/state".format(P.ha_topic, device_type, sensor_unique_id)
                value = "{}".format(getattr(obj, item))
                # payload = P.sensor_template.replace("<device_class>", item).replace("<sensor_value>", value)
                payload = value
                send_mqtt_ha(topic=topic, payload=payload)
                send_mqtt_ha(topic=availability_topic, payload="online")
                P.availability_timestamps[device_name] = datetime.datetime.now()

def send_mqtt_ha(topic, payload):
    transport.send_message_topic(topic=topic, json=payload)

def mqtt_on_message(client, userdata, msg):
    try:
        item = msg.topic.split(P.mqtt_topic_receive_prefix)
        payload = msg.payload.decode('utf-8').lower()
        # L.l.info('Got ha mqtt {}={}'.format(msg.topic, payload))
    except Exception as ex:
        L.l.error('Error ha mqtt {} ex={}'.format(msg.payload, ex), exc_info=True)

def announce_discovery(obj):
    device_name, device_type, availability_topic = _get_variables(obj)
    # publish a discoverable package periodically
    if device_name in P.discovery_timestamps.keys():
        last_discovery = P.discovery_timestamps[device_name]
    else:
        last_discovery = datetime.datetime.min

    if (datetime.datetime.now() - last_discovery).total_seconds() > P.discovery_resent_period:
        ha_field_list = obj.ha_fields.strip().split(',')
        device_class_list = obj.ha_device_class.strip().split(',')
        device_class_unit_list = obj.ha_device_class_unit.strip().split(',')
        index = 0
        for ha_field in ha_field_list:
            device_class = device_class_list[index]
            device_unit = device_class_unit_list[index]
            sensor_unique_id = device_name + '_' + ha_field
            sensor_name = device_name + ' ' + ha_field
            subtopic_discovery = "{}{}/{}/{}/config".format(P.ha_topic, device_type, device_name, sensor_unique_id)
            state_topic = TemplateSensorDiscovery.state_topic.replace(
                "<ha_mqtt_prefix>", P.ha_topic).replace(
                "<device_type>", device_type).replace(
                "<unique_sensor_id>", sensor_unique_id)
            payload = TemplateSensorDiscovery.__doc__.replace(
                "<sensor_name>", sensor_name).replace(
                "<unique_sensor_id>", sensor_unique_id).replace(
                "<availability_topic>", availability_topic).replace(
                "<state_topic>", state_topic).replace(
                "<ha_mqtt_prefix>", P.ha_topic).replace(
                "<device_type>", device_type).replace(
                "<device_name>", device_name).replace(
                "<unique_device_id>", device_name).replace(
                "<device_class>", device_class).replace(
                "<unit_of_measurement>", device_unit)
            if ',"device_class":"",' in payload:
                payload = payload.replace(',"device_class":"",', '').replace(
                    '"unit_of_measurement":""', '')
            send_mqtt_ha(topic=subtopic_discovery, payload=payload)
            L.l.info("Published HA discovery to {}, payload={}".format(subtopic_discovery, payload))
            index += 1
        # else:
        #    send_mqtt_ha(subtopic=subtopic, payload=payload)
        P.discovery_timestamps[device_name] = datetime.datetime.now()

def discovery():
    cls_dict = dict([(name, cls) for name, cls in model.__dict__.items() if isinstance(cls, type)])
    #sorted_keys = sorted(cls_dict)
    for cls in cls_dict.values():
        if issubclass(cls, HADiscoverableDevice) and cls.__name__ != "HADiscoverableDevice":
            rec_list = cls.find()
            if rec_list is not None:
                for obj in rec_list:
                    announce_discovery(obj)

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
    #discovery()
    mqtt_io.P.mqtt_client.message_callback_add(P.mqtt_topic_receive, mqtt_on_message)
    mqtt_io.add_message_callback(P.mqtt_topic_receive, mqtt_on_message)
    #thread_pool.add_interval_callable(thread_run, run_interval_second=30)
    dispatcher.connect(parse_rules, signal=Constant.SIGNAL_DB_CHANGE_FOR_RULES, sender=dispatcher.Any)
    P.initialised = True