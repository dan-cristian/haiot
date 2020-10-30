import requests
# import urllib.request, urllib.parse
# import json
from main.logger_helper import L
from main import thread_pool
import common
from storage.model import m


class P:
    initialised = False
    token = None
    # Sensor parameter
    pm25 = None
    pm10 = None
    temp = None
    humidity = None
    pressure = None

    # Station parameter
    station = {
        'id': 'ro-cluj-napoca-gaudi-1',
        'name': 'Antonio Gaudi S1',
        'location': {
            'latitude': 46.752221,
            'longitude': 23.619609
        }
    }


def upload_sensor():
    sensor_readings = []
    pm25 = None
    pm10 = None
    temp = None
    humidity = None
    pressure = None
    dust_sensor = m.DustSensor.find_one({m.DustSensor.address: "wemos-curte-air_pms5003"})
    if dust_sensor is not None and (P.pm25 != dust_sensor.pm_2_5 or P.pm10 != dust_sensor.pm_10):
        pm25 = dust_sensor.pm_2_5
        pm10 = dust_sensor.pm_10
        # Then Upload the data
        sensor_readings.append({'specie': "pm2.5", 'value': pm25, 'unit': 'mg/m3'})
        sensor_readings.append({'specie': "pm10", 'value': pm10, 'unit': 'mg/m3'})

    air_sensor = m.AirSensor.find_one({m.AirSensor.address: "wemos-curte-air_bme280"})
    if air_sensor is not None and (P.pressure != air_sensor.pressure or P.humidity != air_sensor.humidity):
        pressure = air_sensor.pressure
        humidity = air_sensor.humidity
        sensor_readings.append({'specie': "pressure", 'value': pressure, 'unit': 'hPa'})
        sensor_readings.append({'specie': "humidity", 'value': humidity, 'unit': '%'})

    air_sensor = m.AirSensor.find_one({m.AirSensor.address: "front_garden_we_ds18b20"})
    if air_sensor is not None and P.temp != air_sensor.temperature:
        temp = air_sensor.temperature
        sensor_readings.append({'specie': "temp", 'value': temp, 'unit': 'C'})

    if len(sensor_readings) > 0:
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
            L.l.info("Uploaded air quality data pm2.5={} pm10={} temp={} hum={} pres={}".format(
                pm25, pm10, temp, humidity, pressure))

            if pm25 is not None or pm10 is not None:
                P.pm25 = pm25
                P.pm10 = pm10
            if temp is not None:
                P.temp = temp
            if humidity is not None:
                P.humidity = humidity
            if pressure is not None:
                P.pressure = pressure


def unload():
    pass


def init():
    L.l.info('Aqicn module initialising')
    # User parameter - get yours from https://aqicn.org/data-platform/token/
    P.token = common.get_secure_general("aqicn_token")
    thread_pool.add_interval_callable(upload_sensor, run_interval_second=60)
