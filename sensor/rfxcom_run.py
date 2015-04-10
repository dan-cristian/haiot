__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import logging
import glob
import datetime
from RFXtrx.pyserial import PySerialTransport
import RFXtrx
from main.admin import models, db
from common import constant
from sensor import round_sensor_value

initialised = False
transport = None


def __rfx_reading(packet):
    if packet:
        try:
            assert isinstance(packet, RFXtrx.SensorEvent)
            id = packet.device.id_string
            type = packet.device.type_string
            __save_sensor_db(id=id, type=type, value_list=packet.values)
        except Exception:
            logging.info('Unknown rfx packet type {}'.format(packet))

def __save_sensor_db(id='', type='', value_list=[]):
    sensor = models.Sensor.query.filter_by(address=id).first()
    zone_sensor = models.ZoneSensor.query.filter_by(sensor_address=id).first()
    if sensor == None:
        sensor = models.Sensor(address=id)
        record_is_new = True
    else:
        record_is_new = False
    if zone_sensor:
        sensor.sensor_name = zone_sensor.sensor_name
    else:
        sensor.sensor_name = '(not defined) ' + id
    key_compare = sensor.comparator_unique_graph_record()
    sensor.updated_on = datetime.datetime.now()
    sensor.type = type
    if 'Humidity' in value_list: sensor.humidity = round_sensor_value(value_list['Humidity'])
    if 'Temperature' in value_list: sensor.temperature= round_sensor_value(value_list['Temperature'])
    if 'Battery numeric' in value_list: sensor.battery_level = value_list['Battery numeric']
    if 'Rssi numeric' in value_list: sensor.rssi = value_list['Rssi numeric']

    if key_compare != sensor.comparator_unique_graph_record():
        if record_is_new:
            db.session.add(sensor)
        else:
            logging.info('RFX Sensor {} change, old={} new={}'.format(sensor.sensor_name, key_compare,
                                                                  sensor.comparator_unique_graph_record()))
        sensor.save_to_graph = True
        sensor.notify_transport_enabled = True
        db.session.commit()
    else:
        logging.debug('Ignoring RFX sensor read {}, no value change'.format(key_compare))
        sensor.save_to_graph = False

def get_portpath_linux():
    #/sys/bus/usb/devices/2-1.2/2-1.2:1.0/ttyUSB0/tty/ttyUSB0/dev
    #/sys/bus/usb/devices/2-1.2/product
    logging.info('Searching for RFXCOM devices on linux')
    path_list = glob.glob('/sys/bus/usb/devices/*/*/*/*/tty*/dev')
    for path in path_list:
        words = path.split('/')
        dev_path = '/dev/'+words[len(words)-2]
        root_path = ''
        for index in range(0, len(words) - 5):
            root_path = root_path + '/' + words[index]
        f = open(root_path+'/product')
        product = f.readline()
        f.close()
        if 'RFXtrx433' in product:
            logging.info('Found RFXCOM RFXtrx433 device at {}'.format(dev_path))
            return dev_path
    return None

def init():
    global transport, initialised
    initialised = False
    try:
        if constant.OS in constant.OS_LINUX:
            portpath = get_portpath_linux()
        else:
            #fixme windows autodetect version
            pass
        if portpath:
            logging.info('Initialising RFXCOM on port {}'.format(portpath))
            transport = PySerialTransport(portpath, debug=True)
            transport.reset()
            initialised = True
    except Exception, ex:
        logging.warning('Unable to open RFX tty port, err {}'.format(ex))
    return initialised

def thread_run():
    global transport, initialised
    try:
        logging.info('Waiting for RFX event')
        if initialised:
            __rfx_reading(transport.receive_blocking())
    except Exception, ex:
        logging.warning('Error read RFX tty port, err {}'.format(ex))