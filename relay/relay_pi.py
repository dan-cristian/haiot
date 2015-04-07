__author__ = 'dcristian'

import logging

__pins_setup_list = []

def __setup_pin(bcm_id=''):
    try:
        file = open('/sys/class/gpio/export', 'a')
        print >> file, bcm_id
        file.close()
        if not bcm_id in __pins_setup_list:
            __pins_setup_list.append(bcm_id)
        else:
            logging.warning('Trying to add an existing pin {} in setup list'.format(bcm_id))
    except Exception, ex:
        logging.critical('Unexpected error on pin {} setup, err {}'.format(bcm_id, ex))

def __set_pin_dir_out(bcm_id=''):
    try:
        file = open('/sys/class/gpio/gpio{}/direction'.format(bcm_id), 'a')
        print >> file, 'out'
        file.close()
        return True
    except Exception, ex:
        logging.warning('Unexpected exception on pin {} direction OUT set, err {}'.format(bcm_id, ex))
        return False

def __set_pin_dir_in(bcm_id=''):
    try:
        file = open('/sys/class/gpio/gpio{}/direction'.format(bcm_id), 'a')
        print >> file, 'in'
        file.close()
        return True
    except Exception, ex:
        logging.warning('Unexpected exception on pin {} direction IN set, err {}'.format(bcm_id, ex))
        return False

def __unsetup_pin(bcm_id=''):
    try:
        file = open('/sys/class/gpio/unexport', 'a')
        print >> file, bcm_id
        file.close()
        __pins_setup_list.remove(bcm_id)
    except Exception, ex:
        logging.critical('Unexpected error on pin {} un-setup, err {}'.format(bcm_id, ex))

def __is_pin_setup(bcm_id=''):
    try:
        file = open('/sys/class/gpio/gpio{}/value'.format(bcm_id), 'r')
        file.close()
        return True
    except IOError:
        return False
    except Exception, ex:
        logging.warning('Unexpected exception on pin setup check, err {}'.format(ex))
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
        logging.warning('Unexpected exception on pin setup check, err {}'.format(ex))
        return False

def __read_line(bcm_id=''):
    try:
        file = open('/sys/class/gpio/gpio{}/value'.format(bcm_id), 'r')
        value = file.readline()
        return value
    except Exception, ex:
        logging.critical('Unexpected general exception on pin {} value read, err {}'.format(bcm_id, ex))
        return None

def __write_line(bcm_id='', pin_value=''):
    try:
        file = open('/sys/class/gpio/gpio{}/value'.format(bcm_id), 'a')
        print >> file, pin_value
        file.close()
    except Exception, ex:
        logging.critical('Unexpected general exception on pin {} write, err {}'.format(bcm_id, ex))
        return None

def get_pin_bcm(bcm_id=''):
    '''BCM pin id format. Return value is 0 or 1.'''
    if not __is_pin_setup(bcm_id):
        __set_pin_dir_in(bcm_id)
    if __is_pin_setup(bcm_id):
        return __read_line(bcm_id)
    else:
        logging.critical('Unable to get pin bcm {}'.format(bcm_id))


def set_pin_bcm(bcm_id='', pin_value=''):
    '''BCM pin id format. Value is 0 or 1. Return value is 0 or 1, confirms pin state'''
    if not __is_pin_setup_out(bcm_id):
        __set_pin_dir_out(bcm_id)
    if __is_pin_setup_out(bcm_id):
        __write_line(bcm_id, pin_value)
        return get_pin_bcm(bcm_id)
    else:
        logging.critical('Unable to write pin bcm {}'.format(bcm_id))
        return -1

def unload():
    global __pins_setup_list
    for bcm_pin in __pins_setup_list:
        __unsetup_pin(bcm_pin=bcm_pin)

def init():
    pass
