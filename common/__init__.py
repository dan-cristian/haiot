__author__ = 'dcristian'
import os
import socket
from uuid import getnode as get_mac
import json
import utils


class Constant:
    db_values_json = None

    def __init__(self):
        pass
    
    SIGNAL_SENSOR = 'signal-from-sensor'
    SIGNAL_UI_DB_POST = 'signal-from-db-post'
    SIGNAL_MQTT_RECEIVED = 'signal-from-mqtt-data-received'
    SIGNAL_HEAT = 'signal-from-heat'
    SIGNAL_GPIO = 'signal-from-GPIO'
    SIGNAL_CAMERA = 'signal-from-CAMERA'
    SIGNAL_GPIO_INPUT_PORT_LIST = 'signal-setup-GPIO-input'
    SIGNAL_FILE_WATCH = 'signal-from-file-watch'
    SIGNAL_DB_CHANGE_FOR_RULES = 'signal_db_change_for_rules'
    SIGNAL_UTILITY = 'signal-utility-data'
    SIGNAL_UTILITY_EX = 'signal-utility-extra-data'
    SIGNAL_PUSH_NOTIFICATION = 'signal-push-notification'
    SIGNAL_CHAT_NOTIFICATION = 'signal-chat-notification'
    SIGNAL_EMAIL_NOTIFICATION = 'signal-email-notification'
    SIGNAL_PRESENCE = 'signal-presence'
    SIGNAL_ALARM='signal-alarm'
    SIGNAL_STORABLE_RECORD = 'signal-storable-record'
    SIGNAL_BATTERY_STAT = 'signal-battery-stat'

    PRESENCE_TYPE_CAM = 'cam'
    

    ERROR_CONNECT_MAX_RETRY_COUNT = 2
    ERROR_CONNECT_PAUSE_SECOND = 1
    OS = 'not initialised'
    OS_LINUX = {'linux', 'posix'}
    OS_WINDOWS = {'windows', 'nt'}
    MACHINE_TYPE_BEAGLEBONE = 'beaglebone'
    MACHINE_TYPE_RASPBERRY = 'raspberry'
    MACHINE_TYPE_OPENWRT = 'openwrt'
    MACHINE_TYPE_INTEL_LINUX = 'intel-linux'

    NOT_INIT = 'not initialised'
    HOST_NAME = NOT_INIT
    HOST_MAIN_IP = NOT_INIT
    HOST_MAC = NOT_INIT
    HOST_MACHINE_TYPE = NOT_INIT
    HOST_PRIORITY = -1

    IS_MACHINE_BEAGLEBONE = False
    IS_MACHINE_RASPBERRYPI = False
    IS_MACHINE_INTEL = False
    IS_MACHINE_OPENWRT = False

    HAS_LOCAL_DB_REPORTING_CAPABILITY = False

    MAX_REPORT_LINES = 1000
    URL_OPEN_TIMEOUT = 10

    @staticmethod
    def IS_OS_WINDOWS():
        return Constant.OS in Constant.OS_WINDOWS

    @staticmethod
    def IS_OS_LINUX():
        return Constant.OS in Constant.OS_LINUX

    DB_FIELD_UPDATE = 'updated_on'
    SCRIPT_RESPONSE_OK = 'RESULTOK'
    SCRIPT_RESPONSE_NOTOK = 'RESULTNOTOK'

    P_DB_PATH="DB_PATH"
    P_MZP_SERVER_URL = 'MZP_SERVER_URL'
    P_MQTT_HOST_1 = 'MQTT_HOST_1'
    P_MQTT_PORT_1 = 'MQTT_PORT_1'
    P_MQTT_TOPIC = 'MQTT_TOPIC'
    P_MQTT_HOST_2 = 'MQTT_HOST_2'
    P_MQTT_PORT_2 = 'MQTT_PORT_2'
    P_MQTT_HOST_3 = 'MQTT_HOST_3'
    P_MQTT_PORT_3 = 'MQTT_PORT_3'
    P_PLOTLY_ALTERNATE_CONFIG = 'P_PLOTLY_ALTERNATE_CONFIG'
    P_OWSERVER_HOST_1 = 'OWSERVER_HOST_1'
    P_OWSERVER_PORT_1 = 'OWSERVER_PORT_1'
    P_DDNS_RACKSPACE_CONFIG_FILE = 'DDNS_RACKSPACE_CONFIG_FILE'
    P_USESUDO_DISKTOOLS = 'P_USESUDO_DISKTOOLS'
    P_FLASK_WEB_PORT = 'P_FLASK_WEB_PORT'
    P_MOTION_VIDEO_PATH = 'P_MOTION_VIDEO_PATH'
    P_YOUTUBE_CREDENTIAL_FILE = 'P_YOUTUBE_CREDENTIAL_FILE'
    DB_REPORTING_LOCATION_ENABLED = 'DB_REPORTING_LOCATION_ENABLED'
    DB_REPORTING_LOCATION = 'DB_REPORTING_LOCATION'
    DB_REPORTING_USER = 'DB_REPORTING_USER'
    DB_REPORTING_PASS = 'DB_REPORTING_PASS'
    P_TEMPERATURE_THRESHOLD = 'P_TEMPERATURE_THRESHOLD'
    P_MPD_SERVER = 'P_MPD_SERVER'
    P_NEWTIFY_KEY = 'P_NEWTIFY_KEY'
    P_HIPCHAT_TOKEN = 'P_HIPCHAT_TOKEN'
    P_HIPCHAT_ROOM_API_ID = 'P_HIPCHAT_ROOM_API_ID'
    P_MPD_PORT_ZONE = 'P_MPD_PORT_ZONE'
    P_LASTFM_CONFIG_FILE = 'LASTFM_CONFIG_FILE'
    P_GMUSICPROXY_URL = 'GMUSICPROXY_URL'
    P_AMP_SERIAL_HOST = 'AMP_SERIAL_HOST'
    P_AMP_SERIAL_PORT = 'AMP_SERIAL_PORT'
    P_ALEXA_WEMO_LISTEN_PORT = 'ALEXA_WEMO_LISTEN_PORT'
    P_HEAT_SOURCE_MIN_TEMP = 'HEAT_SOURCE_MIN_TEMP'
    P_HEAT_STATE_REFRESH_PERIOD = 'HEAT_STATE_REFRESH_PERIOD'
    P_GMAIL_NOTIFY_FROM_EMAIL = 'GMAIL_NOTIFY_FROM_EMAIL'
    P_GMAIL_CREDENTIAL_FILE = 'GMAIL_CREDENTIAL_FILE'
    P_THINGSPEAK_API_FILE = 'THINGSPEAK_API_FILE'
    P_NOTIFY_EMAIL_RECIPIENT = 'NOTIFY_EMAIL_RECIPIENT'
    P_SOLAR_APS_LOCAL_URL = 'SOLAR_APS_LOCAL_URL'
    P_SOLAR_UTILITY_NAME = 'SOLAR_UTILITY_NAME'
    P_UPS_ON_HOST = 'UPS_ON_HOST'
    P_SOLAR_PARSER_ON_HOST = 'SOLAR_PARSER_ON_HOST'

    SMARTCTL_MODEL_FAMILY = 'Model Family:'
    SMARTCTL_MODEL_DEVICE = 'Device Model:'
    SMARTCTL_SERIAL_NUMBER = 'Serial Number:'
    SMARTCTL_TEMP_ID = '194 Temperature_Celsius'
    SMARTCTL_STATUS = 'SMART overall-health self-assessment test result:'
    SMARTCTL_ERROR_SECTORS = '198 Offline_Uncorrectable'
    SMARTCTL_START_STOP_COUNT = '4 Start_Stop_Count'
    SMARTCTL_LOAD_CYCLE_COUNT = '193 Load_Cycle_Count'
    SMARTCTL_ERROR_NO_DISK = 'Unable to detect device type'
    SMARTCTL_DEVICE_IN_STANDBY = 'Device is in STANDBY mode'
    HDPARM_STATUS = 'drive state is:'
    FREE_MEM_STATUS = 'Mem:'

    DISK_DEV_MAIN = '/dev/sd'

    JSON_MESSAGE_TYPE = 'message_type'
    JSON_PUBLISH_DATE = 'datetime_'
    JSON_PUBLISH_TABLE = 'table_'
    # JSON_PUBLISH_RECORD_OPERATION='operation_'
    JSON_PUBLISH_OPERATION_UPDATE = 'update'
    JSON_PUBLISH_SOURCE_HOST = 'source_host_'
    JSON_PUBLISH_TARGET_HOST = 'target_host_'
    JSON_PUBLISH_VALUE_TARGET_HOST_ALL = '*'
    JSON_PUBLISH_GRAPH_X = 'graph_x_'
    JSON_PUBLISH_GRAPH_Y = 'graph_y_'
    JSON_PUBLISH_GRAPH_SHAPE = 'graph_shape_'
    JSON_PUBLISH_GRAPH_ID = 'graph_id_'
    JSON_PUBLISH_GRAPH_LEGEND = 'graph_legend_'
    # use exact field names from class BaseGraph
    JSON_PUBLISH_SAVE_TO_GRAPH = 'save_to_graph'
    JSON_PUBLISH_SAVE_TO_HISTORY = 'save_to_history'
    JSON_PUBLISH_FIELDS_CHANGED = 'last_commit_field_changed_list'
    JSON_PUBLISH_NOTIFY_TRANSPORT = 'notify_transport_enabled'
    JSON_PUBLISH_NOTIFY_DB_COMMIT = 'notified_on_db_commit'
    # use exact field name from class DbBase
    JSON_PUBLISH_RECORD_UUID = 'record_uuid'

    GPIO_PIN_TYPE_BBB = 'bbb'
    GPIO_PIN_TYPE_PI_STDGPIO = 'pi-stdgpio'
    GPIO_PIN_TYPE_PI_FACE_SPI = 'pi-face-spi'
    GPIO_PIN_DIRECTION_IN = 'in'
    GPIO_PIN_DIRECTION_OUT = 'out'

    UTILITY_TYPE_ELECTRICITY='electricity'
    #UTILITY_TYPE_ELECTRICITY_MEASURE = 'kWh'
    #UTILITY_TYPE_ELECTRICITY_MEASURE_2 = 'watt'
    UTILITY_TYPE_WATER = 'water'
    #UTILITY_TYPE_WATER_MEASURE = 'l'
    UTILITY_TYPE_GAS = 'gas'
    #UTILITY_TYPE_GAS_MEASURE = 'l'
    UTILITY_TYPE_WATER_LEVEL = 'water level'

    LOG_SENSOR_INACTIVE = ''


def load_config_json():
    from main.logger_helper import L
    try:
        var_path = utils.get_app_root_path() + 'scripts/config/default_db_values.json'
        L.l.info('Loading variables from config file [{}]'.format(var_path))
        with open(var_path, 'r') as f:
            Constant.db_values_json = json.load(f)
    except Exception, ex:
        L.l.error('Cannot load config json, ex={}'.format(ex))
        exit(2)


def get_json_param(name):
    """ retrieves parameter value from json config file"""
    param_fields = Constant.db_values_json["Parameter"]
    value = None
    for config_record in param_fields:
        if config_record["name"] == name:
            value = config_record["value"]
            break
    return value


def init():
    from main.logger_helper import L
    try:
        mac = get_mac()
        # call it twice as get_mac might fake mac: http://stackoverflow.com/questions/159137/getting-mac-address
        if mac == get_mac():
            Constant.HOST_MAC = ':'.join(("%012X" % mac)[i:i + 2] for i in range(0, 12, 2))
        else:
            L.l.warning('Cannot get mac address')
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("gmail.com", 80))
        Constant.HOST_MAIN_IP = s.getsockname()[0]
        s.close()
    except Exception, ex:
        L.l.warning('Cannot obtain main IP accurately, not connected to Internet?, retry, ex={}'.format(ex))
        try:
            Constant.HOST_MAIN_IP = socket.gethostbyname(socket.gethostname())
        except Exception, ex2:
            L.l.warning('Cannot obtain main IP, no DNS available?, ex={}'.format(ex2))
            Constant.HOST_MAIN_IP = '127.0.0.1'
    L.l.info('Running on OS={} HOST={} IP={} MACHINE={}'.format(Constant.OS, Constant.HOST_NAME,
                                                                Constant.HOST_MAIN_IP,
                                                                Constant.HOST_MACHINE_TYPE))


def init_simple():
    Constant.OS = os.name
    Constant.HOST_NAME = socket.gethostname()
