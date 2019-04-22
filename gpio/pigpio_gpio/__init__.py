import socket
import time
from threading import Thread, Lock
from pydispatch import dispatcher
from main.logger_helper import L
from common import Constant
from main import sqlitedb
from main import thread_pool
if sqlitedb:
    from main.admin import models
    from main.admin.model_helper import commit
from gpio.io_common import GpioBase
from main.tinydb_model import Pwm, GpioPin

__author__ = 'Dan Cristian <dan.cristian@gmail.com>'

# http://abyz.co.uk/rpi/pigpio/download.html
# http://abyz.co.uk/rpi/pigpio/python.html
# https://ms-iot.github.io/content/images/PinMappings/RP2_Pinout.png


class P:
    import_ok = False
    initialised = False
    callback = []
    pi = None
    pwm = None
    callback_thread = None
    pin_tick_dict = {}  # {InputEvent}
    lock_dict = {}  # lock list for each gpio

    def __init__(self):
        pass


class Logx:
    def __init__(self):
        pass

    class Logger:
        def __init__(self):
            pass

        @staticmethod
        def info(text):
            print(text)

    logger = Logger()


try:
    import pigpio
    P.import_ok = True
except Exception as ex:
    P.import_ok = False
    L.l.info('Not importing pigpio_gpio, message={}'.format(ex))

'''
http://abyz.co.uk/rpi/pigpio_gpio/index.html

ALL gpios are identified by their Broadcom number.  See elinux.org
There are 54 gpios in total, arranged in two banks.
Bank 1 contains gpios 0-31.  Bank 2 contains gpios 32-54.
A user should only manipulate gpios in bank 1.
There are at least three types of board.
Type 1

26 pin header (P1).
Hardware revision numbers of 2 and 3.
User gpios 0-1, 4, 7-11, 14-15, 17-18, 21-25.
Type 2

26 pin header (P1) and an additional 8 pin header (P5).
Hardware revision numbers of 4, 5, 6, and 15.
User gpios 2-4, 7-11, 14-15, 17-18, 22-25, 27-31.
Type 3

40 pin expansion header (J8).
Hardware revision numbers of 16 or greater.
User gpios 2-27 (0 and 1 are reserved).
It is safe to read all the gpios. If you try to write a system gpio or change its mode you can crash the Pi
or corrupt the data on the SD card.
'''


class InputEvent:
    def __init__(self, gpio, level, tick):
        self.tick = tick
        self.level = level
        self.gpio = gpio
        self.event_count = 0
        self.processed = False

    def __repr__(self):
        return 'gpio={} level={} tick={} count={} processed={}'.format(self.gpio, self.level, self.tick,
                                                                       self.event_count, self.processed)


def get_pin_value(pin_index_bcm=None):
    return P.pi.read(pin_index_bcm)


def set_pin_value(pin_index_bcm=None, pin_value=None):
    P.pi.write(pin_index_bcm, pin_value)
    return get_pin_value(pin_index_bcm=pin_index_bcm)


def announce_event(event):
    L.l.info("DISPATCH IN io={} lvl={} count={} tick={}".format(event.gpio, event.level, event.event_count,
                                                                event.tick))
    # pin connected state assumes pins are pull-up enabled
    dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=event.gpio,
                    direction=Constant.GPIO_PIN_DIRECTION_IN,
                    pin_value=event.level, pin_connected=(event.level == 0))


# executed by a haiot thread (not by gpiopd thread)
def check_notify_event(event):
    # print("Debounce thread started for event {}".format(event))
    all_events_processed = False
    while not all_events_processed:
        time.sleep(0.1)  # latency in detecting changes
        current_tick = P.pi.get_current_tick()
        all_events_processed = True
        for event in P.pin_tick_dict.values():
            lock = P.lock_dict[event.gpio]
            lock.acquire()
            try:
                # debounce period
                if not event.processed and (current_tick - event.tick > 100000):
                    # event old enough to not be a noise event
                    announce_event(event)
                    event.processed = True
                if not event.processed:
                    all_events_processed = False
            finally:
                lock.release()
    # print("Debounce thread exit")
    P.callback_thread = None


# executed by gpiopd thread
def input_event(gpio, level, tick):
    pin_tick_event = P.pin_tick_dict.get(gpio)
    current = P.pi.get_current_tick()
    delta = current - tick
    if pin_tick_event and pin_tick_event.processed:
        # reset event to initial state
        pin_tick_event.event_count = 0
        pin_tick_event.processed = False
    if not pin_tick_event or pin_tick_event.event_count == 0:
        pin_tick_event = InputEvent(gpio, level, tick)
        pin_tick_event.event_count += 1
        P.pin_tick_dict[gpio] = pin_tick_event
        # anounce first state change
        announce_event(pin_tick_event)
    else:
        if tick < pin_tick_event.tick:
            # ignore record events in the past
            L.l.debug("Ignore old gpio={} lvl={} tick={} current={} delta={}".format(gpio, level, tick, current, delta))
        else:
            lock = P.lock_dict.get(gpio)
            if not lock:
                lock = Lock()
                P.lock_dict[gpio] = lock
            lock.acquire()
            try:
                pin_tick_event.level = level
                pin_tick_event.tick = tick
                pin_tick_event.event_count += 1
                # start a thread if not already started to notify the event completion without bounce
                if P.callback_thread is None:
                    P.callback_thread = Thread(target=check_notify_event, args=(pin_tick_event,))
                    P.callback_thread.start()
            finally:
                lock.release()


class PwmIo(GpioBase):
    key_ok = 0

    @staticmethod
    def get_db_record(key):
        # m = models.Pwm
        # rec = m().query_filter_first(m.name == 'boiler2')

        # rec = models.Pwm.query.filter_by(name=key).first()
        if sqlitedb:
            rec = models.Pwm.query.get(key)
        else:
            rec = Pwm.find_one({Pwm.name: key})
        # rec = dbs.session.query(models.Pwm).filter(models.Pwm.name == key).first()
        # db.session.remove()
        # rec = db.session.query(models.Pwm).filter(models.Pwm.name == key).first()

        if rec is not None and rec.id == key:
            # PwmIo.key_ok = PwmIo.key_ok + 1
            # L.l.info("KEY found ok {}, count={}".format(key, PwmIo.key_ok))
            return rec
        # recs = models.Pwm.query.all()
        # if recs is not None:
        #    for rec in recs:
        #        if rec.name == key:
        #            L.l.info("KEY found ok {}, count={}".format(key, PwmIo.key_ok))
        #            return rec
        L.l.error('No key retrieved for pwm {}, got {}'.format(key, rec))
        return None

    @staticmethod
    def _get_pwm_attrib(gpio):
        is_started = True
        try:
            frequency = P.pi.get_PWM_frequency(gpio)
        except Exception as ex:
            frequency = 0
            is_started = False
        try:
            duty_cycle = P.pi.get_PWM_dutycycle(gpio)
        except Exception as ex:
            duty_cycle = 0
            is_started = False
        return is_started, frequency, duty_cycle 

    @staticmethod
    def sync_2_db(key):
        pwm = PwmIo.get_db_record(key=key)
        if pwm is not None:
            if pwm.host_name == Constant.HOST_NAME:
                pwm.is_started, pwm.frequency, pwm.duty_cycle = PwmIo._get_pwm_attrib(pwm.gpio_pin_code)
                pwm.commit_record_to_db_notify()
        else:
            L.l.warning("Cannot find pwm {} to sync2db".format(key))

    @staticmethod
    def _init_pwm():
        if sqlitedb:
            pwm_list = models.Pwm.query.filter_by(host_name=Constant.HOST_NAME).all()
        else:
            pwm_list = Pwm.find({Pwm.host_name: Constant.HOST_NAME})
        for pwm in pwm_list:
            PwmIo.sync_2_db(pwm.id)
        pass

    @staticmethod
    def set(key, **kwargs):
        pwm = PwmIo.get_db_record(key=key)
        if pwm is not None:
            if sqlitedb:
                new_pwm = models.Pwm(id=0)
            else:
                new_pwm = Pwm()
            new_pwm.name = pwm.name
            for name, value in kwargs.items():
                if name == 'frequency':
                    new_pwm.frequency = value
                elif name == 'duty_cycle':
                    new_pwm.duty_cycle = value
                elif name == 'is_started':
                    new_pwm.is_started = value
            if pwm.host_name == Constant.HOST_NAME and P.pi is not None:  # condition for debug
                if pwm.is_started:
                    L.l.info("Set PWM {} to frequency {} duty {}".format(
                        pwm.gpio_pin_code, pwm.frequency, pwm.duty_cycle))
                    P.pi.hardware_PWM(pwm.gpio_pin_code, pwm.frequency, pwm.duty_cycle)
                else:
                    L.l.info("Stop PWM {} ".format(pwm.gpio_pin_code))
                    P.pi.hardware_PWM(pwm.gpio_pin_code, pwm.frequency, 0)
            L.l.info("Saving status PWM {} {} to frequency {} duty old={} new={}".format(
                key, pwm.gpio_pin_code, new_pwm.frequency, pwm.duty_cycle, new_pwm.duty_cycle))
            new_pwm.save_changed_fields(
                current_record=pwm, new_record=new_pwm, notify_transport_enabled=True, force_dirty=False, debug=False)
        else:
            L.l.warning("Cannot find pwm {} to set".format(key))

    @staticmethod
    def save(key, **kwargs):
        pwm = PwmIo.get_db_record(key=key)
        if pwm is not None:
            for key, value in kwargs.items():
                if key == 'frequency':
                    pwm.frequency = value
                elif key == 'duty_cycle':
                    pwm.duty_cycle = value
                elif key == 'is_started':
                    pwm.is_started = value
            pwm.commit_record_to_db()
        else:
            L.l.warning("Cannot find pwm {} to save".format(key))

    @staticmethod
    def get(key):
        pwm = PwmIo.get_db_record(key=key)
        if pwm is not None:
            if pwm.host_name == Constant.HOST_NAME:
                return PwmIo._get_pwm_attrib(pwm.gpio_pin_code)
            else:
                return pwm.is_started, pwm.frequency, pwm.duty_cycle
        else:
            L.l.warning("Cannot find pwm {} on get".format(key))
            return None, None, None

    @staticmethod
    def get_current_record(record):
        rec = PwmIo.get_db_record(key=record.id)
        if rec is not None:
            return rec, rec.id
        else:
            return None, None

    @staticmethod
    def unload():
        if sqlitedb:
            pwm_list = models.Pwm.query.filter_by(host_name=Constant.HOST_NAME).all()
        else:
            pwm_list = Pwm.find({Pwm.host_name: Constant.HOST_NAME})
        for pwm in pwm_list:
            try:
                P.pi.hardware_PWM(pwm.gpio_pin_code, 0, 0)
            except Exception as ex:
                L.l.warning("Unable to unload pwm gpio {}, er={}".format(pwm.gpio_pin_code, ex))

    def __init__(self, obj):
        GpioBase.__init__(self, obj)
        # PwmIo._init_pwm()


def not_used_pwm_record_update(json_object):
    P.pwm.record_update(json_object)


def _pwm_upsert_listener(record):
    P.pwm.record_update(record)


def _setup_in_ports(gpio_pin_list):
    # Log.logger.info('Socket timeout={}'.format(socket.getdefaulttimeout()))
    # socket.setdefaulttimeout(None)
    L.l.info('Configuring {} gpio input ports'.format(len(gpio_pin_list)))
    if P.pi:
        if socket.getdefaulttimeout() is not None:
            L.l.critical('PiGpio callbacks cannot be started as socket timeout is not None')
        else:
            for gpio_pin in gpio_pin_list:
                if gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_STDGPIO:
                    try:
                        L.l.info('Set pincode={} type={} index={} as input'.format(
                            gpio_pin.pin_code, gpio_pin.pin_type, gpio_pin.pin_index_bcm))
                        P.pi.set_mode(int(gpio_pin.pin_index_bcm), pigpio.INPUT)
                        # https://learn.sparkfun.com/tutorials/pull-up-resistors
                        P.pi.set_pull_up_down(int(gpio_pin.pin_index_bcm), pigpio.PUD_UP)
                        P.callback.append(P.pi.callback(user_gpio=int(gpio_pin.pin_index_bcm),
                                                        edge=pigpio.EITHER_EDGE, func=input_event))
                        if sqlitedb:
                            gpio_pin_record = models.GpioPin().query_filter_first(
                                models.GpioPin.pin_code.in_([gpio_pin.pin_code]),
                                models.GpioPin.host_name.in_([Constant.HOST_NAME]))
                        else:
                            curr_rec = GpioPin.find_one({GpioPin.pin_code: gpio_pin.pin_code,
                                                         GpioPin.host_name: Constant.HOST_NAME})
                            gpio_pin_record = GpioPin()
                            if curr_rec is not None:
                                gpio_pin_record.pin_code = curr_rec.pin_code
                        gpio_pin_record.pin_direction = Constant.GPIO_PIN_DIRECTION_IN
                        if sqlitedb:
                            commit()
                        else:
                            gpio_pin_record.save_changed_fields(current=curr_rec, broadcast=False, persist=True)
                    except Exception as ex1:
                        L.l.critical('Unable to setup pigpio_gpio pin, er={}'.format(ex1))
                else:
                    L.l.info('Skipping PiGpio setup for pin {} with type {}'.format(gpio_pin.pin_code,
                                                                                    gpio_pin.pin_type))
        L.l.info('Exit gpio callback thread loop')
    else:
        L.l.critical('PiGpio not yet initialised but was asked to setup IN ports. Check module init order.')


def thread_run():
    pass


def unload():
    P.callback = []
    if P.initialised:
        P.pwm.unload()
        P.pi.stop()


def init():
    if sqlitedb:
        P.pwm = PwmIo(obj=models.Pwm)
    else:
        P.pwm = PwmIo(obj=Pwm)
    L.l.info('PiGpio initialising')
    if P.import_ok:
        try:
            if Constant.HOST_NAME != 'netbook':  # debug
                P.pi = pigpio.pi()
                # test if daemon is on
                P.pi.get_current_tick()
                # setup this to receive list of ports that must be set as "IN" and have callbacks defined
                # dispatcher.connect(setup_in_ports, signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST, sender=dispatcher.Any)
            P.initialised = True
            Pwm.add_upsert_listener(_pwm_upsert_listener)
            thread_pool.add_interval_callable(thread_run, run_interval_second=30)
            L.l.info('PiGpio initialised OK')
        except Exception as ex1:
            L.l.info('Unable to initialise PiGpio, err={}'.format(ex1))
            P.pi = None
            P.initialised = False
    else:
        L.l.info('PiGpio NOT initialised, module unavailable on this system')
