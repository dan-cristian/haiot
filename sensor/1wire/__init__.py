import traceback
import threading
import prctl
import time
from pydispatch import dispatcher
import datetime
from main import general_init, sqlitedb
if sqlitedb:
    from storage.sqalc import models
from storage.model import m
try:
    from common import Constant, utils, get_json_param
    from main.logger_helper import L
    from main import thread_pool
except Exception as ex:
    print("Exception importing key modules, probably started via main")
    class L:
        class l:
            @staticmethod
            def info(msg): print(msg)
            @staticmethod
            def warning(msg): print(msg)


from common import fix_module
while True:
    try:
        import pyownet.protocol
        break
    except ImportError as iex:
        if not fix_module(iex):
            break

'''
Created on Mar 9, 2015

@author: dcristian
'''


class P:
    initialised = False
    last_warning = datetime.datetime.min
    check_period = 120  # how often I check for new sensors
    sampling_period_seconds = 30  # how often I read them
    ow_conn_list = {}  # key is busname, value is ow connection
    func_list = []  # callable functions
    warning_issued = False
    IGNORED_TEMPERATURE = 85  # ignore this temp value, usually is an error
    failed_temp = False
    failed_temp_count = 0
    thread_pool_status = None


def do_device(ow, path):
    # http://pyownet.readthedocs.io/en/latest/protocol.html
    sensor_dict = {}
    sensortype = 'n/a'
    all_start = datetime.datetime.now()
    try:
        sensors = ow.dir(path, slash=True, bus=False)
        count = 0
        last_sensor = ''
        for sensor in sensors:
            # L.l.info("process sensor {}".format(sensor))
            if general_init.P.shutting_down:
                break
            if not ('interface' in sensor or 'simultaneous' in sensor or 'alarm' in sensor):
                # start = datetime.datetime.now()
                try:
                    dev = {}
                    dev['path'] = path
                    sensortype = ow.read(sensor + 'type').decode('utf-8')
                    # L.l.info('Reading s={} type={}'.format(sensor, sensortype))
                    if sensortype == 'DS2423':
                        dev = get_counter(sensor, dev, ow)
                    elif sensortype == 'DS2413':
                        dev = get_io(sensor, dev, ow)
                    elif sensortype == 'DS18B20':
                        dev = get_temperature(sensor, dev, ow)
                    elif sensortype == 'DS2438':
                        dev = get_temperature(sensor, dev, ow)
                        dev = get_voltage(sensor, dev, ow)
                        dev = get_humidity(sensor, dev, ow)
                    else:
                        dev = get_unknown(sensor, dev, ow)
                    sensor_dict[dev['address']] = dev
                    if sensortype != 'DS2401':
                        save_to_db(dev)
                        last_sensor = dev['address']
                        count += 1
                except pyownet.protocol.ConnError as er:
                    L.l.warning('Connection error owserver: {}'.format(er))
                except pyownet.Error as ex:
                    L.l.warning('Error reading sensor type={}, sensor={}, ex={}'.format(sensortype, sensor, ex))
                except Exception as ex:
                    L.l.warning('Other error reading sensors: {}'.format(ex))
                    traceback.print_exc()
                # delta = (datetime.datetime.now() - start).total_seconds()
                # L.l.info("Sensor {} read took {} seconds".format(dev['address'], delta))
        all_delta = (datetime.datetime.now() - all_start).total_seconds()
        if count > 0 and all_delta > 1:
            # L.l.debug("All {} sensors read in bus {} took {} seconds, last was {}".format(
            #     count, path, all_delta, last_sensor))
            pass
    except Exception as ex:
        L.l.warning("Error reading 1wire, err={}".format(ex))
    return sensor_dict


def save_to_db(dev):
    try:
        delta_time_counters = None
        address = dev['address']
        zone_sensor = m.ZoneSensor.find_one({m.ZoneSensor.sensor_address: address})
        record = m.Sensor.find_one({m.Sensor.address: address})
        if record is None:
            record = m.Sensor()
            record.address = address
        if zone_sensor:
            record.sensor_name = zone_sensor.sensor_name
        else:
            record.sensor_name = '{} {} {}'.format(address, dev['n_address'], dev['type'])
        record.type = dev['type']
        record.updated_on = utils.get_base_location_now_date()
        record.comment = dev['path']
        if 'counters_a' in dev.keys():
            if record.counters_a is not None:
                record.delta_counters_a = dev['counters_a'] - record.counters_a
            else:
                record.delta_counters_a = 0  # don't know prev. count, assume no consumption (ticks could be lost)
            if record.updated_on is not None:
                # get accurate interval (e.g. to establish power consumption in watts)
                delta_time_counters = (utils.get_base_location_now_date() - record.updated_on).total_seconds()
            else:  # when running first time with db empty
                delta_time_counters = P.sampling_period_seconds
        if 'counters_b' in dev.keys():
            if record.counters_b is not None:
                record.delta_counters_b = dev['counters_b'] - record.counters_b
            else:
                # fixme: don't know prev. count, assume no consumption (ticks could be lost)
                record.delta_counters_b = 0
        if 'temperature' in dev.keys():
            record.temperature = dev['temperature']
        if 'humidity' in dev.keys():
            record.humidity = dev['humidity']
        if 'iad' in dev.keys():
            record.iad = dev['iad']
        if 'vad' in dev.keys():
            record.vad = dev['vad']
        if 'vdd' in dev.keys():
            record.vdd = dev['vdd']
        if 'pio_a' in dev.keys():
            record.pio_a = dev['pio_a']
        if 'pio_b' in dev.keys():
            record.pio_b = dev['pio_b']
        if 'sensed_a' in dev.keys():
            record.sensed_a = dev['sensed_a']
        if 'sensed_b' in dev.keys():
            record.sensed_b = dev['sensed_b']
        # force field changed detection for delta_counters to enable save in history
        # but allow one 0 record to be saved for nicer graphics
        record.save_changed_fields(broadcast=False, persist=True)
        if record.delta_counters_a is not None or record.delta_counters_b is not None:
            dispatcher.send(Constant.SIGNAL_UTILITY, sensor_name=record.sensor_name,
                            units_delta_a=record.delta_counters_a, units_delta_b=record.delta_counters_b,
                            total_units_a=record.counters_a, total_units_b=record.counters_b,
                            sampling_period_seconds=delta_time_counters)
        if record.vad is not None:
            dispatcher.send(Constant.SIGNAL_UTILITY_EX, sensor_name=record.sensor_name, value=record.vad)
    except Exception as ex:
        L.l.error('Error saving sensor to DB, err {}'.format(ex), exc_info=True)


def get_prefix(sensor, dev, ow):
    dev['address'] = ow.read(sensor + 'r_address').decode('utf-8')
    dev['type'] = ow.read(sensor + 'type').decode('utf-8')
    dev['n_address'] = ow.read(sensor + 'address').decode('utf-8')
    return dev


def get_bus(sensor, dev, ow):
    dev = get_prefix(sensor, dev, ow)
    return dev


def get_temperature(sensor, dev, ow):
    try:
        dev = get_prefix(sensor, dev, ow)
        # val = None
        # 2 digits round
        # if P.failed_temp and P.failed_temp_count < 100:
        #    try:
        #        val = utils.round_sensor_value(ow.read(sensor + 'fasttemp'))
        #    except Exception as ex1:
        #        # fasttemp might not exist, so revert to normal
        #        P.failed_temp = False
        #        P.failed_temp_count = 0
        # if val is None:
        val = utils.round_sensor_value(ow.read(sensor + 'temperature').decode('utf-8'))
        P.failed_temp_count = 0
        P.failed_temp = False
        if val != P.IGNORED_TEMPERATURE:
            dev['temperature'] = val
    except Exception as ex:
        L.l.warning("Read temp with {}".format(ex))
        # P.failed_temp = True
        # P.failed_temp_count += 1
    return dev


def get_humidity(sensor, dev, ow):
    dev = get_prefix(sensor, dev, ow)
    dev['humidity'] = utils.round_sensor_value(ow.read(sensor + 'humidity').decode('utf-8'))
    return dev


def get_voltage(sensor, dev, ow):
    dev = get_prefix(sensor, dev, ow)
    dev['iad'] = float(ow.read(sensor + 'IAD').decode('utf-8'))
    dev['vad'] = float(ow.read(sensor + 'VAD').decode('utf-8'))
    dev['vdd'] = float(ow.read(sensor + 'VDD').decode('utf-8'))
    return dev


def get_counter(sensor, dev, ow):
    dev = get_prefix(sensor, dev, ow)
    dev['counters_a'] = int(ow.read(sensor + 'counters.A').decode('utf-8'))
    dev['counters_b'] = int(ow.read(sensor + 'counters.B').decode('utf-8'))
    return dev


def get_io(sensor, dev, ow):
    # IMPORTANT: do not use . in field names as it throws error on JSON, only use "_"
    dev = get_prefix(sensor, dev, ow)
    dev['pio_a'] = ow.read(sensor + 'PIO.A').decode('utf-8').strip()
    dev['pio_b'] = ow.read(sensor + 'PIO.B').decode('utf-8').strip()
    dev['sensed_a'] = ow.read(sensor + 'sensed.A').decode('utf-8').strip()
    dev['sensed_b'] = ow.read(sensor + 'sensed.B').decode('utf-8').strip()
    return dev


def check_inactive():
    P.thread_pool_status = 'check inactive'
    """check for inactive sensors not read recently but in database"""
    if sqlitedb:
        sensor_list = models.Sensor().query_all()
        defined_sensor_list = models.ZoneSensor().query_all()
    else:
        sensor_list = m.Sensor.find()
        defined_sensor_list = m.ZoneSensor().find()
    ref_list = []
    delta = (datetime.datetime.now() - P.last_warning).total_seconds()
    log_warn = (delta > 60 * 15)
    for zone_sensor in defined_sensor_list:
        ref_list.append(zone_sensor.sensor_address)
    for sensor in sensor_list:
        if sensor.updated_on is not None:
            elapsed = round((utils.get_base_location_now_date() - sensor.updated_on).total_seconds() / 60, 0)
            if sensor.address not in ref_list:
                L.l.warning('Sensor {} {} not defined'.format(sensor.address, sensor.sensor_name))
                #current_record = models.SensorError.query.filter_by(sensor_address=sensor.address).first()
                #record = models.SensorError()
                #record.sensor_name = sensor.sensor_name
                #if current_record is not None:
                #    record.error_count = current_record.error_count
                #else:
                #    record.error_count = 0
                #record.error_count += 1
                #record.error_type = 0
                #record.save_changed_fields(current_record=None, new_record=record, save_to_graph=True, save_all_fields=True)
            if log_warn and elapsed > 2 * P.sampling_period_seconds:
                L.l.warning('Sensor {} type {} not updated since {} min'.format(
                    sensor.sensor_name, sensor.type, elapsed))
                P.last_warning = datetime.datetime.now()


def get_unknown(sensor, dev, ow):
    dev = get_prefix(sensor, dev, ow)
    return dev


def _dynamic_thread_run(ow_conn, ow_bus):
    def _function():
        prctl.set_name("owsensor-bus")
        threading.current_thread().name = "{}{}".format("owsensor", ow_bus)
        do_device(ow=ow_conn, path=ow_bus)
        prctl.set_name("idle_owsensor-bus")
        threading.current_thread().name = "idle_owsensor-bus"
    return _function


def _get_bus_list(ohost, oport):
    ow = pyownet.protocol.proxy(host=ohost, port=oport)
    owitems = ow.dir('/', slash=False, bus=True)
    for owitem in owitems:
        if 'bus' in owitem:
            P.thread_pool_status = 'init bus {}'.format(owitem)
            ow_proxy = pyownet.protocol.proxy(host=ohost, port=oport, flags=pyownet.protocol.FLG_UNCACHED)
            P.ow_conn_list[owitem] = ow_proxy
            func = _dynamic_thread_run(ow_conn=ow_proxy, ow_bus=owitem)
            thread_pool.add_interval_callable(func, P.sampling_period_seconds)
            P.func_list.append(func)
            # start all threads sequentially to avoid peak cpu usage
            time.sleep(P.sampling_period_seconds / len(owitems))
        # else:
        #    L.l.info('Ignoring {}'.format(owitem))
    L.l.info("Found {} owfs busses and initialised {} threads".format(len(P.ow_conn_list), len(P.func_list)))


def _init_comm():
    P.thread_pool_status = 'init ows bus list'
    ohost = "none"
    oport = "none"
    try:
        ohost = get_json_param(Constant.P_OWSERVER_HOST_1)
        oport = int(get_json_param(Constant.P_OWSERVER_PORT_1))
        _get_bus_list(ohost, oport)
        P.initialised = True
        P.warning_issued = False
    except Exception as ex:
        if not P.warning_issued:
            L.l.info('1-wire owserver not initialised on host {} port {}, ex={}'.format(ohost, oport, ex))
            P.initialised = False
            P.warning_issued = True
    return P.initialised


def thread_run():
    prctl.set_name("owsensor")
    threading.current_thread().name = "owsensor"
    if P.initialised:
        check_inactive()
    else:
        _init_comm()
    prctl.set_name("idle_owsensor")
    threading.current_thread().name = "idle_owsensor"


def unload():
    thread_pool.remove_callable(thread_run)
    for func in P.func_list:
        thread_pool.remove_callable(func)
    # for ow in P.ow_conn_list:
    #    P.ow_conn_list[ow].close_connection()
    P.initialised = False


def init():
    L.l.info('1wire module initialising')
    thread_pool.add_interval_callable(thread_run, P.check_period)
