#!/usr/bin/python

""" radon_reader.py: RadonEye RD200 (Bluetooth/BLE) Reader """

# https://github.com/ceandre/radonreader

__progname__ = "RadonEye RD200 (Bluetooth/BLE) Reader"
__version__ = "0.3.8"
__author__ = "Carlos Andre"
__email__ = "candrecn at hotmail dot com"
__date__ = "2019-10-20"

import argparse, struct, time, re, json
# import paho.mqtt.client as mqtt

from bluepy import btle
from time import sleep
from random import randint
import threading
import prctl
from main.logger_helper import L
from main import thread_pool
from storage.model import m


class P:
    initialised = False
    radoneye_id = 0  # Airsensor record id

    def __init__(self):
        pass


def GetRadonValue():
    try:
        sensor = m.AirSensor.find_one({m.AirSensor.id: P.radoneye_id})
        if sensor is not None:
            DevBT = btle.Peripheral(sensor.address, "random")
            RadonEye = btle.UUID("00001523-1212-efde-1523-785feabcd123")
            RadonEyeService = DevBT.getServiceByUUID(RadonEye)

            # Write 0x50 to 00001524-1212-efde-1523-785feabcd123
            uuidWrite = btle.UUID("00001524-1212-efde-1523-785feabcd123")
            RadonEyeWrite = RadonEyeService.getCharacteristics(uuidWrite)[0]
            RadonEyeWrite.write(bytes("\x50", encoding='utf8'))

            # Read from 3rd to 6th byte of 00001525-1212-efde-1523-785feabcd123
            uuidRead = btle.UUID("00001525-1212-efde-1523-785feabcd123")
            RadonEyeValue = RadonEyeService.getCharacteristics(uuidRead)[0]
            RadonValue = RadonEyeValue.read()
            RadonValue = struct.unpack('<f', RadonValue[2:6])[0]

            DevBT.disconnect()

            # Raise exception (will try get Radon value from RadonEye again) if received a very
            # high radon value or lower than 0.
            # Maybe a bug on RD200 or Python BLE Lib?!
            if (RadonValue > 1000) or (RadonValue < 0):
                raise Exception("Very strange radon value. Debugging needed.")
            #if args.becquerel:
            Unit = "Bq/m3"
            RadonValue = (RadonValue * 37)
            #else:
            #    Unit = "pCi/L"
            sensor.radon = RadonValue
            sensor.save_changed_fields(broadcast=True, persist=True)
            L.l.info("Read radoneye {} value {} {}".format(sensor.address, RadonValue, Unit))
        else:
            L.l.erro("Cannot find radoneye record with id={} in config".format(P.radoneye_id))
    except Exception as ex:
        L.l.warning("Exception reading radon value {}".format(ex))


def thread_run():
    prctl.set_name("Radoneye")
    threading.current_thread().name = "Radoneye"
    GetRadonValue()
    prctl.set_name("idle")
    threading.current_thread().name = "idle"
    return 'Processed Radoneye'


def unload():
    L.l.info('Radoneye module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('Radoneye module initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=120)
    P.initialised = True
    # dispatcher.connect(_init_recovery, signal=Constant.SIGNAL_USB_DEVICE_CHANGE, sender=dispatcher.Any)
    # dispatcher.send(Constant.SIGNAL_USB_DEVICE_CHANGE)
