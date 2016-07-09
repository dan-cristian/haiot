from webui.api import api_v1
from main.logger_helper import Log
from main import app
from main.admin import models
from common import Constant
# import mpd
from main.admin.model_helper import get_param


def update_custom_relay(relay_pin_name, power_is_on):
    """carefull with API fields order to match app.route definition """
    # with app.test_client() as c:
    msg = api_v1.generic_db_update(model_name="ZoneCustomRelay", filter_name="relay_pin_name",
                                   field_name="relay_is_on", filter_value=relay_pin_name, field_value=power_is_on)
    #    msg = c.get('/apiv1/db_update/model_name=ZoneCustomRelay&'
    #                'filter_name=relay_pin_name&field_name=relay_is_on&filter_value={}&field_value={}'.
    #                format(relay_pin_name, power_is_on)).data
    Log.logger.info(msg)


def update_command_override_relay(relay_pin_name, is_rule, is_gui):
    m = models.ZoneCustomRelay
    relay_row = m().query_filter_first(m.host_name.in_([Constant.HOST_NAME]), m.relay_pin_name.in_([relay_pin_name]))

    m = models.CommandOverrideRelay
    override_row = m().query_filter_first(m.host_name.in_([Constant.HOST_NAME]), m.relay_pin_name.in_([relay_pin_name]))


def play_bell():
    # client = mpd.MPDClient(use_unicode=True)
    # client.connect(get_param(Constant.P_MPD_SERVER), 6600)
    pass