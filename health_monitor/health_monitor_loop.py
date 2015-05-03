__author__ = 'dcristian'
import subprocess
import os
import cStringIO
from main import logger
import shutil
import time
import math
import datetime
from collections import OrderedDict
from common import constant, utils
from main.admin import models, model_helper, system_info
import main

try:
    import psutil
    import_module_psutil_exist = True
except Exception, ex:
    logger.info('PSUtil module not available')
    import_module_psutil_exist = False

try:
    import wmi
    import pythoncom
    import_module_wmi_ok = True
except Exception, ex:
    logger.info('pywin / wmi module not available')
    import_module_wmi_ok = False

ERR_TEXT_NO_DEV = 'failed: No such device'
ERR_TEXT_NO_DEV_2 = 'HDIO_GET_32BIT failed: Invalid argument'
ERR_TEXT_NO_DEV_3 = 'Unknown USB bridge'

#http://unix.stackexchange.com/questions/18830/how-to-run-a-specific-program-as-root-without-a-password-prompt
# Cmnd alias specification
#Cmnd_Alias      SMARTCTL = /usr/sbin/smartctl
#Cmnd_Alias      HDPARM = /sbin/hdparm
# User privilege specification
#root    ALL=(ALL:ALL) ALL
# Allow members of group sudo to execute any command
#%sudo   ALL=(ALL:ALL) ALL
#%users  ALL=(ALL) NOPASSWD: SMARTCTL
#%users  ALL=(ALL) NOPASSWD: HDPARM
#%dialout  ALL=(ALL) NOPASSWD: SMARTCTL
#%dialout  ALL=(ALL) NOPASSWD: HDPARM

def __read_all_hdd_smart():
    output = cStringIO.StringIO()
    current_disk_valid = True
    disk_letter = 'a'
    disk_count = 1
    global ERR_TEXT_NO_DEV
    if import_module_psutil_exist:
        while current_disk_valid and disk_count < 64:
            try:
                record = models.SystemDisk()
                record.system_name = constant.HOST_NAME
                assert isinstance(record, models.SystemDisk)
                record.hdd_disk_dev = constant.DISK_DEV_MAIN + disk_letter
                logger.debug('Processing disk {}'.format(record.hdd_disk_dev))
                try:
                    record.power_status = __read_hddparm(disk_dev=record.hdd_disk_dev)
                except Exception, ex:
                    record.power_status = None
                try:
                    use_sudo = bool(model_helper.get_param(constant.P_USESUDO_DISKTOOLS))
                    if constant.OS in constant.OS_LINUX and use_sudo:
                        smart_out = subprocess.check_output(['sudo', 'smartctl', '-a', record.hdd_disk_dev,
                                                             '-n', 'sleep'], stderr=subprocess.STDOUT)
                    else:
                        smart_out = subprocess.check_output(['smartctl', '-a', record.hdd_disk_dev, '-n', 'sleep'],
                                                            stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError, exc:
                    smart_out = exc.output
                    if ERR_TEXT_NO_DEV in smart_out or ERR_TEXT_NO_DEV_3 in smart_out:
                        raise exc
                output.reset()
                output.write(smart_out)
                output.seek(0)
                pos = -1
                while pos != output.tell() and current_disk_valid:
                    pos = output.tell()
                    line = output.readline()
                    if constant.SMARTCTL_ERROR_NO_DISK in line:
                        current_disk_valid = False
                        logger.debug('First disk that cannot be read is {}'.format(record.hdd_disk_dev))
                    if constant.SMARTCTL_TEMP_ID in line:
                        words = line.split(None)
                        record.temperature = utils.round_sensor_value(words[9])
                        # print 'Temp is {}'.format(temp)
                    if constant.SMARTCTL_ERROR_SECTORS in line:
                        words = line.split(None)
                        record.sector_error_count = words[9]
                        # print 'Offline sectors with error is {}'.format(errcount)
                    if constant.SMARTCTL_START_STOP_COUNT in line:
                        words = line.split(None)
                        record.start_stop_count = words[9]
                    if constant.SMARTCTL_LOAD_CYCLE_COUNT in line:
                        words = line.split(None)
                        record.load_cycle_count = words[9]
                    if constant.SMARTCTL_STATUS in line:
                        words = line.split(': ')
                        record.smart_status = words[1].replace('\r', '').replace('\n', '').strip()
                        # print 'SMART Status is {}'.format(status)
                    if constant.SMARTCTL_MODEL_DEVICE in line:
                        words = line.split(': ')
                        record.device = words[1].replace('\r', '').replace('\n', '').lstrip()
                        # print 'Device is {}'.format(device)
                    if constant.SMARTCTL_MODEL_FAMILY in line:
                        words = line.split(': ')
                        record.family = words[1].replace('\r', '').replace('\n', '').lstrip()
                        # print 'Family is {}'.format(family)
                    if constant.SMARTCTL_SERIAL_NUMBER in line:
                        words = line.split(': ')
                        record.serial = words[1].replace('\r', '').replace('\n', '').lstrip()
                        # print 'Serial is {}'.format(serial)
                # print ('Disk dev is {}'.format(disk_dev))
                record.updated_on = datetime.datetime.now()
                if record.serial is None or record.serial == '':
                    logger.debug('This hdd will be skipped, probably does not exist if serial not retrieved')
                else:
                    record.hdd_name = '{} {} {}'.format(record.system_name, record.hdd_device, record.hdd_disk_dev)
                    current_record = models.SystemDisk.query.filter_by(hdd_disk_dev=record.hdd_disk_dev,
                                                                   system_name=record.system_name).first()
                    record.save_changed_fields(current_record=current_record, new_record=record,
                                           notify_transport_enabled=True, save_to_graph=True)
                disk_letter = chr(ord(disk_letter) + 1)
                disk_count = disk_count + 1
            except subprocess.CalledProcessError, ex:
                logger.debug('Invalid disk {} err {}'.format(record.hdd_disk_dev, ex))
                current_disk_valid = False
            except Exception as exc:
                if disk_count > 10:
                    logger.warning('Too many disks iterated {}, missing or wrong sudo rights for smartctl'.format(
                        disk_count))
                logger.warning('Disk read error {} dev {}'.format(exc, record.hdd_disk_dev))
                current_disk_valid = False
    else:
        logger.debug('Unable to read smart status')


def get_device_name_linux_style(dev):
    if ':\\' in dev:
        dev_index = ord(dev[0].lower()) - ord('c')
        return constant.DISK_DEV_MAIN + chr(ord('a') + dev_index)
    else:
        return dev


def __read_hddparm(disk_dev=''):
    output = cStringIO.StringIO()
    global ERR_TEXT_NO_DEV
    try:
        if import_module_psutil_exist:
            try:
                use_sudo = bool(model_helper.get_param(constant.P_USESUDO_DISKTOOLS))
                if constant.OS in constant.OS_LINUX and use_sudo:
                    hddparm_out = subprocess.check_output(['sudo', 'hdparm', '-C', disk_dev], stderr=subprocess.STDOUT)
                else:
                    hddparm_out = subprocess.check_output(['hdparm', '-C', disk_dev], stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError, ex1:
                hddparm_out = ex1.output
                if ERR_TEXT_NO_DEV in hddparm_out or ERR_TEXT_NO_DEV_2 in hddparm_out:
                    raise ex1
            output.reset()
            output.write(hddparm_out)
            output.seek(0)
            pos = -1
            while pos != output.tell():
                pos = output.tell()
                line = output.readline()
                if constant.HDPARM_STATUS in line:
                    words = line.split(': ')
                    power_status = words[1].replace('\r', '').replace('\n', '').replace('/', '-').lstrip()
                    if power_status == 'active-idle':
                        power_status = 1 + constant.HOST_PRIORITY
                    elif power_status == 'standby':
                        power_status = 0
                    else:
                        power_status = -1 - constant.HOST_PRIORITY
                    return power_status
        else:
            power_status = 'not available'
            return power_status
    except subprocess.CalledProcessError, ex:
        logger.debug('Invalid disk {} err {}'.format(disk_dev, ex))
    except Exception as exc:
        logger.warning('Disk read error {} disk was {} err {}'.format(exc.message, disk_dev, exc))
    raise subprocess.CalledProcessError(1, 'No power status obtained on hdparm, output={}'.format(hddparm_out))


def __get_mem_avail_percent_linux():
    # http://architects.dzone.com/articles/linux-system-mining-python
    meminfo = OrderedDict()
    with open('/proc/meminfo') as f:
        for line in f:
            try:
                #MemTotal:        8087892 kB
                meminfo[line.split(':')[0]] = line.split(':')[1].split()[0].strip()
            except Exception, ex:
                logger.warning('get mem line split error {} line {}'.format(ex, line))
        total = int(meminfo['MemTotal'])
        free = int(meminfo['MemFree'])
        memory_available_percent = float(100) * free / total
        memory_available_percent = math.ceil(memory_available_percent * 10) / 10
    global progress_status
    progress_status = 'Read mem total {} free {}'.format(total, free)
    return memory_available_percent


def __get_uptime_linux_days():
    try:
        f = open('/proc/uptime')
        line = f.readline()
        uptime_seconds = float(line.split()[0])
    except Exception, ex:
        logger.warning('Unable to read uptime err {}'.format(ex))
    f.close()
    return uptime_seconds / (60 * 60 * 24)


def __get_uptime_win_days():
    """Returns a datetime.timedelta instance representing the uptime in a Windows 2000/NT/XP machine"""
    cmd = "net statistics server"
    p = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    (child_stdin, child_stdout) = (p.stdin, p.stdout)
    lines = child_stdout.readlines()
    child_stdin.close()
    child_stdout.close()
    lines = [line.strip() for line in lines if line.strip()]
    date, time, ampm = lines[1].split()[2:5]
    # print date, time, ampm
    if str(date[2]).isdigit():
        separator = date[1]
    else:
        separator = date[2]
    d, m, y = [v for v in date.split(separator)]
    m = datetime.datetime.strptime(m, '%b').month
    y = datetime.datetime.strptime(y, '%y').year
    H, M, S = [int(v) for v in time.split(':')]
    if ampm.lower() == 'pm':
        H += 12
    now = datetime.datetime.now()
    then = datetime.datetime(int(y), int(m), int(d), H, M)
    diff = now - then
    return diff.days


def __get_cpu_utilisation_linux():
    previous_procstat_list = None
    CPU_Percentage = None
    for i in range(0, 2):
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
                    previdle = previdle + previowait
                    idle = idle + iowait
                    prevnonidle = prevuser + prevnice + prevsystem + previrq + prevsoftirq + prevsteal
                    nonidle = user + nice + system + irq + softirq + steal
                    prevtotal = previdle + prevnonidle
                    total = idle + nonidle
                    CPU_Percentage = float(100) * float((total - prevtotal) - (idle - previdle)) / float(
                        total - prevtotal)
                    CPU_Percentage = math.ceil(CPU_Percentage * 10) / 10
                previous_procstat_list = words
            else:
                logger.warning('proc/stat returned unexpected number of words on line {}'.format(line))
        except Exception, ex:
            logger.warning('get cpu line split error {} line {}'.format(ex, line))
        # sampling CPU usage for 1 second
        time.sleep(1)
    return CPU_Percentage

def __get_cpu_temperature():
    if constant.IS_OS_WINDOWS():
        #http://stackoverflow.com/questions/3262603/accessing-cpu-temperature-in-python
        global import_module_wmi_ok
        if import_module_wmi_ok:
            try:
                pythoncom.CoInitialize()
                w = wmi.WMI(namespace="root\wmi")
                temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
                temp = (temperature_info.CurrentTemperature / 10) - 273
            except Exception, ex:
                logger.error('Unable to get temperature using wmi, err={}'.format(ex))
    else:
        if constant.IS_MACHINE_RASPBERRYPI:
            path = '/sys/class/thermal/thermal_zone0/temp'
        elif constant.IS_MACHINE_BEAGLEBONE:
            path = '/sys/class/hwmon/hwmon0/device/temp1_input'
        elif constant.IS_MACHINE_INTEL:
            path = '/sys/devices/virtual/thermal/thermal_zone0/temp'
        else:
            path=None

        if path:
            try:
                file = open(path)
                line = file.readline()
            except Exception, ex:
                logger.error('Unable to open cpu_temp_read file {}'.format(path))
            file.close()
        else:
            line = '-1'
            logger.info('Unable to get CPU temp for machine type {}'.format(constant.HOST_MACHINE_TYPE))
        temp = float(line) / 1000
    temp = utils.round_sensor_value(temp)
    return temp


def __read_system_attribs():
    global import_module_psutil_exist, progress_status
    try:
        record = models.SystemMonitor()
        if import_module_psutil_exist:
            record.cpu_usage_percent = psutil.cpu_percent(interval=1)
            record.memory_available_percent = psutil.virtual_memory().percent
            record.cpu_temperature = __get_cpu_temperature()
            if constant.OS in constant.OS_LINUX:
                record.uptime_days = int(__get_uptime_linux_days())
            elif constant.OS in constant.OS_WINDOWS:
                record.uptime_days = int(__get_uptime_win_days())
            import_module_psutil_exist = True
        else:
            output = cStringIO.StringIO()
            if constant.OS in constant.OS_WINDOWS:
                # no backup impl in Windows
                pass
            else:
                # this is normally running on OpenWRT
                record.memory_available_percent = __get_mem_avail_percent_linux()
                record.cpu_usage_percent = __get_cpu_utilisation_linux()
                record.uptime_days = int(__get_uptime_linux_days())
                record.cpu_temperature = __get_cpu_temperature()
                logger.info('Read mem free {} cpu% {} cpu_temp {} uptime {}'.format(record.memory_available_percent,
                                                                    record.cpu_usage_percent, record.cpu_temperature,
                                                                    record.uptime_days))
        progress_status = 'Saving mem cpu uptime to db'
        record.name = constant.HOST_NAME
        record.updated_on = datetime.datetime.now()
        current_record = models.SystemMonitor.query.filter_by(name=record.name).first()
        record.save_changed_fields(current_record=current_record, new_record=record,
                                   notify_transport_enabled=True, save_to_graph=True)
    except Exception, ex:
        logger.warning('Error saving system to DB, err {}'.format(ex))

def __check_log_file_size():
    if not main.LOG_FILE is None:
        try:
            size = os.path.getsize(main.LOG_FILE)
            if size > 1024 * 1024 * 10:
                logger.info('Log file {} size is {}, truncating'.format(main.LOG_FILE, size))
                shutil.copy(main.LOG_FILE, main.LOG_FILE+'.last')
                file = open(main.LOG_FILE, mode='rw+')
                file.truncate()
                file.seek(0)
                file.close()
        except Exception, ex:
            logger.warning('Cannot retrieve or truncate log file {} err={}'.format(main.LOG_FILE, ex))

'''
/proc/diskstats
Date:		February 2008
Contact:	Jerome Marchand <jmarchan@redhat.com>
Description:
		The /proc/diskstats file displays the I/O statistics
		of block devices. Each line contains the following 14
		fields:
		 1 - major number
		 2 - minor mumber
		 3 - device name
		 4 - reads completed successfully
		 5 - reads merged
		 6 - sectors read
		 7 - time spent reading (ms)
		 8 - writes completed
		 9 - writes merged
		10 - sectors written
		11 - time spent writing (ms)
		12 - I/Os currently in progress
		13 - time spent doing I/Os (ms)
		14 - weighted time spent doing I/Os (ms)
		For more details refer to Documentation/iostats.txt

   8       0 sda 1264452 108516 266937483 9246396 26186052 21697821 696126202 330211680 0 273631688 339408208
   8       1 sda1 1264262 108498 266935819 9245816 26176857 21697821 696126202 330172072 0 273625840 339368112
   8      16 sdb 11763370 716778077 5926755744 292424284 69189 3018361 24616255 6178444 54 31594756 298616996
   8      32 sdc 10372408 718147281 5926630968 1646330436 68771 3019336 24620503 6615124 48 35857060 1652958924
   8      48 sdd 12075964 716437570 5926572722 152391492 68759 3019611 24622311 3160472 1 23324912 155550488
   8      64 sde 253447 64045 9317516 747916 17886 52020 1359424 55258600 0 902828 56115344
   8      65 sde1 252938 64015 9313216 747528 17886 52020 1359424 55258600 0 902636 56114956
   8      66 sde2 2 0 4 0 0 0 0 0 0 0 0
   8      69 sde5 335 30 2920 316 0 0 0 0 0 312 316
   9       0 md0 15176822 0 416880026 0 289061 0 46834672 0 0 0 0
   7       0 loop0 0 0 0 0 0 0 0 0 0 0 0

'''

def __read_disk_stats():
    if constant.IS_OS_LINUX():
        with open('/proc/diskstats') as f:
            for line in f:
                words = line.split()
                if len(words) > 8:
                    device_major = words[0]
                    device_name = words[2]

                    #skip for non hdds and partitions (ending with digit)
                    if device_major != '8' and device_name[-1:].isdigit():
                        continue #just to avoid another tab


                    reads_completed = utils.round_sensor_value(words[3])
                    writes_completed = utils.round_sensor_value(words[7])
                    record = models.SystemDisk()
                    record.hdd_disk_dev = '/dev/' + device_name
                    record.last_reads_completed_count = reads_completed
                    record.last_writes_completed_count = writes_completed
                    record.system_name = constant.HOST_NAME
                    record.updated_on = datetime.datetime.now()

                    current_record = models.SystemDisk.query.filter_by(hdd_disk_dev=record.hdd_disk_dev,
                                                                   system_name=record.system_name).first()

                    #save read/write date time only if count changes
                    if current_record:
                        read_elapsed = -1
                        write_elapsed = -1
                        if record.last_reads_completed_count != current_record.last_reads_completed_count:
                            record.last_reads_datetime = datetime.datetime.now()
                        else:
                            record.last_reads_datetime = current_record.last_reads_datetime
                        if record.last_writes_completed_count != current_record.last_writes_completed_count:
                            record.last_writes_datetime = datetime.datetime.now()
                        else:
                            record.last_writes_datetime = current_record.last_writes_datetime
                        if current_record.last_reads_datetime:
                            read_elapsed = (datetime.datetime.now() - record.last_reads_datetime).total_seconds()
                            record.last_reads_elapsed = utils.round_sensor_value(read_elapsed)
                        if current_record.last_writes_datetime:
                            write_elapsed = (datetime.datetime.now() - record.last_writes_datetime).total_seconds()
                            record.last_writes_elapsed = utils.round_sensor_value(write_elapsed)
                        logger.info('Disk {} elapsed read {}s write {}s'.format(device_name,
                                                                                int(read_elapsed), int(write_elapsed)))
                    else:
                        record.last_reads_datetime = datetime.datetime.now()
                        record.last_writes_datetime = datetime.datetime.now()
                    record.save_changed_fields(current_record=current_record, new_record=record,
                                               notify_transport_enabled=False, save_to_graph=True, debug=False)
                else:
                    logger.warning('Unexpected lower number of split atoms={} in diskstat={}'.format(len(words), line))

def init():
    pass

progress_status = None


def get_progress():
    global progress_status
    return progress_status


def thread_run():
    global progress_status, import_module_psutil_exist
    progress_status = 'reading hdd smart attribs'
    __read_all_hdd_smart()
    progress_status = 'reading system attribs'
    __read_system_attribs()
    progress_status = 'reading disk stats'
    __read_disk_stats()
    progress_status = 'checking log size'
    #not needed if RotatingFileHandler if used for logging
    #__check_log_file_size()
    progress_status = 'completed'