import wifi
import mqtt
import pwm
import time
import machine
from credentials import ssid, password, mqtt_pass, mqtt_user
import esp
import webrepl

mqtt_server = "192.168.0.12"


def restart_and_reconnect():
    print('Restarting ESP...')
    time.sleep(5)
    machine.reset()


def main():
    esp.osdebug(None)
    print("CPU frequency is {}".format(machine.freq()))
    machine.freq(80000000)
    print("CPU frequency is {}".format(machine.freq()))

    if wifi.connect(ssid, password):
        print("Starting webrepl")
        if webrepl.listen_s is None:
            webrepl.start()
        else:
            print("Webrepl already started")
        # pwm.init(pin=pwm_pin, frequency=pwm_frequency)
        client_id = wifi.station.config("dhcp_hostname")
        topic_sub = "iot/micro/" + client_id
        topic_pub = "iot/sonoff/" + client_id + "/"
        mqtt.connect(client_id, mqtt_server, topic_sub, topic_pub, user=mqtt_user, password=mqtt_pass)
    else:
        print("Wifi did not connect")
    restart_and_reconnect()


if __name__ == '__main__':
    main()
