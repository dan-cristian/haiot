from common import Constant

from storage.model import m
from main.logger_helper import L
import abc
from common import utils


# update in db (without propagatting the change by default)
def update_custom_relay(pin_code, pin_value, notify=False, ignore_missing=False):
    relay = m.ZoneCustomRelay.find_one({m.ZoneCustomRelay.gpio_pin_code: pin_code,
                                        m.ZoneCustomRelay.gpio_host_name: Constant.HOST_NAME})
    if relay is not None:
        relay.relay_is_on = pin_value
        relay.save_changed_fields(broadcast=notify)
        L.l.info('Updated relay {} val={}'.format(pin_code, pin_value))
    else:
        if not ignore_missing:
            L.l.warning('Unable to find relay pin {}'.format(pin_code))


# update in db (without propagatting the change by default)
def update_listener_custom_relay(relay, is_on):
    relay.relay_is_on = is_on
    relay.save_changed_fields(broadcast=True)
    L.l.info('Updated listener relay {} val={}'.format(relay, is_on))


class Port:
    _port_list = []
    type = None
    TYPE_GPIO = 'gpio'
    TYPE_PIFACE = 'piface'
    TYPE_PCF8574 = 'pcf8574'
    _types = frozenset([TYPE_GPIO, TYPE_PIFACE, TYPE_PCF8574])

    def __init__(self):
        pass


class OutputPort(Port):

    def __init__(self):
        pass


class InputPort(Port):

    def __init__(self):
        pass


class IOPort(InputPort, OutputPort):

    def __init__(self):
        pass


class GpioBase:
    __metaclass__ = abc.ABCMeta

    @staticmethod
    @abc.abstractmethod
    def get_current_record(record):
        return None, None
    
    @staticmethod
    @abc.abstractmethod
    def get_db_record(key):
        return None

    def record_update(self, record, changed_fields):
        # record = utils.json_to_record(self.obj, json_object)
        current_record, key = self.get_current_record(record)
        if current_record is not None:
            new_record = self.obj()
            kwargs = {}
            for field in changed_fields:
                val = getattr(record, field)
                # setattr(new_record, field, val)
                kwargs[field] = val
            if record.host_name == Constant.HOST_NAME and record.source_host != Constant.HOST_NAME:
                # https://stackoverflow.com/questions/1496346/passing-a-list-of-kwargs
                self.set(key, **kwargs)
                # do nothing, action done already as it was local
            # save will be done on model.save
            # record.save_changed_fields()

    @staticmethod
    @abc.abstractmethod
    def set(key, values):
        pass

    @staticmethod
    @abc.abstractmethod
    def save(key, values):
        pass

    @staticmethod
    @abc.abstractmethod
    def get(key):
        return None

    @staticmethod
    @abc.abstractmethod
    def sync_to_db(key):
        pass

    @staticmethod
    @abc.abstractmethod
    def unload():
        pass

    def __init__(self, obj):
        self.obj = obj


def format_piface_pin_code(board_index, pin_direction, pin_index):
    return str(board_index) + ":" + str(pin_direction) + ":" + str(pin_index)


#  port format is x:direction:y, e.g. 0:in:3, x=board, direction=in/out, y=pin index (0 based)
def decode_piface_pin(pin_code):
    ar = pin_code.split(':')
    if len(ar) == 3:
        return int(ar[0]), ar[1], int(ar[2])
    else:
        L.l.error('Invalid piface pin code {}'.format(pin_code))
        return None, None, None