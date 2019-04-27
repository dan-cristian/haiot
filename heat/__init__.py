import inspect
import sys
import traceback
from pydispatch import dispatcher
from main import thread_pool
import datetime
import threading
import prctl
from main.logger_helper import L
from common import utils, Constant, get_json_param
import gpio
from storage.model import m

__author__ = 'dcristian'


class P:
    last_main_heat_update = datetime.datetime.min
    TEMP_NO_HEAT = '.'
    MAX_DELTA_TEMP_KEEP_WARM = 0.5  # keep warm a zone with floor heating, check not to go too hot above target temp
    threshold = None  # delta to avoid quick on/off
    temp_limit = None  # alternate source min temp
    check_period = 60  # how often to check for temp target change
    season = None
    PRESENCE_SEC = 60 * 60 * 1  # no of secs after a move considered to be presence
    AWAY_SEC = 60 * 60 * 6  # no of secs after no move to be considered away
    initialised = False
    debug = False
    thread_pool_status = None
    thread_local = None

    def __init__(self):
        pass


# save heat status and announce to all nodes.
def _save_heat_state_db(zone, heat_is_on):
    zone_heat_relay = m.ZoneHeatRelay.find_one({m.ZoneHeatRelay.zone_id: zone.id})
    zone_thermo = m.ZoneThermostat.find_one({m.ZoneThermostat.zone_id: zone.id})
    if zone_thermo is None:
        zone_thermo = m.ZoneThermostat()
        zone_thermo.zone_id = zone.id
        zone_thermo.zone_name = zone.name
    if zone_heat_relay is not None:
        zone_heat_relay.heat_is_on = heat_is_on
        # save latest heat state for caching purposes
        zone_thermo.heat_is_on = heat_is_on
        zone_thermo.last_heat_status_update = utils.get_base_location_now_date()
        zone_heat_relay.save_changed_fields(broadcast=True, persist=True)
        zone_thermo.save_changed_fields()
    else:
        L.l.warning('No heat relay found in zone {} id {}'.format(zone.name, zone.id))


# triggers heat status update if heat changed
def _decide_action(zone, current_temperature, target_temperature, force_on=False, force_off=False, zone_thermo=None):
    heat_is_on = None
    if force_on:
        heat_is_on = True
    if force_off:
        heat_is_on = False
    if heat_is_on is None:
        heat_is_on = zone_thermo.heat_is_on
        if heat_is_on is None:
            heat_is_on = False
        if current_temperature < target_temperature:
            heat_is_on = True
        if current_temperature > (target_temperature + P.threshold):
            heat_is_on = False
    # trigger if state is different and every 5 minutes (in case other hosts with relays have restarted)
    if zone_thermo.last_heat_status_update is not None:
        last_heat_update_age_sec = (utils.get_base_location_now_date()
                                    - zone_thermo.last_heat_status_update).total_seconds()
    else:
        last_heat_update_age_sec = P.check_period
    if zone_thermo.heat_is_on != heat_is_on or last_heat_update_age_sec >= P.check_period \
            or zone_thermo.last_heat_status_update is None:
        _save_heat_state_db(zone=zone, heat_is_on=heat_is_on)
    return heat_is_on


def _get_temp_target(pattern_id):
    hour = utils.get_base_location_now_date().hour
    schedule_pattern = m.SchedulePattern.find_one({m.SchedulePattern.id: pattern_id})
    # strip formatting characters that are not used to represent target temperature
    pattern = str(schedule_pattern.pattern).replace('-', '').replace(' ', '')
    # check pattern validity
    if len(pattern) == 24:
        temp_code = pattern[hour]
        temp_target = float(m.TemperatureTarget.find_one({m.TemperatureTarget.code: temp_code}).target)
    else:
        L.l.warning('Incorrect temp pattern [{}] in zone {}, length is not 24'.format(pattern, schedule_pattern.name))
        temp_target = None
        temp_code = None
    return temp_target, temp_code


# provide heat pattern
def _get_schedule_pattern(heat_schedule):
    weekday = datetime.datetime.today().weekday()
    heat_thermo = m.ZoneThermostat.find_one({m.ZoneThermostat.zone_id: heat_schedule.zone_id})
    schedule_pattern = None
    if heat_thermo is not None and heat_thermo.last_presence_set is not None:
        delta = (datetime.datetime.now() - heat_thermo.last_presence_set).total_seconds()
        if delta <= P.PRESENCE_SEC and heat_schedule.pattern_id_presence is not None:
            # we have recent move
            L.l.info("Move detected, set move heat pattern in zone id {}".format(heat_schedule.zone_id))
            schedule_pattern = m.SchedulePattern.find_one({m.SchedulePattern.id: heat_schedule.pattern_id_presence})
        if delta >= P.AWAY_SEC and heat_schedule.pattern_id_no_presence is not None:
            # no move for a while, switch to away
            L.l.info("No move detected, set away heat pattern in zone id {}".format(heat_schedule.zone_id))
            schedule_pattern = m.SchedulePattern.find_one({m.SchedulePattern.id: heat_schedule.pattern_id_no_presence})
    # if no recent move or away detected, set normal schedule
    if schedule_pattern is None:
        if weekday <= 4:  # Monday=0
            patt_id = heat_schedule.pattern_week_id
        else:
            patt_id = heat_schedule.pattern_weekend_id
        schedule_pattern = m.SchedulePattern.find_one({m.SchedulePattern.id: patt_id})
    return schedule_pattern


# turn heat source off in some cases, for alternate heat sources, when switching from solar to gas etc.
def _get_heat_off_condition(schedule_pattern):
    force_off = False
    relay_name = schedule_pattern.activate_condition_relay
    zone_heat_relay = m.ZoneHeatRelay.find_one({m.ZoneHeatRelay.heat_pin_name: relay_name})
    if zone_heat_relay is not None:
        force_off = zone_heat_relay.heat_is_on is False
    else:
        L.l.error('Could not find the heat relay for zone heat {}'.format(schedule_pattern.name))
    return force_off


# check if we need forced heat on, if for this hour temp has a upper target than min
def _get_heat_on_keep_warm(schedule_pattern, temp_code, temp_target, temp_actual):
    force_on = False
    if schedule_pattern.keep_warm and temp_actual is not None:
        minute = utils.get_base_location_now_date().minute
        if len(schedule_pattern.keep_warm_pattern) == 12:
            interval = int(minute / 5)
            delta_warm = temp_actual - temp_target
            if delta_warm <= P.MAX_DELTA_TEMP_KEEP_WARM:
                force_on = ((schedule_pattern.keep_warm_pattern[interval] == "1") and
                            temp_code is not P.TEMP_NO_HEAT)
                if force_on:
                    L.l.info("Forcing heat on due to keep warm, zone {}".format(schedule_pattern.name))
            else:
                L.l.info("Temp too high in {} with {}, ignoring keep warm".format(schedule_pattern.name, delta_warm))
        else:
            L.l.critical("Missing or incorrect keep warm pattern for zone {}={}".format(
                schedule_pattern.name, schedule_pattern.keep_warm_pattern))
    return force_on


# check if temp target is manually overridden
def _get_heat_on_manual(zone_thermo):
    force_on = False
    manual_temp_target = None
    if zone_thermo.last_manual_set is not None and zone_thermo.is_mode_manual:
        delta_minutes = (datetime.datetime.now() - zone_thermo.last_manual_set).total_seconds() / 60
        if delta_minutes <= zone_thermo.manual_duration_min:
            manual_temp_target = zone_thermo.manual_temp_target
            force_on = True
            L.l.info("Set heat on due to manual in {}, target={}".format(zone_thermo.zone_name, manual_temp_target))
        else:
            zone_thermo.is_mode_manual = False
            zone_thermo.last_manual_set = None
            zone_thermo.save_changed_fields()
            L.l.info("Manual heat expired {}, target={}".format(zone_thermo.zone_name, manual_temp_target))
    return force_on, manual_temp_target


# set and return the required heat state in a zone (True - on, False - off).
# Also return if main source is needed, usefull if you only heat a boiler from alternate heat source
def _update_zone_heat(zone, heat_schedule, sensor):
    heat_is_on = False
    main_source_needed = True
    zone_thermo = m.ZoneThermostat.find_one({m.ZoneThermostat.zone_id: zone.id})
    if zone_thermo is None:
        L.l.info('Adding zone thermo {}:{}'.format(zone.name, zone.id))
        zone_thermo = m.ZoneThermostat()
        zone_thermo.zone_id = zone.id
        zone_thermo.zone_name = zone.name
    try:
        schedule_pattern = _get_schedule_pattern(heat_schedule)
        if schedule_pattern:
            std_temp_target, temp_code = _get_temp_target(schedule_pattern.id)
            main_source_needed = schedule_pattern.main_source_needed
            # set heat to off if condition is met (i.e. do not try to heat water if heat source is cold)
            if std_temp_target is not None:
                act_temp_target = std_temp_target
                if schedule_pattern.activate_on_condition:
                    force_off = _get_heat_off_condition(schedule_pattern)
                else:
                    force_off = False
                force_on = _get_heat_on_keep_warm(schedule_pattern=schedule_pattern, temp_code=temp_code,
                                                  temp_target=std_temp_target, temp_actual=sensor.temperature)
                if not force_on:
                    force_on, manual_temp_target = _get_heat_on_manual(zone_thermo=zone_thermo)
                    if manual_temp_target is not None:
                        act_temp_target = manual_temp_target
                if zone_thermo.active_heat_schedule_pattern_id != schedule_pattern.id:
                    zone_thermo.active_heat_schedule_pattern_id = schedule_pattern.id
                zone_thermo.heat_target_temperature = std_temp_target
                zone_thermo.heat_actual_temperature = sensor.temperature
                zone_thermo.save_changed_fields()
                if sensor.temperature is not None:
                    heat_is_on = _decide_action(zone, sensor.temperature, act_temp_target, force_on=force_on,
                                                force_off=force_off, zone_thermo=zone_thermo)
            else:
                L.l.critical('Unknown temperature pattern code {}'.format(temp_code))
    except Exception as ex:
        L.l.error('Error updatezoneheat, err={}'.format(ex), exc_info=True)
    return heat_is_on, main_source_needed


# iterate zones and decide heat state for each zone and also for master zone (main heat system)
# if one zone requires heat master zone will be on
def _loop_zones():
    try:
        heat_is_on = False
        zone_list = m.Zone.find()
        for zone in zone_list:
            P.thread_pool_status = 'do zone {}'.format(zone.name)
            heat_schedule = m.HeatSchedule.find_one({m.HeatSchedule.zone_id: zone.id, m.HeatSchedule.season: P.season})
            zonesensor_list = m.ZoneSensor.find({m.ZoneSensor.zone_id: zone.id, m.ZoneSensor.is_main: True})
            sensor_processed = {}
            for zonesensor in zonesensor_list:
                if heat_schedule is not None and zonesensor is not None:
                    sensor = m.Sensor.find_one({m.Sensor.address: zonesensor.sensor_address})
                    if sensor is not None:
                        heat_state, main_source_needed = _update_zone_heat(zone, heat_schedule, sensor)
                        if not heat_is_on:
                            heat_is_on = main_source_needed and heat_state
                        if zonesensor.zone_id in sensor_processed:
                            prev_sensor = sensor_processed[zonesensor.zone_id]
                            L.l.warning('Already processed temp sensor {} in zone {}, duplicate?'.format(
                                prev_sensor, zonesensor.zone_id))
                        else:
                            sensor_processed[zonesensor.zone_id] = sensor.sensor_name
        # turn on/off the main heating system based on zone heat needs
        # check first to find alternate valid heat sources
        heatrelay_main_source = m.ZoneHeatRelay.find_one({m.ZoneHeatRelay.is_alternate_heat_source: True})
        if heatrelay_main_source is None:
            heatrelay_main_source = m.ZoneHeatRelay.find_one({m.ZoneHeatRelay.is_main_heat_source: True})
        if heatrelay_main_source is not None:
            main_source_zone = m.Zone.find_one({m.Zone.id: heatrelay_main_source.zone_id})
            main_thermo = m.ZoneThermostat.find_one({m.ZoneThermostat.zone_id: main_source_zone.id})
            if main_source_zone is not None:
                update_age_mins = (utils.get_base_location_now_date() - P.last_main_heat_update).total_seconds() / 60
                # # avoid setting relay state too often but do periodic refreshes every x minutes
                # check when thermo is none
                if main_thermo is None or (main_thermo.heat_is_on != heat_is_on or update_age_mins >=
                                           int(get_json_param(Constant.P_HEAT_STATE_REFRESH_PERIOD))):
                    L.l.info("Setting main heat on={}, zone={}".format(heat_is_on, main_source_zone.name))
                    _save_heat_state_db(zone=main_source_zone, heat_is_on=heat_is_on)
                    P.last_main_heat_update = utils.get_base_location_now_date()
            else:
                L.l.critical('No heat main_src found using zone id {}'.format(heatrelay_main_source.zone_id))
        else:
            L.l.critical('No heat main source is defined in db')
    except Exception as ex:
        L.l.error('Error loop_zones, err={}'.format(ex), exc_info=True)


# set which is the main heat source relay that must be set on
def _set_main_heat_source():
    P.thread_pool_status = 'set main source'
    heat_source_relay_list = m.ZoneHeatRelay.find({'$not': {m.ZoneHeatRelay.temp_sensor_name: None}})
    up_limit = P.temp_limit + P.threshold
    for heat_source_relay in heat_source_relay_list:
        # if heat_source_relay.heat_pin_name == 'puffer gas valve':
        #    traceback.print_stack()
        #    L.l.info('Debug 1 {}'.format(heat_source_relay))
        # is there is a temp sensor defined, consider this source as possible alternate source
        if heat_source_relay.temp_sensor_name is not None:
            temp_rec = m.Sensor.find_one({m.Sensor.sensor_name: heat_source_relay.temp_sensor_name})
            # if alternate source is valid
            # fixok: add temp threshold to avoid quick on/offs
            if temp_rec is not None \
                    and ((temp_rec.temperature >= up_limit and not heat_source_relay.is_alternate_source_switch)
                         or (temp_rec.temperature >= P.temp_limit and heat_source_relay.is_alternate_source_switch)):
                if heat_source_relay.is_alternate_source_switch:
                    # stop main heat source
                    heatrelay_main_source = m.ZoneHeatRelay.find_one({m.ZoneHeatRelay.is_main_heat_source: True})
                    main_source_zone = m.Zone.find_one({m.Zone.id: heatrelay_main_source.zone_id})
                    L.l.info('Stop main heat source {}'.format(main_source_zone))
                    _save_heat_state_db(zone=main_source_zone, heat_is_on=False)
                    # turn switch valve on to alternate position
                    switch_source_zone = m.Zone.find_one({m.Zone.id: heat_source_relay.zone_id})
                    L.l.info('Switch valve {} to on'.format(switch_source_zone))
                    _save_heat_state_db(zone=switch_source_zone, heat_is_on=True)
                else:
                    # mark this source as active, to be started when there is heat need
                    # if heat_source_relay.is_alternate_heat_source is False:
                    L.l.info('Alternate heat source is active with temp={}'.format(temp_rec.temperature))
                    heat_source_relay.is_alternate_heat_source = True
                    heat_source_relay.save_changed_fields()
            else:
                # if alternate source is no longer valid
                if heat_source_relay.is_alternate_source_switch:
                    # stop alternate heat source
                    # heatrelay_alt_source = models.ZoneHeatRelay.query.filter_by(is_alternate_heat_source=1).first()
                    # if heatrelay_alt_source is not None:
                    #    alt_source_zone = models.Zone.query.filter_by(id=heatrelay_alt_source.zone_id).first()
                    #    __save_heat_state_db(zone=alt_source_zone, heat_is_on=False)
                    # turn valve back to main position
                    switch_source_zone = m.Zone.find_one({m.Zone.id: heat_source_relay.zone_id})
                    L.l.info('Switch valve {} back'.format(switch_source_zone))
                    _save_heat_state_db(zone=switch_source_zone, heat_is_on=False)
                else:
                    # mark this source as inactive, let main source to start
                    if heat_source_relay.is_alternate_heat_source:
                        # force alt source shutdown if was on
                        alt_source_zone = m.Zone.find_one({m.Zone.id: heat_source_relay.zone_id})
                        L.l.info('Force alt source {} off'.format(alt_source_zone))
                        _save_heat_state_db(zone=alt_source_zone, heat_is_on=False)
                        # todo: sleep needed to allow for valve return
                    if heat_source_relay.is_alternate_heat_source is True:
                        L.l.info('Alternate heat source is now inactive, temp source is {}'.format(temp_rec))
                    heat_source_relay.is_alternate_heat_source = False
                    heat_source_relay.save_changed_fields()


# start/stop heat based on user movement/presence
def _handle_presence(zone_name=None, zone_id=None):
    if zone_id is not None:
        heat_thermo = m.ZoneThermostat.find_one({m.ZoneThermostat.zone_id: zone_id})
        if heat_thermo is not None:
            heat_thermo.last_presence_set = datetime.datetime.now()
        else:
            L.l.info("No heat thermo for zone {}:{}".format(zone_name, zone_id))


def _zoneheatrelay_upsert_listener(record, changed_fields):
    # set pin only on pins owned by this host
    if record.gpio_host_name == Constant.HOST_NAME and record.heat_is_on is not None:
        # L.l.info("Setting heat pin {}:{} to {}".format(record.heat_pin_name, record.gpio_pin_code, pin_value))
        # if record.heat_pin_name == 'puffer gas valve':
        #    traceback.print_stack()
        #    L.l.info('Debug 2 {} ---- {}'.format(record, changed_fields))
        pin_state = gpio.set_relay_state(
            pin_code=record.gpio_pin_code, relay_is_on=record.heat_is_on, relay_type=record.relay_type)
        L.l.info("Setting heat pin {}:{}:{} to {} returned {}".format(
            record.heat_pin_name, record.gpio_pin_code, record.relay_type, record.heat_is_on, pin_state))


def _zonethermostat_upsert_listener(record, changed_fields):
    # activate manual mode if set by user in UI
    if hasattr(record, m.ZoneThermostat.is_mode_manual) and record.is_mode_manual is True:
        record.last_manual_set = datetime.datetime.now()
        record.save_changed_fields()
        L.l.info('Set thermostat manual to active={} zone={}'.format(record.is_mode_manual, record.zone_name))


def thread_run():
    prctl.set_name("heat")
    threading.current_thread().name = "heat"
    if P.threshold is None:
        P.threshold = float(get_json_param(Constant.P_TEMPERATURE_THRESHOLD))
        P.temp_limit = float(get_json_param(Constant.P_HEAT_SOURCE_MIN_TEMP))
        P.MAX_DELTA_TEMP_KEEP_WARM = float(get_json_param(Constant.P_MAX_DELTA_TEMP_KEEP_WARM))
    month = datetime.datetime.today().month
    P.season = "summer" if month in range(5, 11) else "winter"
    _set_main_heat_source()
    _loop_zones()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"
    return 'Heat ok'


def unload():
    L.l.info('Heat module unloading')
    P.initialised = False
    thread_pool.remove_callable(thread_run)


def init():
    L.l.info('Heat module initialising')
    dispatcher.connect(_handle_presence, signal=Constant.SIGNAL_PRESENCE, sender=dispatcher.Any)
    thread_pool.add_interval_callable(thread_run, 30)
    P.initialised = True
    m.ZoneHeatRelay.add_upsert_listener(_zoneheatrelay_upsert_listener)
    m.ZoneThermostat.add_upsert_listener(_zonethermostat_upsert_listener)
