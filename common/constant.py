__author__ = 'dcristian'

SIGNAL_SENSOR = 'signal-from-sensor'
SIGNAL_SENSOR_DB_POST = 'signal-from-db-post'
SIGNAL_MQTT_RECEIVED = 'signal-from-mqtt-data-received'


ERROR_CONNECT_MAX_RETRY_COUNT = 10
ERROR_CONNECT_PAUSE_SECOND = 1
OS = 'not initialised'
OS_LINUX={'Linux', 'posix'}
OS_WINDOWS={'Windows', 'nt'}

SCRIPT_RESPONSE_OK='RESULTOK'

P_MZP_SERVER_URL='MZP_SERVER_URL'
P_MQTT_HOST='MQTT_HOST'
P_MQTT_PORT='MQTT_PORT'
P_MQTT_TOPIC='MQTT_TOPIC'
P_PLOTLY_USERNAME='PLOTLY_USERNAME'
P_PLOTLY_APIKEY='PLOTLY_APIKEY'


P_OWSERVER_HOST_1='OWSERVER_HOST_1'

SMARTCTL_MODEL_FAMILY='Model Family:'
SMARTCTL_MODEL_DEVICE='Device Model:'
SMARTCTL_SERIAL_NUMBER='Serial Number:'
SMARTCTL_TEMP_ID='194 Temperature_Celsius'
SMARTCTL_STATUS='SMART overall-health self-assessment test result:'
SMARTCTL_ERROR_SECTORS='198 Offline_Uncorrectable'
SMARTCTL_ERROR_NO_DISK='Unable to detect device type'
HDPARM_STATUS='drive state is:'
DISK_DEV_MAIN='/dev/sd'

JSON_PUBLISH_DATE='datetime_'
JSON_PUBLISH_TABLE='table_'
JSON_PUBLISH_RECORD_OPERATION='operation_'
JSON_PUBLISH_SOURCE_HOST='source_host_'
JSON_PUBLISH_TARGET_HOST='target_host_'
JSON_PUBLISH_VALUE_TARGET_HOST_ALL='*'
JSON_PUBLISH_GRAPH_X='graph_x_'
JSON_PUBLISH_GRAPH_Y='graph_y_'
JSON_PUBLISH_GRAPH_ID='graph_id_'