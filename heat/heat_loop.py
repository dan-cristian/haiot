__author__ = 'dcristian'
import logging
from datetime import datetime
from main.admin import models

def decide_action(zone, current_temperature, target_temperature):
    if current_temperature < target_temperature:
        logging.info('Heat must be ON curr temp {} target {}'.format(current_temperature, target_temperature))
    else:
        logging.info('Heat must be OFF curr temp {} target {}'.format(current_temperature, target_temperature))

def check_zone(zone, heat_schedule, sensor):
    assert isinstance(zone, models.Zone)
    assert isinstance(heat_schedule, models.HeatSchedule)
    assert isinstance(sensor, models.Sensor)

    min = datetime.now().minute
    hour = datetime.now().hour
    weekday = datetime.today().weekday()
    if weekday <=5:
        schedule_pattern=models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_week_id).first()
    else:
        schedule_pattern=models.SchedulePattern.query.filter_by(id=heat_schedule.pattern_weekend_id).first()
    if schedule_pattern:
        assert isinstance(schedule_pattern, models.SchedulePattern)
        pattern = schedule_pattern.pattern
        temperature_code = pattern[hour]
        temperature = models.TemperatureTarget.query.filter_by(code=temperature_code).first()
        if temperature:
            logging.info('Active pattern for zone {} is {} temp {}'.format(zone.name, schedule_pattern.name,
                                                                                 temperature.target))
            if sensor.temperature:
                decide_action(zone, sensor.temperature, temperature.target)


def main():
    zone_list = models.Zone.query.all()
    for zone in zone_list:
        heat_schedule = models.HeatSchedule.query.filter_by(zone_id=zone.id).first()
        zonesensor = models.ZoneSensor.query.filter_by(zone_id=zone.id).first()
        if heat_schedule and zonesensor and zonesensor.sensor:
            sensor = zonesensor.sensor
            check_zone(zone, heat_schedule, sensor)

def init():
    pass

def thread_run():
    logging.info('Processing heat')
    main()
    return 'Heat ok'

