from common import Constant
from main.admin import models


# update in db without propagatting the change
def update_custom_relay(pin_code, pin_value):
    gpio = models.GpioPin.query.filter_by(pin_code=pin_code, host_name=Constant.HOST_NAME).first()
    if gpio is not None:
        gpio.pin_value = int(pin_value)
        gpio.notify_transport_enabled = False
        gpio.commit_record_to_db()
    relay = models.ZoneCustomRelay.query.filter_by(gpio_pin_code=pin_code, gpio_host_name=Constant.HOST_NAME).first()
    if relay is not None:
        relay.relay_is_on = bool(pin_value)
        relay.notify_transport_enabled = False
        relay.commit_record_to_db()
