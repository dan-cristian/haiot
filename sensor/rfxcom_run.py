__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import logging
from RFXtrx.pyserial import PySerialTransport

transport = None
def init():
    global transport
    try:
        transport = PySerialTransport('/dev/ttyUSB0', debug=True)
        transport.reset()
    except Exception, ex:
        logging.critical('Unable to open RFX tty port, err {}'.format(ex))

def thread_run():
    global transport
    try:
        print(transport.receive_blocking())
    except Exception, ex:
        logging.warning('Error read RFX tty port, err {}'.format(ex))