__author__ = 'dcristian'

#! venv/bin/python

import datetime
from main.admin import thread_pool, db
from main import logger
from common import utils, constant
import owsensor_loop
import rfxcom_run
from main.admin import models
from main.admin.model_helper import commit

initialised=False

def sensor_update(obj):
    #save sensor state to db, except for current node
    try:
        sensor_host_name = utils.get_object_field_value(obj, 'name')
        logger.debug('Received sensor state update from {}'.format(sensor_host_name))
        #avoid node to update itself in infinite recursion
        if sensor_host_name != constant.HOST_NAME:
            address = utils.get_object_field_value(obj, 'address')
            record = models.Sensor(address=address)
            assert isinstance(record, models.Sensor)
            zone_sensor = models.ZoneSensor.query.filter_by(sensor_address=address).first()
            if zone_sensor:
                record.sensor_name = zone_sensor.sensor_name
            else:
                record.sensor_name = '(not defined) {}'.format(address)
            record.type = utils.get_object_field_value(obj, 'type')
            record.updated_on = utils.get_base_location_now_date()
            if obj.has_key('counters_a'): record.counters_a = utils.get_object_field_value(obj, 'counters_a')
            if obj.has_key('counters_b'): record.counters_b = utils.get_object_field_value(obj, 'counters_b')
            if obj.has_key('temperature'): record.temperature = utils.get_object_field_value(obj, 'temperature')
            if obj.has_key('humidity'): record.humidity = utils.get_object_field_value(obj, 'humidity')
            if obj.has_key('iad'): record.iad = utils.get_object_field_value(obj, 'iad')
            if obj.has_key('vad'): record.vad = utils.get_object_field_value(obj, 'vad')
            if obj.has_key('vdd'): record.vdd = utils.get_object_field_value(obj, 'vdd')
            if obj.has_key('pio_a'): record.pio_a = utils.get_object_field_value(obj, 'pio_a')
            if obj.has_key('pio_b'): record.pio_b = utils.get_object_field_value(obj, 'pio_b')
            if obj.has_key('sensed_a'): record.sensed_a = utils.get_object_field_value(obj, 'sensed_a')
            if obj.has_key('sensed_b'): record.sensed_b = utils.get_object_field_value(obj, 'sensed_b')

            current_record = models.Sensor.query.filter_by(address=address).first()
            record.save_changed_fields(current_record=current_record, new_record=record, notify_transport_enabled=False,
                                       save_to_graph=False)
            commit()
    except Exception, ex:
        logger.warning('Error on sensor update, err {}'.format(ex))
        db.session.rollback()

def unload():
    #...
    global initialised
    thread_pool.remove_callable(owsensor_loop.thread_run)
    thread_pool.remove_callable(rfxcom_run.thread_run)
    rfxcom_run.unload()
    initialised = False

def init():
    logger.info('Sensor module initialising')
    if owsensor_loop.init():
        thread_pool.add_callable(owsensor_loop.thread_run, run_interval_second=30)
    if rfxcom_run.init():
        thread_pool.add_callable(rfxcom_run.thread_run, run_interval_second=30)
    global initialised
    initialised = True
