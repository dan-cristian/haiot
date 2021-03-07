import machine

pin_pwm = None
pin_code = 13
pwm_frequency = 55
last_duty = 0
max_watts = 2400
max_threshold = -120
min_threshold = -20
drop_next_reading = False

# https://docs.micropython.org/en/latest/esp8266/tutorial/pwm.html


def set_duty(duty):
    global last_duty, drop_next_reading
    if pin_pwm is None:
        print("Pwm not yet initialised")
        init()
    # expect duty as a %
    if drop_next_reading:
        # wait for meter to pickup power change (needed when meter updates are sent fast, every 1s)
        print("Dropping this duty update")
        drop_next_reading = False
    else:
        print("                                duty={}%".format(duty))
        pin_pwm.duty(int(1023 * duty/100))
        last_duty = duty
        drop_next_reading = True


def update(power):
    global drop_next_reading
    print("power={}".format(power))
    if power < max_threshold:
        # we have export, divert to PWM
        divert_power = -power
        required_duty = float(100 * 0.8 * divert_power / max_watts)
        print("          delta +d={}".format(required_duty))
        # increase duty with the power export
        new_duty = min(required_duty + last_duty, 100)
        set_duty(new_duty)
    elif power >= min_threshold:
        # need to lower pwm diverted power as we risk to import from grid
        divert_power = abs(power)
        required_duty = float(100 * divert_power / max_watts)
        print("          delta -d={}".format(required_duty))
        new_duty = max(last_duty - required_duty, 0)
        set_duty(new_duty)


def init():
    global pin_pwm, pin_code, pwm_frequency
    if pin_pwm is not None:
        # stop this pwm before initialising another
        pin_pwm.duty(0)
    pin_pwm = machine.PWM(machine.Pin(pin_code), pwm_frequency)
    pin_pwm.duty(0)
