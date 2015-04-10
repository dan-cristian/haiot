'''
Created on Mar 9, 2015

@author: dcristian
'''
import pyownet.protocol
import time
import datetime
import socket
import threading
import logging
import math
import threading
from pydispatch import dispatcher
import common.constant
import sys
from common import constant
from main.admin import model_helper
from main import db
from main.admin import models
from sensor import round_sensor_value
from main.admin import event
from wtforms.ext.sqlalchemy.orm import model_form

def do_device (owproxy):
    sensors = owproxy.dir('/', slash=True, bus=False)
    for sensor in sensors:
        try:
            dev = {}
            sensortype = owproxy.read(sensor+'type')
            if sensortype == 'DS2423':
                dev = get_counter(sensor, owproxy, dev)
            elif sensortype == 'DS2413':
                dev=get_io(sensor, owproxy, dev)
            elif sensortype == 'DS18B20':
                dev=get_temperature(sensor, owproxy, dev)
            elif sensortype == 'DS2438':
                dev=get_temperature(sensor, owproxy, dev)
                dev=get_voltage(sensor, owproxy, dev)
                dev=get_humidity(sensor, owproxy, dev)
            elif sensortype=='DS2401':
                dev=get_bus(sensor, owproxy, dev)
            else:
                dev=get_unknown(sensor, owproxy, dev)
            save_to_db(dev)
        except pyownet.protocol.ConnError:
            logging.warning('Connection error owserver')
    return 'Read {} sensors'.format(len(sensors))


def save_to_db(dev):
    #global db_lock
    #db_lock.acquire()
    try:
        address=dev['address']
        sensor = models.Sensor.query.filter_by(address=address).first()
        zone_sensor = models.ZoneSensor.query.filter_by(sensor_address=address).first()
        if sensor == None:
            sensor = models.Sensor(address=address)
            record_is_new = True
        else:
            record_is_new = False
        if zone_sensor:
            sensor.sensor_name = zone_sensor.sensor_name
        else:
            sensor.sensor_name = '(not defined) ' + address
        key_compare = sensor.comparator_unique_graph_record()
        sensor.type = dev['type']
        sensor.updated_on = datetime.datetime.now()
        if dev.has_key('counters_a'): sensor.counters_a = dev['counters_a']
        if dev.has_key('counters_b'): sensor.counters_b = dev['counters_b']
        if dev.has_key('temperature'): sensor.temperature = dev['temperature']
        if dev.has_key('humidity'): sensor.humidity = dev['humidity']
        if dev.has_key('iad'): sensor.iad = dev['iad']
        if dev.has_key('vad'): sensor.vad = dev['vad']
        if dev.has_key('vdd'): sensor.vdd = dev['vdd']
        if dev.has_key('pio_a'): sensor.pio_a = dev['pio_a']
        if dev.has_key('pio_b'): sensor.pio_b = dev['pio_b']
        if dev.has_key('sensed_a'): sensor.sensed_a = dev['sensed_a']
        if dev.has_key('sensed_b'): sensor.sensed_b = dev['sensed_b']

        #assert isinstance(old_value, models.Sensor)
        db.session.autoflush=False
        if key_compare != sensor.comparator_unique_graph_record():
            if record_is_new:
                db.session.add(sensor)
            else:
                logging.info('Sensor {} change, old={} new={}'.format(sensor.sensor_name, key_compare,
                                                                      sensor.comparator_unique_graph_record()))
            sensor.save_to_graph = True
            sensor.notify_transport_enabled = True
            db.session.commit()
        else:
            logging.debug('Ignoring sensor read {}, no value change'.format(key_compare))
            sensor.save_to_graph = False
    except Exception, ex:
        logging.warning('Error saving sensor to DB, err {}'.format(ex))
    #finally:
    #    db_lock.release()

def get_prefix(sensor, owproxy, dev):
    dev['address']=str(owproxy.read(sensor+'r_address'))
    dev['type']=str(owproxy.read(sensor+'type'))
    return dev

def get_bus( sensor , owproxy, dev):
    dev = get_prefix(sensor, owproxy, dev)
    return dev

def get_temperature( sensor , owproxy, dev):
    dev = get_prefix(sensor, owproxy, dev)
    # 2 digits round
    dev['temperature'] = round_sensor_value(owproxy.read(sensor+'temperature'))
    return dev

def get_humidity( sensor , owproxy, dev):
    dev = get_prefix(sensor, owproxy, dev)
    dev['humidity'] = round_sensor_value(owproxy.read(sensor+'humidity'))
    return dev

def get_voltage(sensor, owproxy, dev):
    dev = get_prefix(sensor, owproxy, dev)
    dev['iad'] = float(owproxy.read(sensor+'IAD'))
    dev['vad'] = float(owproxy.read(sensor+'VAD'))
    dev['vdd'] = float(owproxy.read(sensor+'VDD'))
    return dev

def get_counter( sensor , owproxy, dev):
    dev = get_prefix(sensor, owproxy, dev)
    dev['counters_a'] = int(owproxy.read(sensor+'counters.A'))
    dev['counters_b'] = int(owproxy.read(sensor+'counters.B'))
    return dev

def get_io( sensor , owproxy, dev):
    #IMPORTANT: do not use . in field names as it throws error on JSON, only use "_"
    dev = get_prefix(sensor, owproxy, dev)
    dev['pio_a'] = str(owproxy.read(sensor+'PIO.A')).strip()
    dev['pio_b'] = str(owproxy.read(sensor+'PIO.B')).strip()
    dev['sensed_a'] = str(owproxy.read(sensor+'sensed.A')).strip()
    dev['sensed_b'] = str(owproxy.read(sensor+'sensed.B')).strip()
    return dev

def get_unknown (sensor, owproxy, dev):
    dev = get_prefix(sensor, owproxy, dev)
    return dev

initialised = False
owproxy=None
def init():
    logging.info('Initialising owssensor')
    global owproxy, initialised
    try:
        host = model_helper.get_param(constant.P_OWSERVER_HOST_1)
        port = str(model_helper.get_param(constant.P_OWSERVER_PORT_1))
        owproxy = pyownet.protocol.proxy(host=host, port=port)
        initialised = True
    except Exception, ex:
        logging.warning('Unable to connect to 1-wire owserver host {} port {}'.format(host, port))
        initialised = False
    return initialised

def thread_run():
    global initialised
    logging.debug('Processing sensors')
    if initialised:
        return do_device(owproxy)


