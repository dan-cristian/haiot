__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import sys
import glob
import os
try:
    from main.logger_helper import L
except ImportError as ie:
    class L:
        class l:
            @staticmethod
            def info(msg): print(msg)
            @staticmethod
            def warning(msg): print(msg)
            @staticmethod
            def error(msg): print(msg)

from common import fix_module
while True:
    try:
        import serial
        break
    except ImportError as iex:
        if not fix_module(iex):
            break


class P:
    PORT_EXCLUSION = ['/dev/ttyprintk']

    def __init__(self):
        pass


def get_portpath_linux(product_name=None, manufacturer_name=None):
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
        file_manufacturer = root_path + '/manufacturer'
        search_list = [file_product, file_manufacturer]
        search_values = [product_name, manufacturer_name]
        for i in [0, 1]:
            if os.path.isfile(search_list[i]):
                f = open(search_list[i])
                val = f.readline()
                f.close()
                if search_values[i] is not None and search_values[i] in val:
                    L.l.info('Found {} device at {}'.format(search_values[i], dev_path))
                    return dev_path
    return None


# https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
def get_standard_serial_device_list():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(24)]
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
        if port not in P.PORT_EXCLUSION:
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
