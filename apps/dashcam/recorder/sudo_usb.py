import os
import subprocess
import sys
try:
    import fcntl
except Exception:
    pass


def _get_usb_dev_info(dev_name):
    rec = subprocess.check_output(['lsusb']).split('\n')
    vendor = product = bus = device = None
    for line in rec:
        if dev_name in line:
            #Bus 001 Device 004: ID 046d:0826 Logitech, Inc. HD Webcam C525
            #Bus 001 Device 049: ID 046d:081b Logitech, Inc. Webcam C310
            #Bus 001 Device 019: ID 05a3:9520 ARC International
            parts = line.split()
            bus = parts[1]
            device = parts[3][:3]
            atoms = line.split(' ID ')
            if len(atoms) > 1:
                ven_prod = atoms[1].split(' ')[0].split(':')
                vendor = ven_prod[0]
                product = ven_prod[1]
                print("Vendor:Product for {} is {}:{}".format(dev_name, vendor, product))
                break
    return vendor, product, bus, device, rec


def sudo_send_usb_reset(dev_name):
    # https://gist.github.com/PaulFurtado/fce98aef890469f34d51
    # Equivalent of the _IO('U', 20) constant in the linux kernel.
    USBDEVFS_RESET = ord('U') << (4 * 2) | 20
    """
            Sends the USBDEVFS_RESET IOCTL to a USB device.

            dev_path - The devfs path to the USB device (under /dev/bus/usb/)
                       See get_teensy for example of how to obtain this.
    """
    vendor, product, bus, device, output = _get_usb_dev_info(dev_name)
    if bus is not None and device is not None:
        dev_path = '/dev/bus/usb/%s/%s' % (bus, device)
        print('Sending usb reset to {}'.format(dev_path))
        fd = os.open(dev_path, os.O_WRONLY)
        try:
            fcntl.ioctl(fd, USBDEVFS_RESET, 0)
            print('Usb reset complete')
            res = True
        finally:
            os.close(fd)
    else:
        print('Cannot find usb bus/device for [{}], reset failed'.format(dev_name))
        print('Ouput was:'.format(output))
        res = False
    return res


def sudo_reload_uvc_module():
    try:
        res = subprocess.check_output(['rmmod', 'uvcvideo'])
        print('Module remove returned [{}]'.format(res))
    except Exception, ex:
        print('Module remove error, ex={}'.format(ex))
    try:
        res = subprocess.check_output(['modprobe', 'uvcvideo'])
        print('Module load returned [{}]'.format(res))
    except Exception, ex:
        print('Module load error, ex={}'.format(ex))


if __name__ == '__main__':
    if os.getuid() != 0:
        print('Script must run as root/sudo for usb & mod actions')
    else:
        if len(sys.argv) == 2:
            if sudo_send_usb_reset(sys.argv[1]):
                sudo_reload_uvc_module()
        else:
            print('Unexpected number of arguments, only one needed: <usb dev name>')
