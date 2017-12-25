import subprocess
import shlex
__author__ = 'Dan Cristian<dan.cristian@gmail.com>'


def _get_usb_dev_root(dev_name):
    cmd = 'tail /sys/devices/platform/soc/*/*/*/*/product'
    process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, shell=True)
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
        prev_line = prev_line.replace('==> ', '').replace(' <==', '')
    return prev_line


if __name__ == '__main__':
    print _get_usb_dev_root('C525')



