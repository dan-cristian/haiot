import datetime

import transport.mqtt_io
from main.logger_helper import L
from storage.model import m
import transport


class P:
    openhab_topic = None
    ignored_fields = ['updated_on', 'id', 'source_host']

    def __init__(self):
        pass


def send_mqtt_openhab(subtopic, payload):
    transport.send_message_topic(topic=P.openhab_topic + "/" + subtopic, json=payload)

#  OUTBOUND RULES START


def _get_state(bool_val):
    if bool_val is None:
        return None
    if bool_val:
        state = 'ON'
    else:
        state = 'OFF'
    return state


def rule_openhab_sensor(obj=m.Sensor(), change=None):
    if obj.sensor_name is None:
        L.l.warning('Got empty openhab sensor name {}'.format(obj))
        return
    key = 'temperature'
    if hasattr(obj, key) and obj.temperature is not None:
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


def rule_openhab_dustsensor(obj=m.DustSensor(), change=None):
    if change is not None:
        address = obj.address
        for key in change:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    send_mqtt_openhab(subtopic='dustsensor_' + key + '_' + address, payload=val)
                else:
                    L.l.warning('Field {} in dustsensor change list but not in obj={}'.format(key, obj))


def rule_openhab_airsensor(obj=m.AirSensor(), change=None):
    if change is not None:
        address = obj.address
        for key in change:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    address = address.replace(":", "_")  # safety conversion for openhab
                    if obj.name is None:
                        name = address
                    else:
                        name = obj.name
                    subtopic = 'airsensor_' + key + '_' + name
                    send_mqtt_openhab(subtopic=subtopic, payload=val)
                    # L.l.info("Sent AirSensor openhab {}={}".format(subtopic, val))
                else:
                    L.l.warning('Field {} in airsensor change list but not in obj={}'.format(key, obj))


def rule_openhab_ventilation(obj=m.Ventilation(), change=None):
    if change is not None:
        name = obj.name
        for key in change:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    send_mqtt_openhab(subtopic='ventilation_' + key + '_' + name, payload=val)
                else:
                    L.l.warning('Field {} in ventilation change list but not in obj={}'.format(key, obj))


def rule_openhab_vent(obj=m.Vent(), change=None):
    if change is not None:
        name = obj.name
        for key in change:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    send_mqtt_openhab(subtopic='vent_' + key + '_' + name, payload=val)
                else:
                    L.l.warning('Field {} in vent change list but not in obj={}'.format(key, obj))


def rule_openhab_bms(obj=m.Bms(), change=None):
    if change is not None:
        name = obj.name
        for key in change:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    send_mqtt_openhab(subtopic='bms_' + key + '_' + name, payload=val)
                else:
                    L.l.warning('Field {} in Bms change list but not in obj={}'.format(key, obj))


def rule_openhab_utility(obj=m.Utility(), change=None):
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
        if obj.utility_name is None:
            L.l.warning('Got empty openhab utility name {}'.format(obj))


def rule_openhab_alarm(obj=m.ZoneAlarm(), change=None):
    if obj.alarm_pin_name is not None:
        key = 'contact'
        if obj.alarm_pin_triggered is True:
            state = "OPEN"
        else:
            state = "CLOSED"
        send_mqtt_openhab(subtopic=key + "_" + obj.alarm_pin_name, payload=state)
    else:
        L.l.warning('Got empty alarm pin name {}'.format(obj))


def rule_openhab_ups(obj=m.Ups(), change=None):
    if change is not None:
        for key in change:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                else:
                    L.l.warning('Field {} in ups object change list but not in obj={}'.format(key, obj))
                    val = None
                # do some specific translations for openhab
                if key == 'power_failed':
                    if val:
                        val = "OFF"
                    else:
                        val = "ON"
                send_mqtt_openhab(subtopic='ups_' + key, payload=val)


def rule_openhab_custom_relay(obj=m.ZoneCustomRelay(), change=None):
    if change is not None:
        if obj.relay_is_on:
            state = "ON"
        else:
            state = "OFF"
        send_mqtt_openhab(subtopic="relay_" + obj.relay_pin_name, payload=state)


def rule_openhab_heat_relay(obj=m.ZoneHeatRelay(), change=None):
    if obj.heat_pin_name is not None:
        if change is not None:
            if obj.heat_is_on:
                state = "ON"
            else:
                state = "OFF"
            send_mqtt_openhab(subtopic="heat_" + obj.heat_pin_name, payload=state)
    else:
        L.l.warning('Got empty heat relay pin name {}'.format(obj))


def rule_openhab_thermo(obj=m.ZoneThermostat(), change=None):
    zone = obj.zone_name
    if hasattr(obj, 'heat_target_temperature'):
        temp = obj.heat_target_temperature
        if temp is not None:
            send_mqtt_openhab(subtopic='thermo_target_' + zone, payload=temp)
    # 0- Off, 1-Heating, 2- Cooling
    if obj.heat_is_on:
        state = 'ON'
    else:
        state = 'OFF'
    send_mqtt_openhab(subtopic='thermo_state_' + zone, payload=state)
    if obj.is_mode_manual:
        mode = 'ON'
    else:
        mode = 'OFF'
    send_mqtt_openhab(subtopic='thermo_mode_manual_' + zone, payload=mode)
    if obj.mode_presence_auto:
        mode = 'ON'
    else:
        mode = 'OFF'
    send_mqtt_openhab(subtopic='thermo_mode_presence_' + zone, payload=mode)


def rule_openhab_area_thermo(obj=m.AreaThermostat(), change=None):
    area = m.Area.find_one({m.Area.id: obj.area_id})
    if area is not None:
        if hasattr(obj, 'is_manual_heat'):
            state = _get_state(obj.is_manual_heat)
            if state is not None:
                send_mqtt_openhab(subtopic='areathermo_mode_manual_' + area.name, payload=state)


def rule_openhab_music(obj=m.Music(), change=None):
    if change is not None:
        zone = obj.zone_name
        for key in change:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    send_mqtt_openhab(subtopic='mpd_' + key + '_' + zone, payload=val)
                else:
                    L.l.warning('Field {} in music change list but not in obj={}'.format(key, obj))


def rule_openhab_powermonitor(obj=m.PowerMonitor(), change=None):
    if change is not None:
        name = obj.name
        for key in change:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    send_mqtt_openhab(subtopic='powermonitor_' + key + '_' + name, payload=val)
                else:
                    L.l.warning('Field {} in power change list but not in obj={}'.format(key, obj))


def rule_openhab_solarpanel(obj=m.SolarPanel(), change=None):
    if change is not None:
        id = obj.id
        for key in change:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    send_mqtt_openhab(subtopic='solarpanel_' + key + '_' + id, payload=val)
                else:
                    L.l.warning('Field {} in solarpanel change list but not in obj={}'.format(key, obj))


def rule_openhab_microinverter(obj=m.MicroInverter(), change=None):
    if change is not None:
        id = obj.name
        for key in change:
            if key not in P.ignored_fields:
                if hasattr(obj, key):
                    val = getattr(obj, key)
                    send_mqtt_openhab(subtopic='microinverter_' + key + '_' + id, payload=val)
                else:
                    L.l.warning('Field {} in MicroInverter change list but not in obj={}'.format(key, obj))


def rule_openhab_musicloved(obj=m.MusicLoved(), change=None):
    if change is not None:
        for key in change:
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
    relay = m.ZoneCustomRelay.find_one({m.ZoneCustomRelay.relay_pin_name: name})
    if relay is not None:
        # if relay.gpio_host_name == Constant.HOST_NAME or relay.gpio_host_name in ['', None]:
        L.l.info("Saving custom relay {} to {} from openhab".format(name, value))
        relay.relay_is_on = value
        relay.save_changed_fields(broadcast=True, persist=True)
    else:
        L.l.info('Not saving relay {} as is None'.format(name))


def heat_relay(name, value):
    relay = m.ZoneHeatRelay.find_one({m.ZoneHeatRelay.heat_pin_name: name})
    if relay is not None:
        # if relay.gpio_host_name == Constant.HOST_NAME:
        L.l.info("Saving heat relay {} to {} from openhab".format(name, value))
        relay.heat_is_on = value
        relay.save_changed_fields(broadcast=True, persist=True)
    else:
        L.l.info('Not saving relay {} as is None'.format(name))


def thermostat(zone_name=None, temp_target=None, state=None, mode_manual=None, mode_presence=None):
    L.l.info('Got thermo zone {} temp {} state {} mode_manual={} mode_presence={}'.format(zone_name, temp_target, state,
                                                                                          mode_manual, mode_presence))
    zone_thermo = m.ZoneThermostat.find_one({m.ZoneThermostat.zone_name: zone_name})
    if zone_thermo is None:
        zone = m.Zone.find_one({m.Zone.name: zone_name})
        if zone:
            zone_thermo = m.ZoneThermostat()
            zone_thermo.zone_id = zone.id
            zone_thermo.zone_name = zone_name
        else:
            L.l.warning("Could not find zone from thermo name={}".format(zone_name))

    if zone_thermo:
        if mode_manual is not None:
            zone_thermo.is_mode_manual = mode_manual
        if mode_presence is not None:
            zone_thermo.mode_presence_auto = mode_presence
        if state is not None:
            zone_thermo.heat_is_on = state
        if temp_target is not None:
            zone_thermo.heat_target_temperature = temp_target
        zone_thermo.save_changed_fields(persist=True)


def areathermostat(area_name=None, mode_manual=None):
    area = m.Area.find_one({m.Area.name: area_name})
    if area is not None:
        areath = m.AreaThermostat.find_one({m.AreaThermostat.area_id: area.id})
        if areath is not None:
            if mode_manual is not None:
                areath.is_manual_heat = mode_manual
            areath.save_changed_fields(persist=True)
