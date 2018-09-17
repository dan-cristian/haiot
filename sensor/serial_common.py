__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import sys
import glob
import serial
import os
from main.logger_helper import L


class P:
    PORT_EXCLUSION = ['/dev/ttyprintk']


def get_portpath_linux(product_name):
    # /sys/bus/usb/devices/2-1.2/2-1.2:1.0/ttyUSB0/tty/ttyUSB0/dev
    # /sys/bus/usb/devices/2-1.2/product
    L.l.info('Searching for {} devices on linux'.format(product_name))
    path_list = glob.glob('/sys/bus/usb/devices/*/*/*/*/tty*/dev')
    for path in path_list:
        words = path.split('/')
        dev_path = '/dev/' + words[len(words) - 2]
        root_path = ''
        for index in range(0, len(words) - 5):
            root_path = root_path + '/' + words[index]
        file_product = root_path + '/product'
        if os.path.isfile(file_product):
            f = open(file_product)
            product = f.readline()
            f.close()
            if product_name in product:
                L.l.info('Found {} device at {}'.format(product_name, dev_path))
                return dev_path
    return None


# does not work anymore
def get_standard_serial_device_list_old():
    valid_list = []
    ser = serial.Serial()
    ser.baudrate = 9600
    ser.timeout = 3
    ser.writeTimeout = 3
    for port_no in range(0, 5):
        try:
            L.l.info('Trying to open serial port {}'.format(port_no))
            ser.port = port_no
            ser.open()
            ser.close()
            L.l.info('Found and opened serial port {}'.format(port_no))
            valid_list.append(port_no)
        except Exception as ex:
            L.l.info('Cannot open serial port, ex='.format(ex))
    return valid_list


# https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
def get_standard_serial_device_list():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        L.l.error('Unsupported platform for serial detection, {}'.format(sys.platform))
        return None

    L.l.info("Found {} serial ports".format(len(ports)))
    result = []
    for port in ports:
        try:
            s = serial.Serial()
            s.baudrate = 9600
            s.timeout = 3
            s.writeTimeout = 3
            s.port = port
            s.open()
            s.close()
            L.l.debug('Found and opened serial port {}'.format(port))
            result.append(port)
        except Exception as ex:
            L.l.info('Cannot open serial port {}, ex='.format(port, ex))
    return result
