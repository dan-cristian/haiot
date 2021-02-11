import wifi
import mqtt
import machine
import network
import webrepl
from credentials import ssid, password, mqtt_pass, mqtt_user
import common
import ubinascii
import esp


#machine_id = ubinascii.hexlify(machine.unique_id()).decode("utf-8")
#client_id = "vent-" + machine_id
mqtt_server = "192.168.0.12"


def restart_and_reconnect():
    print('Restarting ESP via deepsleep...')
    common.init_deep_sleep(sleep_sec=5)


def init_stepper(from_deep_sleep=False):
    import vent_control
    vent_control.init_motor()
    if not from_deep_sleep:
        print("Testing stepper")
        vent_control.test_motor()
    else:
        print("Not testing due to deep sleep resume")
    common.read_rtc()


def main():
    esp.osdebug(None)
    common.set_adc_mode(common.ADC_MODE_VCC)
    vcc = machine.ADC(1).read()
    machine_id = ubinascii.hexlify(machine.unique_id()).decode("utf-8")
    print("Main function, VCC={}, hw_id={}".format(vcc, machine_id))
    if machine.reset_cause() == machine.DEEPSLEEP_RESET:
        init_stepper(from_deep_sleep=True)
    else:
        init_stepper(from_deep_sleep=False)
    if wifi.connect(ssid, password):
        print("Starting webrepl")
        if webrepl.listen_s is None:
            webrepl.start()
        else:
            print("Webrepl already started")
        # settime()
        client_id = wifi.station.config("dhcp_hostname")
        topic_sub = "iot/micro/" + client_id
        topic_pub = "iot/sonoff/" + client_id
        result = mqtt.connect(client_id, mqtt_server, topic_sub, topic_pub, user=mqtt_user, password=mqtt_pass)
        if result == 'restart':
            print("Restarting due to connectivity error")
        else:
            print("Unknown action {}".format(result))
    else:
        print("Wifi did not connect")
    restart_and_reconnect()


if __name__ == '__main__':
    main()
