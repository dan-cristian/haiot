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
    sensor = m.DustSensor.find_one({m.AirSensor.address: "wemos-curte-air_pms5003"})
    if sensor is not None:
        pm25 = sensor.pm_2_5
        pm10 = sensor.pm_10
        if P.pm25 != pm25 or P.pm10 != pm10:
            # Then Upload the data
            last_sensor_readings = [
                {'specie': "pm2.5", 'value': pm25},
                {'specie': "pm10", 'value': pm10}]
            params = {'token': P.token, 'station': P.station, 'readings': last_sensor_readings}

            # data_in = urllib.parse.urlencode(params).encode('utf-8')
            # req = urllib.request.Request(url="https://aqicn.org/sensor/upload/", data=data_in, method='POST')
            # resp = urllib.request.urlopen(req)
            # data = json.loads(resp.read())

            request = requests.post(url="https://aqicn.org/sensor/upload/", json=params)
            data = request.json()

            if data['status'] != "ok":
                L.l.warning("Error posting sensor, {} {}".format(data['status'], data['reason']))
            else:
                L.l.info("Uploaded air quality data pm2.5={} pm10={}".format(pm25, pm10))
                P.pm25 = pm25
                P.pm10 = pm10
    else:
        L.l.info("No air quality sensor matching for upload")


def unload():
    pass


def init():
    L.l.info('Aqicn module initialising')
    # User parameter - get yours from https://aqicn.org/data-platform/token/
    P.token = common.get_secure_general("aqicn_token")
    thread_pool.add_interval_callable(upload_sensor, run_interval_second=60)
