__author__ = 'dcristian'

from pydispatch import dispatcher
from main import thread_pool
import datetime
import threading
import prctl
from main.logger_helper import L
from main.admin import models
from main.admin.model_helper import commit, get_param
from common import utils, Constant
import gpio


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

    def __init__(self):
        pass


# execute when heat status change is signaled. changes gpio pin status if pin is local
def record_update(obj_dict=None):
    if not obj_dict:
        obj_dict = {}
    try:
        source_host_name = utils.get_object_field_value(obj_dict, Constant.JSON_PUBLISH_SOURCE_HOST)
        zone_id = utils.get_object_field_value(obj_dict, utils.get_model_field_name(models.ZoneHeatRelay.zone_id))
        pin_name = utils.get_object_field_value(
            obj_dict, utils.get_model_field_name(models.ZoneHeatRelay.heat_pin_name))
        is_on = utils.get_object_field_value(obj_dict,utils.get_model_field_name(models.ZoneHeatRelay.heat_is_on))
        # fixme: remove hard reference to object field
        sent_on = utils.get_object_field_value(obj_dict, "event_sent_datetime")
        L.l.debug('Received heat relay update from {} zoneid={} pin={} is_on={} sent={}'.format(
            source_host_name, zone_id, pin_name, is_on, sent_on))
        zone_heat_relay = models.ZoneHeatRelay.query.filter_by(zone_id=zone_id).first()
        if zone_heat_relay:
            gpio_host_name = zone_heat_relay.gpio_host_name
            cmd_heat_is_on = utils.get_object_field_value(
                obj_dict, utils.get_model_field_name(models.ZoneHeatRelay.heat_is_on))
            L.l.debug('Local heat state zone_id {} must be changed to {} on pin {}'.format(
                zone_id, cmd_heat_is_on, zone_heat_relay.gpio_pin_code))
            if cmd_heat_is_on:
                pin_value = 1
            else:
                pin_value = 0
            # set pin only on pins owned by this host
            if zone_heat_relay and gpio_host_name == Constant.HOST_NAME:
                L.l.info("Setting heat pin {} to {}".format(zone_heat_relay.gpio_pin_code, pin_value))
                pin_state = gpio.relay_update(gpio_pin_code=zone_heat_relay.gpio_pin_code, pin_value=pin_value)
            else:
                pin_state = pin_value
            if pin_state == pin_value:
                pin_state = (pin_state == 1)
                zone_heat_relay.heat_is_on = pin_state
                zone_heat_relay.notify_transport_enabled = False
                commit()
            else:
                L.l.warning('Heat state zone_id {} unexpected val={} after setval={}'.format(
                    zone_id, pin_state, pin_value))
        else:
            L.l.warning('No heat relay defined for zone {}, db data issue?'.format(zone_id))
    except Exception as ex:
        L.l.warning('Error updating heat relay state, err {}'.format(ex))


# when db changes via UI
def zone_thermo_record_update(obj_dict=None):
    if Constant.JSON_PUBLISH_FIELDS_CHANGED in obj_dict.keys():
        changes = obj_dict[Constant.JSON_PUBLISH_FIELDS_CHANGED]
        is_mode_manual = utils.get_object_field_value(
            changes, utils.get_model_field_name(models.ZoneThermostat.is_mode_manual))
        # activate manual mode if set by user in UI
        if is_mode_manual is not None:
            thermo_id = utils.get_object_field_value(obj_dict, utils.get_model_field_name(models.ZoneThermostat.id))
            thermo_rec = models.ZoneThermostat.query.filter_by(id=thermo_id).first()
            if thermo_rec is not None and is_mode_manual:
                thermo_rec.last_manual_set = datetime.datetime.now()
                thermo_rec.commit_record_to_db()


# save heat status and announce to all nodes.
def __save_heat_state_db(zone, heat_is_on):
    assert isinstance(zone, models.Zone)
    zone_heat_relay = models.ZoneHeatRelay.query.filter_by(zone_id=zone.id).first()
    zone_thermo = models.ZoneThermostat.query.filter_by(zone_id=zone.id).first()
    if zone_thermo is None:
        zone_thermo = models.ZoneThermostat()
        zone_thermo.zone_id = zone.id
        zone_thermo.zone_name = zone.name
        zone_thermo.add_record_to_session()
    if zone_heat_relay is not None:
        zone_heat_relay.heat_is_on = heat_is_on
        zone_heat_relay.updated_on = utils.get_base_location_now_date()
        L.l.debug('Heat state changed to is-on={} via pin={} in zone={}'.format(
            heat_is_on, zone_heat_relay.heat_pin_name, zone.name))
        zone_heat_relay.notify_transport_enabled = True
        zone_heat_relay.save_to_graph = True
        zone_heat_relay.save_to_history = True
        # save latest heat state for caching purposes
        zone_thermo.heat_is_on = heat_is_on
        zone_thermo.last_heat_status_update = utils.get_base_location_now_date()
        commit()
    else:
        L.l.warning('No heat relay found in zone {}'.format(zone.name))


# triggers heat status update if heat changed
def __decide_action(zone, current_temperature, target_temperature, force_on=False, force_off=False, zone_thermo=None):
    assert isinstance(zone, models.Zone)
    L.l.debug("Asses heat zone={} current={} target={} thresh={}".format(
        zone, current_temperature, target_temperature, P.threshold))
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
        last_heat_update_age_sec = (utils.get_base_location_now_date() -
                                    zone_thermo.last_heat_status_update).total_seconds()
    else:
        last_heat_update_age_sec = P.check_period
    if zone_thermo.heat_is_on != heat_is_on or last_heat_update_age_sec >= P.check_period \
            or zone_thermo.last_heat_status_update is None:
        L.l.debug('Heat must change, is {} in {} temp={} target+thresh={}, forced={}'.format(
            heat_is_on, zone.name, current_temperature, target_temperature + P.threshold, force_on))
        L.l.debug('Heat change due to: is_on_next={} is_on_db={} age={} last={}'.format(
            heat_is_on, zone_thermo.heat_is_on, last_heat_update_age_sec, zone_thermo.last_heat_status_update))
        __save_heat_state_db(zone=zone, heat_is_on=heat_is_on)
    #else:
    #    Log.logger.info('Heat should not change, is {} in {} temp={} target={}'.format(heat_is_on, zone.name,
    #                                                                        current_temperature, target_temperature))
    return heat_is_on


def _get_temp_target(pattern_id):
    hour = utils.get_base_location_now_date().hour
    schedule_pattern = models.SchedulePattern.query.filter_by(id=pattern_id).first()
    # strip formatting characters that are not used to represent target temperature
    pattern = str(schedule_pattern.pattern).replace('-', '').replace(' ', '')
    # check pattern validity
    if len(pattern) == 24:
        temp_code = pattern[hour]
        temp_target = models.TemperatureTarget.query.filter_by(code=temp_code).first()
    else:
        L.l.warning('Incorrect temp pattern [{}] in zone {}, length is not 24'.format(pattern, schedule_pattern.name))
        temp_target = None
    return temp_target.target, temp_code


# provide heat pattern
def _get_schedule_pattern(heat_schedule):
    weekday = datetime.datetime.today().weekday()
    heat_thermo = models.ZoneThermostat.query.filter_by(zone_id=heat_schedule.zone_id).first()
    schedule_pattern = None
    if heat_thermo is not None and heat_thermo.last_presence_set is not None:
        delta = (datetime.datetime.now() - heat_thermo.last_presence_set).total_seconds()
        if delta <= P.PRESENCE_SEC and heat_schedule.pattern_id_presence is not None:
            # we have recent move
            L.l.info("Move detected, set move heat pattern in zone id {}".format(heat_schedule.zone_id))
            schedule_pattern = models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_id_presence).first()
        if delta >= P.AWAY_SEC and heat_schedule.pattern_id_no_presence is not None:
            # no move for a while, switch to away
            L.l.info("No move detected, set away heat pattern in zone id {}".format(heat_schedule.zone_id))
            schedule_pattern = models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_id_no_presence).first()
    # if no recent move or away detected, set normal schedule
    if schedule_pattern is None:
        if weekday <= 4:  # Monday=0
            schedule_pattern = models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_week_id).first()
        else:
            schedule_pattern = models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_weekend_id).first()
    return schedule_pattern


# turn heat source off in some cases, for alternate heat sources, when switching from solar to gas etc.
def _get_heat_off_condition(schedule_pattern):
    force_off = False
    relay_name = schedule_pattern.activate_condition_relay
    zone_heat_relay = models.ZoneHeatRelay.query.filter_by(heat_pin_name=relay_name).first()
    if zone_heat_relay is not None:
        force_off = zone_heat_relay.heat_is_on is False
        # if force_off:
        #    L.l.info('Heat off condition in zone {} due to relay {}'.format(schedule_pattern.name, zone_heat_relay))
    else:
        L.l.error('Could not find the heat relay for zone heat {}'.format(schedule_pattern.name))
    return force_off


# check if we need forced heat on, if for this hour temp has a upper target than min
def _get_heat_on_keep_warm(schedule_pattern, temp_code, temp_target, temp_actual):
    force_on = False
    if schedule_pattern.keep_warm:
        minute = utils.get_base_location_now_date().minute
        if len(schedule_pattern.keep_warm_pattern) == 20:
            interval = int(minute / 5)
            delta_warm = temp_actual - temp_target
            if delta_warm <= P.MAX_DELTA_TEMP_KEEP_WARM:
                force_on = ((schedule_pattern.keep_warm_pattern[interval] == "1") and
                            temp_code is not P.TEMP_NO_HEAT)
            else:
                L.l.info("Temperature is too high with delta {}, ignoring keep warm".format(delta_warm))
        else:
            L.l.critical("Missing keep warm pattern for zone {}".format(schedule_pattern.name))
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
        else:
            zone_thermo.is_mode_manual = False
            zone_thermo.commit_record_to_db()
    return force_on, manual_temp_target


# set and return the required heat state in a zone (True - on, False - off).
# Also return if main source is needed, usefull if you only heat a boiler from alternate heat source
def _update_zone_heat(zone, heat_schedule, sensor):
    heat_is_on = False
    main_source_needed = True
    zone_thermo = models.ZoneThermostat.query.filter_by(zone_id=zone.id).first()
    if zone_thermo is None:
        zone_thermo = models.ZoneThermostat()
        zone_thermo.zone_id = zone.id
        zone_thermo.zone_name = zone.name
        zone_thermo.add_record_to_session()
    try:
        schedule_pattern = _get_schedule_pattern(heat_schedule)
        if schedule_pattern:
            std_temp_target, temp_code = _get_temp_target(schedule_pattern.id)
            main_source_needed = schedule_pattern.main_source_needed
            # if main_source_needed is False:
            #    L.l.info("Main heat source is not needed for zone {}".format(zone))
            # set heat to off if condition is met (i.e. do not try to heat water if heat source is cold)
            if std_temp_target is not None:
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
                    else:
                        act_temp_target = std_temp_target
                if zone_thermo.active_heat_schedule_pattern_id != schedule_pattern.id:
                    L.l.debug('Pattern {} is {}, target={}'.format(zone.name, schedule_pattern.name, act_temp_target))
                    zone_thermo.active_heat_schedule_pattern_id = schedule_pattern.id
                zone_thermo.heat_target_temperature = std_temp_target
                commit()
                if sensor.temperature is not None:
                    heat_is_on = __decide_action(zone, sensor.temperature, act_temp_target, force_on=force_on,
                                                 force_off=force_off, zone_thermo=zone_thermo)
            else:
                L.l.critical('Unknown temperature pattern code {}'.format(temp_code))
    except Exception as ex:
        L.l.error('Error updatezoneheat, err={}'.format(ex), exc_info=True)
    return heat_is_on, main_source_needed


# iterate zones and decide heat state for each zone and also for master zone (main heat system)
# if one zone requires heat master zone will be on
def loop_zones():
    try:
        heat_is_on = False
        zone_list = models.Zone().query_all()
        global progress_status
        for zone in zone_list:
            progress_status = 'do zone {}'.format(zone.name)
            heat_schedule = models.HeatSchedule.query.filter_by(zone_id=zone.id, season=P.season).first()
            zonesensor_list = models.ZoneSensor.query.filter_by(zone_id=zone.id).all()
            for zonesensor in zonesensor_list:
                if heat_schedule is not None and zonesensor is not None:
                    sensor = models.Sensor.query.filter_by(address=zonesensor.sensor_address).first()
                    if sensor is not None:
                        # sensor_last_update_seconds = (utils.get_base_location_now_date() - sensor.updated_on).total_seconds()
                        # if sensor_last_update_seconds > 120 * 60:
                        #    Log.logger.warning('Sensor {} not updated in last 120 minutes, unusual'.format(
                        # sensor.sensor_name))
                        heat_state, main_source_needed = _update_zone_heat(zone, heat_schedule, sensor)
                        if not heat_is_on:
                            heat_is_on = main_source_needed and heat_state
        # turn on/off the main heating system based on zone heat needs
        # check first to find alternate valid heat sources
        heatrelay_main_source = models.ZoneHeatRelay.query.filter_by(is_alternate_heat_source=1).first()
        if heatrelay_main_source is None:
            heatrelay_main_source = models.ZoneHeatRelay.query.filter_by(is_main_heat_source=1).first()
        if heatrelay_main_source is not None:
            L.l.info("Main heat relay={}".format(heatrelay_main_source))
            main_source_zone = models.Zone.query.filter_by(id=heatrelay_main_source.zone_id).first()
            main_thermo = models.ZoneThermostat.query.filter_by(zone_id=main_source_zone.id).first()
            if main_source_zone is not None:
                update_age_mins = (utils.get_base_location_now_date() - P.last_main_heat_update).total_seconds() / 60
                # # avoid setting relay state too often but do periodic refreshes every x minutes
                # check when thermo is none
                if main_thermo is None or (main_thermo.heat_is_on != heat_is_on or update_age_mins >= int(get_param(
                        Constant.P_HEAT_STATE_REFRESH_PERIOD))):
                    L.l.info("Setting main heat on={}, zone={}".format(heat_is_on, main_source_zone))
                    __save_heat_state_db(zone=main_source_zone, heat_is_on=heat_is_on)
                    P.last_main_heat_update = utils.get_base_location_now_date()
            else:
                L.l.critical('No heat main_src found using zone id {}'.format(heatrelay_main_source.zone_id))
        else:
            L.l.critical('No heat main source is defined in db')
    except Exception as ex:
        L.l.error('Error loop_zones, err={}'.format(ex), exc_info=True)


# check actual heat relay status in db in case relay pin was modified externally
# todo: check as might introduce state change miss
def loop_heat_relay():
    heat_relay_list = models.ZoneHeatRelay().query_filter_all(
        models.ZoneHeatRelay.gpio_host_name.in_([Constant.HOST_NAME]))
    for heat_relay in heat_relay_list:
        gpio_pin = None
        try:
            gpiopin_list = models.GpioPin.query.filter_by(pin_code=heat_relay.gpio_pin_code,
                                                          host_name=Constant.HOST_NAME).all()
            if len(gpiopin_list) == 0:
                L.l.warning("Cannot find gpiopin_bcm for heat relay={} zone={}".format(heat_relay.gpio_pin_code,
                                                                                       heat_relay.heat_pin_name))
            else:
                if len(gpiopin_list) > 1:
                    L.l.warning("Multiple unexpected pins on heat loop code {}".format(heat_relay.gpio_pin_code))
                for gpio_pin in gpiopin_list:
                    # gpio_pin = models.GpioPin().query_filter_first(models.GpioPin.host_name.in_([Constant.HOST_NAME]),
                    #                                               models.GpioPin.pin_code.in_([heat_relay.gpio_pin_code]))
                    pin_state_int = gpio.relay_get(gpio_pin_obj=gpio_pin)
                    pin_state = (pin_state_int == 1)
                    zone = models.Zone().query_filter_first(models.Zone.id.in_([heat_relay.zone_id]))
                    relay_inconsistency = heat_relay.heat_is_on != pin_state
                    zone_inconsistency = zone.heat_is_on != heat_relay.heat_is_on
                    if relay_inconsistency:
                        L.l.warning("Inconsistent heat status relay={} db_relay_status={} pin_status={}".format(
                            heat_relay.heat_pin_name, heat_relay.heat_is_on, pin_state_int))
                    if zone_inconsistency:
                        L.l.warning("Inconsistent zone heat zone={}  db_relay_status={}".format(
                            zone.name, heat_relay.heat_is_on))
                    if relay_inconsistency or zone_inconsistency:
                        # fixme: we got flip of states due to inconsistency messages
                        # __save_heat_state_db(zone=zone, heat_is_on=pin_state)
                        __save_heat_state_db(zone=zone, heat_is_on=heat_relay.heat_is_on)
                    # else:
                    #    Log.logger.info("Heat pin {} status equal to gpio status {}".format(heat_relay.heat_is_on, pin_state_int))
        except Exception as ex:
            L.l.exception('Error processing heat relay=[{}] pin=[{}] err={}'.format(heat_relay, gpio_pin, ex))


# set which is the main heat source relay that must be set on
def set_main_heat_source():
    heat_source_relay_list = models.ZoneHeatRelay.query.filter(models.ZoneHeatRelay.temp_sensor_name is not None).all()
    up_limit = P.temp_limit + P.threshold
    for heat_source_relay in heat_source_relay_list:
        # is there is a temp sensor defined, consider this source as possible alternate source
        if heat_source_relay.temp_sensor_name is not None:
            temp_rec = models.Sensor().query_filter_first(
                models.Sensor.sensor_name.in_([heat_source_relay.temp_sensor_name]))
            # if alternate source is valid
            # fixok: add temp threshold to avoid quick on/offs
            if temp_rec is not None \
                    and ((temp_rec.temperature >= up_limit and not heat_source_relay.is_alternate_source_switch)
                         or (temp_rec.temperature >= P.temp_limit and heat_source_relay.is_alternate_source_switch)):
                if heat_source_relay.is_alternate_source_switch:
                    # stop main heat source
                    heatrelay_main_source = models.ZoneHeatRelay.query.filter_by(is_main_heat_source=1).first()
                    main_source_zone = models.Zone.query.filter_by(id=heatrelay_main_source.zone_id).first()
                    __save_heat_state_db(zone=main_source_zone, heat_is_on=False)
                    # turn switch valve on to alternate position
                    switch_source_zone = models.Zone.query.filter_by(id=heat_source_relay.zone_id).first()
                    __save_heat_state_db(zone=switch_source_zone, heat_is_on=True)
                else:
                    # mark this source as active, to be started when there is heat need
                    if heat_source_relay.is_alternate_heat_source is False:
                        L.l.info('Alternate heat source is active with temp={}'.format(temp_rec.temperature))
                    heat_source_relay.is_alternate_heat_source = True
                commit()
            else:
                # if alternate source is no longer valid
                if heat_source_relay.is_alternate_source_switch:
                    # stop alternate heat source
                    # heatrelay_alt_source = models.ZoneHeatRelay.query.filter_by(is_alternate_heat_source=1).first()
                    # if heatrelay_alt_source is not None:
                    #    alt_source_zone = models.Zone.query.filter_by(id=heatrelay_alt_source.zone_id).first()
                    #    __save_heat_state_db(zone=alt_source_zone, heat_is_on=False)
                    # turn valve back to main position
                    switch_source_zone = models.Zone.query.filter_by(id=heat_source_relay.zone_id).first()
                    __save_heat_state_db(zone=switch_source_zone, heat_is_on=False)
                else:
                    # mark this source as inactive, let main source to start
                    if heat_source_relay.is_alternate_heat_source:
                        # force alt source shutdown if was on
                        alt_source_zone = models.Zone.query.filter_by(id=heat_source_relay.zone_id).first()
                        __save_heat_state_db(zone=alt_source_zone, heat_is_on=False)
                        # todo: sleep needed to allow for valve return
                    if heat_source_relay.is_alternate_heat_source is True:
                        L.l.info('Alternate heat source is now inactive, temp source is {}'.format(temp_rec))
                    heat_source_relay.is_alternate_heat_source = False
                commit()


# start/stop heat based on user movement/presence
def _handle_presence(zone_name=None, zone_id=None):
    if zone_id is not None:
        heat_thermo = models.ZoneThermostat.query.filter_by(zone_id=zone_id).first()
        if heat_thermo is not None:
            heat_thermo.last_presence_set = datetime.datetime.now()
        else:
            L.l.info("No heat thermo for zone {}".format(zone_name))


progress_status = None


def get_progress():
    global progress_status
    return progress_status


def thread_run():
    prctl.set_name("heat")
    threading.current_thread().name = "heat"
    global progress_status
    L.l.debug('Processing heat')
    progress_status = 'Looping zones'
    if P.threshold is None:
        P.threshold = float(get_param(Constant.P_TEMPERATURE_THRESHOLD))
        P.temp_limit = float(get_param(Constant.P_HEAT_SOURCE_MIN_TEMP))
        P.MAX_DELTA_TEMP_KEEP_WARM = float(get_param(Constant.P_MAX_DELTA_TEMP_KEEP_WARM))
    month = datetime.datetime.today().month
    P.season = "summer" if month in range(5, 11) else "winter"
    set_main_heat_source()
    loop_zones()
    # loop_heat_relay()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"
    return 'Heat ok'


def unload():
    L.l.info('Heat module unloading')
    P.initialised = False
    thread_pool.remove_callable(thread_run)
    # dispatcher.disconnect(handle_event_heat, signal=Constant.SIGNAL_HEAT, sender=dispatcher.Any)


def init():
    L.l.info('Heat module initialising')
    dispatcher.connect(_handle_presence, signal=Constant.SIGNAL_PRESENCE, sender=dispatcher.Any)
    # dispatcher.connect(handle_event_heat, signal=Constant.SIGNAL_HEAT, sender=dispatcher.Any)
    thread_pool.add_interval_callable(thread_run, 60)
    P.initialised = True
