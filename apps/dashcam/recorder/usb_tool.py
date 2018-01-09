import subprocess
import os
import sudo_usb
try:
    from main.logger_helper import L
except Exception:
    pass


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


# /dev/v4l/by-id/usb-046d_081b_5CB759A0-video-index0
def _get_first_usb_video_dev_id():
    root = '/dev/v4l/by-id/'
    vendor = None
    prod = None
    if os.path.exists(root):
        for filename in os.listdir(root):
            if 'video' in filename:
                p = filename.split('usb-')
                if len(p) > 1:
                    p = p[0].split('_')
                    vendor = p[0]
                    prod = p[1]
                    break
    return vendor, prod


def get_usb_dev(dev_name):
    res = None
    root = '/dev/v4l/by-id/'
    if os.path.exists(root):
        for filename in os.listdir(root):
            if dev_name in filename:
                res = root + filename
                L.l.info("Found usb cam at {}".format(res))
                break
        return res
    else:
        #L.l.info('No v4l folder, probably no usb vide device yet available')
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
                        L.l.info("Found audio card {}".format(res))
                        break
    except Exception, ex:
        L.l.info("Got error when looking for audio interface, ex={}".format(ex))
    return res


# Bus 001 Device 049: ID 046d:081b Logitech, Inc. Webcam C310
def get_usb_camera_name():
    vendor, prod = _get_first_usb_video_dev_id()
    camera_name = None
    if vendor is not None:
        out = subprocess.check_output(['lsusb']).split('\n')
        for line in out:
            if vendor in line and prod in line:
                p = line.split(prod + " ")
                camera_name = p[1]
                break
    return camera_name


def reset_usb(dev_name):
    try:
        path = sudo_usb.__file__.replace(".pyc", ".py")
        res = subprocess.check_output(['sudo', 'python', path, dev_name])
        L.l.info('Reset returned {}'.format(res))
        return True
    except Exception, ex:
        L.l.error("Error on reset_usb {}".format(ex))
        return False


if __name__ == '__main__':
    #L.l.info(_get_usb_dev_root('C525'))
    #L.l.info(get_usb_dev('C525'))
    #reset_usb('C525')
    cam = get_usb_camera_name()
    print cam

