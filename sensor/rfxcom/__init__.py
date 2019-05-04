__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

from pydispatch import dispatcher
from main.logger_helper import L
# from sensor.rfxcom.RFXtrx import PySerialTransport
# L.l.error("Unable to import package, err={}".format(ex), exc_info=True)
from common import Constant, utils, variable
import threading
import prctl
from main import thread_pool, sqlitedb
if sqlitedb:
    from storage.sqalc import models
from sensor import serial_common
from sensor.rfxcom import RFXtrx
from sensor.rfxcom.RFXtrx import PySerialTransport
from storage.model import m


class P:
    initialised = False
    transport = None
    last_packet_received = None
    INTERVAL_NORMAL = 1
    INTERVAL_ERROR = 120
    interval = INTERVAL_NORMAL
    MAX_MINUTES_SILENCE = 10
    init_failed_count = 0
    MAX_FAILED_RETRY = 10
    thread_pool_status = None


# 0x0a 0x52 0x01 0x00 0xcc 0x01 0x00 0x09 0x27 0x02 0x59
# type='THGN122/123, THGN132, THGR122/228/238/268' id='cc:01'] values=[
# ('Battery numeric', 9), ('Humidity', 39), ('Humidity status', 'normal'), ('Humidity status numeric', 2),
# ('Rssi numeric', 5), ('Temperature', 0.9)
#
# 0x0a 0x52 0x01 0x01 0xcc 0x01 0x00 0x0a 0x27 0x02 0x59
# type='THGN122/123, THGN132, THGR122/228/238/268' id='cc:01'] values=[
# ('Battery numeric', 9), ('Humidity', 39), ('Humidity status', 'normal'), ('Humidity status numeric', 2),
# ('Rssi numeric', 5), ('Temperature', 1.0)
def __rfx_reading(packet):
    if packet:
        try:
            L.l.info("Received RFX packet={}".format(packet))
            if isinstance(packet, RFXtrx.SensorEvent):
                __save_sensor_db(p_id=packet.device.id_string, p_type=packet.device.type_string,
                                 value_list=packet.values)
                P.last_packet_received = utils.get_base_location_now_date()
            elif isinstance(packet, RFXtrx.LightingDevice):
                __save_relay_db(p_id=packet.device.id_string, p_type=packet.device.type_string,
                                value_list=packet.values)
        except Exception as ex:
            L.l.info('Unknown rfx packet type {} err={}'.format(packet, ex))


def __save_relay_db(p_id='', p_type='', value_list=None):
    # todo: add save to relay db
    pass


def __save_sensor_db(p_id='', p_type='', value_list=None):
    if not value_list:
        value_list = []

    record = m.Sensor.find_one({m.Sensor.address: p_id})
    if record is None:
        record = m.Sensor()
        record.address = p_id
    zone_sensor = m.ZoneSensor.find_one({m.Sensor.address: p_id})
    if zone_sensor:
        record.sensor_name = zone_sensor.sensor_name
    else:
        record.sensor_name = '(not defined) ' + p_id
    record.updated_on = utils.get_base_location_now_date()
    record.type = p_type
    if 'Humidity' in value_list:
        record.humidity = utils.round_sensor_value(value_list['Humidity'])
    if 'Temperature' in value_list:
        record.temperature = utils.round_sensor_value(value_list['Temperature'])
    if 'Battery numeric' in value_list:
        record.battery_level = value_list['Battery numeric']
    if 'Rssi numeric' in value_list:
        record.rssi = value_list['Rssi numeric']
    record.save_changed_fields(broadcast=True, persist=True)


# ON COMMAND
#Packettype    = Lighting4
#subtype       = PT2262
#Sequence nbr  = 20
#Code          = 451451 decimal:4527185
#S1- S24  = 0100 0101 0001 0100 0101 0001
#Pulse         = 325 usec
#Signal level  = 6  -72dBm


# OFF COMMAND
# Code          = 451454 decimal:4527188

# CLOSE COMMAND
#Code          = 45155F decimal:4527455
#S1- S24  = 0100 0101 0001 0101 0101 1111

def elro_relay_on():
    pkt = None
    pkt.packettype = RFXtrx.lowlevel.Lighting4
    pkt.subtype = 'PT2262'
    pkt.cmd = 451451
    #pkt.type_string = 1
    #pkt.id_string = 1
    #event = RFXtrx.LightingDevice()
    event = RFXtrx.lowlevel.Lighting4()
    event.set_transmit()


# https://github.com/Danielhiversen/pyRFXtrx/
def _init_board():
    P.initialised = False
    P.last_packet_received = utils.get_base_location_now_date()
    try:
        if Constant.OS in Constant.OS_LINUX:
            portpath = serial_common.get_portpath_linux(product_name='RFXtrx433')
        else:
            portpath = None
            # fixme windows autodetect version
        if portpath:
            L.l.info('Initialising RFXCOM on port {}'.format(portpath))
            P.transport = PySerialTransport(portpath, debug=True)
            P.transport.reset()
            P.initialised = True
            variable.USB_PORTS_IN_USE.append(portpath)
        else:
            L.l.info('No RFX device detected on this system')
    except Exception as ex:
        L.l.warning('Unable to open RFX tty port, err={}'.format(ex))
    if not P.initialised:
        P.init_failed_count += 1
    return P.initialised


def thread_run():
    prctl.set_name("rfxcom")
    threading.current_thread().name = "rfxcom"
    try:
        if not P.initialised:
            _init_board()
        if P.initialised:
            L.l.debug('Waiting for RFX event')
            time_elapsed_minutes = (utils.get_base_location_now_date() - P.last_packet_received).seconds / 60
            if time_elapsed_minutes > P.MAX_MINUTES_SILENCE:
                L.l.warning('RFX event not received since {} mins, device err? Reseting!'.format(time_elapsed_minutes))
                P.transport.reset()
            event = P.transport.receive_blocking()
            __rfx_reading(event)
        else:
            if P.init_failed_count > P.MAX_FAILED_RETRY:
                unload()
    except IndexError as iex:
        P.initialised = False
        P.init_failed_count += 1
        utils.sleep(10)
    except Exception as ex:
        L.l.error('Error read RFX tty port, err={}'.format(ex), exc_info=True)
        P.initialised = False
        P.init_failed_count += 1
        utils.sleep(10)
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def get_progress():
    return P.thread_pool_status


def unload():
    L.l.info('Unloading RFXCom')
    thread_pool.remove_callable(thread_run)
    if P.initialised:
        P.transport.close()
    P.initialised = False
    dispatcher.disconnect(_init_recovery, signal=Constant.SIGNAL_USB_DEVICE_CHANGE)
    thread_pool.remove_callable(thread_run)


# called once a usb change is detected
def _init_recovery():
    if not P.initialised:
        thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval)


def init():
    thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval, long_running=True)
    dispatcher.connect(_init_recovery, signal=Constant.SIGNAL_USB_DEVICE_CHANGE, sender=dispatcher.Any)
