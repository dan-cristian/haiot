__author__ = 'dcristian'
import subprocess
import cStringIO
import logging
import psutil
import socket
import os
import sys
import datetime
from common import constant
from main.admin import models
from main import db

g_cpu_percent = float(0)
g_memory_available_percent = float(0)

def save_hdd_to_db(serial, power_status, temperature, sector_error_count, smart_status, device, family, disk_dev):
    try:
        system_name=socket.gethostname()
        disk = models.SystemDisk.query.filter_by(serial=serial).first()
        if disk is None:
            disk = models.SystemDisk()
            disk.system_name = system_name
            disk.hdd_name = family + ' ' + device + ' ' + serial
            record_is_new = True
        else:
            record_is_new = False
        key_compare = disk.comparator_unique_graph_record()

        disk.serial = serial
        disk.hdd_disk_dev = disk_dev
        disk.power_status = power_status
        disk.temperature = float(temperature)#important to make it float as it is read as int from SMART table
        disk.sector_error_count = sector_error_count
        disk.smart_status = smart_status
        disk.updated_on = datetime.datetime.now()
        db.session.autoflush=False
        if key_compare != disk.comparator_unique_graph_record():
            if record_is_new:
                db.session.add(disk)
            else:
                logging.info('Disk {} change, old={} new={}'.format(disk.hdd_name, key_compare,
                                                                      disk.comparator_unique_graph_record()))
            disk.save_to_graph = True
            db.session.commit()
        else:
            logging.debug('Ignoring disk read {}, no value change'.format(key_compare))
            disk.save_to_graph = False
    except Exception, ex:
        logging.warning('Error saving disk to DB, err {}'.format(ex))

ERR_TEXT_NO_DEV = 'failed: No such device'

def read_all_hdd_smart():
    output = cStringIO.StringIO()
    current_disk_valid = True
    disk_letter='a'
    disk_dev=''
    global ERR_TEXT_NO_DEV
    while current_disk_valid:
        try:
            disk_dev=constant.DISK_DEV_MAIN + disk_letter
            logging.debug('Processing disk {}'.format(disk_dev))
            sector_error_count = -1
            #disk_dev=get_device_name_linux_style(part.device)
            power_status = read_hddparm(disk_dev=disk_dev)
            try:
                smart_out = subprocess.check_output(['sudo', 'smartctl', '-a', disk_dev, '-n', 'standby'],
                                                stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError, exc:
                smart_out = exc.output
                if ERR_TEXT_NO_DEV in smart_out:
                    raise subprocess.CalledProcessError('Probably invalid disk on smartctl {}'.format(disk_dev))
            output.reset()
            output.write(smart_out)
            output.seek(0)
            pos=-1
            while pos != output.tell() and current_disk_valid:
                pos = output.tell()
                line=output.readline()
                if constant.SMARTCTL_ERROR_NO_DISK in line:
                    current_disk_valid = False
                    logging.debug('First disk that cannot be read is {}'.format(disk_dev))
                if constant.SMARTCTL_TEMP_ID in line:
                    words=line.split(None)
                    temperature = words[9]
                    #print 'Temp is {}'.format(temp)
                if constant.SMARTCTL_ERROR_SECTORS in line:
                    words=line.split(None)
                    sector_error_count = words[9]
                    #print 'Offline sectors with error is {}'.format(errcount)
                if constant.SMARTCTL_STATUS in line:
                    words = line.split(': ')
                    smart_status = words[1].replace('\r','').replace('\n','').strip()
                    #print 'SMART Status is {}'.format(status)
                if constant.SMARTCTL_MODEL_DEVICE in line:
                    words = line.split(': ')
                    device = words[1].replace('\r','').replace('\n','').lstrip()
                    #print 'Device is {}'.format(device)
                if constant.SMARTCTL_MODEL_FAMILY in line:
                    words = line.split(': ')
                    family = words[1].replace('\r','').replace('\n','').lstrip()
                    #print 'Family is {}'.format(family)
                if constant.SMARTCTL_SERIAL_NUMBER in line:
                    words = line.split(': ')
                    serial = words[1].replace('\r','').replace('\n','').lstrip()
                    #print 'Serial is {}'.format(serial)
            #print ('Disk dev is {}'.format(disk_dev))
            save_hdd_to_db(serial, power_status, temperature, sector_error_count, smart_status, device, family,
                           disk_dev)
            disk_letter = chr(ord(disk_letter) + 1)
        except subprocess.CalledProcessError, ex:
            logging.info('Invalid disk {} err {}'.format(disk_dev, ex))
            current_disk_valid = False
        except Exception as exc:
            logging.warning('Disk read error {} dev {}'.format(exc, disk_dev))
            current_disk_valid = False


def get_device_name_linux_style(dev):
    if ':\\' in dev:
        dev_index = ord(dev[0].lower()) - ord('c')
        return constant.DISK_DEV_MAIN + chr(ord('a')+dev_index)
    else:
        return dev

def read_hddparm(disk_dev=''):
    output = cStringIO.StringIO()
    global ERR_TEXT_NO_DEV
    try:
        try:
            hddparm_out = subprocess.check_output(['sudo', 'hdparm', '-C', disk_dev], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError, exc:
            smart_out = exc.output
            if ERR_TEXT_NO_DEV in smart_out:
                raise subprocess.CalledProcessError('Probably invalid disk on hdparm {}'.format(disk_dev))
        output.reset()
        output.write(hddparm_out)
        output.seek(0)
        pos=-1
        while pos != output.tell():
            pos = output.tell()
            line=output.readline()
            if constant.HDPARM_STATUS in line:
                words = line.split(': ')
                status = words[1].replace('\r','').replace('\n','').lstrip()
                return status
    except subprocess.CalledProcessError, ex:
        logging.info('Invalid disk {} err {}'.format(disk_dev, ex))
    except Exception as exc:
        logging.warning('Disk read error {} disk was {} err {}'.format(exc.message, disk_dev, exc))

def read_system_attribs():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_available_percent = psutil.virtual_memory().percent
    save_system_attribs_to_db(cpu_percent=cpu_percent, memory_available_percent=memory_available_percent)

def save_system_attribs_to_db(cpu_percent='', memory_available_percent=''):
    try:
        system_name=socket.gethostname()
        system = models.SystemMonitor.query.filter_by(name=system_name).first()
        if system is None:
            system = models.SystemMonitor()
            system.name = system_name
            record_is_new = True
        else:
            record_is_new = False

        system.cpu_usage_percent = cpu_percent
        system.memory_available_percent = memory_available_percent
        key_compare = system.comparator_unique_graph_record()

        system.updated_on = datetime.datetime.now()
        db.session.autoflush=False
        if key_compare != system.comparator_unique_graph_record():
            if record_is_new:
                db.session.add(system)
            else:
                logging.info('System {} change, old={} new={}'.format(system.name, key_compare,
                                                                      system.comparator_unique_graph_record()))
            system.save_to_graph = True
            db.session.commit()
        else:
            logging.debug('Ignoring system read {}, no value change'.format(key_compare))
            system.save_to_graph = False
    except Exception, ex:
        logging.warning('Error saving system to DB, err {}'.format(ex))


def init():
    pass

def thread_run():
    read_all_hdd_smart()
    read_system_attribs()
    pass