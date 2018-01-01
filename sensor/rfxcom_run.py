__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

from main.logger_helper import L
from RFXtrx.pyserial import PySerialTransport
import RFXtrx
from main.admin import models
from common import Constant, utils
import serial_common

initialised = False
transport = None
last_packet_received = None


def __rfx_reading(packet):
    if packet:
        try:
            assert isinstance(packet, RFXtrx.SensorEvent)
            p_id = packet.device.id_string
            p_type = packet.device.type_string
            __save_sensor_db(p_id=p_id, p_type=p_type, value_list=packet.values)
            global last_packet_received
            last_packet_received = utils.get_base_location_now_date()
        except Exception, ex:
            L.l.info('Unknown rfx packet type {} err={}'.format(packet, ex))


def __save_sensor_db(p_id='', p_type='', value_list=None):
    if not value_list:
        value_list = []
    record = models.Sensor(address=p_id)
    assert isinstance(record, models.Sensor)
    zone_sensor = models.ZoneSensor.query.filter_by(sensor_address=p_id).first()
    if zone_sensor:
        record.sensor_name = zone_sensor.sensor_name
    else:
        record.sensor_name = '(not defined) ' + p_id
    record.updated_on = utils.get_base_location_now_date()
    record.type = p_type
    if 'Humidity' in value_list: record.humidity = utils.round_sensor_value(value_list['Humidity'])
    if 'Temperature' in value_list: record.temperature = utils.round_sensor_value(value_list['Temperature'])
    if 'Battery numeric' in value_list: record.battery_level = value_list['Battery numeric']
    if 'Rssi numeric' in value_list: record.rssi = value_list['Rssi numeric']
    current_record = models.Sensor.query.filter_by(address=p_id).first()
    record.save_changed_fields(current_record=current_record, new_record=record, notify_transport_enabled=True,
                               save_to_graph=True, ignore_only_updated_on_change=True)


def unload():
    pass


def init():
    global transport, initialised, last_packet_received
    initialised = False
    last_packet_received = utils.get_base_location_now_date()
    try:
        if Constant.OS in Constant.OS_LINUX:
            portpath = serial_common.get_portpath_linux('RFXtrx433')
        else:
            portpath = None
            # fixme windows autodetect version
        if portpath:
            L.l.info('Initialising RFXCOM on port {}'.format(portpath))
            transport = PySerialTransport(portpath, debug=True)
            transport.reset()
            initialised = True
        else:
            L.l.info('No RFX device detected on this system')
    except Exception, ex:
        L.l.warning('Unable to open RFX tty port, err {}'.format(ex))
    return initialised


def thread_run():
    global transport, initialised, last_packet_received
    try:
        L.l.debug('Waiting for RFX event')
        time_elapsed_minutes = (utils.get_base_location_now_date() - last_packet_received).seconds / 60
        if time_elapsed_minutes > 10:
            L.l.warning('RFX event not received since {} minutes, device error?'.format(time_elapsed_minutes))
        if initialised:
            __rfx_reading(transport.receive_blocking())
    except Exception, ex:
        L.l.warning('Error read RFX tty port, err {}'.format(ex))
