from webui.api import api_v1
from main.logger_helper import Log
from main import app

# carefull with API fields order to match app.route definition
def update_custom_relay(relay_pin_name, power_is_on):
    # with app.test_client() as c:
    msg = api_v1.generic_db_update(model_name="ZoneCustomRelay", filter_name="relay_pin_name",
                                   field_name="relay_is_on", filter_value=relay_pin_name, field_value=power_is_on)
    #    msg = c.get('/apiv1/db_update/model_name=ZoneCustomRelay&'
    #                'filter_name=relay_pin_name&field_name=relay_is_on&filter_value={}&field_value={}'.
    #                format(relay_pin_name, power_is_on)).data
    Log.logger.info(msg)
