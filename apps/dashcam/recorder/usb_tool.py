import subprocess
import os
import time
from usb.core import find as finddev
try:
    import fcntl
except Exception:
    pass

#import shlex
__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


def _get_usb_dev_root(dev_name):
    #cmd = 'tail /sys/devices/platform/soc/*/*/*/*/product'
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


def _get_usb_dev_info(dev_name):
    rec = subprocess.check_output(['lsusb']).split('\n')
    vendor = product = bus = device = None
    for line in rec:
        if dev_name in line:
            #Bus 001 Device 004: ID 046d:0826 Logitech, Inc. HD Webcam C525
            parts = line.split()
            bus = parts[1]
            device = parts[3][:3]
            atoms = line.split(' ID ')
            if len(atoms) > 1:
                ven_prod = atoms[1].split(' ')[0].split(':')
                vendor = ven_prod[0]
                product = ven_prod[1]
                print "Vendor:Product for {} is {}:{}".format(dev_name, vendor, product)
                break
    return vendor, product, bus, device


def get_usb_dev(dev_name):
    res = None
    root = '/dev/v4l/by-id/'
    for filename in os.listdir(root):
        if dev_name in filename:
            res = root + filename
            print "Found usb cam at {}".format(res)
            break
    return res


# card 1: C525 [HD Webcam C525], device 0: USB Audio [USB Audio]
def get_usb_audio(dev_name):
    rec = subprocess.check_output(['arecord', '-l']).split('\n')
    res = None
    for line in rec:
        if len(line) > 1:
            atoms = line.split(',')
            if len(atoms) > 1:
                if dev_name in atoms[0]:
                    hw_card = atoms[0].split(':')[0].split('card ')[1]
                    hw_dev = atoms[1].split(':')[0].split(' device ')[1]
                    res = '{},{}'.format(hw_card, hw_dev)
                    print "Found audio card {}".format(res)
                    break
    return res


def recover_usb_video(dev_name):
    # rmmod uvcvideo
    # modprobe uvcvideo

    vendor, product, bus, device = _get_usb_dev_info(dev_name)
    dev = finddev(idVendor=hex(int('0x' + vendor, 16)), idProduct=hex(int('0x' + product, 16)))
    if dev is not None:
        print "Reseting USB {}".format(dev)
        dev.reset()
    else:
        print "USB dev not found for reset"


def send_reset(dev_name):
    # Equivalent of the _IO('U', 20) constant in the linux kernel.
    USBDEVFS_RESET = ord('U') << (4 * 2) | 20
    """
            Sends the USBDEVFS_RESET IOCTL to a USB device.

            dev_path - The devfs path to the USB device (under /dev/bus/usb/)
                       See get_teensy for example of how to obtain this.
    """
    vendor, product, bus, device = _get_usb_dev_info(dev_name)
    dev_path = '/dev/bus/usb/%s/%s' % (bus, device)
    fd = os.open(dev_path, os.O_WRONLY)
    try:
        fcntl.ioctl(fd, USBDEVFS_RESET, 0)
    finally:
        os.close(fd)

if __name__ == '__main__':
    print _get_usb_dev_root('C525')
    print get_usb_dev('C525')
    print "Recover"
    recover_usb_video('C525')
    time.sleep(10)
    print "Reset"
    send_reset('C525')


