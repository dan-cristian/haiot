import traceback
import pyownet.protocol
from pydispatch import dispatcher
from main.logger_helper import L
from common import Constant, utils
from main.admin import model_helper, models
import datetime
'''
Created on Mar 9, 2015

@author: dcristian
'''


initialised = False
__owproxy = None
sampling_period_seconds = 1


def do_device():
    global __owproxy
    sensor_dict = {}
    sensortype = 'n/a'
    all_start = datetime.datetime.now()
    sensors = __owproxy.dir('/', slash=True, bus=False)
    for sensor in sensors:
        start = datetime.datetime.now()
        try:
            dev = {}
            sensortype = __owproxy.read(sensor + 'type')
            if sensortype == 'DS2423':
                dev = get_counter(sensor, dev)
            elif sensortype == 'DS2413':
                dev = get_io(sensor, dev)
            elif sensortype == 'DS18B20':
                dev = get_temperature(sensor, dev)
            elif sensortype == 'DS2438':
                dev = get_temperature(sensor, dev)
                dev = get_voltage(sensor, dev)
                dev = get_humidity(sensor, dev)
            elif sensortype == 'DS2401':
                dev = get_bus(sensor, dev)
            else:
                dev = get_unknown(sensor, dev)
            sensor_dict[dev['address']] = dev
            save_to_db(dev)
        except pyownet.protocol.ConnError, er:
            L.l.warning('Connection error owserver: {}'.format(er))
        except pyownet.Error, ex:
            L.l.warning('Error reading sensor type={}: {}'.format(sensortype, ex))
        except Exception, ex:
            L.l.warning('Other error reading sensors: {}'.format(ex))
            traceback.print_exc()
        delta = (datetime.datetime.now() - start).total_seconds()
        L.l.info("Sensor {} read took {} seconds".format(dev['address'], delta))
    all_delta = (datetime.datetime.now() - all_start).total_seconds()
    L.l.info("All sensors read took {} seconds".format(all_delta))
    return sensor_dict


def save_to_db(dev):
    # global db_lock
    # db_lock.acquire()
    try:
        delta_time_counters = None
        address = dev['address']
        record = models.Sensor(address=address)
        assert isinstance(record, models.Sensor)
        zone_sensor = models.ZoneSensor.query.filter_by(sensor_address=address).first()
        current_record = models.Sensor.query.filter_by(address=address).first()
        if zone_sensor:
            record.sensor_name = zone_sensor.sensor_name
        else:
            record.sensor_name = '(not defined) {}'.format(address)
        record.type = dev['type']
        record.updated_on = utils.get_base_location_now_date()
        if dev.has_key('counters_a'):
            record.counters_a = dev['counters_a']
            if current_record:
                record.delta_counters_a = record.counters_a - current_record.counters_a
                # get accurate interval (e.g. to establish power consumption in watts)
                delta_time_counters = (utils.get_base_location_now_date() - current_record.updated_on).total_seconds()
            else:
                record.delta_counters_a = 0  # don't know prev. count, assume no consumption (ticks could be lost)
                delta_time_counters = sampling_period_seconds
        if dev.has_key('counters_b'):
            record.counters_b = dev['counters_b']
            if current_record:
                record.delta_counters_b = record.counters_b - current_record.counters_b
            else:
                # fixme: don't know prev. count, assume no consumption (ticks could be lost)
                record.delta_counters_b = 0
        if dev.has_key('temperature'):
            record.temperature = dev['temperature']
        if dev.has_key('humidity'):
            record.humidity = dev['humidity']
        if dev.has_key('iad'):
            record.iad = dev['iad']
        if dev.has_key('vad'):
            record.vad = dev['vad']
        if dev.has_key('vdd'):
            record.vdd = dev['vdd']
        if dev.has_key('pio_a'):
            record.pio_a = dev['pio_a']
        if dev.has_key('pio_b'):
            record.pio_b = dev['pio_b']
        if dev.has_key('sensed_a'):
            record.sensed_a = dev['sensed_a']
        if dev.has_key('sensed_b'):
            record.sensed_b = dev['sensed_b']
        # force field changed detection for delta_counters to enable save in history
        # but allow one 0 record to be saved for nicer graphics
        if current_record is not None:
            if record.delta_counters_a != 0:
                current_record.delta_counters_a = 0
            if record.delta_counters_b != 0:
                current_record.delta_counters_b = 0
        record.save_changed_fields(current_record=current_record, new_record=record, notify_transport_enabled=True,
                                   save_to_graph=True, debug=False)
        if record.delta_counters_a is not None or record.delta_counters_b is not None:
            dispatcher.send(Constant.SIGNAL_UTILITY, sensor_name=record.sensor_name,
                            units_delta_a=record.delta_counters_a, units_delta_b=record.delta_counters_b,
                            total_units_a=record.counters_a, total_units_b=record.counters_b,
                            sampling_period_seconds=delta_time_counters)
        if record.vad is not None:
            dispatcher.send(Constant.SIGNAL_UTILITY_EX, sensor_name=record.sensor_name, value=record.vad)
    except Exception, ex:
        L.l.error('Error saving sensor to DB, err {}'.format(ex), exc_info=True)
        # finally:
        #    db_lock.release()


def get_prefix(sensor, dev):
    global __owproxy
    dev['address'] = str(__owproxy.read(sensor + 'r_address'))
    dev['type'] = str(__owproxy.read(sensor + 'type'))
    return dev


def get_bus(sensor, dev):
    global __owproxy
    dev = get_prefix(sensor, dev)
    return dev


def get_temperature(sensor, dev):
    global __owproxy
    dev = get_prefix(sensor, dev)
    # 2 digits round
    dev['temperature'] = utils.round_sensor_value(__owproxy.read(sensor + 'temperature'))
    return dev


def get_humidity(sensor, dev):
    global __owproxy
    dev = get_prefix(sensor, dev)
    dev['humidity'] = utils.round_sensor_value(__owproxy.read(sensor + 'humidity'))
    return dev


def get_voltage(sensor, dev):
    global __owproxy
    dev = get_prefix(sensor, dev)
    dev['iad'] = float(__owproxy.read(sensor + 'IAD'))
    dev['vad'] = float(__owproxy.read(sensor + 'VAD'))
    dev['vdd'] = float(__owproxy.read(sensor + 'VDD'))
    return dev


def get_counter(sensor, dev):
    global __owproxy
    dev = get_prefix(sensor, dev)
    dev['counters_a'] = int(__owproxy.read(sensor + 'counters.A'))
    dev['counters_b'] = int(__owproxy.read(sensor + 'counters.B'))
    return dev


def get_io(sensor, dev):
    global __owproxy
    # IMPORTANT: do not use . in field names as it throws error on JSON, only use "_"
    dev = get_prefix(sensor, dev)
    dev['pio_a'] = str(__owproxy.read(sensor + 'PIO.A')).strip()
    dev['pio_b'] = str(__owproxy.read(sensor + 'PIO.B')).strip()
    dev['sensed_a'] = str(__owproxy.read(sensor + 'sensed.A')).strip()
    dev['sensed_b'] = str(__owproxy.read(sensor + 'sensed.B')).strip()
    return dev


def check_inactive(sensor_dict):
    """check for inactive sensors not read recently but in database"""
    inactive_list = ''
    record_list = models.Sensor().query_all()
    for sensor in record_list:
        if sensor.address not in sensor_dict.keys():
            current_record = models.SensorError.query.filter_by(sensor_address=sensor.address).first()
            record = models.SensorError()
            record.sensor_name = sensor.sensor_name
            if current_record is not None:
                record.error_count = current_record.error_count
            else:
                record.error_count = 0
            record.error_count += 1
            record.error_type = 0
            record.save_changed_fields(current_record=None, new_record=record, save_to_graph=True, save_all_fields=True)
        elapsed = round((utils.get_base_location_now_date() - sensor.updated_on).total_seconds() / 60, 0)
        if elapsed > 2 * sampling_period_seconds:
            L.l.warning('Sensor {} type {} not responding since {} min'.format(
                sensor.sensor_name,sensor.type, elapsed))


def get_unknown(sensor, dev):
    global __owproxy
    dev = get_prefix(sensor, dev)
    return dev


def init():
    L.l.debug('Initialising owssensor')
    global __owproxy, initialised
    host = "none"
    port = "none"
    try:
        host = model_helper.get_param(Constant.P_OWSERVER_HOST_1)
        port = str(model_helper.get_param(Constant.P_OWSERVER_PORT_1))
        __owproxy = pyownet.protocol.proxy(host=host, port=port)
        initialised = True
    except Exception, ex:
        L.l.info('1-wire owserver not found on host {} port {}'.format(host, port))
        initialised = False
    return initialised


def thread_run():
    global initialised
    L.l.debug('Processing sensors')
    if initialised:
        sensor_dict = do_device()
        check_inactive(sensor_dict)
