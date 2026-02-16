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
    unique_id_mapping = {} # memory store for all objects defined in ha carrying commands, used for incoming actions

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
    "command_topic":"<command_topic>",
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
    command_topic = '<ha_mqtt_prefix>receive/<device_type>/<unique_sensor_id>/command'

def _get_variables(obj):
    device_name = type(obj).__name__ + "_" + "{}".format(getattr(obj, obj._main_key)).replace(":", "-")
    device_name = device_name.replace(' ', '_')
    # https://www.home-assistant.io/integrations/mqtt/#discovery-payload
    fields = {}
    fields_atoms = obj.ha_fields.split(",")
    for field in fields_atoms:
        try:
            key = field.split(":")[0]
            defs = []
            remaining = field[len(key)+1:]
            # [field class-temperature, field unit measurement-Wh, field type-sensor/switch]
            for atom in remaining.split(":"):
                defs.append(atom)
            fields[key] = defs
        except Exception as ex:
            L.l.error("Cannot process ha definitions for {}".format(device_name))
    availability_topic = TemplateSensorDiscovery.availability_topic.replace(
        "<ha_mqtt_prefix>", P.ha_topic).replace(
        "<device_name>", device_name)
    return device_name, fields, availability_topic

def parse_rules(obj, change):
    """ running rule method corresponding with obj type """
    if issubclass(type(obj), HADiscoverableDevice):
        # executed on all db value changes
        device_name, ha_fields, availability_topic = _get_variables(obj)
        index = 0
        for item in change:
            if item != 'updated_on' and item != 'source_host':
                sensor_unique_id = device_name + '_' + item
                device_type = None
                if item in ha_fields.keys():
                    if len(ha_fields[item]) == 3:
                        device_type = ha_fields[item][2]
                    else:
                        L.l.error("Incorrect ha definition for device {} item {}".format(device_name, item))
                else:
                    L.l.info("Missing ha definition for device {} item {}".format(device_name, item))
                topic = "{}{}/{}/state".format(P.ha_topic, device_type, sensor_unique_id)
                value = "{}".format(getattr(obj, item))
                if sensor_unique_id not in P.discovery_timestamps.keys():
                    added = announce_discovery(obj, fields=[item])
                    L.l.info("Detected new object, added={}, {}={}".format(added, sensor_unique_id, value))
                # payload = P.sensor_template.replace("<device_class>", item).replace("<sensor_value>", value)
                if device_type == 'switch':
                    if value.lower() == 'true':
                        payload = 'off'
                    else:
                        payload = 'on'
                else:
                    payload = value
                send_mqtt_ha(topic=topic, payload=payload)
                send_mqtt_ha(topic=availability_topic, payload="online")
                P.availability_timestamps[device_name] = datetime.datetime.now()
            index += 1
def send_mqtt_ha(topic, payload):
    transport.send_message_topic(topic=topic, json=payload)

def mqtt_on_message(client, userdata, msg):
    try:
        item = msg.topic.split(P.mqtt_topic_receive_prefix)
        unique_id = None
        if len(item)==2:
            item = item[1].split("/")
            if len(item) >= 2:
                unique_id = item[1]
        if unique_id is not None:
            if unique_id in P.unique_id_mapping.keys():
                obj = P.unique_id_mapping[unique_id][0]
                field = P.unique_id_mapping[unique_id][1]
                payload = msg.payload.decode('utf-8').lower()
                if payload == 'on':
                    value = True
                elif payload == 'off':
                    value = False
                else:
                    L.l.warning("Unknown command value {} for id {}".format(payload, unique_id))
                L.l.info("Got ha command id {} value={}".format(unique_id, value))
                setattr(obj, field, value)
                obj.save_changed_fields(broadcast=False, persist=True, listeners=True)


        # L.l.info('Got ha mqtt {}={}'.format(msg.topic, payload))
    except Exception as ex:
        L.l.error('Error ha mqtt {} ex={}'.format(msg.payload, ex), exc_info=True)

def announce_discovery(obj, fields=None):
    added_one = False
    device_name, ha_fields, availability_topic = _get_variables(obj)
    ha_field_list = ha_fields.keys()
    index = 0
    for ha_field in ha_field_list:
        if fields is not None and ha_field in fields:
            if index >= len(ha_field_list):
                L.l.error("Too many unexpected fields vs ha object definition for {}, {}".format(obj, fields))
            else:
                device_class = ha_fields[ha_field][0]
                device_unit = ha_fields[ha_field][1]
                device_type = ha_fields[ha_field][2]
                sensor_unique_id = device_name + '_' + ha_field
                sensor_name = device_name + ' ' + ha_field
                topic_discovery = "{}{}/{}/{}/config".format(P.ha_topic, device_type, device_name, sensor_unique_id)
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
                if device_type == 'switch':
                    command_topic = TemplateSensorDiscovery.command_topic.replace(
                        "<ha_mqtt_prefix>", P.ha_topic).replace(
                        "<device_type>", device_type).replace(
                        "<unique_sensor_id>", sensor_unique_id)
                    P.unique_id_mapping[sensor_unique_id] = [obj, ha_field]
                    payload = payload.replace("<command_topic>", command_topic)
                send_mqtt_ha(topic=topic_discovery, payload=payload)
                L.l.info("Published HA discovery to {}, payload={}".format(topic_discovery, payload))
                P.discovery_timestamps[sensor_unique_id] = datetime.datetime.now()
                added_one = True
        index += 1
    return added_one

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