# https://github.com/micropython/micropython/issues/2352

import esp
from flashbdev import bdev
import machine
import ujson
import mqtt

ADC_MODE_VCC = 255
ADC_MODE_ADC = 0
rtc = machine.RTC()


class rtc_storage:
    mqtts = 0
    mqttp = 0
    closed = 1
    angle = 0


def set_adc_mode(mode):
    sector_size = bdev.SEC_SIZE
    flash_size = esp.flash_size()  # device dependent
    init_sector = int(flash_size / sector_size - 4)
    data = bytearray(esp.flash_read(init_sector * sector_size, sector_size))
    if data[107] == mode:
        return  # flash is already correct; nothing to do
    else:
        data[107] = mode  # re-write flash
        esp.flash_erase(init_sector)
        esp.flash_write(init_sector * sector_size, data)
        print("ADC mode changed in flash; restart to use it!")
        return


def init_deep_sleep(sleep_sec=60):
    # configure RTC.ALARM0 to be able to wake the device
    rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)
    # set RTC.ALARM0 to fire after 60 seconds (waking the device)
    rtc.alarm(rtc.ALARM0, sleep_sec * 1000)
    save_rtc()
    # mqtt.disconnect()
    print("Entering deep sleep")
    machine.deepsleep()


def save_rtc():
    try:
        stor_dict = rtc_storage.__dict__.copy()  # needs a copy otherwise pop won't work
        # print("Saving dict {}".format(stor_dict))
        stor_dict.pop("__module__", None)
        stor_dict.pop("__qualname__", None)
        json = ujson.dumps(stor_dict)
        print("Saving to rtc: {}".format(json))
        rtc.memory(json)
    except Exception as ex:
        print("Unable to save rtc, ex={}".format(ex))


def read_rtc():
    mem = rtc.memory()
    print("Reading from rtc: {}".format(mem))
    if mem is not None and len(mem) > 0:
        mems = str(mem, "utf-8")  # replace("b'{", "{").replace("}'", "}")
        try:
            obj = ujson.loads(mems)
            if type(obj) is dict:
                for key in obj.keys():
                    setattr(rtc_storage, key, obj[key])
                # P.closed = int(mem)
                print("Read rtc memory closed={} sub={} pub={}".format(
                    rtc_storage.closed, rtc_storage.mqtts, rtc_storage.mqttp))
            else:
                print("Unexpected rtc object type {}".format(obj))
        except ValueError as ve:
            print("Unable to convert from rtc json: {}, json was:{}".format(ve, mems))


def publish_state():
    vcc = machine.ADC(1).read()
    # send current state to mqtt
    mqtt.publish('{{"vcc": {},"angle": {}, "mqttp": {}}}'.format(
        vcc, rtc_storage.angle, rtc_storage.mqttp))
