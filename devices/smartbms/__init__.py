import socket
import threading
import gatt
import json
import sys
import time


class AnyDevice(gatt.Device):
    def connect(self):
        print("[%s] Connecting" % (self.mac_address))
        self.event = threading.Event()
        super().connect()

    def connect_succeeded(self):
        super().connect_succeeded()
        print("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        print("[%s] Disconnected" % (self.mac_address))

    def services_resolved(self):
        super().services_resolved()

        device_information_service = next(
            s for s in self.services
            if s.uuid == '0000ff00-0000-1000-8000-00805f9b34fb')

        print("Device info service is {}".format(device_information_service))

        self.bms_read_characteristic = next(
            c for c in device_information_service.characteristics
            if c.uuid == '0000ff01-0000-1000-8000-00805f9b34fb')

        print("Bms read characteristic is {}".format(self.bms_read_characteristic))

        self.bms_write_characteristic = next(
            c for c in device_information_service.characteristics
            if c.uuid == '0000ff02-0000-1000-8000-00805f9b34fb')

        print("Bms write characteristic is {}".format(self.bms_write_characteristic))

        # print("BMS found")
        self.bms_read_characteristic.enable_notifications()

    def characteristic_enable_notifications_succeeded(self, characteristic):
        super().characteristic_enable_notifications_succeeded(characteristic)
        print("Notifications enabled")
        self.response = bytearray()
        self.rawdat = {}
        self.get_voltages = False
        self.bms_write_characteristic.write_value(status_cmd)

    def request_bms_data(self, request):
        print("BMS write data {}".format(request))
        self.response = bytearray()
        self.event.clear()
        self.bms_write_characteristic.write_value(request)

    def characteristic_enable_notifications_failed(self, characteristic, error):
        super.characteristic_enable_notifications_failed(characteristic, error)
        print("BMS notification failed:", error)

    def characteristic_value_updated(self, characteristic, value):
        print("BMS answering: {}".format(value))
        self.response += value
        if self.response.endswith(b'w'):
            print("BMS answer:", self.response.hex())
            self.response = self.response[4:]
            if self.get_voltages:
                print("Read voltages")
                packVolts = 0
                for i in range(int(len(self.response) / 2) - 1):
                    cell = int.from_bytes(self.response[i * 2:i * 2 + 2], byteorder='big') / 1000
                    volt_name = 'V{0:0=2}'.format(i + 1)
                    self.rawdat[volt_name] = cell
                    print("Volt {}={}".format(volt_name, cell))
                    packVolts += cell

                # + self.rawdat['V{0:0=2}'.format(i)]
                self.rawdat['Vbat'] = packVolts
                self.rawdat['P'] = round(self.rawdat['Vbat'] * self.rawdat['Ibat'], 1)
                self.rawdat['State'] = int.from_bytes(self.response[16:18], byteorder='big', signed=True)
                print(
                    "Capacity: {capacity}% ({Ah_remaining} of {Ah_full}Ah)\nPower: {power}W ({I}Ah)\nTemperature: {temp}°C\nCycles: {cycles}".format(
                        capacity=self.rawdat['Ah_percent'],
                        Ah_remaining=self.rawdat['Ah_remaining'],
                        Ah_full=self.rawdat['Ah_full'],
                        power=self.rawdat['P'],
                        I=self.rawdat['Ibat'],
                        temp=self.rawdat['T1'],
                        cycles=self.rawdat['Cycles'],
                    ))
                # self.manager.stop()
                self.response = bytearray()
                self.get_voltages = False
            else:
                print("Read alternate")
                self.rawdat['packV'] = int.from_bytes(self.response[0:2], byteorder='big', signed=True) / 100.0
                self.rawdat['Ibat'] = int.from_bytes(self.response[2:4], byteorder='big', signed=True) / 100.0
                self.rawdat['Bal'] = int.from_bytes(self.response[12:14], byteorder='big', signed=False)
                self.rawdat['Ah_remaining'] = int.from_bytes(self.response[4:6], byteorder='big', signed=True) / 100
                self.rawdat['Ah_full'] = int.from_bytes(self.response[6:8], byteorder='big', signed=True) / 100
                self.rawdat['Ah_percent'] = round(self.rawdat['Ah_remaining'] / self.rawdat['Ah_full'] * 100, 2)
                self.rawdat['Cycles'] = int.from_bytes(self.response[8:10], byteorder='big', signed=True)

                for ti in range(int.from_bytes(self.response[22:23], 'big')):  # read temperatures
                    temp_name = 'T{0:0=1}'.format(ti + 1)
                    temp_val = (int.from_bytes(self.response[23 + ti * 2:ti * 2 + 25], 'big') - 2731) / 10
                    self.rawdat[temp_name] = temp_val
                    print("Temp {}={}".format(temp_name, temp_val))

                # print("BMS request voltages")
                print("raw=".format(self.rawdat))
                self.get_voltages = True
                self.response = bytearray()
                self.bms_write_characteristic.write_value(bytes([0xDD, 0xA5, 0x04, 0x00, 0xFF, 0xFC, 0x77]))
            #self.event.set()

    def characteristic_write_value_failed(self, characteristic, error):
        print("BMS write failed:", error)

    def wait(self):
        return self.event.wait(timeout=5)


def bluetooth_manager_thread(manager):
    print("Running BT manager")
    manager.run()


bluetooth_device = "A4:C1:38:C6:30:57"
status_cmd = bytes([0xDD, 0xA5, 0x03, 0x00, 0xFF, 0xFD, 0x77])

manager = gatt.DeviceManager(adapter_name='hci0')
bluetooth_manager = threading.Thread(target=bluetooth_manager_thread, args=[manager, ])
bluetooth_manager.start()
device = AnyDevice(mac_address=bluetooth_device, manager=manager)
device.connect()
time.sleep(2)
print('BMS server for {} started'.format(bluetooth_device))

# device.request_bms_data(bytes([0xDD, 0xA5, 0x03, 0x00, 0xFF, 0xFD, 0x77]))
# device.request_bms_data(bytes([0xDD, 0xA5, 0x05, 0x00, 0xFF, 0xFB, 0x77]))
# device.request_bms_data(bytes([0xDB, 0xDB, 0x00, 0x00, 0x00, 0x00]))
# device.request_bms_data(bytes([0x5A, 0x5A, 0x00, 0x00, 0x00, 0x00]))
for i in range(0, 5):
    time.sleep(30)
    device.bms_write_characteristic.write_value(status_cmd)
device.disconnect()
