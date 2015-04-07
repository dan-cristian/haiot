__author__ = 'dcristian'
import subprocess
import cStringIO
import logging
import time
import math
import datetime
from collections import OrderedDict
from common import constant
from main.admin import models
from main import db

try:
    import psutil
    import_module_psutil_exist = True
except Exception, ex:
    logging.critical('PSUtil module not available')
    import_module_psutil_exist = False

def save_hdd_to_db(serial, power_status, temperature, sector_error_count, smart_status, device, family, disk_dev,
                   start_stop_count, load_cycle_count):
    try:
        system_name=constant.HOST_NAME
        disk = models.SystemDisk.query.filter_by(hdd_disk_dev=disk_dev, system_name=system_name).first()
        if disk is None:
            disk = models.SystemDisk()
            disk.system_name = system_name
            disk.hdd_disk_dev = disk_dev
            record_is_new = True
        else:
            record_is_new = False
        key_compare = disk.comparator_unique_graph_record()
        if not serial is None: disk.serial = serial
        if not device is None: disk.hdd_name = system_name + ' ' +device + ' ' + disk_dev
        if not power_status is None: disk.power_status = power_status
        #important to make it float as it is read as int from SMART table
        if not temperature is None: disk.temperature = float(temperature)
        if not sector_error_count is None: disk.sector_error_count = sector_error_count
        if not smart_status is None: disk.smart_status = smart_status
        if not start_stop_count is None: disk.start_stop_count = start_stop_count
        if not load_cycle_count is None: disk.load_cycle_count  = load_cycle_count
        disk.updated_on = datetime.datetime.now()
        db.session.autoflush=False
        if key_compare != disk.comparator_unique_graph_record():
            if record_is_new:
                db.session.add(disk)
            else:
                logging.info('SystemDisk {} change, old={} new={}'.format(disk.hdd_name, key_compare,
                                                                      disk.comparator_unique_graph_record()))
            disk.save_to_graph = True
            disk.notify_enabled_ = True
            db.session.commit()
        else:
            logging.debug('Ignoring SystemDisk read {}, no value change'.format(key_compare))
            disk.save_to_graph = False
            db.session.rollback()
    except Exception, ex:
        logging.warning('Error saving disk to DB, err {}'.format(ex))

ERR_TEXT_NO_DEV = 'failed: No such device'

def read_all_hdd_smart():
    output = cStringIO.StringIO()
    current_disk_valid = True
    disk_letter='a'
    disk_dev=''
    global ERR_TEXT_NO_DEV
    if import_module_psutil_exist:
        while current_disk_valid:
            try:
                disk_dev=constant.DISK_DEV_MAIN + disk_letter
                logging.debug('Processing disk {}'.format(disk_dev))
                #disk_dev=get_device_name_linux_style(part.device)
                power_status = read_hddparm(disk_dev=disk_dev)
                try:
                    if constant.OS in constant.OS_LINUX:
                        smart_out = subprocess.check_output(['sudo', 'smartctl', '-a', disk_dev, '-n', 'sleep'],
                                                    stderr=subprocess.STDOUT)
                    else:
                        smart_out = subprocess.check_output(['smartctl', '-a', disk_dev, '-n', 'sleep'],
                                                    stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError, exc:
                    smart_out = exc.output
                    if ERR_TEXT_NO_DEV in smart_out:
                        raise exc

                temperature = None
                sector_error_count = None
                device = None
                family = None
                serial = None
                smart_status = None
                load_cycle_count = None
                start_stop_count = None
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
                    if constant.SMARTCTL_START_STOP_COUNT in line:
                        words=line.split(None)
                        start_stop_count = words[9]
                    if constant.SMARTCTL_LOAD_CYCLE_COUNT in line:
                        words=line.split(None)
                        load_cycle_count = words[9]
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
                               disk_dev, start_stop_count, load_cycle_count)
                disk_letter = chr(ord(disk_letter) + 1)
            except subprocess.CalledProcessError, ex:
                logging.debug('Invalid disk {} err {}'.format(disk_dev, ex))
                current_disk_valid = False
            except Exception as exc:
                logging.warning('Disk read error {} dev {}'.format(exc, disk_dev))
                current_disk_valid = False
    else:
         logging.debug('Unable to read smart status')


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
        if import_module_psutil_exist:
            try:
                if constant.OS in constant.OS_LINUX:
                    hddparm_out = subprocess.check_output(['sudo', 'hdparm', '-C', disk_dev], stderr=subprocess.STDOUT)
                else:
                    hddparm_out = subprocess.check_output(['hdparm', '-C', disk_dev], stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError, ex1:
                hddparm_out = ex1.output
                if ERR_TEXT_NO_DEV in hddparm_out:
                    raise ex1
            output.reset()
            output.write(hddparm_out)
            output.seek(0)
            pos=-1
            while pos != output.tell():
                pos = output.tell()
                line=output.readline()
                if constant.HDPARM_STATUS in line:
                    words = line.split(': ')
                    power_status = words[1].replace('\r','').replace('\n','').replace('/','-').lstrip()
                    return power_status
        else:
            power_status = 'not available'
            return power_status
    except subprocess.CalledProcessError, ex:
        logging.debug('Invalid disk {} err {}'.format(disk_dev, ex))
    except Exception as exc:
        logging.warning('Disk read error {} disk was {} err {}'.format(exc.message, disk_dev, exc))
    raise subprocess.CalledProcessError(1, 'No power status obtained on hdparm, output={}'.format(hddparm_out))

def get_mem_avail_percent_linux():
    #http://architects.dzone.com/articles/linux-system-mining-python
    meminfo=OrderedDict()
    with open('/proc/meminfo') as f:
        for line in f:
            try:
                #MemTotal:        8087892 kB
                meminfo[line.split(':')[0]] = line.split(':')[1].split()[0].strip()
            except Exception, ex:
                logging.warning('get mem line split error {} line {}'.format(ex, line))
        total = int(meminfo['MemTotal'])
        free = int(meminfo['MemFree'])
        memory_available_percent = float(100) * free / total
        memory_available_percent = math.ceil(memory_available_percent*10)/10
    global progress_status
    progress_status = 'Read mem total {} free {}'.format(total, free)
    return memory_available_percent

def get_cpu_utilisation_linux():
    previous_procstat_list = None
    CPU_Percentage = None
    for i in range(0,2):
        file = open('/proc/stat')
        line = file.readline()
        file.close()
        try:
            words = line.split()
            if len(words) == 11:
                user = int(words[1].strip())
                nice = int(words[2].strip())
                system = int(words[3].strip())
                idle = int(words[4].strip())
                iowait = int(words[5].strip())
                irq = int(words[6].strip())
                softirq = int(words[7].strip())
                steal = int(words[8].strip())
                guest = int(words[9].strip())
                guest_nice = int(words[10].strip())
                if not previous_procstat_list is None:
                    prevuser = int(previous_procstat_list[1].strip())
                    prevnice = int(previous_procstat_list[2].strip())
                    prevsystem = int(previous_procstat_list[3].strip())
                    previdle = int(previous_procstat_list[4].strip())
                    previowait = int(previous_procstat_list[5].strip())
                    previrq = int(previous_procstat_list[6].strip())
                    prevsoftirq = int(previous_procstat_list[7].strip())
                    prevsteal = int(previous_procstat_list[8].strip())
                    prevguest = int(previous_procstat_list[9].strip())
                    prevguest_nice = int(previous_procstat_list[10].strip())
                    previdle = previdle+previowait
                    idle=idle+iowait
                    prevnonidle = prevuser+prevnice+prevsystem+previrq+prevsoftirq+prevsteal
                    nonidle = user+nice+system+irq+softirq+steal
                    prevtotal = previdle+prevnonidle
                    total = idle+nonidle
                    CPU_Percentage = float(100) * float((total - prevtotal)-(idle-previdle))/float(total-prevtotal)
                    CPU_Percentage = math.ceil(CPU_Percentage*10)/10
                previous_procstat_list = words
            else:
                logging.warning('proc/stat returned unexpected number of words on line {}'.format(line))
        except Exception, ex:
            logging.warning('get cpu line split error {} line {}'.format(ex, line))
        #sampling CPU usage for 1 second
        time.sleep(1)
    return CPU_Percentage

def read_system_attribs():
    global import_module_psutil_exist, progress_status
    cpu_percent = None
    memory_available_percent = None
    if import_module_psutil_exist:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_available_percent = psutil.virtual_memory().percent
        import_module_psutil_exist = True
    else:
        output = cStringIO.StringIO()
        if constant.OS in constant.OS_WINDOWS:
            #no backup impl in Windows
            pass
        else:
            #this is normally running on OpenWRT
            memory_available_percent = get_mem_avail_percent_linux()
            cpu_percent = get_cpu_utilisation_linux()
            logging.info('Read mem free {} cpu {}'.format(memory_available_percent, cpu_percent))
    progress_status = 'Saving mem and cpu to db'
    if not cpu_percent is None and not memory_available_percent is None:
        save_system_attribs_to_db(cpu_percent=cpu_percent, memory_available_percent=memory_available_percent)

def save_system_attribs_to_db(cpu_percent='', memory_available_percent=''):
    try:
        system_name=constant.HOST_NAME
        system = models.SystemMonitor.query.filter_by(name=system_name).first()
        if system is None:
            system = models.SystemMonitor()
            system.name = system_name
            record_is_new = True
        else:
            record_is_new = False

        key_compare = system.comparator_unique_graph_record()
        system.cpu_usage_percent = cpu_percent
        system.memory_available_percent = memory_available_percent

        system.updated_on = datetime.datetime.now()
        db.session.autoflush=False
        if key_compare != system.comparator_unique_graph_record():
            if record_is_new:
                db.session.add(system)
            else:
                logging.info('SystemMonitor {} change, old={} new={}'.format(system.name, key_compare,
                                                                      system.comparator_unique_graph_record()))
            system.save_to_graph = True
            system.notify_enabled_ = True
            db.session.commit()
        else:
            logging.debug('Ignoring system read {}, no value change'.format(key_compare))
            system.save_to_graph = False
            db.session.rollback()
    except Exception, ex:
        logging.warning('Error saving system to DB, err {}'.format(ex))

def init():
    pass

progress_status = None
def get_progress():
    global progress_status
    return progress_status

def thread_run():
    global progress_status, import_module_psutil_exist
    progress_status = 'reading hdd smart attribs'
    read_all_hdd_smart()
    progress_status = 'reading system attribs'
    read_system_attribs()
    progress_status = 'completed'
    pass