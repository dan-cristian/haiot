__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import serial
import time
from main import logger
from main.admin import models
from common import constant, utils
import serial_common


initialised = False
__serial = None

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

def __search_ups(port_no):
    ser = serial.Serial()
    ser.port = port_no
    __open_port(ser)
    if ser.isOpen():
        try:
            ser.flushInput()
            ser.flushOutput()
            for i in range(0, 3):
                ser.write('I')
                time.sleep(0.5)
                response = ser.readline()
                if response != '':
                    logger.info('Got serial response [{}] on ups init port {}'.format(response, port_no))
                    break;
                else:
                    logger.info('Got empty response on ups init port {}'.format(port_no))
        except Exception, ex:
            logger.warning('Unable to init ups legrand on serial port {}, err={}'.format(ser.port, ex))
        finally:
            ser.close()



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
                    break;
            initialised = True
        else:
            logger.info('No standard open serial ports detected on this system')
    except Exception, ex:
        logger.warning('Unable to open ups port, err {}'.format(ex))
    return initialised

def thread_run():
    global initialised

    if initialised:
        pass
