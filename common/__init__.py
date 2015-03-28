__author__ = 'dcristian'
import os
import logging
import socket
import constant

def init():
    constant.OS = os.name
    constant.HOST_NAME = socket.gethostname()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("gmail.com",80))
        constant.HOST_MAIN_IP = s.getsockname()[0]
        s.close()
    except Exception, ex:
        logging.warning('Cannot obtain main IP accurately, probably not connected to Internet, ex={}'.format(ex))
        constant.HOST_MAIN_IP=socket.gethostbyname(socket.gethostname())

    logging.info('Running on OS {} HOST {} IP {}'.format(constant.OS, constant.HOST_NAME, constant.HOST_MAIN_IP))
