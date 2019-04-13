from datetime import datetime
from tinydb_helper import TinyBase


class Module(TinyBase):
    def __init__(self):
        self.id = 0
        self.name = ''
        self.start_order = 0
        self.active = False
        self.host_name = ''
        TinyBase.__init__(self, dict(self.__dict__))
        Module.coll = self.coll


class Pwm(TinyBase):
    def __init__(self):
        self.id = 0
        self.name = ''
        self.frequency = 0
        self.duty_cycle = 0
        self.gpio_pin_code = 0
        self.host_name = ''
        self.update_on = datetime.now()
        TinyBase.__init__(self, dict(self.__dict__))


