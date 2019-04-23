import transport.mqtt_io
from main.logger_helper import L
from main import sqlitedb
if sqlitedb:
    from main.admin import models
else:
    from main import tinydb_model as models
import transport
from common import Constant, utils


class P:
    openhab_topic = None
    ignored_fields = ['updated_on', '_id']

    def __init__(self):
        pass


def send_mqtt_openhab(subtopic, payload):
    transport.send_message_topic(payload, P.openhab_topic + "/" + subtopic)

#  OUTBOUND RULES START


def rule_openhab_sensor(obj=models.Sensor(), field_changed_list=None):
    if obj.sensor_name is None:
        L.l.warning('Got empty openhab sensor name {}'.format(obj))
        return
    key = 'temperature'
    if hasattr(obj, key) and obj.temperature is not None:
        # if obj.sensor_name == 'curte fata':
        #    obj_text = utils.dump_primitives_as_text(obj)
        #    L.l.info('CURTE TEMP={}'.format(obj_text))
        send_mqtt_openhab(subtopic=key + "_" + obj.sensor_name, payload=obj.temperature)
    key = 'humidity'
    if hasattr(obj, key) and obj.humidity is not None:
        send_mqtt_openhab(subtopic=key + "_" + obj.sensor_name, payload=obj.humidity)
    key = 'pressure'
    if hasattr(obj, key) and obj.pressure is not None:
        send_mqtt_openhab(subtopic=key + "_" + obj.sensor_name, payload=obj.pressure)
    key = 'vad'
    if hasattr(obj, key) and obj.vad is not None:
        send_mqtt_openhab(subtopic=key + "_" + obj.sensor_name, payload=obj.vad)
    key = 'vdd'
    if hasattr(obj, key) and obj.vdd is not None:
        send_mqtt_openhab(subtopic=key + "_" + obj.sensor_name, payload=obj.vdd)
    key = 'iad'
    if hasattr(obj, key) and obj.iad is not None:
        send_mqtt_openhab(subtopic=key + "_" + obj.sensor_name, payload=obj.iad)


def rule_openhab_dustsensor(obj=models.DustSensor(), field_changed_list=None):
    if field_changed_list is not None:
        address = obj.address
        for key in field_changed_list:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    send_mqtt_openhab(subtopic='dustsensor_' + key + '_' + address, payload=val)
                else:
                    L.l.warning('Field {} in dustsensor change list but not in obj={}'.format(key, obj))


def rule_openhab_utility(obj=models.Utility(), field_changed_list=None):
    if hasattr(obj, 'utility_type') and hasattr(obj, 'utility_name') and obj.utility_name is not None:
        # L.l.info("PROCESSING utility {}".format(obj.utility_type))
        key = 'electricity'
        if obj.utility_type == key:
            if obj.units_2_delta is not None:
                send_mqtt_openhab(subtopic=key + "_" + obj.utility_name, payload=obj.units_2_delta)
            if obj.units_delta is not None and obj.units_delta != 0:
                send_mqtt_openhab(subtopic=key + "_" + obj.unit_name + "_" + obj.utility_name,
                                  payload=obj.units_delta)
        key = 'water'
        if obj.utility_type == key and obj.units_delta is not None:
            send_mqtt_openhab(subtopic=key + "_" + obj.utility_name, payload=obj.units_delta)
        key = 'gas'
        if obj.utility_type == key and obj.units_delta is not None:
            send_mqtt_openhab(subtopic=key + "_" + obj.utility_name, payload=obj.units_delta)
    else:
        # L.l.info("NO UTILITY TYPE in {}".format(obj))
        if obj.utility_name is None:
            L.l.warning('Got empty openhab utility name {}'.format(obj))


def rule_openhab_alarm(obj=models.ZoneAlarm(), field_changed_list=None):
    if obj.alarm_pin_name is not None:
        key = 'contact'
        if obj.alarm_pin_triggered is True:
            state = "OPEN"
        else:
            state = "CLOSED"
        send_mqtt_openhab(subtopic=key + "_" + obj.alarm_pin_name, payload=state)
    else:
        L.l.warning('Got empty alarm pin name {}'.format(obj))


def rule_openhab_ups(obj=models.Ups(), field_changed_list=None):
    if field_changed_list is not None:
        key = 'power_failed'
        if key in field_changed_list:
            if obj.power_failed:
                state = "OFF"
            else:
                state = "ON"
            send_mqtt_openhab(subtopic="ups_" + key, payload=state)
        key = 'load_percent'
        if key in field_changed_list:
            send_mqtt_openhab(subtopic="ups_" + key, payload=obj.load_percent)
        key = 'battery_voltage'
        if key in field_changed_list:
            send_mqtt_openhab(subtopic="ups_" + key, payload=obj.battery_voltage)
        key = 'input_voltage'
        if key in field_changed_list:
            send_mqtt_openhab(subtopic="ups_" + key, payload=obj.input_voltage)


def rule_openhab_custom_relay(obj=models.ZoneCustomRelay(), field_changed_list=None):
    if field_changed_list is not None:
        if obj.relay_is_on:
            state = "ON"
        else:
            state = "OFF"
        send_mqtt_openhab(subtopic="relay_" + obj.relay_pin_name, payload=state)


def rule_openhab_heat_relay(obj=models.ZoneHeatRelay(), field_changed_list=None):
    if obj.heat_pin_name is not None:
        if field_changed_list is not None:
            if obj.heat_is_on:
                state = "ON"
            else:
                state = "OFF"
            send_mqtt_openhab(subtopic="heat_" + obj.heat_pin_name, payload=state)
    else:
        L.l.warning('Got empty heat relay pin name {}'.format(obj))


def rule_openhab_thermo(obj=models.ZoneThermostat(), field_changed_list=None):
    # if field_changed_list is not None and len(field_changed_list) > 0:
    #if 'heat_target_temperature' in field_changed_list:
    if hasattr(obj, 'heat_target_temperature'):
        temp = obj.heat_target_temperature
        if temp is not None:
            zone = obj.zone_name
            send_mqtt_openhab(subtopic='temperature_target_' + zone, payload=temp)
    #if 'heat_is_on' in field_changed_list:
    #0- Off, 1-Heating, 2- Cooling
    if obj.heat_is_on:
        state = 1
    else:
        state = 0
    zone = obj.zone_name
    send_mqtt_openhab(subtopic='temperature_mode_' + zone, payload=state)


def rule_openhab_music(obj=models.Music(), field_changed_list=None):
    if field_changed_list is not None:
        zone = obj.zone_name
        for key in field_changed_list:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    send_mqtt_openhab(subtopic='mpd_' + key + '_' + zone, payload=val)
                else:
                    L.l.warning('Field {} in music change list but not in obj={}'.format(key, obj))


def rule_openhab_powermonitor(obj=models.PowerMonitor(), field_changed_list=None):
    if field_changed_list is not None:
        name = obj.name
        for key in field_changed_list:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    send_mqtt_openhab(subtopic='powermonitor_' + key + '_' + name, payload=val)
                else:
                    L.l.warning('Field {} in power change list but not in obj={}'.format(key, obj))


def rule_openhab_musicloved(obj=models.MusicLoved(), field_changed_list=None):
    if field_changed_list is not None:
        for key in field_changed_list:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    if key == 'lastfmloved':
                        if val is True:
                            val = 'ON'
                        else:
                            val = 'OFF'
                    send_mqtt_openhab(subtopic='mpd_' + key, payload=val)
                else:
                    L.l.warning('Field musicloved {} in change list but not in obj={}'.format(key, obj))


# INBOUD RULES START
def custom_relay(name, value):
    # L.l.info("Try to set custom relay {} to {}".format(name, value))
    if sqlitedb:
        t = models.ZoneCustomRelay
        relay = t().query_filter_first(t.relay_pin_name == name)
    else:
        relay = models.ZoneCustomRelay.find_one({models.ZoneCustomRelay.relay_pin_name: name})
    if relay is not None:
        if relay.gpio_host_name == Constant.HOST_NAME:
            L.l.info("OK setting custom relay {} to {} from openhab".format(name, value))
            relay.relay_is_on = value
            relay.save_changed_fields(new_record=relay, notify_transport_enabled=True, save_all_fields=True)


def heat_relay(name, value):
    if sqlitedb:
        t = models.ZoneHeatRelay
        relay = t().query_filter_first(t.heat_pin_name == name)
    else:
        relay = models.ZoneHeatRelay.find_one({models.ZoneHeatRelay.heat_pin_name: name})
    if relay is not None:
        if relay.gpio_host_name == Constant.HOST_NAME:
            L.l.info("OK setting heat relay {} to {} from openhab".format(name, value))
            relay.heat_is_on = value
            relay.save_changed_fields(new_record=relay, notify_transport_enabled=True, save_all_fields=True)
