import socket
import threading
import gatt
import json
import sys

bind_ip = '0.0.0.0'


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

        print("BMS found")
        self.bms_read_characteristic.enable_notifications()

    def characteristic_enable_notifications_succeeded(self, characteristic):
        super().characteristic_enable_notifications_succeeded(characteristic)
        print("Notifications enabled")

    def request_bms_data(self, request):
        print("BMS request data")
        self.response = bytearray()
        self.event.clear()
        self.bms_write_characteristic.write_value(request)

    def characteristic_enable_notifications_failed(self, characteristic, error):
        super.characteristic_enable_notifications_failed(characteristic, error)
        print("BMS notification failed:", error)

    def characteristic_value_updated(self, characteristic, value):
        print("BMS answering")
        self.response += value
        if self.response.endswith(b'w'):
            print("BMS answer:", self.response.hex())
            self.event.set()

    def characteristic_write_value_failed(self, characteristic, error):
        print("BMS write failed:", error)

    def wait(self):
        return self.event.wait(timeout=5)


def bluetooth_manager_thread(manager):
    print("Running BT manager")
    manager.run()


bluetooth_device = "A4:C1:38:EC:1B:B0"

manager = gatt.DeviceManager(adapter_name='hci0')
bluetooth_manager = threading.Thread(target=bluetooth_manager_thread, args=[manager, ])
bluetooth_manager.start()
device = AnyDevice(mac_address=bluetooth_device, manager=manager)
device.connect()

print('BMS server for {} started'.format(bluetooth_device))

# device.request_bms_data(bytes([0xDD, 0xA5, 0x03, 0x00, 0xFF, 0xFD, 0x77]))
# device.request_bms_data(bytes([0xDD, 0xA5, 0x05, 0x00, 0xFF, 0xFB, 0x77]))
device.request_bms_data(bytes([0xDB, 0xDB, 0x00, 0x00, 0x00, 0x00, 0x00]))
if device.wait():
    print(device.response)
else:
    print('BMS timed out')
    device.disconnect()
