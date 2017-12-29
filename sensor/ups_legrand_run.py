__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import time
import serial
from main.logger_helper import Log
from common import Constant, utils
import serial_common
from main.admin import models

initialised = False
__serial = None
__ups = None


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
    except Exception, ex:
        Log.logger.warning('Unable to open serial port {}'.format(ser.port))
        return False


def __write_read_port(ser, command):
    response = None
    if ser.isOpen():
        try:
            ser.flushInput()
            ser.flushOutput()
            ser.write(command)
            time.sleep(0.3)
            response = str(ser.readline()).replace('\n', '')
        except Exception, ex:
            Log.logger.warning('Error writing to serial {}, err={}'.format(ser.port, ex))
    else:
        Log.logger.warning('Error writing to closed serial {}'.format(ser.port))
    return response


def __search_ups(port_name):
    global __serial, __ups
    ser = serial.Serial()
    ser.port = port_name
    __open_port(ser)
    if ser.isOpen():
        # first read returns unknown response, second works
        for i in range(0, 2):
            response = __write_read_port(ser, 'I\r')
            # [#                           JP00106G  #015]
            if "JP00106G" in response:
                Log.logger.info('Got serial response [{}] on ups init port {}'.format(response, port_name))
                __serial = ser
                __ups = LegrandUps()
                __ups.Id = str(response).replace(' ', '').replace('\r', '')
                __ups.Name = 'Legrand Nicky ' + __ups.Id
                __ups.Port = port_name
                break
            else:
                Log.logger.info('Got unknown response [{}][{}] on ups init port {}'.format(
                    response, len(response), port_name))
    if __serial is None:
        ser.close()


# (219.7 150.0 226.8 011 49.9 56.2 30.0 00001001
def __read_ups_status():
    global __ups, __serial
    status = __write_read_port(__serial, 'Q1\r')
    if status != '':
        status = status.replace('(', '')
        atoms = status.split()
        if len(atoms) >= 8:
            __ups.InputVoltage = utils.round_sensor_value(atoms[0])
            __ups.RemainingMinutes = utils.round_sensor_value(atoms[1])
            __ups.OutputVoltage = atoms[2]
            __ups.LoadPercent = utils.round_sensor_value(atoms[3])
            __ups.PowerFrequency = atoms[4]
            __ups.BatteryVoltage = atoms[5]
            __ups.Temperature = atoms[6]
            __ups.OtherStatus = atoms[7]
            if len(__ups.OtherStatus) >= 8:
                __ups.PowerFailed = (__ups.OtherStatus[0] == '1')
                __ups.TestInProgress = (__ups.OtherStatus[5] == '1')
                __ups.BeeperOn = (__ups.OtherStatus[7] == '1')

            record = models.Ups()
            record.name = __ups.Name
            record.system_name = Constant.HOST_NAME
            record.input_voltage = __ups.InputVoltage
            record.remaining_minutes = __ups.RemainingMinutes
            record.battery_voltage = __ups.BatteryVoltage
            record.beeper_on = __ups.BeeperOn
            record.load_percent = __ups.LoadPercent
            record.output_voltage = __ups.OutputVoltage
            record.power_frequency = __ups.PowerFrequency
            record.temperature = __ups.Temperature
            record.other_status = __ups.OtherStatus
            record.power_failed = __ups.PowerFailed
            record.updated_on = utils.get_base_location_now_date()
            current_record = models.Ups.query.filter_by(system_name=Constant.HOST_NAME).first()
            record.save_changed_fields(current_record=current_record, new_record=record, notify_transport_enabled=True,
                                       save_to_graph=True)

            Log.logger.debug('UPS remaining={} load={} input={} output={}'.format(
                __ups.RemainingMinutes, __ups.LoadPercent, __ups.InputVoltage, __ups.OutputVoltage))
        else:
            Log.logger.warning('Unexpected number of parameters ({}) on ups status read'.format(len(atoms)))
    else:
        Log.logger.info('Read empty UPS status')


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


def unload():
    global initialised
    if __serial is not None and __serial.isOpen():
        __serial.close()
    initialised = False


def init():
    global initialised, __serial
    initialised = False
    try:
        # if constant.OS in constant.OS_LINUX:
        Log.logger.info('Looking for serial ports')
        serial_list = serial_common.get_standard_serial_device_list()
        # else:
        #    portpath = None
        #    #fixme windows autodetect version
        if len(serial_list) > 0:
            Log.logger.info('Looking for Legrand UPS on {} serial ports'.format(len(serial_list)))
            for device in serial_list:
                __search_ups(device)
                if __serial is not None:
                    break
            initialised = True
        else:
            Log.logger.info('No standard open serial ports detected on this system')
    except Exception, ex:
        Log.logger.warning('Unable to open ups port, err {}'.format(ex))
    if not initialised:
        _create_dummy_entry()
    return initialised


def thread_run():
    global initialised, __serial
    if not initialised:
        init()

    if initialised and __serial is not None:
        __read_ups_status()
