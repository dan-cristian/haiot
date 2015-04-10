__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import logging
from RFXtrx.pyserial import PySerialTransport

transport = None
def init():
    global transport
    try:
        port = '/dev/ttyUSB0'
        logging.info('Initialising RFXCOM on port {}'.format(port))
        transport = PySerialTransport(port, debug=True)
        transport.reset()
    except Exception, ex:
        logging.critical('Unable to open RFX tty port, err {}'.format(ex))

def thread_run():
    global transport
    try:
        logging.info('Waiting for RFX event')
        logging.info(transport.receive_blocking())
    except Exception, ex:
        logging.warning('Error read RFX tty port, err {}'.format(ex))