import subprocess
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


def _get_usb_dev(dev_name):
    process = subprocess.Popen(['ls /dev/v4l/by-id/*'],
                               stdout=subprocess.PIPE, shell=True)
    output = None
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            if dev_name in output:
                break
    rc = process.poll()
    if output is not None:
        # /dev/v4l/by-id/usb-046d_HD_Webcam_C525_1B0A4790-video-index0
        output = output.strip()
        # /sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.5/
    return output


if __name__ == '__main__':
    print _get_usb_dev_root('C525')
    print _get_usb_dev('C525')


