import wifi
import mqtt
import time
import machine
from credentials import ssid, password, mqtt_pass, mqtt_user

client_id = "vent-living-1"
mqtt_server = "192.168.0.12"
topic_sub = "iot/micro/" + client_id
topic_pub = "iot/sonoff/" + client_id + "/"


def restart_and_reconnect():
    print('Restarting ESP...')
    time.sleep(5)
    machine.reset()


def test_stepper():
    print("Testing stepper")
    import uln2003
    from machine import Pin
    '''
    IN1 -->  D5
    IN2 -->  D6
    IN3 -->  D1
    IN4 -->  D2
    '''
    s1 = uln2003.create(Pin(14, Pin.OUT), Pin(12, Pin.OUT), Pin(5, Pin.OUT), Pin(4, Pin.OUT), delay=2)
    s1.step(100)
    s1.step(100, -1)
    s1.angle(180)
    s1.angle(360, -1)


def main():
    test_stepper()
    print("Wifi connect")
    wifi.connect(ssid, password)
    result = mqtt.connect(client_id, mqtt_server, topic_sub, topic_pub, user=mqtt_user, password=mqtt_pass)
    if result == 'restart':
        restart_and_reconnect()
    else:
        print("Unknown action")



if __name__ == '__main__':
    main()
