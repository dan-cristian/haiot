import time
import threading
import prctl
import gatt
from main.logger_helper import L
from main import thread_pool
from storage.model import m
from common import Constant
import binascii

__author__ = 'Dan Cristian<dan.cristian@gmail.com>'
# reused: https://github.com/stefanandres/bms-monitoring-stack
# https://blog.ja-ke.tech/2020/02/07/ltt-power-bms-chinese-protocol.html
# https://github.com/simat/BatteryMonitor/wiki/Generic-Chinese-Bluetooth-BMS-communication-protocol
# https://mono.software/2018/11/15/multiple-bms-monitor/

# gatt/dbus install issues:
# https://github.com/getsenic/gatt-python/issues/31
# https://stackoverflow.com/questions/61285415/no-package-dbus-1-found

# gi.repository fix
# https://pygobject.readthedocs.io/en/latest/getting_started.html

# other interfacing methods
# https://secondlifestorage.com/index.php?threads/jdb-xiaoxiang-bms-tool.10329/

# set BT to compat
# sudo nano /lib/systemd/system/bluetooth.service
# ExecStart=/usr/lib/bluetooth/bluetoothd --compat --noplugin=sap
# ExecStartPost=/usr/bin/sdptool add SP
# sudo systemctl daemon-reload
# sudo systemctl restart bluetooth


# init BT
# sudo bluetoothctl
# scan on
# trust xx:xx
# connect xx:xx

class P:
    initialised = False

    status_cmd = bytes([0xDD, 0xA5, 0x03, 0x00, 0xFF, 0xFD, 0x77])
    voltage_cmd = bytes([0xDD, 0xA5, 0x04, 0x00, 0xFF, 0xFC, 0x77])
    status_old = bytes([0xDB, 0xDB, 0x00, 0x00, 0x00, 0x00])
    manager = None
    bluetooth_manager = None
    bt_device = None
    processing = False


class AnyDevice(gatt.Device):
    bms_rec = None
    response = None
    event = None
    bms_read_characteristic = None
    bms_write_characteristic = None
    rawdat = None
    get_voltages = False

    def connect(self, bms_rec):
        L.l.info("Connecting {} {}".format(self.mac_address, bms_rec.name))
        self.bms_rec = bms_rec
        self.event = threading.Event()
        super().connect()
        L.l.info("Connecting done: {}".format(self.mac_address))

    def connect_succeeded(self):
        super().connect_succeeded()
        L.l.info("[%s] Connected" % self.mac_address)

    def connect_failed(self, error):
        super().connect_failed(error)
        L.l.warning("[%s] Connection failed: %s" % (self.mac_address, str(error)))
        self.disconnect()  # needed?

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        L.l.info("[%s] Disconnected ok" % self.mac_address)

    def services_resolved(self):
        L.l.info("BT services resolved")
        super().services_resolved()

        device_information_service = next(
            s for s in self.services
            if s.uuid == '0000ff00-0000-1000-8000-00805f9b34fb')

        self.bms_read_characteristic = next(
            c for c in device_information_service.characteristics
            if c.uuid == '0000ff01-0000-1000-8000-00805f9b34fb')

        self.bms_write_characteristic = next(
            c for c in device_information_service.characteristics
            if c.uuid == '0000ff02-0000-1000-8000-00805f9b34fb')

        L.l.info("BMS found")
        self.bms_read_characteristic.enable_notifications()  # enabled=True)

    def characteristic_enable_notifications_succeeded(self, characteristic):
        super().characteristic_enable_notifications_succeeded(characteristic)
        L.l.info("Notifications enabled")
        self.clean_vars()
        self.bms_write_characteristic.write_value(P.status_cmd)

    def request_bms_data(self, request):
        L.l.info("BMS write data {}".format(request))
        self.response = bytearray()
        self.event.clear()
        self.bms_write_characteristic.write_value(request)

    def characteristic_enable_notifications_failed(self, characteristic, error):
        super().characteristic_enable_notifications_failed(characteristic, error)
        L.l.info("BMS notification failed:", error)

    def characteristic_value_updated(self, characteristic, value):
        assert isinstance(self.bms_rec, m.Bms)
        L.l.info("BMS answering:{}".format(value))
        self.response += value
        if self.response.endswith(b'w'):
            # L.l.info("BMS answer:", self.response)
            data = self.response[3:len(self.response) - 3]
            check = self.response[-3:-1]
            valid_record = crc_check(data, check)
            if valid_record:
                self.response = self.response[4:]
                if self.get_voltages:
                    # dd0400100cf30cf60cf10cf20cfa0cf60cf70cf8f7e577
                    # print("Read voltages")
                    pack_volts = 0
                    for i in range(int(len(self.response) / 2) - 1):
                        cell_voltage = int.from_bytes(self.response[i * 2:i * 2 + 2], byteorder='big') / 1000
                        volt_name = 'v{0:0=2}'.format(i + 1)
                        self.rawdat[volt_name] = cell_voltage
                        setattr(self.bms_rec, volt_name, cell_voltage)
                        print("Volt {}={}".format(volt_name, cell_voltage))
                        pack_volts += cell_voltage
                    self.rawdat['Vbat'] = pack_volts
                    self.bms_rec.voltage_cells = pack_volts
                    self.rawdat['P'] = round(self.rawdat['Vbat'] * self.rawdat['Ibat'], 1)
                    self.bms_rec.power = self.rawdat['P']
                    self.rawdat['State'] = int.from_bytes(self.response[16:18], byteorder='big', signed=True)
                    print(
                        "Capacity: {capacity}% ({Ah_remaining} of {Ah_full}Ah)\nPower: {power}W ({I}Ah)\nTemperature: {temp}°C\nCycles: {cycles}".format(
                            capacity=self.rawdat['Ah_percent'],
                            Ah_remaining=self.rawdat['Ah_remaining'],
                            Ah_full=self.rawdat['Ah_full'],
                            power=self.rawdat['P'],
                            I=self.rawdat['Ibat'],
                            temp=self.rawdat['t1'],
                            cycles=self.rawdat['Cycles'],
                        ))
                    # self.manager.stop()
                    self.bms_rec.save_changed_fields(persist=True)
                    self.clean_vars()
                    P.processing = False
                else:
                    # dd03001b0a5dffe416f817700001290700000000000016620308020ada0adbf98777
                    # command  LEN data                                                                              CRC
                    # dd 03 00 1b 0a.5d.ff.e4.16.f8.17.70.00.01.29.07.00.00.00.00.00.00.16.62.03.08.02.0a.da.0a.db. f987 77
                    self.rawdat['packV'] = int.from_bytes(self.response[0:2], byteorder='big', signed=True) / 100.0
                    self.rawdat['Ibat'] = int.from_bytes(self.response[2:4], byteorder='big', signed=True) / 100.0
                    self.rawdat['Bal'] = int.from_bytes(self.response[12:14], byteorder='big', signed=False)
                    self.rawdat['Ah_remaining'] = int.from_bytes(self.response[4:6], byteorder='big', signed=True) / 100
                    self.rawdat['Ah_full'] = int.from_bytes(self.response[6:8], byteorder='big', signed=True) / 100
                    self.rawdat['Ah_percent'] = round(self.rawdat['Ah_remaining'] / self.rawdat['Ah_full'] * 100, 2)
                    self.rawdat['Cycles'] = int.from_bytes(self.response[8:10], byteorder='big', signed=True)

                    if self.rawdat['Ah_full'] < 0:
                        L.l.warning("Invalid Ah capacity range, unexpected as CRC is ok")
                        invalid_record = True

                    for ti in range(int.from_bytes(self.response[22:23], 'big')):  # read temperatures
                        temp_name = 't{0:0=1}'.format(ti + 1)
                        temp_val = (int.from_bytes(self.response[23 + ti * 2:ti * 2 + 25], 'big') - 2731) / 10
                        self.rawdat[temp_name] = temp_val
                        if -30 < temp_val < 500:
                            setattr(self.bms_rec, temp_name, temp_val)
                            # L.l.info("Temp {}={}".format(temp_name, temp_val))
                        else:
                            L.l.warning("Invalid temp range {}={}, unexpected as CRC ok".format(temp_name, temp_val))
                            invalid_record = True

                        self.bms_rec.voltage = self.rawdat['packV']
                        self.bms_rec.current = self.rawdat['Ibat']
                        self.bms_rec.remaining_capacity = self.rawdat['Ah_remaining']
                        self.bms_rec.full_capacity = self.rawdat['Ah_full']
                        self.bms_rec.capacity_percent = self.rawdat['Ah_percent']
                        self.bms_rec.cycles = self.rawdat['Cycles']
                        L.l.info("Saving t1={} t2={}".format(self.bms_rec.t1, self.bms_rec.t2))
                        self.bms_rec.save_changed_fields(persist=True)
                        # print("BMS request voltages")
                        self.get_voltages = True
                        self.response = bytearray()
                        self.bms_write_characteristic.write_value(P.voltage_cmd)
            else:
                L.l.warning("Invalid CRC BMS response detected={}".format(self.response))
                L.l.warning("Response was={}".format(binascii.hexlify(self.response)))
                self.clean_vars()
                P.processing = False

    def characteristic_write_value_failed(self, characteristic, error):
        L.l.error("BMS write failed:", error)

    # unused?
    def wait(self):
        return self.event.wait(timeout=2)

    def clean_vars(self):
        self.response = bytearray()
        self.rawdat = {}
        self.get_voltages = False


def crc_check(data, check):
    crc = 0x10000
    check_int = int.from_bytes(check, byteorder='big', signed=False)
    for i in data:
        crc = crc - int(i)
    if check_int != crc:
        crc_b = crc.to_bytes(2, byteorder='big')
        L.l.warning("Invalid CRC, expected {}/{}, got {}/{}".format(check, check_int, crc_b, crc))
    return check_int == crc


def bluetooth_manager_thread(manager):
    # print("Running BT manager")
    manager.run()


def connect_bt(bms_rec):
    try:
        if P.bt_device is None:
            P.bt_device = AnyDevice(mac_address=bms_rec.mac_address, manager=P.manager)
            L.l.info("BT Connect first time")
            P.processing = True
            P.bt_device.connect(bms_rec)
        else:
            if not P.bt_device.is_connected():
                L.l.info("BT reconnect")
                P.bt_device.connect(bms_rec)
            P.processing = True
            P.bt_device.bms_write_characteristic.write_value(P.status_cmd)

        for i in range(0, 300):
            if P.processing:
                time.sleep(0.2)
            else:
                L.l.info("BT processing done")
                break
        if P.processing:
            L.l.warning("No response from BMS, timeout!")
        if P.bt_device is not None:
            if P.bt_device.is_connected():
                # L.l.info("Disconnecting BT")
                # P.bt_device.disconnect()
                pass
            else:
                L.l.info("BT not connected")
            # P.bluetooth_manager.stop()
            # P.bt_device = None
    except Exception as ex:
        L.l.error("Exception on connect btle, ex={}".format(ex))


def get_status():
    # recs = m.Bms.find()
    # for rec in recs:
    rec = m.Bms.find_one({m.Bms.host_name: Constant.HOST_NAME})
    if rec is not None:
        connect_bt(rec)
        # rec.save_changed_fields(persist=True)
        L.l.info("v={} v1={} t1={}".format(rec.voltage, rec.v01, rec.t1))
    else:
        L.l.warning("No bms config record defined for this host={}".format(Constant.HOST_NAME))


def bms_upsert_listener(record, changed_fields):
    # L.l.info("RECEIVED Bms {} changed={}".format(record, changed_fields))
    assert isinstance(record, m.Bms)
    # if "xxx" in changed_fields and record.xxx is not None:
    #    pass


def thread_run():
    prctl.set_name("bms")
    threading.current_thread().name = "bms"
    get_status()
    prctl.set_name("idle_bms")
    threading.current_thread().name = "idle_bms"
    return 'Processed bms'


def unload():
    L.l.info('BMS module unloading')
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    L.l.info('BMS module initialising')
    thread_pool.add_interval_callable(thread_run, run_interval_second=90)
    m.Bms.add_upsert_listener(bms_upsert_listener)
    P.manager = gatt.DeviceManager(adapter_name='hci0')
    P.bluetooth_manager = threading.Thread(target=bluetooth_manager_thread, args=[P.manager, ])
    P.bluetooth_manager.start()
    P.initialised = True
