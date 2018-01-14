import subprocess
import os
#from collections import namedtuple
from recordtype import recordtype
import sudo_usb
try:
    from main.logger_helper import L
except Exception:
    class L:
        class l:
            @staticmethod
            def info(msg): print msg
            @staticmethod
            def warning(msg): print msg
            @staticmethod
            def error(msg): print msg


__author__ = 'Dan Cristian<dan.cristian@gmail.com>'

Camera = recordtype('Camera', 'name longname devpath audio bus device vendor prod')
_v4l_root = '/dev/v4l/by-id/'


#**** List of CAPTURE Hardware Devices ****
#card 0: C525 [HD Webcam C525], device 0: USB Audio [USB Audio]
#  Subdevices: 1/1
#  Subdevice #0: subdevice #0
#card 1: U0x46d0x81b [USB Device 0x46d:0x81b], device 0: USB Audio [USB Audio]
#  Subdevices: 1/1
#  Subdevice #0: subdevice #0
def _get_usb_audio(camera):
    res = None
    try:
        rec = subprocess.check_output(['arecord', '-l']).split('\n')
        for line in rec:
            if 'card' in line and ', device' in line:
                found = False
                atoms = line.split(',')
                #if len(atoms) > 1:
                if camera.name in atoms[0]:
                    found = True
                else:
                    # try second detect method by vendor/prod id
                    vendor = camera.vendor
                    prod = camera.prod
                    if vendor[0] == '0':
                        vendor = '0x' + vendor[1:]
                    if prod[0] == '0':
                        prod = '0x' + prod[1:]
                    if vendor in atoms[0] and prod in atoms[0]:
                        found = True
                if found:
                    hw_card = atoms[0].split(':')[0].split('card ')[1]
                    hw_dev = atoms[1].split(':')[0].split(' device ')[1]
                    res = '{},{}'.format(hw_card, hw_dev)
                    L.l.info("Found audio card {} for camera {}".format(res, camera.name))
                    break
                else:
                    #L.l.info("Could not map camera {} to audio record entry {}".format(camera.name, line))
                    pass
    except Exception, ex:
        L.l.info("Got error when looking for audio interface, ex={}".format(ex))
    camera.audio = res
    return res


#Bus 001 Device 011: ID 046d:0826 Logitech, Inc. HD Webcam C525
#Bus 001 Device 013: ID 19d2:0016 ZTE WCDMA Technologies MSM
#Bus 001 Device 010: ID 05a3:9520 ARC International
#Bus 001 Device 009: ID 046d:081b Logitech, Inc. Webcam C310
#Bus 001 Device 003: ID 0424:ec00 Standard Microsystems Corp. SMSC9512/9514 Fast Ethernet Adapter
#Bus 001 Device 002: ID 0424:9514 Standard Microsystems Corp. SMC9514 Hub
#Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
def _set_cam_attrib(camera):
    out = subprocess.check_output(['lsusb']).split('\n')
    for line in out:
        if camera.name in line or (camera.vendor is not None and (camera.vendor in line and camera.prod in line)):
            p = line.split(": ID ")
            b = p[0].split(' Device ')
            camera.bus = b[0].split(' ')[1]
            camera.device = b[1]
            v = p[1].split(' ')[0].split(':')
            camera.vendor = v[0]
            camera.prod = v[1]
            start = p[1].index(' ')
            camera.longname = p[1][start + 1:]
            break
    if camera.vendor is None:
        L.l.info("Could no retrieve details for camera [{}], trying alternate".format(camera))
        if not _set_attrib_alt(camera):
            L.l.warning("Could no retrieve alternate details for camera [{}]".format(camera))
    else:
        camera.audio = _get_usb_audio(camera)


def _set_attrib_alt(camera):
    p1 = subprocess.Popen(['tail', '/sys/devices/platform/soc/*/*/*/*/product'], stdout=subprocess.PIPE)
    p2 = subprocess.Popen(['grep', '-B', '1', camera.name], stdin=p1.stdout, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    p1.stdout.close()
    out, err = p2.communicate()
    lines = out.split('\n')
    res = False
    if len(lines) > 0:
        # ==> /sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.5/product <==
        line = lines[0].replace('==> ', '').replace(' <==', '').replace('product', '').strip()
        vendor_path = line + "/idVendor"
        prod_path = line + "/idProduct"
        if os.path.isfile(vendor_path) and os.path.isfile(prod_path):
            with open(vendor_path, 'r') as f:
                camera.vendor = f.read().replace('\n', '')
            with open(prod_path, 'r') as f:
                camera.prod = f.read().replace('\n', '')
            res = True
    return res


#UVC Camera (046d:081b) (usb-3f980000.usb-1.2):
#        /dev/video1
#HD USB Camera (usb-3f980000.usb-1.3):
#        /dev/video2
#HD Webcam C525 (usb-3f980000.usb-1.5):
#        /dev/video0
def get_usb_camera_list():
    res = {}
    cam_name = None
    camera = None
    out = subprocess.check_output(['v4l2-ctl', '--list-devices']).split('\n')
    for line in out:
        if '/dev' not in line:
            a = line.split(' (usb')
            # save previous cam
            if camera is not None:
                res[camera.name] = camera
            camera = Camera(name=a[0], longname=a[0], devpath=None, audio=None, bus=None, device=None, vendor=None,
                            prod=None)
            # try to detect vendor & prod for nasty cams
            a = camera.name.split(':')
            if len(a) > 1:
                v = a[0].split('(')
                if len(v) > 1:
                    camera.vendor = v[1]
                    p = a[1].split(')')
                    if len(p) > 1:
                        camera.prod = p[0]
        else:
            camera.devpath = line.strip()
            _set_cam_attrib(camera)
            L.l.info("Cam is {}".format(camera))
    # save previous cam
    if camera is not None:
        res[camera.name] = camera
    return res


def reset_usb(dev_name):
    res = False
    if dev_name is None:
        L.l.info('Trying to reset a None name device, ignoring reset attempt')
    else:
        try:
            path = sudo_usb.__file__.replace(".pyc", ".py")
            res = subprocess.check_output(['sudo', 'python', path, dev_name])
            L.l.info('Reset returned {}'.format(res))
            res = True
        except Exception, ex:
            L.l.error("Error for device=[{}] on reset_usb {}".format(dev_name, ex))
    return res


if __name__ == '__main__':
    for cam in get_usb_camera_list().itervalues():
        print cam


# Bus 001 Device 049: ID 046d:081b Logitech, Inc. Webcam C310
# Bus 001 Device 010: ID 046d:0826 Logitech, Inc. HD Webcam C525
# Bus 001 Device 019: ID 05a3:9520 ARC International
#def get_usb_camera_name():
#    vendor, prod = _get_first_usb_video_dev_id()
#    camera_name = None
#    if vendor is not None:
#        out = subprocess.check_output(['lsusb']).split('\n')
#        for line in out:
#            if vendor in line and prod in line:
#                p = line.split(vendor + ":")
#                start = p[1].index(' ')
#                camera_name = p[1][start + 1:]
#                break
#    return camera_name

#def _get_usb_dev_root(dev_name):
#    process = subprocess.Popen(['tail /sys/devices/platform/soc/*/*/*/*/product'],
#                               stdout=subprocess.PIPE, shell=True)
#    prev_line = None
#    while True:
#        output = process.stdout.readline()
#        if output == '' and process.poll() is not None:
#            break
#        if output:
#            if dev_name in output:
#                break
#            else:
#                prev_line = output
#    rc = process.poll()
#    if prev_line is not None:
#        # ==> /sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.5/product <==
#        # HD Webcam C525
#        prev_line = prev_line.replace('==> ', '').replace(' <==', '').replace('product', '').strip()
#        # /sys/devices/platform/soc/3f980000.usb/usb1/1-1/1-1.5/
#    return prev_line

# /dev/v4l/by-id/usb-046d_081b_5CB759A0-video-index0
# /dev/v4l/by-id/usb-046d_HD_Webcam_C525_1B0A4790-video-index0
# /dev/v4l/by-id/usb-HD_Camera_Manufacturer_HD_USB_Camera-video-index0
#def _get_first_usb_video_dev_id():
#    vendor = None
#    prod = None
#    if os.path.exists(_v4l_root):
#        for filename in os.listdir(_v4l_root):
#            if 'video' in filename:
#                p = filename.split('usb-')
#                if len(p) > 1:
#                    p = p[1].split('_')
#                    vendor = p[0]
#                    prod = p[1]
#                    break
#    return vendor, prod


#def get_usb_video_dev(cam_name):
#    res = None
#    if os.path.exists(_v4l_root):
#        for filename in os.listdir(_v4l_root):
#            if 'video' in filename:
#                res = _v4l_root + filename
#                L.l.info("Found usb cam at {}".format(res))
#                break
#        return res
#    else:
#        #L.l.info('No v4l folder, probably no usb vide device yet available')
#        return None


# card 1: C525 [HD Webcam C525], device 0: USB Audio [USB Audio]
# card 1: U0x46d0x81b [USB Device 0x46d:0x81b], device 0: USB Audio [USB Audio]

