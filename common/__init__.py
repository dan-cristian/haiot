__author__ = 'dcristian'
import os
import logging
import socket
import constant

def init():
    constant.OS = os.name
    constant.HOST_NAME = socket.gethostname()
    logging.info('Running on OS {} HOST {}'.format(constant.OS, constant.HOST_NAME))
