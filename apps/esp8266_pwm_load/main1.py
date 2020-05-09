import wifi
import mqtt
import pwm
import time
import machine
from credentials import ssid, password, mqtt_pass, mqtt_user

pwm_pin = 13
pwm_frequency = 55
client_id = "pizero1"
mqtt_server = "192.168.0.12"
# topic_sub = "iot/sonoff/" + client_id + "/"
topic_sub = "iot/main/#"
topic_pub = "iot/sonoff/" + client_id + "/"


def restart_and_reconnect():
    print('Restarting ESP...')
    time.sleep(5)
    machine.reset()


def main():
    wifi.connect(ssid, password)
    pwm.init(pin=pwm_pin, frequency=pwm_frequency)
    result = mqtt.connect(client_id, mqtt_server, topic_sub, topic_pub, user=mqtt_user, password=mqtt_pass)
    if result == 'restart':
        restart_and_reconnect()
    else:
        print("Unknown action")


if __name__ == '__main__':
    main()
