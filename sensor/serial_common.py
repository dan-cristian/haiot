__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

from main import logger
import glob
import serial

def get_portpath_linux(product_name):
    #/sys/bus/usb/devices/2-1.2/2-1.2:1.0/ttyUSB0/tty/ttyUSB0/dev
    #/sys/bus/usb/devices/2-1.2/product
    logger.info('Searching for {} devices on linux'.format(product_name))
    path_list = glob.glob('/sys/bus/usb/devices/*/*/*/*/tty*/dev')
    for path in path_list:
        words = path.split('/')
        dev_path = '/dev/'+words[len(words)-2]
        root_path = ''
        for index in range(0, len(words) - 5):
            root_path = root_path + '/' + words[index]
        f = open(root_path + '/product')
        product = f.readline()
        f.close()
        if product_name in product:
            logger.info('Found {} device at {}'.format(product_name, dev_path))
            return dev_path
    return None

def get_standard_serial_device_list():
    valid_list = []
    ser = serial.Serial()
    ser.baudrate = 9600
    ser.timeout = 3
    ser.writeTimeout = 3
    for port_no in range(0,5):
        ser.port = port_no
        try:
            ser.open()
            ser.close()
            logger.info('Found and opened serial port {}'.format(port_no))
            valid_list.append(port_no)
        except Exception, ex:
            pass
    return valid_list