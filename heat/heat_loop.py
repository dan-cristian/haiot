__author__ = 'dcristian'

import datetime

from main.logger_helper import Log
from main.admin import models
from main.admin.model_helper import commit, get_param
from common import utils, Constant
import gpio


# save heat status and announce to all nodes
def __save_heat_state_db(zone='', heat_is_on=''):
    assert isinstance(zone, models.Zone)
    zone_heat_relay = models.ZoneHeatRelay.query.filter_by(zone_id=zone.id).first()
    if zone_heat_relay is not None:
        zone_heat_relay.heat_is_on = heat_is_on
        zone_heat_relay.updated_on = utils.get_base_location_now_date()
        Log.logger.info('Heat state changed to is-on={} in zone {}'.format(heat_is_on, zone.name))
        zone_heat_relay.notify_transport_enabled = True
        # save latest heat state for caching purposes
        zone.heat_is_on = heat_is_on
        zone.last_heat_status_update = utils.get_base_location_now_date()
        commit()
    else:
        Log.logger.warning('No heat relay found in zone {}'.format(zone.name))


# triggers heat status update if heat changed
def __decide_action(zone, current_temperature, target_temperature):
    assert isinstance(zone, models.Zone)
    threshold = float(get_param(Constant.P_TEMPERATURE_THRESHOLD))
    Log.logger.debug("Asses heat zone={} current={} target={} thresh={}".format(
        zone, current_temperature, target_temperature, threshold))
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
        Log.logger.info('Heat must change, is {} in {} temp={} target+thresh={}'.format(
            heat_is_on, zone.name, current_temperature, target_temperature+ threshold))
        Log.logger.info('Heat change due to: is_on_next={} is_on_db={} age={} last={}'.format(
            heat_is_on, zone.heat_is_on, last_heat_update_age_sec, zone.last_heat_status_update ))
        __save_heat_state_db(zone=zone, heat_is_on=heat_is_on)
    #else:
    #    Log.logger.info('Heat should not change, is {} in {} temp={} target={}'.format(heat_is_on, zone.name,
    #                                                                        current_temperature, target_temperature))
    return heat_is_on


# return the required heat state in a zone (True - on, False - off)
def __update_zone_heat(zone, heat_schedule, sensor):
    heat_is_on = False
    try:
        minute = utils.get_base_location_now_date().minute
        hour = utils.get_base_location_now_date().hour
        weekday = datetime.datetime.today().weekday()
        # todo: insert here auto heat change based on presence status
        if weekday <= 4:  # Monday=0
            schedule_pattern= models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_week_id).first()
        else:
            schedule_pattern= models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_weekend_id).first()
        if schedule_pattern:
            # strip formatting characters that are not used to represent target temperature
            pattern = str(schedule_pattern.pattern).replace('-', '').replace(' ','')
            # check pattern validity
            if len(pattern) == 24:
                temperature_code = pattern[hour]
                temperature_target = models.TemperatureTarget.query.filter_by(code=temperature_code).first()
                if temperature_target:
                    if zone.active_heat_schedule_pattern_id != schedule_pattern.id:
                        Log.logger.info('Pattern in zone {} changed to {}, target={}'.format(zone.name,
                                                                schedule_pattern.name, temperature_target.target))
                        zone.active_heat_schedule_pattern_id = schedule_pattern.id
                    zone.heat_target_temperature = temperature_target.target
                    commit()
                    if sensor.temperature is not None:
                        heat_is_on = __decide_action(zone, sensor.temperature, temperature_target.target)
                    #else:
                    #    heat_is_on = zone.heat_is_on
                else:
                    Log.logger.critical('Unknown temperature pattern code {}'.format(temperature_code))
            else:
                Log.logger.warning('Incorrect temp pattern [{}] in zone {}, length is not 24'.format(
                    pattern, zone.name))
    except Exception, ex:
        Log.logger.error('Error updatezoneheat, err={}'.format(ex, exc_info=True))
    #Log.logger.info("Temp in {} has target={} and current={}, heat should be={}".format(zone.name,
    #                                                                            zone.heat_target_temperature,
    #                                                                             sensor.temperature, heat_is_on))
    return heat_is_on


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
            zonesensor = models.ZoneSensor.query.filter_by(zone_id=zone.id).first()
            if heat_schedule and zonesensor:
                sensor = models.Sensor.query.filter_by(address=zonesensor.sensor_address).first()
                if heat_schedule.active and sensor is not None:
                    # sensor_last_update_seconds = (utils.get_base_location_now_date() - sensor.updated_on).total_seconds()
                    # if sensor_last_update_seconds > 120 * 60:
                    #    Log.logger.warning('Sensor {} not updated in last 120 minutes, unusual'.format(
                    # sensor.sensor_name))
                    if __update_zone_heat(zone, heat_schedule, sensor):
                        heat_is_on = True
        heatrelay_main_source = models.ZoneHeatRelay.query.filter_by(is_main_heat_source=True).first()
        if heatrelay_main_source:
            main_source_zone = models.Zone.query.filter_by(id=heatrelay_main_source.zone_id).first()
            if main_source_zone:
                # fixme: heat state might not be set ok if remote relay set was not succesfull
                if main_source_zone.heat_is_on != heat_is_on:  # avoid setting relay state too often
                    __save_heat_state_db(zone=main_source_zone, heat_is_on=heat_is_on)
            else:
                Log.logger.critical('No heat main_src found using zone id {}'.format(heatrelay_main_source.zone_id))
        else:
            Log.logger.critical('No heat main source is defined in db')
    except Exception, ex:
        Log.logger.error('Error loop_zones, err={}'.format(ex, exc_info=True))


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
                    Log.logger.warning("Inconsistent heat relay status relay={} db_relay_status={} pin_status={}".format(
                        heat_relay.heat_pin_name, heat_relay.heat_is_on, pin_state_int))
                if zone_inconsistency:
                    Log.logger.warning("Inconsistent zone heat status zone={} db_heat_status={} db_relay_status={}".format(
                        zone.name, zone.heat_is_on, heat_relay.heat_is_on))
                if relay_inconsistency or zone_inconsistency:
                    # fixme: we got flip of states due to inconsistency messages
                    # __save_heat_state_db(zone=zone, heat_is_on=pin_state)
                    __save_heat_state_db(zone=zone, heat_is_on=heat_relay.heat_is_on)
                #else:
                #    Log.logger.info("Heat pin {} status equal to gpio status {}".format(heat_relay.heat_is_on, pin_state_int))
            else:
                Log.logger.warning("Cannot find gpiopin_bcm for heat relay={} zone={}".format(heat_relay.gpio_pin_code,
                                                                                          heat_relay.heat_pin_name))
        except Exception, ex:
            Log.logger.exception('Error processing heat relay=[{}] pin=[{}] err={}'.format(heat_relay, gpio_pin, ex))


progress_status = None


def get_progress():
    global progress_status
    return progress_status


def thread_run():
    global progress_status
    Log.logger.debug('Processing heat')
    progress_status = 'Looping zones'
    loop_zones()
    # loop_heat_relay()
    return 'Heat ok'
