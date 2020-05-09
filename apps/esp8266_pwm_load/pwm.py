import machine

pin_pwm = None


def set_duty(duty):
    global pin_pwm
    pin_pwm.duty(duty)


def set_frequency(frequency):
    global pin_pwm
    pin_pwm.freq(frequency)


def init(pin, frequency):
    global pin_pwm
    pin_pwm = machine.PWM(machine.Pin(pin), frequency)
    pin_pwm.duty(0)
