__author__ = 'dcristian'

import subprocess
import os
from main import logger
from common import constant

__pins_setup_list = []

def __write_to_file_as_root(file, value):
    try:
        if constant.OS in constant.OS_LINUX :
            res = os.system('echo {} | sudo tee --append  {}'.format(str(value), file))
            if res==0:
                return True
            else:
                logger.warning('Error writing value {} to file {} result={}'.format(value, file, res))
    except Exception, ex:
        logger.warning('Exception writing value {} to file {} err='.format(value, file, ex))

def __setup_pin(bcm_id=''):
    try:
        #file = open('/sys/class/gpio/export', 'a')
        #print >> file, bcm_id
        #file.close()
        if __write_to_file_as_root('/sys/class/gpio/export', bcm_id):
            logger.info('Pin {} exported OK'.format(bcm_id))
        if not bcm_id in __pins_setup_list:
            __pins_setup_list.append(bcm_id)
        else:
            logger.warning('Trying to add an existing pin {} in setup list'.format(bcm_id))
    except Exception, ex:
        logger.critical('Unexpected error on pin {} setup, err {}'.format(bcm_id, ex))

def __set_pin_dir_out(bcm_id=''):
    try:
        #file = open('/sys/class/gpio/gpio{}/direction'.format(bcm_id), 'a')
        #print >> file, 'out'
        #file.close()
        __setup_pin(bcm_id)
        if __write_to_file_as_root(file='/sys/class/gpio/gpio{}/direction'.format(bcm_id), value='out'):
            logger.info('Pin {} direction out OK'.format(bcm_id))
        return True
    except Exception, ex:
        logger.warning('Unexpected exception on pin {} direction OUT set, err {}'.format(bcm_id, ex))
        return False

def __set_pin_dir_in(bcm_id=''):
    try:
        #file = open('/sys/class/gpio/gpio{}/direction'.format(bcm_id), 'a')
        #print >> file, 'in'
        #file.close()
        __setup_pin(bcm_id)
        if __write_to_file_as_root(file='/sys/class/gpio/gpio{}/direction'.format(bcm_id), value='in'):
            logger.info('Pin {} direction in OK'.format(bcm_id))
        return True
    except Exception, ex:
        logger.warning('Unexpected exception on pin {} direction IN set, err {}'.format(bcm_id, ex))
        return False

def __unsetup_pin(bcm_id=''):
    try:
        #file = open('/sys/class/gpio/unexport', 'a')
        #print >> file, bcm_id
        #file.close()
        if __write_to_file_as_root('/sys/class/gpio/unexport', bcm_id):
            logger.info('Pin {} unexport OK'.format(bcm_id))
        __pins_setup_list.remove(bcm_id)
    except Exception, ex:
        logger.critical('Unexpected error on pin {} un-setup, err {}'.format(bcm_id, ex))

def __is_pin_setup(bcm_id=''):
    try:
        file = open('/sys/class/gpio/gpio{}/value'.format(bcm_id), 'r')
        file.close()
        return True
    except IOError:
        return False
    except Exception, ex:
        logger.warning('Unexpected exception on pin setup check, err {}'.format(ex))
        return False

def __is_pin_setup_out(bcm_id=''):
    try:
        file = open('/sys/class/gpio/gpio{}/direction'.format(bcm_id), 'r')
        dir = file.readline()
        file.close()
        return dir.replace('\n','') == 'out'
    except IOError:
        return False
    except Exception, ex:
        logger.warning('Unexpected exception on pin setup check, err {}'.format(ex))
        return False

def __read_line(bcm_id=''):
    try:
        file = open('/sys/class/gpio/gpio{}/value'.format(bcm_id), 'r')
        value = file.readline()
        return value
    except Exception, ex:
        logger.critical('Unexpected general exception on pin {} value read, err {}'.format(bcm_id, ex))
        return None

def __write_line(bcm_id='', pin_value=''):
    try:
        file = open('/sys/class/gpio/gpio{}/value'.format(bcm_id), 'a')
        print >> file, pin_value
        file.close()
        __write_to_file_as_root(file='/sys/class/gpio/gpio{}/value'.format(bcm_id), value=pin_value)

    except Exception, ex:
        logger.critical('Unexpected general exception on pin {} write, err {}'.format(bcm_id, ex))
        return None

def get_pin_bcm(bcm_id=''):
    '''BCM pin id format. Return value is 0 or 1.'''
    if not __is_pin_setup(bcm_id):
        __set_pin_dir_in(bcm_id)
    if __is_pin_setup(bcm_id):
        return __read_line(bcm_id)
    else:
        logger.critical('Unable to get pin bcm {}'.format(bcm_id))


def set_pin_bcm(bcm_id='', pin_value=''):
    '''BCM pin id format. Value is 0 or 1. Return value is 0 or 1, confirms pin state'''
    if not __is_pin_setup_out(bcm_id):
        __set_pin_dir_out(bcm_id)
    if __is_pin_setup_out(bcm_id):
        __write_line(bcm_id, pin_value)
        return get_pin_bcm(bcm_id)
    else:
        logger.critical('Unable to write pin bcm {}'.format(bcm_id))
        return -1

def unload():
    global __pins_setup_list
    for bcm_pin in __pins_setup_list:
        __unsetup_pin(bcm_pin=bcm_pin)

def init():
    pass
