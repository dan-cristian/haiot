from datetime import datetime
from main.logger_helper import L
from main.admin import models
from rule import rule_common


class P:
    grid_watts = None
    plug1_watts = None
    last_state_change = datetime.min
    PLUG1_MIN_WATTS = 20
    EXPORT_MIN_WATTS = -50
    RELAY_1_NAME = 'plug_1'
    STATE_CHANGE_INTERVAL = 60  # how often can change state
    grid_importing = None

    def __init__(self):
        pass


def _can_state_change():
    return (datetime.now() - P.last_state_change).total_seconds() > P.STATE_CHANGE_INTERVAL


# energy rule
def rule_energy_export(obj=models.Utility(), field_changed_list=None):
    if field_changed_list is not None:
        if 'units_2_delta' in field_changed_list:
            if obj.utility_name == 'power main mono':
                P.grid_watts = obj.units_2_delta
            elif obj.utility_name == 'power plug 1':
                P.plug1_watts = obj.units_2_delta
            if P.grid_watts is not None and P.grid_watts < 0:
                if P.grid_importing is True or P.grid_importing is None:
                    L.l.info("Exporting power {}w".format(P.grid_watts))
                    P.grid_importing = False
                if P.grid_watts < P.EXPORT_MIN_WATTS and _can_state_change():
                    L.l.info("Starting plug 1 to reduce export, grid={}".format(P.grid_watts))
                    rule_common.update_custom_relay(relay_pin_name=P.RELAY_1_NAME, power_is_on=True)
                    P.last_state_change = datetime.now()
            else:
                if P.grid_importing is False or P.grid_importing is None:
                    L.l.info("Importing power {}w".format(P.grid_watts))
                    P.grid_importing = True
                if P.plug1_watts is not None and P.plug1_watts > P.PLUG1_MIN_WATTS and _can_state_change():
                    L.l.info("Stopping plug 1 to cut import, plug {}w, grid {}w".format(P.plug1_watts, P.grid_watts))
                    rule_common.update_custom_relay(relay_pin_name=P.RELAY_1_NAME, power_is_on=False)
                    P.last_state_change = datetime.now()
