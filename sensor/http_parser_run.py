__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

from main.logger_helper import L
from common import Constant, utils, variable
from main.admin import models, model_helper

# APS SOLAR ECU LINK: http://192.168.0.10/cgi-bin/home
_initialised_solar_aps = False
__start_keyword = 'Lifetime generation</td><td align=center>'
__end_keyword = ' kWh</td>'
__start_keyword_now = 'Last System Power</td><td align=center>'
__end_keyword_now = ' W</td>'
# APS Temperature params: 192.168.0.10/cgi-bin/parameters
__start_key_temp = '<td align=center> '
__end_key_temp = '&nbsp;<sup>o</sup>C'
__start_key_panel = '<td align=center>'
__end_key_panel = '-A</td>'


def init_solar_aps():
    global __start_keyword, __end_keyword, _initialised_solar_aps
    try:
        production = utils.parse_http(model_helper.get_param(Constant.P_SOLAR_APS_LOCAL_URL),
                                      __start_keyword, __end_keyword)
        if production is not None and production is not '':
            _initialised_solar_aps = True
        else:
            _initialised_solar_aps = False
        return _initialised_solar_aps
    except Exception, ex:
        L.l.warning("Unable to connect to aps solar server, ex={}".format(ex))


def thread_solar_aps_run():
    global __start_keyword, __end_keyword, _initialised_solar_aps
    if not _initialised_solar_aps:
        init_solar_aps()
    if variable.NODE_THIS_IS_MASTER_OVERALL and _initialised_solar_aps:
        try:
            production = utils.parse_http(model_helper.get_param(Constant.P_SOLAR_APS_LOCAL_URL),
                                          __start_keyword, __end_keyword)
            last_power = utils.parse_http(model_helper.get_param(Constant.P_SOLAR_APS_LOCAL_URL),
                                          __start_keyword_now, __end_keyword_now)
            temperature = utils.parse_http(model_helper.get_param(Constant.P_SOLAR_APS_LOCAL_REALTIME_URL),
                                           __start_key_temp, __end_key_temp, end_first=True)
            panel_id = utils.parse_http(model_helper.get_param(Constant.P_SOLAR_APS_LOCAL_REALTIME_URL),
                                        __start_key_panel, __end_key_panel, end_first=True)
            utility_name = model_helper.get_param(Constant.P_SOLAR_UTILITY_NAME)
            if temperature is not None:
                record = models.Sensor(address=panel_id)
                current_record = models.Sensor.query.filter_by(address=panel_id).first()
                record.type = 'solar aps'
                # record.sensor_name = 'solar' + panel_id
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
                                           notify_transport_enabled=True, save_to_graph=True, save_all_fields=True)
        except Exception, ex:
            L.l.warning("Got exception on solar thread run, ex={}".format(ex))


