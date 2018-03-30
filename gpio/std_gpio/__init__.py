__author__ = 'dcristian'
import os
from main.logger_helper import L
from main import db
from common import Constant
from main.admin import models
from main.admin.model_helper import commit

initialised = False
__pins_setup_list = []


def __get_gpio_db_pin(bcm_id=None):
    gpio_pin = models.GpioPin.query.filter_by(pin_index_bcm=bcm_id, host_name=Constant.HOST_NAME).first()
    return gpio_pin


def __write_to_file_as_root(file, value):
    try:
        if Constant.OS in Constant.OS_LINUX:
            string_out = 'echo {} | sudo tee --append  {}'.format(str(value), file)
            L.l.info("Writing to console [{}]".format(string_out))
            res = os.system(string_out)
            if res == 0:
                return True
            else:
                L.l.warning('Error writing value [{}] to file {} result={}'.format(value, file, res))
    except Exception, ex:
        L.l.warning('Exception writing value [{}] to file {} err='.format(value, file, ex))


def __setup_pin(bcm_id=''):
    try:
        # file = open('/sys/class/gpio/export', 'a')
        # print >> file, bcm_id
        # file.close()
        if __write_to_file_as_root('/sys/class/gpio/export', bcm_id):
            L.l.info('Pin {} exported OK'.format(bcm_id))
        if not bcm_id in __pins_setup_list:
            __pins_setup_list.append(bcm_id)
            gpio_pin = __get_gpio_db_pin(bcm_id)
            if gpio_pin:
                gpio_pin.is_active = True
            else:
                L.l.warning('Unable to find gpio pin with bcmid={} to mark as active'.format(bcm_id))
        else:
            L.l.warning('Trying to add an existing pin {} in setup list'.format(bcm_id))
    except Exception, ex:
        L.l.critical('Unexpected error on pin {} setup, err {}'.format(bcm_id, ex))


def __set_pin_dir_out(bcm_id=''):
    try:
        # file = open('/sys/class/gpio/gpio{}/direction'.format(bcm_id), 'a')
        # print >> file, 'out'
        # file.close()
        __setup_pin(bcm_id)
        if __write_to_file_as_root(file='/sys/class/gpio/gpio{}/direction'.format(bcm_id), value='out'):
            L.l.info('Set pin {} direction OUT is OK'.format(bcm_id))
            gpio_pin = __get_gpio_db_pin(bcm_id)
            if gpio_pin:
                gpio_pin.pin_direction = 'out'
                commit()
        return True
    except Exception, ex:
        L.l.warning('Unexpected exception on pin {} direction OUT set, err {}'.format(bcm_id, ex))
        return False


def __set_pin_dir_in(bcm_id=''):
    try:
        # file = open('/sys/class/gpio/gpio{}/direction'.format(bcm_id), 'a')
        # print >> file, 'in'
        # file.close()
        __setup_pin(bcm_id)
        if __write_to_file_as_root(file='/sys/class/gpio/gpio{}/direction'.format(bcm_id), value='in'):
            L.l.info('Set pin {} direction IN is OK'.format(bcm_id))
            gpio_pin = __get_gpio_db_pin(bcm_id)
            if gpio_pin:
                gpio_pin.pin_direction = 'in'
                commit()
        return True
    except Exception, ex:
        L.l.warning('Unexpected exception on pin {} direction IN set, err {}'.format(bcm_id, ex))
        return False


def __unsetup_pin(bcm_id=''):
    try:
        # file = open('/sys/class/gpio/unexport', 'a')
        # print >> file, bcm_id
        # file.close()
        if __write_to_file_as_root('/sys/class/gpio/unexport', bcm_id):
            L.l.info('Pin {} unexport OK'.format(bcm_id))
        __pins_setup_list.remove(bcm_id)
        gpio_pin = models.GpioPin.query.filter_by(pin_index_bcm=bcm_id, host_name=Constant.HOST_NAME).first()
        if gpio_pin:
            gpio_pin.is_active = False
        else:
            L.l.warning('Unable to find gpio pin with bcmid={} to mark as inactive'.format(bcm_id))
    except Exception, ex:
        L.l.critical('Unexpected error on pin {} un-setup, err {}'.format(bcm_id, ex))


def __is_pin_setup(bcm_id=''):
    try:
        file = open('/sys/class/gpio/gpio{}/value'.format(bcm_id), 'r')
        file.close()
        gpio_pin = models.GpioPin.query.filter_by(pin_index_bcm=bcm_id, host_name=Constant.HOST_NAME).first()
        if gpio_pin and not gpio_pin.is_active:
            L.l.warning(
                'Gpio pin={} is used not via me, conflict with ext. apps or unclean stop?'.format(bcm_id))
            gpio_pin.is_active = True
            commit()
        return True
    except IOError:
        return False
    except Exception, ex:
        L.l.warning('Unexpected exception on pin setup check, err {}'.format(ex))
        db.session.rollback()
        return False


def __is_pin_setup_out(bcm_id=''):
    try:
        file = open('/sys/class/gpio/gpio{}/direction'.format(bcm_id), 'r')
        dir = file.readline()
        file.close()
        return dir.replace('\n', '') == 'out'
    except IOError:
        return False
    except Exception, ex:
        L.l.warning('Unexpected exception on pin setup check, err {}'.format(ex))
        return False


def __read_line(bcm_id=''):
    try:
        file = open('/sys/class/gpio/gpio{}/value'.format(bcm_id), 'r')
        value = file.readline().replace('\n', '')
        return int(value)
    except Exception, ex:
        L.l.critical('Unexpected general exception on pin {} value read, err {}'.format(bcm_id, ex))
        return None


def __write_line(bcm_id='', pin_value=''):
    try:
        # file = open('/sys/class/gpio/gpio{}/value'.format(bcm_id), 'a')
        # print >> file, pin_value
        # file.close()
        L.l.info('Write bcm pin={} value={}'.format(bcm_id, pin_value))
        __write_to_file_as_root(file='/sys/class/gpio/gpio{}/value'.format(bcm_id), value=pin_value)
    except Exception, ex:
        L.l.critical('Unexpected general exception on pin {} write, err {}'.format(bcm_id, ex))
        return None


def get_pin_bcm(bcm_id=''):
    '''BCM pin id format. Return value is 0 or 1.'''
    if not __is_pin_setup(bcm_id):
        __set_pin_dir_in(bcm_id)
    if __is_pin_setup(bcm_id):
        pin_value = __read_line(bcm_id)
        gpio_pin = models.GpioPin.query.filter_by(pin_index_bcm=bcm_id, host_name=Constant.HOST_NAME).first()
        if gpio_pin:
            gpio_pin.pin_value = pin_value
            commit()
        return pin_value
    else:
        L.l.critical('Unable to get pin bcm {}'.format(bcm_id))


# set gpio pin and return the actual pin state
def set_pin_bcm(bcm_id=None, pin_value=None):
    '''BCM pin id format. Value is 0 or 1. Return value is 0 or 1, confirms pin state'''
    if pin_value is None or bcm_id is None:
        L.l.warning('None values, pin={} value={}, ignoring'.format(bcm_id, pin_value))
    else:
        if not __is_pin_setup_out(bcm_id):
            __set_pin_dir_out(bcm_id)
        if __is_pin_setup_out(bcm_id):
            if get_pin_bcm(bcm_id=bcm_id) != pin_value:
                __write_line(bcm_id, pin_value)
            result = get_pin_bcm(bcm_id)
            L.l.info('Set pin={} value={} result_value={}'.format(bcm_id, pin_value, result))
            if result is None:
                L.l.warning('Get pin {} returned None result'.format(bcm_id))
            return result
        else:
            L.l.critical('Unable to write pin bcm {}'.format(bcm_id))
            return -1


def set_pin_edge(bcm_id=None, pin_edge=None):
    if not __is_pin_setup(bcm_id):
        __set_pin_dir_in(bcm_id)
    __write_to_file_as_root(file='/sys/class/gpio/gpio{}/edge'.format(bcm_id), value=pin_edge)
    L.l.info('Writen bcm pin={} EDGE={}'.format(bcm_id, pin_edge))


def thread_run():
    global initialised
    if initialised:
        pass


def unload():
    # set all pins to low and unexport
    global __pins_setup_list
    for bcm_pin in __pins_setup_list:
        if __is_pin_setup_out(bcm_id=bcm_pin):
            set_pin_bcm(bcm_id=bcm_pin, pin_value=0)
        __unsetup_pin(bcm_id=bcm_pin)


def init():
    global initialised
    initialised = True
