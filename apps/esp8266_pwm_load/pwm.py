import machine

pin_pwm = None
pin_code = 13
pwm_frequency = 55
last_diverted_power = 0
last_duty = 0
max_watts = 2400
threshold = -75

# https://docs.micropython.org/en/latest/esp8266/tutorial/pwm.html


def set_duty(duty):
    global last_duty
    if pin_pwm is None:
        print("Pwm not yet initialised")
        init()
    # expect duty as a %
    print("Set duty={}%".format(duty))
    pin_pwm.duty(int(1023 * duty/100))
    last_duty = duty


def update(power):
    global last_diverted_power
    print("Got power={}".format(power))
    if power < threshold:
        # we have export, divert to PWM
        divert_power = -power
        required_duty = int(100 * 0.9 * divert_power / max_watts)
        # increase duty with the power export
        new_duty = min(required_duty + last_duty, 100)
        set_duty(new_duty)
    elif power >= 0:
        # need to lower pwm diverted power as we import from grid
        required_duty = int(100 * power / max_watts)
        new_duty = max(last_duty - required_duty, 0)
        set_duty(new_duty)


def init():
    global pin_pwm, pin_code, pwm_frequency
    if pin_pwm is not None:
        # stop this pwm before initialising another
        pin_pwm.duty(0)
    pin_pwm = machine.PWM(machine.Pin(pin_code), pwm_frequency)
    pin_pwm.duty(0)
