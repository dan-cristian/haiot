__author__ = 'dcristian'
import os
import socket
import constant
from uuid import getnode as get_mac

def init():
    from main import logger
    try:
        mac = get_mac()
        #call it twice as get_mac might fake mac: http://stackoverflow.com/questions/159137/getting-mac-address
        if mac == get_mac():
            constant.HOST_MAC = ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))
        else:
            logger.warning('Cannot get mac address')
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("gmail.com",80))
        constant.HOST_MAIN_IP = s.getsockname()[0]
        s.close()
    except Exception, ex:
        logger.warning('Cannot obtain main IP accurately, probably not connected to Internet, ex={}'.format(ex))
        constant.HOST_MAIN_IP=socket.gethostbyname(socket.gethostname())
    logger.info('Running on OS {} HOST {} IP {}'.format(constant.OS, constant.HOST_NAME, constant.HOST_MAIN_IP))

def init_simple():
    constant.OS = os.name
    constant.HOST_NAME = socket.gethostname()
