__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

from collections import OrderedDict

from main.logger_helper import L
from common import Constant

description_system_type = None
description_machine = None
description_model_name = None
description_hardware = None
description_revision = None
description_cpu_model = None


def init():
    if Constant.IS_OS_LINUX():
        sysinfo = OrderedDict()
        with open('/proc/cpuinfo') as f:
            for line in f:
                try:
                    # beaglebone
                    # model name      : ARMv7 Processor rev 2 (v7l)
                    # Hardware        : Generic AM33XX (Flattened Device Tree)

                    # router tplink openwrt
                    # system type             : Atheros AR9344 rev 2
                    # machine                 : TP-LINK TL-WDR3600/4300/4310
                    # cpu model               : MIPS 74Kc V4.12

                    # raspberry
                    # model name      : ARMv6-compatible processor rev 7 (v6l)
                    # Hardware        : BCM2708
                    # Revision        : 000e

                    # raspberry b+
                    # model name      : ARMv7 Processor rev 5 (v7l)
                    # Hardware        : BCM2709

                    # debian Intel
                    # model name      : Intel(R) Celeron(R) CPU 1037U @ 1.80GHz
                    words = line.split(':')
                    sysinfo[words[0].strip().lower()] = words[1].strip()
                except Exception, ex:
                    L.l.debug('get sysinfo line split error [{}] line [{}]'.format(ex, line))
            global description_model_name, description_machine, description_system_type, description_hardware, \
                description_revision, description_cpu_model
            if 'model name' in sysinfo:     description_model_name = sysinfo['model name']
            if 'machine' in sysinfo:        description_machine = sysinfo['machine']
            if 'system type' in sysinfo:    description_system_type = sysinfo['system type']
            if 'hardware' in sysinfo:       description_hardware = sysinfo['hardware']
            if 'revision' in sysinfo:       description_revision = sysinfo['revision']
            if 'cpu model' in sysinfo:      description_cpu_model = sysinfo['cpu model']

            if description_hardware and 'AM33XX' in description_hardware:
                Constant.HOST_MACHINE_TYPE = Constant.MACHINE_TYPE_BEAGLEBONE
                Constant.IS_MACHINE_BEAGLEBONE = True
            elif description_hardware and 'BCM2' in description_hardware:
                Constant.HOST_MACHINE_TYPE = Constant.MACHINE_TYPE_RASPBERRY
                Constant.IS_MACHINE_RASPBERRYPI = True
            if description_system_type and 'Atheros' in description_system_type:
                Constant.HOST_MACHINE_TYPE = Constant.MACHINE_TYPE_OPENWRT
                Constant.IS_MACHINE_OPENWRT = True
            if description_model_name and 'Intel' in description_model_name:
                Constant.HOST_MACHINE_TYPE = Constant.MACHINE_TYPE_INTEL_LINUX
                Constant.IS_MACHINE_INTEL = True
        if Constant.HOST_MACHINE_TYPE == Constant.NOT_INIT:
            L.l.error("Unknown machine type")
    elif Constant.IS_OS_WINDOWS():
        import platform
        Constant.HOST_MACHINE_TYPE = platform.machine()
    else:
        L.l.warning("Unknown OS on system init")

