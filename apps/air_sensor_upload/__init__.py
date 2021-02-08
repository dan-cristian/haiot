import requests
# import urllib.request, urllib.parse
# import json
from main.logger_helper import L
from main import thread_pool
import common
from storage.model import m
import datetime

class P:
    initialised = False
    token = None
    luftdaten_sensor_id = None
    # Sensor parameter
    pm25_updated_on = datetime.datetime.min
    temp_updated_on = datetime.datetime.min
    humidity_updated_on = datetime.datetime.min
    pressure_updated_on = datetime.datetime.min

    # Station parameter
    station = {
        'id': 'ro-cluj-napoca-gaudi-1',
        'name': 'Antonio Gaudi S1',
        'location': {
            'latitude': 46.752221,
            'longitude': 23.619609
        }
    }


# https://aqicn.org/data-feed/verification
def upload_aqicn(pm25, pm10, temp, humidity, pressure):
    sensor_readings = []
    if pm25 is not None:
        sensor_readings.append({'specie': "pm25", 'value': pm25, 'unit': 'mg/m3'})
    if pm10 is not None:
        sensor_readings.append({'specie': "pm10", 'value': pm10, 'unit': 'mg/m3'})
    if humidity is not None:
        sensor_readings.append({'specie': "humidity", 'value': humidity, 'unit': '%'})
    if pressure is not None:
        sensor_readings.append({'specie': "pressure", 'value': pressure, 'unit': 'hPa'})
    if temp is not None:
        sensor_readings.append({'specie': "temp", 'value': temp, 'unit': 'C'})

    params = {'token': P.token, 'station': P.station, 'readings': sensor_readings}
    request = requests.post(url="https://aqicn.org/sensor/upload/", json=params)
    data = request.json()
    # data_in = urllib.parse.urlencode(params).encode('utf-8')
    # req = urllib.request.Request(url="https://aqicn.org/sensor/upload/", data=data_in, method='POST')
    # resp = urllib.request.urlopen(req)
    # data = json.loads(resp.read())

    if data['status'] != "ok":
        L.l.warning("Error posting sensor, {} {}".format(data['status'], data['reason']))
    else:
        L.l.info("Uploaded air quality data pm2.5={}/{} pm10={} temp={}/{} hum={}/{} pres={}".format(
            pm25, P.pm25_updated_on, pm10, temp, P.temp_updated_on, humidity, P.humidity_updated_on, pressure))


# https://devices.sensor.community/
# https://forums.pimoroni.com/t/basic-intro-for-uploading-to-luftdaten-air-quality-project/12629/1
def upload_luftdaten(pm25, pm10, temp, humidity, pressure):
    values = {"1": {}, "11": {}}
    if pm10 is not None:
        values["1"]["P1"] = str(pm10)
    if pm25 is not None:
        values["1"]["P2"] = str(pm25)
    if temp is not None:
        values["11"]["temperature"] = str(temp)
    if humidity is not None:
        values["11"]["humidity"] = str(humidity)
    if pressure is not None:
        values["11"]["pressure"] = str(pressure * 100)

    # pm_values = dict(i for i in values.items() if i[0].startswith("P"))
    # temp_values = dict(i for i in values.items() if not i[0].startswith("P"))

    for pin in values.keys():
        if len(values[pin]) > 0:
            resp = requests.post("https://api.luftdaten.info/v1/push-sensor-data/",
                                 json={
                                       "software_version": "enviro-plus 0.0.1",
                                       "sensordatavalues": [{"value_type": key, "value": val} for
                                                            key, val in values[pin].items()]
                                    },
                                 headers={
                                       "X-PIN": pin,
                                       "X-Sensor": P.luftdaten_sensor_id,
                                       "Content-Type": "application/json",
                                       "cache-control": "no-cache"
                                   })
            if resp.ok:
                L.l.info("Uploaded luftdaten sensors {}".format(values[pin]))
            else:
                L.l.warning("Failed to upload luftdaten sensors, err={}".format(resp))

    return


def upload_sensor():
    try:
        pm25 = None
        pm10 = None
        temp = None
        humidity = None
        pressure = None
        dust_sensor = m.DustSensor.find_one({m.DustSensor.address: "wemos-curte-air_pms5003"})
        if dust_sensor is not None and P.pm25_updated_on != dust_sensor.updated_on:
            pm25 = dust_sensor.pm_2_5
            pm10 = dust_sensor.pm_10
            P.pm25_updated_on = dust_sensor.updated_on

        air_sensor = m.AirSensor.find_one({m.AirSensor.address: "wemos-curte-air_bme280"})
        if air_sensor is not None and P.humidity_updated_on != air_sensor.updated_on:
            # pressure = air_sensor.pressure
            humidity = air_sensor.humidity
            # sensor_readings.append({'specie': "pressure", 'value': pressure, 'unit': 'hPa'})
            P.humidity_updated_on = air_sensor.updated_on

        if air_sensor is not None and P.pressure_updated_on != air_sensor.updated_on:
            pressure = air_sensor.pressure
            P.pressure_updated_on = air_sensor.updated_on

        air_sensor2 = m.AirSensor.find_one({m.AirSensor.address: "front_garden_we_ds18b20"})
        if air_sensor2 is not None and P.temp_updated_on != air_sensor2.updated_on:
            temp = air_sensor2.temperature
            P.temp_updated_on = air_sensor2.updated_on

        if pm25 is pm10 is temp is humidity is pressure is None:
            L.l.info('No air sensors data to upload dust={} air={} air2={}'.format(dust_sensor, air_sensor, air_sensor2))
        else:
            upload_aqicn(pm25=pm25, pm10=pm10, temp=temp, humidity=humidity, pressure=pressure)
            upload_luftdaten(pm25=pm25, pm10=pm10, temp=temp, humidity=humidity, pressure=pressure)
    except Exception as ex:
        L.l.error("Unable to upload air sensor data, err={}".format(ex))


def unload():
    pass


def init():
    L.l.info('Air sensor upload module initialising')
    # User parameter - get yours from https://aqicn.org/data-platform/token/
    P.token = common.get_secure_general("aqicn_token")
    P.luftdaten_sensor_id = common.get_secure_general("luftdaten_sensor_id")
    thread_pool.add_interval_callable(upload_sensor, run_interval_second=60)
