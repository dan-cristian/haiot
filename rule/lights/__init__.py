from main.logger_helper import L
from rule import rule_common
from storage.model import m


def rule_start_lights(obj=m.ZoneAlarm(), change=None):
    if obj.alarm_pin_triggered:
        if hasattr(obj, 'target_relay') and obj.target_relay is not None:
            # switch on relay
            rule_common.update_custom_relay(obj.target_relay, True)
            return True
    return False

