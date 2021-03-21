import signal
import time
import paho.mqtt.client as mqtt
import socket
import credentials
import serial


class P:
    shutting_down = False
    mqtt_client = None
    topic = "shellies/shellyem3-ECFABCC7F0F4/emeter/0/power"
    host = "192.168.0.12"
    port = 1883
    client_connected = False
    HOST_NAME = socket.gethostname()
    serial_name = "/dev/ttyUSB0"
    serial_port = None


class C:
    voltage = 0
    default_voltage = 28.0  # set all as float
    max_voltage = 28.4
    max_current = 4.0


# http://www.tutorialspoint.com/python/python_command_line_arguments.htm
def signal_handler(signal_name, frame):
    print('I got signal {} frame {}, exiting'.format(signal_name, frame))


def subscribe():
    print('Subscribing to mqtt topic={}'.format(P.topic))
    P.mqtt_client.username_pw_set(P.HOST_NAME)
    P.mqtt_client.user_data_set(P.HOST_NAME + " userdata")
    P.mqtt_client.will_set(P.HOST_NAME + " DIE")
    P.mqtt_client.subscribe(topic=P.topic, qos=0)


def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection from mqtt")
    else:
        print("Expected disconnect from mqtt")
    P.mqtt_client.loop_stop()
    P.client_connected = False


# The callback for when the client receives a CONNACK response from the server.
def on_connect_paho(client, userdata, flags, rc):
    print("Connected to mqtt paho with result code " + str(rc))
    P.client_connected = True
    subscribe()


def on_message(client, userdata, msg):
    msg = msg.payload.decode('utf-8')
    val = "{}".format(msg).replace("b", "").replace("\\", "").replace("'", "")
    power = float(val)
    charger_update(power=power)


def mqtt_init():
    P.mqtt_client = mqtt.Client(client_id="pi_battery_charger")
    P.mqtt_client.on_connect = on_connect_paho
    # P.mqtt_client.on_subscribe = on_subscribe
    # P.mqtt_client.on_unsubscribe = on_unsubscribe
    P.mqtt_client.username_pw_set(credentials.mqtt_user, credentials.mqtt_pass)
    P.mqtt_client.max_inflight_messages_set(100)
    P.mqtt_client.max_queued_messages_set(0)
    retry_count = 0
    while (not P.client_connected) and (retry_count < 10):
        P.mqtt_client.connect(host=P.host, port=P.port, keepalive=60)
        P.mqtt_client.loop_start()
        seconds_lapsed = 0
        while not P.client_connected and seconds_lapsed < 10:
            time.sleep(1)
            seconds_lapsed += 1
            print('Waiting for mqtt connect {}'.format(seconds_lapsed))
            if P.client_connected:
                P.mqtt_client.on_message = on_message
                # P.mqtt_client.message_callback_add(P.topic_main, on_message)
                P.mqtt_client.on_disconnect = on_disconnect
                P.initialised = True
            else:
                print('Timeout connecting to mqtt')
                retry_count += 1


def __open_port(ser):
    ser.baudrate = 4800
    ser.timeout = 3
    ser.writeTimeout = 3
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.bytesize = serial.EIGHTBITS
    try:
        ser.open()
        return True
    except Exception as ex:
        print('Unable to open serial port {}'.format(ser.port))
        return False


def __write_read_port(ser, command):
    response = None
    if ser.isOpen():
        try:
            ser.flushInput()
            ser.flushOutput()
            cmd = "{}\r\n".format(command).encode()
            print("Serial writing={}".format(cmd))
            ser.write(cmd)
            # time.sleep(0.1)
            resp = ser.readline()
            print("Serial read={}".format(resp))
            response = resp.decode('utf-8').replace('\r', '').replace('\n', '')
        except Exception as ex:
            print('Error writing to serial {}, err={}'.format(ser.port, ex))
    else:
        print('Error writing to closed serial {}'.format(ser.port))
    return response


def charge_cmd_read(cmd):
    if P.serial_port is not None:
        resp = __write_read_port(P.serial_port, cmd)
        if len(resp) == 14:
            numb = int(resp[-4:]) / 100
            return numb
        else:
            return resp
    else:
        return None


def charge_cmd_set(cmd, value):
    if P.serial_port is not None:
        if value != 0:
            full_cmd = "{}".format(value * 100)[:4].split(".", 1)[0].zfill(4)
        else:
            full_cmd = "0"
        full_cmd = "{}{}".format(cmd, full_cmd)
        resp = charge_cmd_read(full_cmd)
        if "ok" in resp:
            return True
        else:
            return resp
    else:
        return None


def serial_init():
    ser = serial.Serial()
    ser.port = P.serial_name
    __open_port(ser)
    if ser.isOpen():
        response = __write_read_port(ser, "aro")
        if "#ro0" in response:
            P.serial_port = ser
        else:
            print("Unexpected serial response={}".format(response))
    else:
        print("Unable to open port {}".format(P.serial_name))


def get_charger_status():
    C.voltage_set = charge_cmd_read("arv")
    C.current_set = charge_cmd_read("ara")
    C.output_state = int(charge_cmd_read("aro") * 100)
    C.working_time = charge_cmd_read("art")
    C.voltage_actual = charge_cmd_read("aru")
    C.current_actual = charge_cmd_read("ari")
    C.capacity_actual = charge_cmd_read("arc")
    print("Vs={}V Cs={}A O={} Ti={} Va={}V Ca={}A Sa={}AH".format(
        C.voltage_set, C.current_set, C.output_state, C.working_time,
        C.voltage_actual, C.current_actual, C.capacity_actual))


def charger_init():
    if P.serial_port is not None:
        get_charger_status()
        if C.voltage_set != C.default_voltage:
            set_voltage_set(C.default_voltage)
        if C.output_state == 1:
            set_output(0)


def set_voltage_set(voltage):
    charge_cmd_set("awu", voltage)
    C.voltage_set = charge_cmd_read("arv")
    if C.voltage_set != voltage:
        print("Error voltage set, new={} actual={}".format(voltage, C.voltage_set))


def set_current_set(current):
    current = min(current, C.max_current)
    print("Set current={}".format(current))
    return charge_cmd_set("awi", current)


# 0=OFF, 1=ON
def set_output(state):
    return charge_cmd_set("awo", state/100)


def set_power(new_power):
    if P.serial_port is None:
        return
    if C.voltage_actual == 0:
        voltage = C.voltage_set
    else:
        voltage = C.voltage_actual
    if voltage == 0:
        voltage = C.default_voltage
    target_current = new_power / voltage
    set_current_set(target_current)


def charger_update(power):
    print("Power={}".format(power))
    set_power(power)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, signal_handler)
    serial_init()
    charger_init()
    mqtt_init()

    try:
        print("Looping forever")
        while not P.shutting_down:
            time.sleep(1)
    except KeyboardInterrupt:
        print('CTRL+C was pressed, exiting')
        exit_code = 1
    except Exception as ex:
        print('Main exit with exception {}'.format(ex))
