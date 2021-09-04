__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

import urllib.request
from main.logger_helper import L
from common import Constant, utils, get_json_param
from main import thread_pool
from storage.model import m


class P:
    initialised = False
    interval = 60
    # APS SOLAR ECU LINK: http://192.168.0.10/cgi-bin/home
    start_keyword = 'Lifetime generation</td><td align=center>'
    end_keyword = ' kWh</td>'
    start_keyword_now = 'Last System Power</td><td align=center>'
    end_keyword_now = ' W</td>'
    # APS Temperature params: 192.168.0.10/cgi-bin/parameters
    start_key_temp = '<td align=center> '
    end_key_temp = '&nbsp;<sup>o</sup>C'
    start_key_panel = '<td align=center>'
    end_key_panel = '-A</td>'

    def __init__(self):
        pass


def init_solar_aps():
    try:
        production = utils.parse_http(get_json_param(Constant.P_SOLAR_APS_LOCAL_URL), P.start_keyword, P.end_keyword)
        if production is not None and production is not '':
            P.initialised = True
        else:
            P.initialised = False
        return P.initialised
    except Exception as ex:
        L.l.warning("Unable to connect to aps solar server, ex={}".format(ex))


def thread_run():
    if not P.initialised:
        init_solar_aps()
    if P.initialised:
        try:
            aps_text = str(urllib.request.urlopen(get_json_param(Constant.P_SOLAR_APS_LOCAL_URL)).read())
            production = utils.parse_text(aps_text, P.start_keyword, P.end_keyword)
            last_power = utils.parse_text(aps_text, P.start_keyword_now, P.end_keyword_now)
            temperature = utils.parse_text(aps_text, P.start_key_temp, P.end_key_temp, end_first=True)
            panel_id = utils.parse_text(aps_text, P.start_key_panel, P.end_key_panel, end_first=True)
            utility_name = get_json_param(Constant.P_SOLAR_UTILITY_NAME)
            if temperature is not None:
                zone_sensor = m.ZoneSensor.find_one({m.ZoneSensor.sensor_address: panel_id})
                if zone_sensor is None:
                    L.l.warning('Solar panel id {} is not defined in zone sensor list'.format(panel_id))
                record = m.Sensor.find_one({m.Sensor.address: panel_id})
                if record is None:
                    record = m.Sensor()
                    record.address = panel_id
                    record.type = 'solar'
                    if zone_sensor:
                        record.sensor_name = zone_sensor.sensor_name
                    else:
                        record.sensor_name = record.type + panel_id
                record.temperature = temperature
                record.updated_on = utils.get_base_location_now_date()
                # fixme: keeps saving same temp even when panels are off. stop during night.
                record.save_changed_fields(broadcast=True, persist=True)
            if production is not None:
                production = float(production)
                record = m.Utility.find_one({m.Utility.utility_name: utility_name})
                if record is None:
                    record = m.Utility()
                    record.utility_name = utility_name
                    record.units_delta = production
                    record.units_total = production
                else:
                    if record.units_total is None:
                        record.units_total = production
                        record.units_delta = 0
                    else:
                        record.units_delta = production - record.units_total
                        if record.units_delta == 0:
                            # do not waste db space if no power generated
                            L.l.info('Solar production is energy={} watts={} temp={}'.format(
                                production, last_power, temperature))
                            # return
                        else:
                            L.l.info('Solar production is {}'.format(record.units_delta))
                record.units_2_delta = last_power
                # L.l.info('Solar watts is {}'.format(last_power))
                if record.unit_cost is None:
                    record.unit_cost = 0.0
                record.cost = 1.0 * record.units_delta * record.unit_cost
                record.save_changed_fields(broadcast=True, persist=True)
            else:
                L.l.info('Solar production is none')
        except Exception as ex:
            L.l.error("Got exception on solar thread run, ex={}".format(ex), exc_info=True)


def unload():
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval)
