import machine

pin_pwm = None

# https://docs.micropython.org/en/latest/esp8266/tutorial/pwm.html


def set_duty(duty):
    global pin_pwm
    # expect duty as a %
    pin_pwm.duty(int(1023 * duty/100))


def set_frequency(frequency):
    global pin_pwm
    pin_pwm.freq(frequency)


def init(pin, frequency):
    global pin_pwm
    pin_pwm = machine.PWM(machine.Pin(pin), frequency)
    pin_pwm.duty(0)
