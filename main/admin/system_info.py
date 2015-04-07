__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import logging
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

                    sysinfo[line.split(':')[0]] = line.split(':')[1].strip()
                except Exception, ex:
                    logging.warning('get sysinfo line split error {} line {}'.format(ex, line))
            global description_model_name, description_machine, description_system_type, description_hardware, \
                description_revision, description_cpu_model
            if 'model name' in sysinfo:     description_model_name = sysinfo['model name']
            if 'machine' in sysinfo:        description_machine = sysinfo['machine']
            if 'system type' in sysinfo:    description_system_type = sysinfo['system type']
            if 'hardware' in sysinfo:       description_hardware = sysinfo['hardware']
            if 'revision' in sysinfo:       description_revision = sysinfo['revision']
            if 'cpu model' in sysinfo:      description_cpu_model = sysinfo['cpu model']

            if 'AM33XX' in description_hardware:
                constant.HOST_MACHINE_TYPE = constant.MACHINE_TYPE_BEAGLEBONE
            if 'BCM2708' in description_hardware:
                constant.HOST_MACHINE_TYPE = constant.MACHINE_TYPE_RASPBERRY
            if 'Atheros' in description_system_type:
                constant.HOST_MACHINE_TYPE = constant.MACHINE_TYPE_OPENWRT