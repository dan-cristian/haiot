__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import logging
import glob
import datetime
from RFXtrx.pyserial import PySerialTransport
import RFXtrx
from main.admin import models, db
from common import constant, utils

initialised = False
transport = None
last_packet_received=datetime.datetime.now()

def __rfx_reading(packet):
    if packet:
        try:
            assert isinstance(packet, RFXtrx.SensorEvent)
            id = packet.device.id_string
            type = packet.device.type_string
            __save_sensor_db(id=id, type=type, value_list=packet.values)
            global last_packet_received
            last_packet_received = datetime.datetime.now()
        except Exception:
            logging.info('Unknown rfx packet type {}'.format(packet))

def __save_sensor_db(id='', type='', value_list=[]):
    record = models.Sensor(address=id)
    assert isinstance(record, models.Sensor)
    zone_sensor = models.ZoneSensor.query.filter_by(sensor_address=id).first()
    if zone_sensor:
        record.sensor_name = zone_sensor.sensor_name
    else:
        record.sensor_name = '(not defined) ' + id
    record.updated_on = datetime.datetime.now()
    record.type = type
    if 'Humidity' in value_list: record.humidity = utils.round_sensor_value(value_list['Humidity'])
    if 'Temperature' in value_list: record.temperature= utils.round_sensor_value(value_list['Temperature'])
    if 'Battery numeric' in value_list: record.battery_level = value_list['Battery numeric']
    if 'Rssi numeric' in value_list: record.rssi = value_list['Rssi numeric']
    current_record = models.Sensor.query.filter_by(address=id).first()
    record.save_changed_fields(current_record=current_record, new_record=record, notify_transport_enabled=True,
                                   save_to_graph=True, ignore_only_updated_on_change=True)

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

def unload():
    pass

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
    global transport, initialised, last_packet_received
    try:
        logging.debug('Waiting for RFX event')
        time_elapsed_minutes = (datetime.datetime.now()-last_packet_received).microseconds / 60
        if time_elapsed_minutes > 10:
            logging.warning('RFX event not received since {} minutes, device error?'.format(time_elapsed_minutes))
        if initialised:
            __rfx_reading(transport.receive_blocking())
    except Exception, ex:
        logging.warning('Error read RFX tty port, err {}'.format(ex))