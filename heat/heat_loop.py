__author__ = 'dcristian'

import datetime

from main.logger_helper import Log
from main.admin import models
from main.admin.model_helper import commit
from common import utils


def __save_heat_state_db(zone='', heat_is_on=''):
    assert isinstance(zone, models.Zone)
    zone_heat_relay = models.ZoneHeatRelay.query.filter_by(zone_id=zone.id).first()
    if zone_heat_relay:
        #if zone_heat_relay.heat_is_on != heat_is_on:
            zone_heat_relay.heat_is_on = heat_is_on
            zone_heat_relay.updated_on = utils.get_base_location_now_date()
            Log.logger.info('Heat state changed to is-on={} in zone {}'.format(heat_is_on, zone.name))
            zone_heat_relay.notify_transport_enabled = True
            #save latest heat state for caching purposes
            zone.heat_is_on = heat_is_on
            commit()
        #else:
        #    Log.logger.debug('Heat state [{}] unchanged in zone {}'.format(heat_is_on, zone.name))
    else:
        Log.logger.warning('No heat relay found in zone {}'.format(zone.name))

def __decide_action(zone, current_temperature, target_temperature):
    assert isinstance(zone, models.Zone)
    if current_temperature < target_temperature:
        heat_is_on = True
    else:
        heat_is_on = False
    if zone.heat_is_on != heat_is_on:
        Log.logger.info('Heat is {} in {} temp={} target={}'.format(heat_is_on, zone.name, current_temperature,
                                                                target_temperature))
        __save_heat_state_db(zone=zone, heat_is_on=heat_is_on)
    return heat_is_on

def __update_zone_heat(zone, heat_schedule, sensor):
    heat_is_on = False
    try:
        minute = utils.get_base_location_now_date().minute
        hour = utils.get_base_location_now_date().hour
        weekday = datetime.datetime.today().weekday()
        if weekday <= 4: #Monday=0
            schedule_pattern=models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_week_id).first()
        else:
            schedule_pattern=models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_weekend_id).first()
        if schedule_pattern:
            pattern = str(schedule_pattern.pattern).replace('-', '').replace(' ','')
            if len(pattern) == 24:
                temperature_code = pattern[hour]
                temperature_target = models.TemperatureTarget.query.filter_by(code=temperature_code).first()
                if temperature_target:
                    #if not zone.last_heat_status_update:
                    #    zone.last_heat_status_update = datetime.datetime.min
                    #elapsed_since_heat_changed = (utils.get_base_location_now_date()
                    #                              - zone.last_heat_status_update).total_seconds()
                    #if temperature_target.target != zone.heat_target_temperature:
                    if zone.active_heat_schedule_pattern_id != schedule_pattern.id:
                        Log.logger.info('Pattern in zone {} changed to {}, target={}'.format(zone.name,
                                                                schedule_pattern.name, temperature_target.target))
                        zone.active_heat_schedule_pattern_id = schedule_pattern.id

                    zone.last_heat_status_update = utils.get_base_location_now_date()
                    zone.heat_target_temperature = temperature_target.target
                    commit()
                    if sensor.temperature:
                        heat_is_on = __decide_action(zone, sensor.temperature, temperature_target.target)
                    #else:
                    #    heat_is_on = zone.heat_is_on
                else:
                    Log.logger.critical('Unknown temperature pattern code {}'.format(temperature_code))
            else:
                Log.logger.warning('Incorrect temp pattern [{}] in zone {}, length is not 24'.format(pattern, zone.name))
    except Exception, ex:
        Log.logger.error('Error updatezoneheat, err={}'.format(ex, exc_info=True))
    return heat_is_on

#iterate zones and decide heat state for each zone and also for master zone (main heat system)
#if one zone requires heat master zone will be on
def loop_zones():
    try:
        heat_is_on = False
        zone_list = models.Zone.query.all()
        global progress_status
        for zone in zone_list:
            progress_status = 'do zone {}'.format(zone.name)
            heat_schedule = models.HeatSchedule.query.filter_by(zone_id=zone.id).first()
            zonesensor = models.ZoneSensor.query.filter_by(zone_id=zone.id).first()
            if heat_schedule and zonesensor:
                sensor = models.Sensor.query.filter_by(address=zonesensor.sensor_address).first()
                if heat_schedule.active and sensor:
                    sensor_last_update_seconds = (utils.get_base_location_now_date()-sensor.updated_on).total_seconds()
                    if sensor_last_update_seconds > 120 * 60:
                        Log.logger.warning('Sensor {} not updated in last 120 minutes, unusual'.format(sensor.sensor_name))
                    if __update_zone_heat(zone, heat_schedule, sensor):
                        heat_is_on = True
        heatrelay_main_source = models.ZoneHeatRelay.query.filter_by(is_main_heat_source=True).first()
        if heatrelay_main_source:
            main_source_zone = models.Zone.query.filter_by(id=heatrelay_main_source.zone_id).first()
            if main_source_zone:
                if main_source_zone.heat_is_on != heat_is_on:#avoid setting relay state too often
                    __save_heat_state_db(zone=main_source_zone, heat_is_on=heat_is_on)
            else:
                Log.logger.critical('No heat main_src found using zone id {}'.format(heatrelay_main_source.zone_id))
        else:
            Log.logger.critical('No heat main source is defined in db')
    except Exception, ex:
        Log.logger.error('Error loop_zones, err={}'.format(ex, exc_info=True))

progress_status = None
def get_progress():
    global progress_status
    return progress_status

def thread_run():
    global progress_status
    Log.logger.debug('Processing heat')
    progress_status = 'Looping zones'
    loop_zones()
    return 'Heat ok'
