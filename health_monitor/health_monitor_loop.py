import subprocess
import os
import cStringIO
import shutil
import time
import math
import datetime
from pydispatch import dispatcher
from collections import OrderedDict
from main.logger_helper import L
from common import Constant, utils
from main.admin import model_helper, models
from main import logger_helper
from ina219 import INA219
#from ina219 import DeviceRangeError

__author__ = 'dcristian'

try:
    import psutil
    import_module_psutil_exist = True
except Exception, ex:
    #Log.logger.info('PSUtil module not available')
    import_module_psutil_exist = False

try:
    import wmi
    import pythoncom
    import_module_wmi_ok = True
except Exception, ex:
    #Log.logger.info('pywin / wmi module not available')
    import_module_wmi_ok = False

ERR_TEXT_NO_DEV = 'failed: No such device'
ERR_TEXT_NO_DEV_2 = 'HDIO_GET_32BIT failed: Invalid argument'
ERR_TEXT_NO_DEV_3 = 'Unknown USB bridge'

_import_ina_failed = False

# http://unix.stackexchange.com/questions/18830/how-to-run-a-specific-program-as-root-without-a-password-prompt
# Cmnd alias specification
# Cmnd_Alias      SMARTCTL = /usr/sbin/smartctl
# Cmnd_Alias      HDPARM = /sbin/hdparm
# User privilege specification
# root    ALL=(ALL:ALL) ALL
# Allow members of group sudo to execute any command
# %sudo   ALL=(ALL:ALL) ALL
# %users  ALL=(ALL) NOPASSWD: SMARTCTL
# %users  ALL=(ALL) NOPASSWD: HDPARM
# %dialout  ALL=(ALL) NOPASSWD: SMARTCTL
# %dialout  ALL=(ALL) NOPASSWD: HDPARM

def _read_all_hdd_smart():
    output = cStringIO.StringIO()
    current_disk_valid = True
    disk_letter = 'a'
    disk_count = 1
    global ERR_TEXT_NO_DEV
    if import_module_psutil_exist:
        while current_disk_valid and disk_count < 64:
            try:
                record = models.SystemDisk()
                record.system_name = Constant.HOST_NAME
                assert isinstance(record, models.SystemDisk)
                record.hdd_disk_dev = Constant.DISK_DEV_MAIN + disk_letter
                L.l.debug('Processing disk {}'.format(record.hdd_disk_dev))
                try:
                    record.power_status = __read_hddparm(disk_dev=record.hdd_disk_dev)
                except Exception, ex1:
                    record.power_status = None
                try:
                    use_sudo = bool(model_helper.get_param(Constant.P_USESUDO_DISKTOOLS))
                    if Constant.OS in Constant.OS_LINUX and use_sudo:
                        smart_out = subprocess.check_output(['sudo', 'smartctl', '-a', record.hdd_disk_dev,
                                                             '-n', 'sleep'], stderr=subprocess.STDOUT)
                    else:  # in windows
                        smart_out = subprocess.check_output(['smartctl', '-a', record.hdd_disk_dev, '-n', 'sleep'],
                                                            stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError, exc:
                    smart_out = exc.output
                    if ERR_TEXT_NO_DEV in smart_out or ERR_TEXT_NO_DEV_3 in smart_out:
                        raise exc
                except Exception, ex:
                    smart_out = None
                    current_disk_valid = False
                    L.l.warning("Error checking smart status {}".format(ex))

                if smart_out:
                    output.reset()
                    output.write(smart_out)
                    output.seek(0)
                    pos = -1
                    while pos != output.tell() and current_disk_valid:
                        pos = output.tell()
                        line = output.readline()
                        if Constant.SMARTCTL_ERROR_NO_DISK in line:
                            current_disk_valid = False
                            L.l.debug('First disk that cannot be read is {}'.format(record.hdd_disk_dev))
                        if Constant.SMARTCTL_TEMP_ID in line:
                            words = line.split(None)
                            record.temperature = utils.round_sensor_value(words[9])
                            # print 'Temp is {}'.format(temp)
                        if Constant.SMARTCTL_ERROR_SECTORS in line:
                            words = line.split(None)
                            record.sector_error_count = words[9]
                            # print 'Offline sectors with error is {}'.format(errcount)
                        if Constant.SMARTCTL_START_STOP_COUNT in line:
                            words = line.split(None)
                            record.start_stop_count = words[9]
                        if Constant.SMARTCTL_LOAD_CYCLE_COUNT in line:
                            words = line.split(None)
                            record.load_cycle_count = words[9]
                        if Constant.SMARTCTL_STATUS in line:
                            words = line.split(': ')
                            record.smart_status = words[1].replace('\r', '').replace('\n', '').strip()
                            # print 'SMART Status is {}'.format(status)
                        if Constant.SMARTCTL_MODEL_DEVICE in line:
                            words = line.split(': ')
                            record.device = words[1].replace('\r', '').replace('\n', '').lstrip()
                            # print 'Device is {}'.format(device)
                        if Constant.SMARTCTL_MODEL_FAMILY in line:
                            words = line.split(': ')
                            record.family = words[1].replace('\r', '').replace('\n', '').lstrip()
                            # print 'Family is {}'.format(family)
                        if Constant.SMARTCTL_SERIAL_NUMBER in line:
                            words = line.split(': ')
                            record.serial = words[1].replace('\r', '').replace('\n', '').lstrip()
                            # print 'Serial is {}'.format(serial)
                            # print ('Disk dev is {}'.format(disk_dev))
                record.updated_on = utils.get_base_location_now_date()
                if record.serial is None or record.serial == '':
                    L.l.debug('This hdd will be skipped, probably does not exist if serial not retrieved')
                    record.serial = 'serial not available {} {}'.format(Constant.HOST_NAME, record.hdd_disk_dev)
                else:
                    record.hdd_name = '{} {} {}'.format(record.system_name, record.hdd_device, record.hdd_disk_dev)
                    current_record = models.SystemDisk.query.filter_by(hdd_disk_dev=record.hdd_disk_dev,
                                                                       system_name=record.system_name).first()
                    record.save_changed_fields(current_record=current_record, new_record=record,
                                               notify_transport_enabled=True, save_to_graph=True)
                disk_letter = chr(ord(disk_letter) + 1)
                disk_count += 1
            except subprocess.CalledProcessError, ex1:
                L.l.debug('Invalid disk {} err {}'.format(record.hdd_disk_dev, ex1))
                current_disk_valid = False
            except Exception as exc:
                if disk_count > 10:
                    L.l.warning('Too many disks iterated {}, missing or wrong sudo rights for smartctl'.format(
                        disk_count))
                L.l.exception('Disk read error={} dev={}'.format(exc, record.hdd_disk_dev))
                current_disk_valid = False
    else:
        L.l.debug('Unable to read smart status')


def get_device_name_linux_style(dev):
    if ':\\' in dev:
        dev_index = ord(dev[0].lower()) - ord('c')
        return Constant.DISK_DEV_MAIN + chr(ord('a') + dev_index)
    else:
        return dev


def __read_hddparm(disk_dev=''):
    output = cStringIO.StringIO()
    hddparm_out = "None"
    global ERR_TEXT_NO_DEV
    try:
        if import_module_psutil_exist:
            try:
                use_sudo = bool(model_helper.get_param(Constant.P_USESUDO_DISKTOOLS))
                if Constant.OS in Constant.OS_LINUX and use_sudo:
                    hddparm_out = subprocess.check_output(['sudo', 'hdparm', '-C', disk_dev], stderr=subprocess.STDOUT)
                else:
                    hddparm_out = subprocess.check_output(['hdparm', '-C', disk_dev], stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError, ex1:
                hddparm_out = ex1.output
                if ERR_TEXT_NO_DEV in hddparm_out or ERR_TEXT_NO_DEV_2 in hddparm_out:
                    raise ex1
            except Exception, ex:
                L.l.warning("Error running process, err={}".format(ex))
                hddparm_out = None
            if hddparm_out:
                output.reset()
                output.write(hddparm_out)
                output.seek(0)
                pos = -1
                while pos != output.tell():
                    pos = output.tell()
                    line = output.readline()
                    if Constant.HDPARM_STATUS in line:
                        words = line.split(': ')
                        power_status = words[1].replace('\r', '').replace('\n', '').replace('/', '-').lstrip()
                        if power_status == 'active-idle':
                            power_status = 1 + Constant.HOST_PRIORITY
                        elif power_status == 'standby':
                            power_status = 0
                        else:
                            power_status = -1 - Constant.HOST_PRIORITY
                        return power_status
        else:
            power_status = 'not available'
            return power_status
    except subprocess.CalledProcessError, ex:
        L.l.debug('Invalid disk {} err {}'.format(disk_dev, ex))
    except Exception as exc:
        L.l.exception('Disk read error disk was {} err {}'.format(disk_dev, exc))
    raise subprocess.CalledProcessError(1, 'No power status obtained on hdparm, output={}'.format(hddparm_out))


def __get_mem_avail_percent_linux():
    # http://architects.dzone.com/articles/linux-system-mining-python
    meminfo = OrderedDict()
    with open('/proc/meminfo') as f:
        for line in f:
            try:
                # MemTotal:        8087892 kB
                meminfo[line.split(':')[0]] = line.split(':')[1].split()[0].strip()
            except Exception, ex:
                L.l.warning('get mem line split error {} line {}'.format(ex, line))
        total = int(meminfo['MemTotal'])
        free = int(meminfo['MemFree'])
        memory_available_percent = float(100) * free / total
        memory_available_percent = math.ceil(memory_available_percent * 10) / 10
    global progress_status
    progress_status = 'Read mem total {} free {}'.format(total, free)
    return memory_available_percent


def __get_uptime_linux_days():
    uptime_seconds = 0
    try:
        f = open('/proc/uptime')
        line = f.readline()
        uptime_seconds = float(line.split()[0])
        f.close()
    except Exception, ex:
        L.l.warning('Unable to read uptime err {}'.format(ex))
    return uptime_seconds / (60 * 60 * 24)


# fixme: does not work always, depends on regional settings
def __get_uptime_win_days():
    """Returns a datetime.timedelta instance representing the uptime in a Windows 2000/NT/XP machine"""
    try:
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
        now = utils.get_base_location_now_date()
        then = datetime.datetime(int(y), int(m), int(d), H, M)
        diff = now - then
        return diff.days
    except Exception, ex:
        L.l.warning("Unable to get uptime windows, err={}".format(ex))
        return 0


def __get_cpu_utilisation_linux():
    previous_procstat_list = None
    CPU_Percentage = None
    for i in range(0, 2):
        file = open('/proc/stat')
        line = file.readline()
        file.close()
        try:
            words = line.split()
            if len(words) >= 9:
                user = int(words[1].strip())
                nice = int(words[2].strip())
                system = int(words[3].strip())
                idle = int(words[4].strip())
                iowait = int(words[5].strip())
                irq = int(words[6].strip())
                softirq = int(words[7].strip())
                steal = int(words[8].strip())
                # guest = int(words[9].strip())
                # guest_nice = int(words[10].strip())
                if not previous_procstat_list is None:
                    prevuser = int(previous_procstat_list[1].strip())
                    prevnice = int(previous_procstat_list[2].strip())
                    prevsystem = int(previous_procstat_list[3].strip())
                    previdle = int(previous_procstat_list[4].strip())
                    previowait = int(previous_procstat_list[5].strip())
                    previrq = int(previous_procstat_list[6].strip())
                    prevsoftirq = int(previous_procstat_list[7].strip())
                    prevsteal = int(previous_procstat_list[8].strip())
                    # prevguest = int(previous_procstat_list[9].strip())
                    # prevguest_nice = int(previous_procstat_list[10].strip())
                    previdle += previowait
                    idle += iowait
                    prevnonidle = prevuser + prevnice + prevsystem + previrq + prevsoftirq + prevsteal
                    nonidle = user + nice + system + irq + softirq + steal
                    prevtotal = previdle + prevnonidle
                    total = idle + nonidle
                    CPU_Percentage = float(100) * float((total - prevtotal) - (idle - previdle)) / float(
                        total - prevtotal)
                    CPU_Percentage = math.ceil(CPU_Percentage * 10) / 10
                previous_procstat_list = words
            else:
                L.l.warning('proc/stat returned unexpected number of words on line {}'.format(line))
        except Exception, ex:
            L.l.warning('get cpu line split error {} line {}'.format(ex, line))
        # sampling CPU usage for 1 second
        time.sleep(1)
    return CPU_Percentage


def __get_cpu_temperature():
    temp = -1
    if Constant.IS_OS_WINDOWS():
        # http://stackoverflow.com/questions/3262603/accessing-cpu-temperature-in-python
        global import_module_wmi_ok
        if import_module_wmi_ok:
            try:
                pythoncom.CoInitialize()
                w = wmi.WMI(namespace="root\wmi")
                temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
                temp = (temperature_info.CurrentTemperature / 10) - 273
            except Exception, ex:
                L.l.error('Unable to get temperature using wmi, err={}'.format(ex))
        else:
            L.l.warning('Unable to get CPU temp, no function available')
    else:
        if Constant.IS_MACHINE_RASPBERRYPI:
            path = '/sys/class/thermal/thermal_zone0/temp'
        elif Constant.IS_MACHINE_BEAGLEBONE:
            path = '/sys/class/hwmon/hwmon0/device/temp1_input'
        elif Constant.IS_MACHINE_INTEL:
            path = '/sys/devices/virtual/thermal/thermal_zone0/temp'
        else:
            path = None
        line = '-1'
        if path and os.path.isfile(path):
            file = None
            try:
                file = open(path)
                line = file.readline()
            except Exception, ex:
                L.l.error('Unable to open cpu_temp_read file {}'.format(path))
            if file:
                file.close()
        else:
            L.l.debug('Unable to get CPU temp for machine type {}'.format(Constant.HOST_MACHINE_TYPE))
        temp = float(line) / 1000
    temp = utils.round_sensor_value(temp)
    return temp


def _read_system_attribs():
    global import_module_psutil_exist, progress_status
    try:
        record = models.SystemMonitor()
        if import_module_psutil_exist:
            record.cpu_usage_percent = psutil.cpu_percent(interval=1)
            record.memory_available_percent = psutil.virtual_memory().percent
            record.cpu_temperature = __get_cpu_temperature()
            if Constant.OS in Constant.OS_LINUX:
                record.uptime_days = int(__get_uptime_linux_days())
            elif Constant.OS in Constant.OS_WINDOWS:
                record.uptime_days = int(__get_uptime_win_days())
            import_module_psutil_exist = True
        else:
            output = cStringIO.StringIO()
            if Constant.OS in Constant.OS_WINDOWS:
                # fixme: no backup impl in Windows
                return
            else:
                # this is normally running on OpenWRT
                record.memory_available_percent = __get_mem_avail_percent_linux()
                record.cpu_usage_percent = __get_cpu_utilisation_linux()
                record.uptime_days = int(__get_uptime_linux_days())
                record.cpu_temperature = __get_cpu_temperature()
                L.l.debug(
                    'Read mem free {} cpu% {} cpu_temp {} uptime {}'.format(record.memory_available_percent,
                                                                            record.cpu_usage_percent,
                                                                            record.cpu_temperature,
                                                                            record.uptime_days))
        progress_status = 'Saving mem cpu uptime to db'
        record.name = Constant.HOST_NAME
        record.updated_on = utils.get_base_location_now_date()
        current_record = models.SystemMonitor.query.filter_by(name=record.name).first()
        record.save_changed_fields(current_record=current_record, new_record=record,
                                   notify_transport_enabled=False, save_to_graph=True)
    except Exception, ex:
        L.l.exception('Error saving system to DB err={}'.format(ex))


def __check_log_file_size():
    if not logger_helper.L.LOG_FILE is None:
        try:
            size = os.path.getsize(logger_helper.L.LOG_FILE)
            if size > 1024 * 1024 * 10:
                L.l.info('Log file {} size is {}, truncating'.format(logger_helper.L.LOG_FILE, size))
                shutil.copy(logger_helper.L.LOG_FILE, logger_helper.L.LOG_FILE + '.last')
                file = open(logger_helper.L.LOG_FILE, mode='rw+')
                file.truncate()
                file.seek(0)
                file.close()
        except Exception, ex:
            L.l.warning('Cannot retrieve or truncate log file {} err={}'.format(logger_helper.L.LOG_FILE, ex))


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


def _read_disk_stats():
    if Constant.IS_OS_LINUX():
        with open('/proc/diskstats') as f:
            for line in f:
                words = line.split()
                if len(words) > 8:
                    device_major = words[0]
                    device_name = words[2]

                    # skip for non hdds and partitions (ending with digit)
                    if device_major != '8' or device_name[-1:].isdigit():
                        continue  # just to avoid another tab

                    reads_completed = utils.round_sensor_value(words[3])
                    writes_completed = utils.round_sensor_value(words[7])
                    record = models.SystemDisk()
                    record.hdd_disk_dev = '/dev/' + device_name
                    record.last_reads_completed_count = reads_completed
                    record.last_writes_completed_count = writes_completed
                    record.system_name = Constant.HOST_NAME
                    record.updated_on = utils.get_base_location_now_date()

                    current_record = models.SystemDisk.query.filter_by(hdd_disk_dev=record.hdd_disk_dev,
                                                                       system_name=record.system_name).first()
                    # save read/write date time only if count changes
                    if current_record:
                        if current_record.serial is None or current_record.serial == '':
                            record.serial = 'serial not available {} {}'.format(Constant.HOST_NAME, record.hdd_disk_dev)
                        if current_record.hdd_name is None or current_record.hdd_name == '':
                            record.hdd_name = '{} {}'.format(Constant.HOST_NAME, record.hdd_disk_dev)
                        read_elapsed = -1
                        write_elapsed = -1
                        if record.last_reads_completed_count != current_record.last_reads_completed_count:
                            record.last_reads_datetime = utils.get_base_location_now_date()
                        else:
                            record.last_reads_datetime = current_record.last_reads_datetime
                        if record.last_writes_completed_count != current_record.last_writes_completed_count:
                            record.last_writes_datetime = utils.get_base_location_now_date()
                        else:
                            record.last_writes_datetime = current_record.last_writes_datetime
                        if current_record.last_reads_datetime:
                            read_elapsed = (
                            utils.get_base_location_now_date() - record.last_reads_datetime).total_seconds()
                            record.last_reads_elapsed = utils.round_sensor_value(read_elapsed)
                        if current_record.last_writes_datetime:
                            write_elapsed = (
                            utils.get_base_location_now_date() - record.last_writes_datetime).total_seconds()
                            record.last_writes_elapsed = utils.round_sensor_value(write_elapsed)
                        L.l.debug('Disk {} elapsed read {}s write {}s'.format(device_name,
                                                                              int(read_elapsed),
                                                                              int(write_elapsed)))
                    else:
                        record.last_reads_datetime = utils.get_base_location_now_date()
                        record.last_writes_datetime = utils.get_base_location_now_date()
                        record.serial = 'serial not available {} {}'.format(Constant.HOST_NAME, record.hdd_disk_dev)
                    record.save_changed_fields(current_record=current_record, new_record=record,
                                               notify_transport_enabled=True, save_to_graph=True, debug=False)
                else:
                    L.l.warning(
                        'Unexpected lower number of split atoms={} in diskstat={}'.format(len(words), line))


def _read_battery_power():
    global _import_ina_failed
    if not _import_ina_failed:
        SHUNT_OHMS = 0.1
        MAX_EXPECTED_AMPS = 2
        try:
            ina = INA219(SHUNT_OHMS, MAX_EXPECTED_AMPS)
            ina.configure(voltage_range=ina.RANGE_16V, bus_adc=ina.ADC_128SAMP, shunt_adc=ina.ADC_128SAMP)
            voltage = ina.voltage()
            current = ina.current()
            power = ina.power()
            dispatcher.send(signal=Constant.SIGNAL_BATTERY_STAT,
                            battery="INA", voltage=voltage, current=current, power=power)
        except ImportError, imp:
            L.l.info("INA module not available on this system, ex={}".format(imp))
            _import_ina_failed = True
        except Exception, ex:
            L.l.error("Current out of device range with specified shunt resister, ex={}".format(ex))


def init():
    pass


progress_status = None


def get_progress():
    global progress_status
    return progress_status


def thread_run():
    global progress_status, import_module_psutil_exist
    progress_status = 'reading hdd smart attribs'
    _read_all_hdd_smart()
    progress_status = 'reading system attribs'
    _read_system_attribs()
    progress_status = 'reading disk stats'
    _read_disk_stats()
    #progress_status = 'checking log size'
    # not needed if RotatingFileHandler if used for logging
    # __check_log_file_size()
    _read_battery_power()
    progress_status = 'completed'
