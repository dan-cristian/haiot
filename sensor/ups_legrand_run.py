__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import serial
import time
from main import logger
from main.admin import models
from common import constant, utils
import serial_common
from main.admin import models

initialised = False
__serial = None
__ups = None

class LegrandUps():
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
    OtherStatus= None

def __open_port(ser):
    ser.baudrate = 2400
    ser.timeout = 3
    ser.writeTimeout = 3
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.bytesize = serial.EIGHTBITS
    try:
        ser.open()
    except Exception, ex:
        logger.warning('Unable to open serial port {}'.format(ser.port))

def __write_read_port(ser, command):
    response = None
    if ser.isOpen():
        try:
            ser.flushInput()
            ser.flushOutput()
            ser.write(command)
            time.sleep(0.3)
            response = str(ser.readline()).replace('\n','')
        except Exception, ex:
            logger.warning('Error writing to serial {}, err={}'.format(ser.port, ex))
    else:
        logger.warning('Error writing to closed serial {}'.format(ser.port))
    return response

def __search_ups(port_no):
    global __serial, __ups
    ser = serial.Serial()
    ser.port = port_no
    __open_port(ser)
    if ser.isOpen():
        for i in range(0, 4):
            response = __write_read_port(ser, 'I\r')
            if response != '':
                logger.info('Got serial response [{}] on ups init port {}'.format(response, port_no))
                __serial = ser
                __ups = LegrandUps()
                __ups.Id = str(response).replace(' ', '')
                __ups.Name = 'Legrand Nicky ' + __ups.Id
                __ups.Port = port_no
                break
            else:
                logger.info('Got empty response on ups init port {}'.format(port_no))
    if __serial is None:
        ser.close()

#(219.7 150.0 226.8 011 49.9 56.2 30.0 00001001
def __read_ups_status():
    global __ups, __serial
    status = __write_read_port(__serial, 'Q1\r')
    if status != '':
        status = status.replace('(','')
        atoms = status.split()
        if len(atoms) >= 8:
            __ups.InputVoltage = utils.round_sensor_value(atoms[0])
            __ups.RemainingMinutes = utils.round_sensor_value(atoms[1])
            __ups.OutputVoltage = atoms[2]
            __ups.LoadPercent = int(utils.round_sensor_value(atoms[3]))
            __ups.PowerFrequency = atoms[4]
            __ups.BatteryVoltage = atoms[5]
            __ups.Temperature = atoms[6]
            __ups.OtherStatus= atoms[7]
            if len(__ups.OtherStatus) >= 8:
                __ups.PowerFailed = (__ups.OtherStatus[0] == '1')
                __ups.TestInProgress = (__ups.OtherStatus[5] == '1')
                __ups.BeeperOn = (__ups.OtherStatus[7] == '1')

            record = models.Ups()
            record.name = __ups.Name
            record.system_name = constant.HOST_NAME
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
            current_record = models.Ups.query.filter_by(system_name=constant.HOST_NAME).first()
            record.save_changed_fields(current_record=current_record, new_record=record, notify_transport_enabled=True,
                                   save_to_graph=True)

            #logger.info('UPS remaining={} load={}'.format(__ups.RemainingMinutes, __ups.LoadPercent))
        else:
            logger.warning('Unexpected number of parameters {} on ups status read'.format(len(atoms)))
    else:
        logger.info('Read empty UPS status')

def unload():
    global initialised
    if __serial is not None and __serial.isOpen():
        __serial.close()
    initialised = False

def init():
    global initialised, __serial
    initialised = False
    try:
        #if constant.OS in constant.OS_LINUX:
        serial_list = serial_common.get_standard_serial_device_list()
        #else:
        #    portpath = None
        #    #fixme windows autodetect version
        if len(serial_list) > 0:
            logger.info('Looking for Legrand UPS on {} serial ports'.format(len(serial_list)))
            for device in serial_list:
                __search_ups(device)
                if __serial is not None:
                    break
            initialised = True
        else:
            logger.info('No standard open serial ports detected on this system')
    except Exception, ex:
        logger.warning('Unable to open ups port, err {}'.format(ex))
    return initialised

def thread_run():
    global initialised, __serial
    if initialised and __serial is not None:
        __read_ups_status()
