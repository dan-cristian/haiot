__author__ = 'dcristian'

from main import logger
import datetime
from pydispatch import dispatcher
from main.admin import models
from main import db

from common import constant
import transport

def __save_heat_state_db(zone='', heat_is_on=''):
    assert isinstance(zone, models.Zone)
    zone_heat_relay = models.ZoneHeatRelay.query.filter_by(zone_id=zone.id).first()
    if zone_heat_relay:
        #if zone_heat_relay.heat_is_on != heat_is_on:
            zone_heat_relay.heat_is_on = heat_is_on
            zone_heat_relay.updated_on = datetime.datetime.now()
            logger.info('Heat state changed to is-on={} in zone {}'.format(heat_is_on, zone.name))
            zone_heat_relay.notify_transport_enabled = True
            db.session.commit()
        #else:
        #    logger.debug('Heat state [{}] unchanged in zone {}'.format(heat_is_on, zone.name))
    else:
        logger.warning('No heat relay found in zone {}'.format(zone.name))

def __decide_action(zone, current_temperature, target_temperature):
    assert isinstance(zone, models.Zone)
    if current_temperature < target_temperature:
        logger.info('Heat must be ON in {} temp {} target {}'.format(zone.name, current_temperature,
                                                                      target_temperature))
        heat_is_on = True
    else:
        logger.info('Heat must be OFF in {} temp {} target {}'.format(zone.name, current_temperature,
                                                                       target_temperature))
        heat_is_on = False
    __save_heat_state_db(zone=zone, heat_is_on=heat_is_on)
    return heat_is_on

def __update_zone_heat(zone, heat_schedule, sensor):
    try:
        heat_is_on = False
        minute = datetime.datetime.now().minute
        hour = datetime.datetime.now().hour
        weekday = datetime.datetime.today().weekday()
        if weekday <= 4: #Monday=0
            schedule_pattern=models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_week_id).first()
        else:
            schedule_pattern=models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_weekend_id).first()
        if schedule_pattern:
            pattern = str(schedule_pattern.pattern).replace('-', '').replace(' ','')
            if len(pattern) == 24:
                temperature_code = pattern[hour]
                temperature = models.TemperatureTarget.query.filter_by(code=temperature_code).first()
                if temperature:
                    logger.info('Active pattern for zone {} is {} temp {}'.format(zone.name, schedule_pattern.name,
                                                                                         temperature.target))
                    if sensor.temperature:
                        heat_is_on = __decide_action(zone, sensor.temperature, temperature.target)
                else:
                    logger.critical('Unknown temperature pattern code {}'.format(temperature_code))
            else:
                logger.warning('Incorrect temp pattern [{}] in zone {}, length is not 24'.format(pattern, zone.name))
    except Exception, ex:
        logger.error('Error updatezoneheat, err={}'.format(ex, exc_info=True))
    return heat_is_on

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
                    sensor_last_update_seconds = (datetime.datetime.now()-sensor.updated_on).total_seconds()
                    if sensor_last_update_seconds > 60 * 60:
                        logger.warning('Sensor {} not updated in last 60 minutes, unusual'.format(sensor.sensor_name))
                    if __update_zone_heat(zone, heat_schedule, sensor):
                        heat_is_on = True
        heatrelay_main_source = models.ZoneHeatRelay.query.filter_by(is_main_heat_source=True).first()
        if heatrelay_main_source:
            main_source_zone = models.Zone.query.filter_by(zone_id=heatrelay_main_source.zone_id).first()
            if main_source_zone:
                __save_heat_state_db(zone=main_source_zone, heat_is_on=heat_is_on)
            else:
                logger.critical('No heat main source can be located using zone id {}'.format(
                    heatrelay_main_source.zone_id))
        else:
            logger.critical('No heat main source is defined in db')
    except Exception, ex:
        logger.error('Error loop_zones, err={}'.format(ex, exc_info=True))

progress_status = None
def get_progress():
    global progress_status
    return progress_status

def thread_run():
    global progress_status
    logger.debug('Processing heat')
    progress_status = 'Looping zones'
    loop_zones()
    return 'Heat ok'
