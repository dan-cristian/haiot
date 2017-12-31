import subprocess
import os
import sudo_usb
from main.logger_helper import Log
#import shlex

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


def _get_usb_dev_root(dev_name):
    process = subprocess.Popen(['tail /sys/devices/platform/soc/*/*/*/*/product'],
                               stdout=subprocess.PIPE, shell=True)
    prev_line = None
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            if dev_name in output:
                break
            else:
                prev_line = output
    rc = process.poll()
    if prev_line is not None:
        # ==> /sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.5/product <==
        # HD Webcam C525
        prev_line = prev_line.replace('==> ', '').replace(' <==', '').replace('product', '').strip()
        # /sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.5/
    return prev_line


def get_usb_dev(dev_name):
    res = None
    root = '/dev/v4l/by-id/'
    if os.path.exists(root):
        for filename in os.listdir(root):
            if dev_name in filename:
                res = root + filename
                Log.logger.info("Found usb cam at {}".format(res))
                break
        return res
    else:
        Log.logger.info('No v4l folder, probably no usb vide device yet available')
        return None


# card 1: C525 [HD Webcam C525], device 0: USB Audio [USB Audio]
def get_usb_audio(dev_name):
    res = None
    try:
        rec = subprocess.check_output(['arecord', '-l']).split('\n')
        for line in rec:
            if len(line) > 1:
                atoms = line.split(',')
                if len(atoms) > 1:
                    if dev_name in atoms[0]:
                        hw_card = atoms[0].split(':')[0].split('card ')[1]
                        hw_dev = atoms[1].split(':')[0].split(' device ')[1]
                        res = '{},{}'.format(hw_card, hw_dev)
                        Log.logger.info("Found audio card {}".format(res))
                        break
    except Exception, ex:
        Log.logger.info("Got error when looking for audio interface, ex={}".format(ex))
    return res


def reset_usb(dev_name):
    path = sudo_usb.__file__.replace(".pyc", ".py")
    res = subprocess.check_output(['sudo', 'python', path, dev_name])
    Log.logger.info('Reset returned {}'.format(res))


if __name__ == '__main__':
    Log.logger.info(_get_usb_dev_root('C525'))
    Log.logger.info(get_usb_dev('C525'))
    reset_usb('C525')

