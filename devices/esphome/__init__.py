from common import Constant, utils, get_json_param
from main.logger_helper import L
from main import thread_pool
from transport import mqtt_io
import prctl
import threading
from storage.model import m


class P:
    initialised = False
    esphome_topic = None
    esp_topic_clean = None


# jbd 'esphome/A4:C1:38:22:C4:23/sensor/jbd-bms-ble_cell_voltage_25/state'
# 'jk-bms/sensor/jk-bms_cell_voltage_1/state' 3.301
def _process_message(msg):
    # L.l.info("Topic={} payload={}".format(msg.topic, msg.payload))
    mac = msg.topic.replace(P.esp_topic_clean, '')[:17]
    # fixme: identify bms name from mqtt data
    rec = m.Bms.find_one({m.Bms.mac_address: mac})
    if rec is not None:
        topic = msg.topic.replace(P.esp_topic_clean, '')[18:].replace('jbd-bms-ble_', '').replace('jk-bms_', '')
        if 'sensor/' in topic:
            if 'total_voltage' in topic:
                rec.voltage = float(msg.payload)
                rec.save_changed_fields(persist=True)
                # L.l.info("Total bms battery {} voltage={}".format(rec.name, rec.voltage))
            # 'jk-bms/sensor/jk-bms_cell_voltage_1/state' 3.301
            elif 'cell_voltage_' in topic:
                cell_no = topic.split('sensor/cell_voltage_')[1].split('/state')[0]
                cell_voltage = float(msg.payload)
                volt_name = 'v{0:0=2}'.format(int(cell_no))
                setattr(rec, volt_name, cell_voltage)
                rec.save_changed_fields(persist=True)
            elif '/power/' in topic:
                rec.power = float(msg.payload)
                rec.save_changed_fields(persist=True)
            elif '/current/' in topic:
                rec.current = float(msg.payload)
                rec.save_changed_fields(persist=True)
            elif 'charging_power' in topic:
                bms_charging_power = float(msg.payload)
            elif 'discharging_power' in topic:
                bms_discharging_power = float(msg.payload)
            elif 'state_of_charge' in topic:
                bms_state_of_charge = float(msg.payload)
            elif 'total_battery_capacity_setting/state' in topic:
                rec.full_capacity = float(msg.payload)
                rec.save_changed_fields(persist=True)
            elif 'capacity_remaining' in topic:
                rec.capacity_percent = float(msg.payload)
                rec.save_changed_fields(persist=True)
            elif 'power_tube_temperature' in topic:
                rec.t1 = float(msg.payload)
                rec.save_changed_fields(persist=True)
            elif 'temperature_sensor_1' in topic:
                rec.t1 = float(msg.payload)
                rec.save_changed_fields(persist=True)
            elif 'temperature_sensor_2' in topic:
                rec.t2 = float(msg.payload)
                rec.save_changed_fields(persist=True)
            elif 'charging_cycles' in topic:
                rec.cycles = int(msg.payload)
                rec.save_changed_fields(persist=True)
            elif 'balancing_current' in topic:
                pass
                # rec.t2 = float(msg.payload)
                # rec.save_changed_fields(persist=True)
            elif '_device_model' in topic:
                rec.device_model = msg.payload
                rec.save_changed_fields(persist=True)
            else:
                # L.l.info("Unprocessed topic esphome: {}=".format(msg.topic, msg.payload))
                pass
    else:
        L.l.warning("Cannot find bms record with mac {}".format(mac))
    return True


def mqtt_on_message(client, userdata, msg):
    try:
        prctl.set_name("mqtt_jkbms")
        threading.current_thread().name = "mqtt_jkbms"
        if not _process_message(msg):
            L.l.warning("Error processing esphome mqtt")
    except Exception as ex:
        L.l.error("Error processing esphome mqtt {}, err={}, msg={}".format(msg.topic, ex, msg), exc_info=True)
    finally:
        prctl.set_name("idle_mqtt_jkbms")
        threading.current_thread().name = "idle_mqtt_jkbms"


def init():
    L.l.info('Jkbms module initialising')
    P.esphome_topic = str(get_json_param(Constant.P_MQTT_TOPIC_ESPHOME))
    P.esp_topic_clean = P.esphome_topic.replace('#', '')
    # mqtt_io.P.mqtt_client.message_callback_add(P.sonoff_topic, mqtt_on_message)
    mqtt_io.add_message_callback(P.esphome_topic, mqtt_on_message)
    # thread_pool.add_interval_callable(thread_run, P.check_period, long_running=True)
    P.initialised = True
