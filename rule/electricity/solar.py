from main.logger_helper import L
from main.admin import models
from rule import rule_common


class P:
    grid_watts = 0
    plug1_watts = 0
    PLUG1_MIN_WATTS = 10
    EXPORT_MIN_WATTS = -100
    RELAY_1_NAME = 'plug_1'

    def __init__(self):
        pass


# energy rule
def rule_energy_export(obj=models.Utility(), field_changed_list=None):
    if field_changed_list is not None:
        if 'units_2_delta' in field_changed_list:
            if obj.utility_name == 'power main mono':
                P.grid_watts = obj.units_2_delta
            elif obj.utility_name == 'power plug 1':
                P.plug1_watts = obj.units_2_delta
            if P.grid_watts < 0:
                L.l.info("Exporting power {}w".format(P.grid_watts))
                if P.grid_watts < P.EXPORT_MIN_WATTS:
                    L.l.info("Starting plug 1 additional power consumption")
                    rule_common.update_custom_relay(relay_pin_name=P.RELAY_1_NAME, power_is_on=True)
            else:
                L.l.info("Importing power {}w".format(P.grid_watts))
                if P.plug1_watts > P.PLUG1_MIN_WATTS:
                    L.l.info("Stopping plug 1 due to consumption {}w".format(P.plug1_watts))
                    rule_common.update_custom_relay(relay_pin_name=P.RELAY_1_NAME, power_is_on=False)
