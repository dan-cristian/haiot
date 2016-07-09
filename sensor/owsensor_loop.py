import traceback
import pyownet.protocol
from pydispatch import dispatcher
from main.logger_helper import Log
from common import Constant, utils
from main.admin import model_helper, models

'''
Created on Mar 9, 2015

@author: dcristian
'''


initialised = False
owproxy = None


def do_device():
    global owproxy
    sensortype = 'n/a'
    sensors = owproxy.dir('/', slash=True, bus=False)
    for sensor in sensors:
        try:
            dev = {}
            sensortype = owproxy.read(sensor + 'type')
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
            save_to_db(dev)
        except pyownet.protocol.ConnError, er:
            Log.logger.warning('Connection error owserver: {}'.format(er))
        except pyownet.Error, ex:
            Log.logger.warning('Error reading sensor type={}: {}'.format(sensortype, ex))
        except Exception, ex:
            Log.logger.warning('Other error reading sensors: {}'.format(ex))
            traceback.print_exc()
    return 'Read {} sensors'.format(len(sensors))


def save_to_db(dev):
    # global db_lock
    # db_lock.acquire()
    try:
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
            else:
                record.delta_counters_a = 0  # don't know prev. count, assume no consumption (ticks could be lost)
        if dev.has_key('counters_b'):
            record.counters_b = dev['counters_b']
            if current_record:
                record.delta_counters_b = record.counters_b - current_record.counters_b
            else:
                record.delta_counters_b = 0  # don't know prev. count, assume no consumption (ticks could be lost)
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
                                   save_to_graph=True)
        if record.delta_counters_a is not None or record.delta_counters_b is not None:
            dispatcher.send(Constant.SIGNAL_UTILITY, sensor_name=record.sensor_name,
                            units_delta_a=record.delta_counters_a, units_delta_b=record.delta_counters_b,
                            total_units_a=record.counters_a, total_units_b=record.counters_b)
    except Exception, ex:
        Log.logger.warning('Error saving sensor to DB, err {}'.format(ex))
        # finally:
        #    db_lock.release()


def get_prefix(sensor, dev):
    global owproxy
    dev['address'] = str(owproxy.read(sensor + 'r_address'))
    dev['type'] = str(owproxy.read(sensor + 'type'))
    return dev


def get_bus(sensor, dev):
    global owproxy
    dev = get_prefix(sensor, dev)
    return dev


def get_temperature(sensor, dev):
    global owproxy
    dev = get_prefix(sensor, dev)
    # 2 digits round
    dev['temperature'] = utils.round_sensor_value(owproxy.read(sensor + 'temperature'))
    return dev


def get_humidity(sensor, dev):
    global owproxy
    dev = get_prefix(sensor, dev)
    dev['humidity'] = utils.round_sensor_value(owproxy.read(sensor + 'humidity'))
    return dev


def get_voltage(sensor, dev):
    global owproxy
    dev = get_prefix(sensor, dev)
    dev['iad'] = float(owproxy.read(sensor + 'IAD'))
    dev['vad'] = float(owproxy.read(sensor + 'VAD'))
    dev['vdd'] = float(owproxy.read(sensor + 'VDD'))
    return dev


def get_counter(sensor, dev):
    global owproxy
    dev = get_prefix(sensor, dev)
    dev['counters_a'] = int(owproxy.read(sensor + 'counters.A'))
    dev['counters_b'] = int(owproxy.read(sensor + 'counters.B'))
    return dev


def get_io(sensor, dev):
    global owproxy
    # IMPORTANT: do not use . in field names as it throws error on JSON, only use "_"
    dev = get_prefix(sensor, dev)
    dev['pio_a'] = str(owproxy.read(sensor + 'PIO.A')).strip()
    dev['pio_b'] = str(owproxy.read(sensor + 'PIO.B')).strip()
    dev['sensed_a'] = str(owproxy.read(sensor + 'sensed.A')).strip()
    dev['sensed_b'] = str(owproxy.read(sensor + 'sensed.B')).strip()
    return dev


def get_unknown(sensor, dev):
    global owproxy
    dev = get_prefix(sensor, dev)
    return dev


def init():
    Log.logger.info('Initialising owssensor')
    global owproxy, initialised
    host = "none"
    port = "none"
    try:
        host = model_helper.get_param(Constant.P_OWSERVER_HOST_1)
        port = str(model_helper.get_param(Constant.P_OWSERVER_PORT_1))
        owproxy = pyownet.protocol.proxy(host=host, port=port)
        initialised = True
    except Exception, ex:
        Log.logger.info('Unable to connect to 1-wire owserver host {} port {}'.format(host, port))
        initialised = False
    return initialised


def thread_run():
    global initialised
    Log.logger.debug('Processing sensors')
    if initialised:
        return do_device()
