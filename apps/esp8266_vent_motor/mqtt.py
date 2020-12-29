from umqtt.simple import MQTTClient
import time
import ujson
import vent_control


# Complete project details at https://RandomNerdTutorials.com
class P:
    mqtt_client_id = None
    msg_count = 0
    client = None
    topic_pub = None


def sub_cb(topic, msg):
    P.msg_count += 1
    print("Received message #{}".format(P.msg_count))
    try:
        # print("device={}, topic={}, start={}, my_name={}".format(device_id, name, msg[0], mqtt_client_id))
        if msg[0] != 123:  # check for valid json staring with { character
            return
        data = msg.decode()
        # topic = topic.decode().split('/')
        # device_id = topic.pop(-1)
        # name = topic[-1]
        # print(data)
        # ensure message if addressed to us and contains Pwm info
        if True or "'host_name': '{}'".format(mqtt_client_id) in data:
            if 'Vent' in data:
                # print("'host_name': '{}'".format(mqtt_client_id) in data)
                js = ujson.loads(data)
                # print(js)
                for key, value in js.items():
                    # print("Parsing {}".format(key))
                    if key == "open":
                        vent_control.open_full_vent(direction=value)
                        print("Opened vent")
                    if key == "close":
                        vent_control.close_full_vent(direction=value)
                        print("Closed vent")
                    if key == "move":
                        vent_control.vent_move(angle=value)
                    # elif value is not None:
                    #    for key1, value1 in value.items():
                    #        print("SubParsing {}".format(key1))
            else:
                print("Got a message without Vent payload: {}".format(data))
                pass
        else:
            print("Ignoring message: {}".format(data[:40]))
    except Exception as ex:
        print('Got exception {}, string={}'.format(ex, msg))


def publish(message):
    print("Publishing {} to {}".format(message, P.topic_pub))
    P.client.publish(P.topic_pub, msg=message, retain=True)


def connect_and_subscribe(client_id, server, topic_sub, topic_pub, user, password):
    P.client = MQTTClient(client_id=client_id, server=server, user=user, password=password)
    P.client.set_callback(sub_cb)
    P.client.connect(clean_session=False)
    P.client.subscribe(topic_sub, qos=1)
    # client.publish(topic_pub, b'I am alive')
    print('Connected to %s MQTT broker, subscribed to %s topic' % (server, topic_sub))


def connect(client_id, server, topic_sub, topic_pub, user, password):
    P.topic_pub = topic_pub
    for i in range(1, 4):
        try:
            P.mqtt_client_id = client_id
            connect_and_subscribe(client_id=client_id, server=server,
                                  topic_sub=topic_sub, topic_pub=topic_pub, user=user, password=password)
            break
        except OSError as e:
            print("Error in try {}, mqtt connect: {}".format(i, e))
            time.sleep(3)
    if P.client is None:
        return "restart"
    else:
        while True:
            try:
                # client.wait_msg()
                msg = P.client.check_msg()
                vent_control.timer_actions()
                if msg is None:
                    time.sleep(1)

                # new_message = client.wait_msg()
                # new_message = client.check_msg()
                # print(new_message)
                # if new_message is not None:
                    # print(new_message)
                    #    pass
                # else:
            except OSError as e:
                print("Error in mqtt listen: {}".format(e))
                break
        return "restart"


def disconnect():
    P.client.disconnect()
