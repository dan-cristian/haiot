__author__ = 'dcristian'

import datetime
import threading
from main.logger_helper import L
from main.admin import models
from main.admin.model_helper import commit, get_param
from common import utils, Constant
import gpio

__last_main_heat_update = datetime.datetime.min
__TEMP_NO_HEAT = '.'


# save heat status and announce to all nodes.
def __save_heat_state_db(zone='', heat_is_on=''):
    assert isinstance(zone, models.Zone)
    zone_heat_relay = models.ZoneHeatRelay.query.filter_by(zone_id=zone.id).first()
    if zone_heat_relay is not None:
        zone_heat_relay.heat_is_on = heat_is_on
        zone_heat_relay.updated_on = utils.get_base_location_now_date()
        L.l.debug('Heat state changed to is-on={} via pin={} in zone={}'.format(
            heat_is_on, zone_heat_relay.heat_pin_name, zone.name))
        zone_heat_relay.notify_transport_enabled = True
        zone_heat_relay.save_to_graph = True
        zone_heat_relay.save_to_history = True
        # save latest heat state for caching purposes
        zone.heat_is_on = heat_is_on
        zone.last_heat_status_update = utils.get_base_location_now_date()
        commit()
    else:
        L.l.warning('No heat relay found in zone {}'.format(zone.name))


# triggers heat status update if heat changed
def __decide_action(zone, current_temperature, target_temperature, force_on=False, force_off=False):
    assert isinstance(zone, models.Zone)
    threshold = float(get_param(Constant.P_TEMPERATURE_THRESHOLD))
    L.l.debug("Asses heat zone={} current={} target={} thresh={}".format(
        zone, current_temperature, target_temperature, threshold))
    heat_is_on = None
    if force_on:
        heat_is_on = True
    if force_off:
        heat_is_on = False
    if heat_is_on is None:
        heat_is_on = zone.heat_is_on
        if heat_is_on is None:
            heat_is_on = False
        if current_temperature < target_temperature:
            heat_is_on = True
        if current_temperature > (target_temperature + threshold):
            heat_is_on = False
    # trigger if state is different and every 5 minutes (in case other hosts with relays have restarted)
    if zone.last_heat_status_update is not None:
        last_heat_update_age_sec = (utils.get_base_location_now_date() - zone.last_heat_status_update).total_seconds()
    else:
        last_heat_update_age_sec = 300
    if zone.heat_is_on != heat_is_on or last_heat_update_age_sec >= 300 or zone.last_heat_status_update is None:
        L.l.info('Heat must change, is {} in {} temp={} target+thresh={}, forced={}'.format(
            heat_is_on, zone.name, current_temperature, target_temperature+ threshold, force_on))
        L.l.info('Heat change due to: is_on_next={} is_on_db={} age={} last={}'.format(
            heat_is_on, zone.heat_is_on, last_heat_update_age_sec, zone.last_heat_status_update ))
        __save_heat_state_db(zone=zone, heat_is_on=heat_is_on)
    #else:
    #    Log.logger.info('Heat should not change, is {} in {} temp={} target={}'.format(heat_is_on, zone.name,
    #                                                                        current_temperature, target_temperature))
    return heat_is_on


# set and return the required heat state in a zone (True - on, False - off).
# Also return if main source is needed, usefull if you only heat a boiler from alternate heat source
def __update_zone_heat(zone, heat_schedule, sensor):
    heat_is_on = False
    main_source_needed = True
    try:
        minute = utils.get_base_location_now_date().minute
        hour = utils.get_base_location_now_date().hour
        weekday = datetime.datetime.today().weekday()
        # todo: insert here auto heat change based on presence status
        if weekday <= 4:  # Monday=0
            schedule_pattern = models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_week_id).first()
        else:
            schedule_pattern = models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_weekend_id).first()
        if schedule_pattern:
            main_source_needed = schedule_pattern.main_source_needed
            if main_source_needed is False:
                L.l.info("Main heat source is not needed for zone {}".format(zone))
            force_off = False
            # set heat to off if condition is met (i.e. do not try to heat water if heat source is cold)
            if schedule_pattern.activate_on_condition:
                relay_name = schedule_pattern.activate_condition_relay
                zone_heat_relay = models.ZoneHeatRelay.query.filter_by(heat_pin_name=relay_name).first()
                if zone_heat_relay is not None:
                    force_off = zone_heat_relay.heat_is_on is False
                    if force_off:
                        L.l.info('Deactivating heat in zone {} due to relay {}'.format(zone, zone_heat_relay))
                else:
                    L.l.error('Could not find the heat relay for zone heat {}'.format(zone))
            # strip formatting characters that are not used to represent target temperature
            pattern = str(schedule_pattern.pattern).replace('-', '').replace(' ', '')
            # check pattern validity
            if len(pattern) == 24:
                temperature_code = pattern[hour]
                temperature_target = models.TemperatureTarget.query.filter_by(code=temperature_code).first()
                # check if we need forced heat on, if for this hour temp has a upper target than min
                force_on = False
                if schedule_pattern.keep_warm:
                    if len(schedule_pattern.keep_warm_pattern) == 20:
                        interval = int(minute / 5)
                        force_on = ((schedule_pattern.keep_warm_pattern[interval] == "1") and
                                    temperature_code is not __TEMP_NO_HEAT)
                    else:
                        L.l.critical("Missing keep warm pattern for zone {}".format(zone.name))
                if temperature_target:
                    if zone.active_heat_schedule_pattern_id != schedule_pattern.id:
                        L.l.info('Pattern in zone {} changed to {}, target={}'.format(
                            zone.name, schedule_pattern.name, temperature_target.target))
                        zone.active_heat_schedule_pattern_id = schedule_pattern.id
                    zone.heat_target_temperature = temperature_target.target
                    commit()
                    if sensor.temperature is not None:
                        heat_is_on = __decide_action(zone, sensor.temperature, temperature_target.target,
                                                     force_on=force_on, force_off=force_off)
                    #else:
                    #    heat_is_on = zone.heat_is_on
                else:
                    L.l.critical('Unknown temperature pattern code {}'.format(temperature_code))
            else:
                L.l.warning('Incorrect temp pattern [{}] in zone {}, length is not 24'.format(pattern, zone.name))
    except Exception as ex:
        L.l.error('Error updatezoneheat, err={}'.format(ex, exc_info=True))
    #Log.logger.info("Temp in {} has target={} and current={}, heat should be={}".format(zone.name,
    #                                                                            zone.heat_target_temperature,
    #                                                                             sensor.temperature, heat_is_on))
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
            heat_schedule = models.HeatSchedule.query.filter_by(zone_id=zone.id).first()
            zonesensor_list = models.ZoneSensor.query.filter_by(zone_id=zone.id).all()
            for zonesensor in zonesensor_list:
                if heat_schedule and zonesensor:
                    sensor = models.Sensor.query.filter_by(address=zonesensor.sensor_address).first()
                    if heat_schedule.active and sensor is not None:
                        # sensor_last_update_seconds = (utils.get_base_location_now_date() - sensor.updated_on).total_seconds()
                        # if sensor_last_update_seconds > 120 * 60:
                        #    Log.logger.warning('Sensor {} not updated in last 120 minutes, unusual'.format(
                        # sensor.sensor_name))
                        heat_state, main_source_needed = __update_zone_heat(zone, heat_schedule, sensor)
                        heat_is_on = main_source_needed and heat_state
        # turn on/off the main heating system based on zone heat needs
        # check first to find alternate valid heat sources
        heatrelay_main_source = models.ZoneHeatRelay.query.filter_by(is_alternate_heat_source=1).first()
        if heatrelay_main_source is None:
            heatrelay_main_source = models.ZoneHeatRelay.query.filter_by(is_main_heat_source=1).first()
        if heatrelay_main_source is not None:
            L.l.info("Main heat relay={}".format(heatrelay_main_source))
            main_source_zone = models.Zone.query.filter_by(id=heatrelay_main_source.zone_id).first()
            if main_source_zone is not None:
                global __last_main_heat_update
                update_age_mins = (utils.get_base_location_now_date() - __last_main_heat_update).total_seconds() / 60
                # # avoid setting relay state too often but do periodic refreshes every x minutes
                if main_source_zone.heat_is_on != heat_is_on or update_age_mins >= int(get_param(
                        Constant.P_HEAT_STATE_REFRESH_PERIOD)):
                    L.l.info("Setting main heat on={}, zone={}".format(heat_is_on, main_source_zone))
                    __save_heat_state_db(zone=main_source_zone, heat_is_on=heat_is_on)
                    __last_main_heat_update = utils.get_base_location_now_date()
            else:
                L.l.critical('No heat main_src found using zone id {}'.format(heatrelay_main_source.zone_id))
        else:
            L.l.critical('No heat main source is defined in db')
    except Exception as ex:
        L.l.error('Error loop_zones, err={}'.format(ex, exc_info=True))


# check actual heat relay status in db in case relay pin was modified externally
# todo: check as might introduce state change miss
def loop_heat_relay():
    heat_relay_list = models.ZoneHeatRelay().query_filter_all(
        models.ZoneHeatRelay.gpio_host_name.in_([Constant.HOST_NAME]))
    for heat_relay in heat_relay_list:
        gpio_pin = None
        try:
            gpio_pin = models.GpioPin().query_filter_first(models.GpioPin.host_name.in_([Constant.HOST_NAME]),
                                                           models.GpioPin.pin_code.in_([heat_relay.gpio_pin_code]))
            if gpio_pin:
                pin_state_int = gpio.relay_get(gpio_pin_obj=gpio_pin)
                pin_state = (pin_state_int == 1)
                zone = models.Zone().query_filter_first(models.Zone.id.in_([heat_relay.zone_id]))
                relay_inconsistency = heat_relay.heat_is_on != pin_state
                zone_inconsistency = zone.heat_is_on != heat_relay.heat_is_on
                if relay_inconsistency:
                    L.l.warning("Inconsistent heat relay status relay={} db_relay_status={} pin_status={}".format(
                        heat_relay.heat_pin_name, heat_relay.heat_is_on, pin_state_int))
                if zone_inconsistency:
                    L.l.warning("Inconsistent zone heat status zone={} db_heat_status={} db_relay_status={}".format(
                        zone.name, zone.heat_is_on, heat_relay.heat_is_on))
                if relay_inconsistency or zone_inconsistency:
                    # fixme: we got flip of states due to inconsistency messages
                    # __save_heat_state_db(zone=zone, heat_is_on=pin_state)
                    __save_heat_state_db(zone=zone, heat_is_on=heat_relay.heat_is_on)
                #else:
                #    Log.logger.info("Heat pin {} status equal to gpio status {}".format(heat_relay.heat_is_on, pin_state_int))
            else:
                L.l.warning("Cannot find gpiopin_bcm for heat relay={} zone={}".format(heat_relay.gpio_pin_code,
                                                                                       heat_relay.heat_pin_name))
        except Exception as ex:
            L.l.exception('Error processing heat relay=[{}] pin=[{}] err={}'.format(heat_relay, gpio_pin, ex))


# set which is the main heat source relay that must be set on
def set_main_heat_source():
    heat_source_relay_list = models.ZoneHeatRelay.query.filter(models.ZoneHeatRelay.temp_sensor_name is not None).all()
    temp_limit = float(get_param(Constant.P_HEAT_SOURCE_MIN_TEMP))
    up_limit = temp_limit + float(get_param(Constant.P_TEMPERATURE_THRESHOLD))
    for heat_source_relay in heat_source_relay_list:
        # is there is a temp sensor defined, consider this source as possible alternate source
        if heat_source_relay.temp_sensor_name is not None:
            temp_rec = models.Sensor().query_filter_first(
                models.Sensor.sensor_name.in_([heat_source_relay.temp_sensor_name]))
            # if alternate source is valid
            # fixok: add temp threshold to avoid quick on/offs
            if temp_rec is not None \
                    and ((temp_rec.temperature >= up_limit and not heat_source_relay.is_alternate_source_switch)
                         or (temp_rec.temperature >= temp_limit and heat_source_relay.is_alternate_source_switch)):
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
                    heat_source_relay.is_alternate_heat_source = True
                commit()
            else:
                # if alternate source is no longer valid
                if heat_source_relay.is_alternate_source_switch:
                    # stop alternate heat source
                    #heatrelay_alt_source = models.ZoneHeatRelay.query.filter_by(is_alternate_heat_source=1).first()
                    #if heatrelay_alt_source is not None:
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
                        #todo: sleep needed to allow for valve return
                    heat_source_relay.is_alternate_heat_source = False
                commit()


progress_status = None


def get_progress():
    global progress_status
    return progress_status


def thread_run():
    threading.current_thread().name = "heat"
    global progress_status
    L.l.debug('Processing heat')
    progress_status = 'Looping zones'
    set_main_heat_source()
    loop_zones()
    # loop_heat_relay()
    return 'Heat ok'
