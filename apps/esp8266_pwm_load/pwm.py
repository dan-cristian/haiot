import machine

pin_code = None
pin_pwm = None

# https://docs.micropython.org/en/latest/esp8266/tutorial/pwm.html


def set_duty(duty):
    global pin_pwm
    if pin_pwm is None:
        print("Pwm not yet initialised")
        return
    # expect duty as a %
    pin_pwm.duty(int(1023 * duty/100))


def set_frequency(frequency):
    global pin_pwm
    if pin_pwm is None:
        print("Pwm not yet initialised")
        return
    pin_pwm.freq(frequency)


def set_pin(pin):
    if pin_code != pin:
        init(pin, 0)


def init(pin, frequency):
    global pin_pwm, pin_code
    if pin_pwm is not None:
        # stop this pwm before initialising another
        pin_pwm.duty(0)
    pin_pwm = machine.PWM(machine.Pin(pin), frequency)
    pin_pwm.duty(0)
    pin_code = pin
