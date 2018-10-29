__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

from main.logger_helper import L
from common import Constant, utils
from main.admin import models, model_helper
from main import thread_pool


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
        production = utils.parse_http(model_helper.get_param(Constant.P_SOLAR_APS_LOCAL_URL),
                                      P.start_keyword, P.end_keyword)
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
            production = utils.parse_http(model_helper.get_param(Constant.P_SOLAR_APS_LOCAL_URL),
                                          P.start_keyword, P.end_keyword)
            last_power = utils.parse_http(model_helper.get_param(Constant.P_SOLAR_APS_LOCAL_URL),
                                          P.start_keyword_now, P.end_keyword_now)
            temperature = utils.parse_http(model_helper.get_param(Constant.P_SOLAR_APS_LOCAL_REALTIME_URL),
                                           P.start_key_temp, P.end_key_temp, end_first=True)
            panel_id = utils.parse_http(model_helper.get_param(Constant.P_SOLAR_APS_LOCAL_REALTIME_URL),
                                        P.start_key_panel, P.end_key_panel, end_first=True)
            utility_name = model_helper.get_param(Constant.P_SOLAR_UTILITY_NAME)
            if temperature is not None:
                zone_sensor = models.ZoneSensor.query.filter_by(sensor_address=panel_id).first()
                if zone_sensor is None:
                    L.l.warning('Solar panel id {} is not defined in zone sensor list'.format(panel_id))
                record = models.Sensor(address=panel_id)
                current_record = models.Sensor.query.filter_by(address=panel_id).first()
                record.type = 'solar'
                if current_record is not None:
                    record.sensor_name = current_record.sensor_name
                else:
                    if zone_sensor:
                        record.sensor_name = zone_sensor.sensor_name
                    else:
                        record.sensor_name = record.type + panel_id
                record.temperature = temperature
                record.updated_on = utils.get_base_location_now_date()
                record.save_changed_fields(current_record=current_record, new_record=record,
                                           notify_transport_enabled=True, save_to_graph=True, debug=False)
            if production is not None:
                production = float(production)
                record = models.Utility()
                record.utility_name = utility_name
                current_record = models.Utility.query.filter_by(utility_name=utility_name).first()
                if current_record is not None:
                    if current_record.units_total is None:
                        record.units_delta = 0
                    else:
                        record.units_delta = production - current_record.units_total
                        if record.units_delta == 0:
                            # do not waste db space if no power generated
                            return
                    record.units_total = production
                    record.unit_name = current_record.unit_name
                    record.units_2_delta = last_power
                    record.unit_2_name = current_record.unit_2_name
                else:
                    record.units_delta = production
                    record.units_total = production
                if current_record.unit_cost is None:
                    current_record.unit_cost = 0.0
                record.cost = 1.0 * record.units_delta * current_record.unit_cost
                record.save_changed_fields(current_record=current_record, new_record=record, debug=False,
                                           notify_transport_enabled=True, save_to_graph=True, save_all_fields=False)
        except Exception as ex:
            L.l.warning("Got exception on solar thread run, ex={}".format(ex))


def unload():
    thread_pool.remove_callable(thread_run)
    P.initialised = False


def init():
    thread_pool.add_interval_callable(thread_run, run_interval_second=P.interval)
