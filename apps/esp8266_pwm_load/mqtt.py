from umqtt.simple import MQTTClient
import time
import machine
import pwm
import ujson

# Complete project details at https://RandomNerdTutorials.com
mqtt_client_id = None


def sub_cb(topic, msg):
    # print((topic, msg))
    try:
        topic = topic.decode().split('/')
        device_id = topic.pop(-1)
        name = topic[-1]
        # print("device={}, topic={}, start={}, my_name={}".format(device_id, name, msg[0], mqtt_client_id))
        data = msg.decode()
        if msg[0] != 123:  # check for valid json staring with { character
            return
        # print(data)
        # ensure message if addressed to us and contains Pwm info
        if True or "'host_name': '{}'".format(mqtt_client_id) in data:
            if 'Pwm' in data:
                js = ujson.loads(data)
                print(js)
                for key, value in js.items():
                    print("Parsing {}".format(key))
                    if key == "duty_cycle":
                        pwm.set_duty(duty=value)
                        print("Set duty to {}".format(value))
                    elif key == "frequency":
                        pwm.set_frequency(frequency=value)
                        print("Set frequency to {}".format(value))
                    # elif value is not None:
                    #    for key1, value1 in value.items():
                    #        print("SubParsing {}".format(key1))

            else:
                # print("Got a message without Pwm payload: {}".format(data))
                pass
        else:
            print("Ignoring message: {}".format(data[:40]))
    except Exception as ex:
        print('Got exception {}, string={}'.format(ex, msg))


def connect_and_subscribe(client_id, server, topic_sub, user, password):
    client = MQTTClient(client_id=client_id, server=server, user=user, password=password)
    client.set_callback(sub_cb)
    client.connect()
    client.subscribe(topic_sub)
    print('Connected to %s MQTT broker, subscribed to %s topic' % (server, topic_sub))
    return client


def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Restarting...')
    time.sleep(10)
    machine.reset()


def connect(client_id, server, topic_sub, topic_pub, user, password):
    try:
        global mqtt_client_id
        mqtt_client_id = client_id

        client = connect_and_subscribe(client_id=client_id, server=server, topic_sub=topic_sub,
                                       user=user, password=password)
        while True:
            try:
                new_message = client.check_msg()
                # new_message = client.wait_msg()
                # print(new_message)
                if new_message is not None:
                    # print(new_message)
                    # client.publish(topic_pub, b'received')
                    pass
                else:
                    time.sleep(0.01)
            except OSError as e:
                print(e)
                restart_and_reconnect()
    except OSError as e:
        print(e)
        restart_and_reconnect()
