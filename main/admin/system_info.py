__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

from main import logger
from collections import OrderedDict
from common import constant

description_system_type = None
description_machine = None
description_model_name = None
description_hardware = None
description_revision = None
description_cpu_model = None

def init():
    if constant.OS in constant.OS_LINUX:
        sysinfo = OrderedDict()
        with open('/proc/cpuinfo') as f:
            for line in f:
                try:
                    #beaglebone
                    #model name      : ARMv7 Processor rev 2 (v7l)
                    #Hardware        : Generic AM33XX (Flattened Device Tree)

                    #router tplink openwrt
                    #system type             : Atheros AR9344 rev 2
                    #machine                 : TP-LINK TL-WDR3600/4300/4310
                    #cpu model               : MIPS 74Kc V4.12

                    #raspberry
                    #model name      : ARMv6-compatible processor rev 7 (v6l)
                    #Hardware        : BCM2708
                    #Revision        : 000e

                    #debian Intel
                    #model name      : Intel(R) Celeron(R) CPU 1037U @ 1.80GHz
                    words = line.split(':')
                    sysinfo[words[0].strip()] = words[1].strip()
                except Exception, ex:
                    logger.warning('get sysinfo line split error [{}] line [{}]'.format(ex, line))
            global description_model_name, description_machine, description_system_type, description_hardware, \
                description_revision, description_cpu_model
            if 'model name' in sysinfo:     description_model_name = sysinfo['model name']
            if 'machine' in sysinfo:        description_machine = sysinfo['machine']
            if 'system type' in sysinfo:    description_system_type = sysinfo['system type']
            if 'hardware' in sysinfo:       description_hardware = sysinfo['hardware']
            if 'revision' in sysinfo:       description_revision = sysinfo['revision']
            if 'cpu model' in sysinfo:      description_cpu_model = sysinfo['cpu model']

            if description_hardware and 'AM33XX' in description_hardware:
                constant.HOST_MACHINE_TYPE = constant.MACHINE_TYPE_BEAGLEBONE
            if description_hardware and 'BCM2708' in description_hardware:
                constant.HOST_MACHINE_TYPE = constant.MACHINE_TYPE_RASPBERRY
            if description_system_type and 'Atheros' in description_system_type:
                constant.HOST_MACHINE_TYPE = constant.MACHINE_TYPE_OPENWRT
            if description_model_name and 'Intel' in description_model_name:
                constant.HOST_MACHINE_TYPE = constant.MACHINE_TYPE_INTEL_LINUX
