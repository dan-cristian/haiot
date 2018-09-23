__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import time
import serial
import threading
import prctl
from pydispatch import dispatcher
from main.logger_helper import L
from common import Constant, utils, variable
from sensor import serial_common
from main.admin import models
from main import thread_pool
import traceback


class P:
    initialised = False
    serial = None
    ups = None
    interval = 30
    port_pattern = 'ttyUSB'


class LegrandUps:
    def __init__(self):
        pass

    Connected = False
    Id = None
    Name = None
    Port = None
    InputVoltage = None
    RemainingMinutes = None
    OutputVoltage = None
    LoadPercent = None
    PowerFrequency = None
    BatteryVoltage = None
    Temperature = None
    OtherStatus = None


def __open_port(ser):
    ser.baudrate = 2400
    ser.timeout = 3
    ser.writeTimeout = 3
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.bytesize = serial.EIGHTBITS
    try:
        ser.open()
        return True
    except Exception as ex:
        L.l.warning('Unable to open serial port {}'.format(ser.port))
        return False


def __write_read_port(ser, command):
    response = None
    if ser.isOpen():
        try:
            ser.flushInput()
            ser.flushOutput()
            ser.write(command)
            time.sleep(1)
            response = str(ser.readline()).replace('\n', '')
        except Exception as ex:
            L.l.warning('Error writing to serial {}, err={}'.format(ser.port, ex))
    else:
        L.l.warning('Error writing to closed serial {}'.format(ser.port))
    return response


def __search_ups(port_name):
    ser = serial.Serial()
    ser.port = port_name
    __open_port(ser)
    if ser.isOpen():
        # first read returns unknown response, second works
        for i in range(0, 4):
            response = __write_read_port(ser, 'I\r')
            # [#                           JP00106G  #015]
            if response is not None and "JP00106G" in response:
                L.l.info('Found UPS [{}] on port {}'.format(response, port_name))
                P.serial = ser
                P.ups = LegrandUps()
                P.ups.Id = str(response).replace(' ', '').replace('\r', '')
                P.ups.Name = 'Legrand Nicky ' + P.ups.Id
                P.ups.Port = port_name
                break
            else:
                L.l.info('Got unknown response [{}] on ups init port {}'.format(response, port_name))
    if P.serial is None:
        ser.close()


# (219.7 150.0 226.8 011 49.9 56.2 30.0 00001001
def __read_ups_status():
    status = __write_read_port(P.serial, 'Q1\r')
    if status != '':
        status = status.replace('(', '')
        atoms = status.split()
        if len(atoms) >= 8:
            P.ups.InputVoltage = round(utils.round_sensor_value(atoms[0]), 0)
            P.ups.RemainingMinutes = utils.round_sensor_value(atoms[1])
            P.ups.OutputVoltage = round(utils.round_sensor_value(atoms[2]), 0)
            P.ups.LoadPercent = utils.round_sensor_value(atoms[3])
            P.ups.PowerFrequency = atoms[4]
            P.ups.BatteryVoltage = atoms[5]
            P.ups.Temperature = atoms[6]
            P.ups.OtherStatus = atoms[7]
            if len(P.ups.OtherStatus) >= 8:
                P.ups.PowerFailed = (P.ups.OtherStatus[0] == '1')
                P.ups.TestInProgress = (P.ups.OtherStatus[5] == '1')
                P.ups.BeeperOn = (P.ups.OtherStatus[7] == '1')

            record = models.Ups()
            record.name = P.ups.Name
            record.system_name = Constant.HOST_NAME
            record.input_voltage = P.ups.InputVoltage
            record.remaining_minutes = P.ups.RemainingMinutes
            record.battery_voltage = P.ups.BatteryVoltage
            record.beeper_on = P.ups.BeeperOn
            record.load_percent = P.ups.LoadPercent
            record.output_voltage = P.ups.OutputVoltage
            record.power_frequency = P.ups.PowerFrequency
            record.temperature = P.ups.Temperature
            record.other_status = P.ups.OtherStatus
            record.power_failed = P.ups.PowerFailed
            record.updated_on = utils.get_base_location_now_date()
            current_record = models.Ups.query.filter_by(system_name=Constant.HOST_NAME).first()
            record.save_changed_fields(current_record=current_record, new_record=record, notify_transport_enabled=True,
                                       save_to_graph=True)

            L.l.debug('UPS remaining={} load={} input={} output={}'.format(
                P.ups.RemainingMinutes, P.ups.LoadPercent, P.ups.InputVoltage, P.ups.OutputVoltage))
        else:
            L.l.warning('Unexpected number of parameters ({}) on ups status read'.format(len(atoms)))
    else:
        L.l.info('Read empty UPS status')


def _create_dummy_entry():
    name = "dummy UPS"
    record = models.Ups()
    record.name = name
    current_record = models.Ups.query.filter_by(name=name).first()
    if current_record is None:
        record.save_changed_fields(current_record=current_record, new_record=record)
    else:
        record.name = current_record.name
        record.power_failed = 1
        record.save_changed_fields(current_record=current_record, new_record=record, notify_transport_enabled=True,
                                   save_to_graph=True)


def _init_comm():
    P.initialised = False
    try:
        # if constant.OS in constant.OS_LINUX:
        L.l.debug('Looking for UPS serial ports')
        portpath = serial_common.get_portpath_linux(product_name='USB-Serial Controller D')
        if portpath is not None:
            __search_ups(portpath)
            if P.serial is not None:
                variable.USB_PORTS_IN_USE.append(portpath)
                P.initialised = True
        if not P.initialised:
            serial_list = serial_common.get_standard_serial_device_list()
            if len(serial_list) > 0:
                L.l.info('Looking for Legrand UPS on {} serial ports'.format(len(serial_list)))
                for port_name in serial_list:
                    if port_name not in variable.USB_PORTS_IN_USE and P.port_pattern in port_name:
                        __search_ups(port_name)
                        if P.serial is not None:
                            variable.USB_PORTS_IN_USE.append(port_name)
                            P.initialised = True
                            break
                    else:
                        L.l.info("Skip UPS search on port {}".format(port_name))
            else:
                L.l.info('No standard open serial ports detected on this system')
    except Exception as ex:
        L.l.error('Unable to open ups port, err {}'.format(ex), exc_info=True)
    # if not P.initialised:
    #    _create_dummy_entry()
    return P.initialised


def thread_run():
    prctl.set_name("ups_legrand")
    threading.current_thread().name = "ups_legrand"
    if not P.initialised:
        _init_comm()
    if P.initialised and P.serial is not None:
        __read_ups_status()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"


def unload():
    thread_pool.remove_callable(thread_run)
    if P.serial is not None and P.serial.isOpen():
        P.serial.close()
    P.initialised = False


# called once a usb change is detected
def _init_recovery():
    if not P.initialised:
        thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval)


def init():
    thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval)
    dispatcher.connect(_init_recovery, signal=Constant.SIGNAL_USB_DEVICE_CHANGE, sender=dispatcher.Any)
