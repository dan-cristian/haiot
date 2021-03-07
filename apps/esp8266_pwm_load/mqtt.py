from umqtt.simple import MQTTClient
import time
import pwm
import ujson

# Complete project details at https://RandomNerdTutorials.com
mqtt_client_id = None
# msg_count = 0


def sub_cb(topic, msg):
    # global msg_count
    # msg_count += 1
    # print(msg_count)
    try:
        msg = msg.decode('utf-8')
        val = "{}".format(msg).replace("b", "").replace("\\", "").replace("'", "")
        pwm.update(power=float(val))
    except Exception as ex:
        print('Got exception {}, string={}'.format(ex, msg))


def connect_and_subscribe(client_id, server, topic_sub, topic_pub, user, password):
    client = MQTTClient(client_id=client_id, server=server, user=user, password=password)
    client.set_callback(sub_cb)
    client.connect(clean_session=False)
    client.subscribe(topic_sub, qos=1)
    # client.publish(topic_pub, b'I am alive')
    print('Connected to %s MQTT broker, subscribed to %s topic' % (server, topic_sub))
    return client


def connect(client_id, server, topic_sub, topic_pub, user, password):
    try:
        global mqtt_client_id
        mqtt_client_id = client_id
        client = connect_and_subscribe(client_id=client_id, server=server,
                                       topic_sub=topic_sub, topic_pub=topic_pub, user=user, password=password)
        while True:
            try:
                client.wait_msg()
            except OSError as e:
                print(e)
    except OSError as e:
        print(e)
