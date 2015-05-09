__author__ = 'dcristian'

import subprocess
import os
from main import logger, db
from common import constant
from main.admin import models

__pins_setup_list = []

def __get_gpio_db_pin(bcm_id=None):
    gpio_pin = models.GpioPin.query.filter_by(pin_index = bcm_id, host_name = constant.HOST_NAME).first()
    return gpio_pin

def __write_to_file_as_root(file, value):
    try:
        if constant.OS in constant.OS_LINUX :
            res = os.system('echo {} | sudo tee --append  {}'.format(str(value), file))
            if res == 0:
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
            gpio_pin = __get_gpio_db_pin(bcm_id)
            if gpio_pin:
                gpio_pin.is_active = True
            else:
                logger.warning('Unable to find gpio pin with bcmid={} to mark as active'.format(bcm_id))
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
            gpio_pin = __get_gpio_db_pin(bcm_id)
            if gpio_pin:
                gpio_pin.pin_direction = 'out'
                db.session.commit()
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
            gpio_pin = __get_gpio_db_pin(bcm_id)
            if gpio_pin:
                gpio_pin.pin_direction = 'in'
                db.session.commit()
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
        gpio_pin = models.GpioPin.query.filter_by(pin_index = bcm_id, host_name = constant.HOST_NAME).first()
        if gpio_pin:
            gpio_pin.is_active = False
        else:
            logger.warning('Unable to find gpio pin with bcmid={} to mark as inactive'.format(bcm_id))
    except Exception, ex:
        logger.critical('Unexpected error on pin {} un-setup, err {}'.format(bcm_id, ex))

def __is_pin_setup(bcm_id=''):
    try:
        file = open('/sys/class/gpio/gpio{}/value'.format(bcm_id), 'r')
        file.close()
        gpio_pin = models.GpioPin.query.filter_by(pin_index = bcm_id, host_name = constant.HOST_NAME).first()
        if gpio_pin and not gpio_pin.is_active:
            logger.warning('Gpio pin={} is used not via me, conflict with ext. apps or unclean stop?'.format(bcm_id))
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
        value = file.readline().replace('\n','')
        return int(value)
    except Exception, ex:
        logger.critical('Unexpected general exception on pin {} value read, err {}'.format(bcm_id, ex))
        return None

def __write_line(bcm_id='', pin_value=''):
    try:
        #file = open('/sys/class/gpio/gpio{}/value'.format(bcm_id), 'a')
        #print >> file, pin_value
        #file.close()
        logger.info('Write bcm pin={} value={}'.format(bcm_id, pin_value))
        __write_to_file_as_root(file='/sys/class/gpio/gpio{}/value'.format(bcm_id), value=pin_value)
    except Exception, ex:
        logger.critical('Unexpected general exception on pin {} write, err {}'.format(bcm_id, ex))
        return None

def get_pin_bcm(bcm_id=''):
    '''BCM pin id format. Return value is 0 or 1.'''
    if not __is_pin_setup(bcm_id):
        __set_pin_dir_in(bcm_id)
    if __is_pin_setup(bcm_id):
        pin_value = __read_line(bcm_id)
        gpio_pin = models.GpioPin.query.filter_by(pin_index = bcm_id, host_name = constant.HOST_NAME).first()
        if gpio_pin:
            gpio_pin.pin_value = pin_value
            db.session.commit()
        return pin_value
    else:
        logger.critical('Unable to get pin bcm {}'.format(bcm_id))

def set_pin_bcm(bcm_id=None, pin_value=None):
    '''BCM pin id format. Value is 0 or 1. Return value is 0 or 1, confirms pin state'''
    if pin_value is None or bcm_id is None:
        logger.warning('None values, pin={} value={}, ignoring'.format(bcm_id, pin_value))
    else:
        if not __is_pin_setup_out(bcm_id):
            __set_pin_dir_out(bcm_id)
        if __is_pin_setup_out(bcm_id):
            if get_pin_bcm(bcm_id=bcm_id) != pin_value:
                __write_line(bcm_id, pin_value)
            result = get_pin_bcm(bcm_id)
            if result is None:
                logger.warning('Get pin {} returned None result'.format(bcm_id))
            return result
        else:
            logger.critical('Unable to write pin bcm {}'.format(bcm_id))
            return -1

def unload():
    #set all pins to low and unexport
    global __pins_setup_list
    for bcm_pin in __pins_setup_list:
        if __is_pin_setup_out(bcm_id=bcm_pin):
            set_pin_bcm(bcm_id=bcm_pin, pin_value=0)
        __unsetup_pin(bcm_pin=bcm_pin)

def init():
    pass
