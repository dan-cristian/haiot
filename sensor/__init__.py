from main import sqlitedb
from main.logger_helper import L
from common import utils, Constant
if sqlitedb:
    from storage.sqalc import models
from storage.model import m

__author__ = 'dcristian'


def not_used_record_update(obj):
    # save sensor state to db, except for current node
    try:
        sensor_host_name = utils.get_object_field_value(obj, Constant.JSON_PUBLISH_SOURCE_HOST)
        # avoid node to update itself in infinite recursion
        if sensor_host_name != Constant.HOST_NAME:
            address = utils.get_object_field_value(obj, 'address')
            n_address = utils.get_object_field_value(obj, 'n_address')
            sensor_type = utils.get_object_field_value(obj, 'type')
            record = m.Sensor.find_one({m.Sensor.address: address})
            if record is None:
                record = m.Sensor()
                record.address = address
            zone_sensor = m.ZoneSensor.find_one({m.ZoneSensor.sensor_address: address})
            if zone_sensor is not None:
                record.sensor_name = zone_sensor.sensor_name
            else:
                record.sensor_name = '(n/a) {} {} {}'.format(address, n_address, sensor_type)
            # mark the source to avoid duplicate actions
            setattr(record, Constant.JSON_PUBLISH_SOURCE_HOST, sensor_host_name)
            record.type = utils.get_object_field_value(obj, 'type')
            record.updated_on = utils.get_base_location_now_date()
            if 'counters_a' in obj:
                record.counters_a = utils.get_object_field_value(obj, 'counters_a')
            if 'counters_b' in obj:
                record.counters_b = utils.get_object_field_value(obj, 'counters_b')
            if 'delta_counters_a' in obj:
                record.delta_counters_a = utils.get_object_field_value(obj, 'delta_counters_a')
            if 'delta_counters_b' in obj:
                record.delta_counters_b = utils.get_object_field_value(obj, 'delta_counters_b')
            if 'temperature' in obj: record.temperature = utils.get_object_field_value(obj, 'temperature')
            if 'humidity' in obj: record.humidity = utils.get_object_field_value(obj, 'humidity')
            if 'iad' in obj: record.iad = utils.get_object_field_value(obj, 'iad')
            if 'vad' in obj: record.vad = utils.get_object_field_value(obj, 'vad')
            if 'vdd' in obj: record.vdd = utils.get_object_field_value(obj, 'vdd')
            if 'pio_a' in obj: record.pio_a = utils.get_object_field_value(obj, 'pio_a')
            if 'pio_b' in obj: record.pio_b = utils.get_object_field_value(obj, 'pio_b')
            if 'sensed_a' in obj: record.sensed_a = utils.get_object_field_value(obj, 'sensed_a')
            if 'sensed_b' in obj: record.sensed_b = utils.get_object_field_value(obj, 'sensed_b')

            # force field changed detection for delta_counters
            record.delta_counters_a = 0
            record.delta_counters_b = 0
            record.save_changed_fields(broadcast=False, persist=False)
            # commit() # not needed?

            # enable below only for testing on netbook
            # if Constant.HOST_NAME == 'xxxnetbook' and (record.delta_counters_a or record.delta_counters_b):
            #    dispatcher.send(Constant.SIGNAL_UTILITY, sensor_name=record.sensor_name,
            #                    units_delta_a=record.delta_counters_a,
            #                    units_delta_b=record.delta_counters_b, total_units_a=record.counters_a,
            #                    total_units_b=record.counters_b,
            #                    sampling_period_seconds=owsensor_loop.sampling_period_seconds)
    except Exception as ex:
        L.l.error('Error on sensor update, err {}'.format(ex), exc_info=True)
        