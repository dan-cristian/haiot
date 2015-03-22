__author__ = 'dcristian'
import subprocess
import cStringIO
import logging
from common import constant

def read_all_hdd_smart():
    output = cStringIO.StringIO()
    disk_letter='a'
    current_disk_valid = True
    disk_dev=''
    while current_disk_valid:
        try:
            disk_dev=constant.DISK_DEV_MAIN + disk_letter
            smart_out = subprocess.check_output('smartctl -a ' + disk_dev, stderr=subprocess.STDOUT)
            output.reset()
            output.write(smart_out)
            output.seek(0)
            pos=-1
            while pos != output.tell() and current_disk_valid:
                pos = output.tell()
                line=output.readline()
                if constant.SMARTCTL_ERROR_NO_DISK in line:
                    current_disk_valid = False
                    logging.info('First disk that cannot be read is {}'.format(disk_dev))
                if constant.SMARTCTL_TEMP_ID in line:
                    words=line.split(None)
                    temp = words[9]
                    print 'Temp is {}'.format(temp)
                if constant.SMARTCTL_ERROR_SECTORS in line:
                    words=line.split(None)
                    errcount = words[9]
                    print 'Offline sectors with error is {}'.format(errcount)
                if constant.SMARTCTL_STATUS in line:
                    words = line.split(': ')
                    status = words[1].replace('\r','').replace('\n','').strip()
                    print 'SMART Status is {}'.format(status)
                if constant.SMARTCTL_MODEL_DEVICE in line:
                    words = line.split(': ')
                    device = words[1].replace('\r','').replace('\n','').lstrip()
                    print 'Device is {}'.format(device)
                if constant.SMARTCTL_MODEL_FAMILY in line:
                    words = line.split(': ')
                    family = words[1].replace('\r','').replace('\n','').lstrip()
                    print 'Family is {}'.format(family)
                if constant.SMARTCTL_SERIAL_NUMBER in line:
                    words = line.split(': ')
                    serial = words[1].replace('\r','').replace('\n','').lstrip()
                    print 'Serial is {}'.format(serial)
            print ('Disk dev is {}'.format(disk_dev))
            disk_letter = chr(ord(disk_letter) + 1)
        except subprocess.CalledProcessError:
            logging.info('Invalid disk '.format(disk_dev))
            current_disk_valid = False
        except Exception as exc:
            logging.warning('Disk read error {} dev {}'.format(exc, disk_dev))
            current_disk_valid = False

def read_hddparm():
    output = cStringIO.StringIO()
    disk_letter='a'
    current_disk_valid = True
    disk_dev=''
    while current_disk_valid:
        try:
            disk_dev=constant.DISK_DEV_MAIN + disk_letter
            hddparm_out = subprocess.check_output('hdparm -C '+ disk_dev, stderr=subprocess.STDOUT)
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
                    print 'Power Status is {}'.format(status)
            disk_letter = chr(ord(disk_letter) + 1)
        except subprocess.CalledProcessError:
            logging.info('Invalid disk '.format(disk_dev))
            current_disk_valid = False
        except Exception as exc:
            logging.critical('Disk read error {} disk was {}'.format(exc.message, disk_dev))
            current_disk_valid = False

def init():
    pass

def thread_run():
    read_all_hdd_smart()
    read_hddparm()
    pass