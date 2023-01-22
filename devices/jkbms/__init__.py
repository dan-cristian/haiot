from common import Constant, utils, get_json_param
from main.logger_helper import L
from main import thread_pool
from transport import mqtt_io
import prctl
import threading
from storage.model import m


class P:
    initialised = False
    jkbms_topic = None


def _process_message(msg):
    L.l.info("Topic={} payload={}".format(msg.topic, msg.payload))
    # fixme: identify bms name from mqtt data
    rec = m.Bms.find_one({m.Bms.name: 'jkbms_100ah_be_a9'})
    if 'sensor/' in msg.topic:
        topic_clean = P.jkbms_topic.replace('#', '')
        if 'jk-bms_total_voltage' in msg.topic:
            total_voltage = float(msg.payload)
            rec.voltage = total_voltage
            rec.save_changed_fields(persist=True)
        # 'jk-bms/sensor/jk-bms_cell_voltage_1/state' 3.301
        elif 'jk-bms_cell_voltage' in msg.topic:
            cell_no = msg.topic.split(topic_clean + 'sensor/jk-bms_cell_voltage_')[1].split('/state')[0]
            cell_voltage = float(msg.payload)
            volt_name = 'v{0:0=2}'.format(int(cell_no))
            setattr(rec, volt_name, cell_voltage)
            rec.save_changed_fields(persist=True)
        elif 'jk-bms_power' in msg.topic:
            bms_power = float(msg.payload)
            rec.power = bms_power
            rec.save_changed_fields(persist=True)
        elif 'jk-bms_charging_power' in msg.topic:
            bms_charging_power = float(msg.payload)
        elif 'jk-bms_discharging_power' in msg.topic:
            bms_discharging_power = float(msg.payload)
        elif 'jk-bms_state_of_charge' in msg.topic:
            bms_state_of_charge = float(msg.payload)
        elif 'jk-bms_capacity_remaining' in msg.topic:
            bms_capacity_remaining = float(msg.payload)
            rec.capacity_percent = bms_capacity_remaining
            rec.save_changed_fields(persist=True)
        else:
            L.l.info("Unprocessed topic jkbms: {}=".format(msg.topic, msg.payload))

    return True

def mqtt_on_message(client, userdata, msg):
    try:
        prctl.set_name("mqtt_jkbms")
        threading.current_thread().name = "mqtt_jkbms"
        if not _process_message(msg):
            L.l.warning("Error processing jkbms mqtt")
    except Exception as ex:
        L.l.error("Error processing jkbms mqtt {}, err={}, msg={}".format(msg.topic, ex, msg), exc_info=True)
    finally:
        prctl.set_name("idle_mqtt_jkbms")
        threading.current_thread().name = "idle_mqtt_jkbms"

def init():
    L.l.info('Jkbms module initialising')
    P.jkbms_topic = str(get_json_param(Constant.P_MQTT_TOPIC_JKBMS))
    # mqtt_io.P.mqtt_client.message_callback_add(P.sonoff_topic, mqtt_on_message)
    mqtt_io.add_message_callback(P.jkbms_topic, mqtt_on_message)
    # thread_pool.add_interval_callable(thread_run, P.check_period, long_running=True)
    P.initialised = True
