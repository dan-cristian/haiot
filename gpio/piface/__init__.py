import time
from gpio.io_common import format_piface_pin_code
from pydispatch import dispatcher
from main.logger_helper import L
from main import thread_pool
from common import Constant, fix_module
from gpio import io_common

while True:
    try:
        #if Constant.is_os_linux():
        import pifacedigitalio as pfio
        break
    except ImportError as iex:
        if not fix_module(iex):
            break

__author__ = 'Dan Cristian <dan.cristian@gmail.com>'


# https://piface.github.io/pifacedigitalio/example.html
class P:
    import_ok = False
    pfd = {}
    listener = {}
    listeners_active = False
    initialised = False
    board_init = False
    gpio_ports = [25, 24, 23, 22]
    input_pin_val = {}
    input_pin_dir = {}
    # pool_pin_codes = []

    def __init__(self):
        pass


try:
    # import pifacedigitalio as pfio
    from pifacedigitalio.core import NoPiFaceDigitalDetectedError
    import pifacecommon
    from pifacecommon.spi import SPIInitError
    from pifacecommon import interrupts
    P.import_ok = True
except Exception as ex:
    P.import_ok = False
    L.l.info('Pifacedigitalio module not available due to {}'.format(ex))


class InputEventListenerMulti(pfio.InputEventListener):
    def __init__(self, chip=None):
        # monkey patch
        pifacecommon.interrupts.GPIO_INTERRUPT_DEVICE_VALUE = \
            pifacecommon.interrupts.GPIO_INTERRUPT_DEVICE_VALUE.replace('25', P.gpio_ports[chip])
        pfio.InputEventListener.__init__(self, chip)


class GPIOInterruptDeviceMulti(interrupts.GPIOInterruptDevice):
    def __init__(self, gpio):
        L.l.info('Initialising custom piface interrupts on GPIO {}'.format(gpio))
        self.GPIO_INTERRUPT_PIN = gpio
        self.GPIO_INTERRUPT_DEVICE = "/sys/class/gpio/gpio%d" % self.GPIO_INTERRUPT_PIN
        self.GPIO_INTERRUPT_DEVICE_EDGE = '%s/edge' % self.GPIO_INTERRUPT_DEVICE
        self.GPIO_INTERRUPT_DEVICE_VALUE = '%s/value' % self.GPIO_INTERRUPT_DEVICE
        super(interrupts.GPIOInterruptDevice, self).__init__()

    def bring_gpio_interrupt_into_userspace(self):  # activate gpio interrupt
        """Bring the interrupt pin on the GPIO into Linux userspace."""
        try:
            # is it already there?
            with open(self.GPIO_INTERRUPT_DEVICE_VALUE):
                return
        except IOError:
            # no, bring it into userspace
            with open(interrupts.GPIO_EXPORT_FILE, 'w') as export_file:
                export_file.write(str(self.GPIO_INTERRUPT_PIN))
            interrupts.wait_until_file_exists(self.GPIO_INTERRUPT_DEVICE_VALUE)

    def deactivate_gpio_interrupt(self):
        """Remove the GPIO interrupt pin from Linux userspace."""
        with open(interrupts.GPIO_UNEXPORT_FILE, 'w') as unexport_file:
            unexport_file.write(str(self.GPIO_INTERRUPT_PIN))

    def set_gpio_interrupt_edge(self, edge='falling'):
        """Set the interrupt edge on the userspace GPIO pin.

        :param edge: The interrupt edge ('none', 'falling', 'rising').
        :type edge: string
        """
        # we're only interested in the falling edge (1 -> 0)
        start_time = time.time()
        time_limit = start_time + interrupts.FILE_IO_TIMEOUT
        while time.time() < time_limit:
            try:
                with open(self.GPIO_INTERRUPT_DEVICE_EDGE, 'w') as gpio_edge:
                    gpio_edge.write(edge)
                    return
            except IOError:
                pass

    """A device that interrupts using the GPIO pins."""
    def gpio_interrupts_enable(self):
        """Enables GPIO interrupts."""
        try:
            self.bring_gpio_interrupt_into_userspace()
            self.set_gpio_interrupt_edge()
        except interrupts.Timeout as e:
            raise IOError("There was an error bringing gpio{} into userspace. {}".format(self.GPIO_INTERRUPT_PIN, e))

    def gpio_interrupts_disable(self):
        """Disables gpio interrupts."""
        self.set_gpio_interrupt_edge('none')
        self.deactivate_gpio_interrupt()


class PiFaceDigitalMulti(pfio.PiFaceDigital, pifacecommon.mcp23s17.MCP23S17, GPIOInterruptDeviceMulti):
    DEFAULT_SPI_BUS = 0
    DEFAULT_SPI_CHIP_SELECT = 0
    MAX_BOARDS = 4

    def __init__(self, hardware_addr=0, bus=DEFAULT_SPI_BUS, chip_select=DEFAULT_SPI_CHIP_SELECT,
                 init_board=True, gpio=25):
        GPIOInterruptDeviceMulti.__init__(self, gpio)
        pfio.PiFaceDigital.__init__(self, hardware_addr, bus, chip_select)


# To read the state of an input use the pfio.digital_read(pin) function. If a button is
# pressed the function returns a 1, otherwise it returns a 0.
def _get_in_pin_value(pin_index, board_index):
    try:
        return P.pfd[board_index].input_pins[pin_index].value
        # return pfio.digital_read(pin_num=pin_index, hardware_addr=board_index)
    except Exception as ex:
        L.l.error('Unable to read pin {} board {}, err={}'.format(pin_index, board_index, ex))
        return None


def get_out_pin_value(pin_index, board_index):
    out_pin = None
    try:
        out_pin = P.pfd[board_index].output_pins[pin_index]
        # if isinstance(out_pin, int):
        #    return out_pin
        # else:
        return out_pin.value
    except Exception as ex:
        L.l.error('Out error pin val={}, board={}, index={}, err={}'.format(
            out_pin, board_index, pin_index, ex), exc_info=True)
        return None


def set_pin_code_value(pin_code, pin_value):
    if Constant.debug_dummy:
        return pin_value
    board, direction, pin = io_common.decode_piface_pin(pin_code)
    return set_pin_value(pin_index=pin, pin_value=pin_value, board_index=board)


# http://www.farnell.com/datasheets/1881551.pdf
def set_pin_value(pin_index, pin_value, board_index):
    L.l.info('Set piface pin {} to value={}, board {}'.format(pin_index, pin_value, board_index))
    if Constant.debug_dummy: return pin_value
    try:
        #pfio.digital_write(pin_num=pin_index, value=pin_value, hardware_addr=board_index)
        P.pfd[board_index].output_pins[pin_index].value = pin_value
        act_value = get_out_pin_value(pin_index=pin_index, board_index=board_index)
        if pin_value != act_value:
            L.l.warning("Piface set pin {} failed, actual value={}".format(pin_index, act_value))
        return act_value
    except Exception as ex:
        L.l.error('Unable to set pin {}:{}, ex={}'.format(pin_index, board_index, ex))
        return None


# for normal open contacts
def _input_event_reversed(event):
    _input_event(event, reversed=True)


def _input_event(event, reversed=False):
    # L.l.info('Piface switch event={}'.format(event))
    pin_num = event.pin_num
    board_index = event.chip.hardware_addr
    gpio_pin_code = format_piface_pin_code(board_index=board_index, pin_direction=Constant.GPIO_PIN_DIRECTION_IN,
                                           pin_index=pin_num)
    # direction gives different results than pin value, not used, reading value instead
    direction = event.direction  # 0 for press/contact, 1 for release/disconnect
    if direction != P.input_pin_dir[board_index][pin_num]:
        pin_val = _get_in_pin_value(pin_num, board_index)
        P.input_pin_val[board_index][pin_num] = pin_val
        P.input_pin_dir[board_index][pin_num] = direction
        L.l.info('Event piface gpio={} direction={} val={}'.format(gpio_pin_code, direction, pin_val))
        pin_connected = (direction == 0)
        if reversed:
            pin_connected = not pin_connected
        dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=gpio_pin_code, direction=Constant.GPIO_PIN_DIRECTION_IN,
                        pin_value=pin_val, pin_connected=pin_connected)
    else:
        L.l.info('Duplicate input event pin {} direction {}'.format(gpio_pin_code, direction))


#  define all ports that are used as read/input
#  port format is x:direction:y, e.g. 0:in:3, x=board, direction=in/out, y=pin index (0 based)
# !!! make sure piface listener is enabled in the same thread, and pin index is integer
def _setup_in_ports_pif(gpio_pin_list):
    for gpio_pin in gpio_pin_list:
        if gpio_pin.pin_type == Constant.GPIO_PIN_TYPE_PI_FACE_SPI:
            # Log.logger.info('Set piface code={} type={} index={}'.format(
            #    gpio_pin.pin_code,gpio_pin.pin_type, gpio_pin.pin_index_bcm))
            board = None
            try:
                # Log.logger.info("Piface registering input pin {}".format(gpio_pin.pin_index_bcm))
                pin = int(gpio_pin.pin_index_bcm)
                board = int(gpio_pin.board_index)
                if board in P.listener.keys():
                    if gpio_pin.contact_type == Constant.CONTACT_TYPE_NO:
                        P.listener[board].register(pin, pfio.IODIR_ON, _input_event_reversed)
                        P.listener[board].register(pin, pfio.IODIR_OFF, _input_event_reversed)
                    else:
                        P.listener[board].register(pin, pfio.IODIR_ON, _input_event)
                        P.listener[board].register(pin, pfio.IODIR_OFF, _input_event)
                    val = _get_in_pin_value(pin_index=pin, board_index=board)
                    L.l.info('Callback OK board {} code {} pin {} val {}'.format(board, gpio_pin.pin_code, pin, val))
            except Exception as ex:
                L.l.critical('Unable to setup piface listener board={} pin={} err={}'.format(
                    board, gpio_pin.pin_code, ex))



def _setup_board():
    # if Constant.MACHINE_TYPE_RASPBERRY or Constant.MACHINE_TYPE_ODROID:
    try:
        chip_range = [0, 1]
        board_range = [0, 1, 2, 3]
        if Constant.IS_MACHINE_ODROID:
            bus = 32766
        else:
            # Constant.IS_MACHINE_RASPBERRYPI:
            bus = 0
        last_err = ''
        # for chip in chip_range:
        #    try:
                # L.l.info("Try piface init on spi spidev{}.{}".format(bus, chip))
        #        pfio.init(bus=bus, chip_select=chip)
        #        P.chip_list.append(chip)
        #        L.l.info("Initialised piface spi spidev{}.{} OK".format(bus, chip))
            # except SPIInitError as ex1:
        #    except Exception as ex1:
        #        last_err += "{}".format(ex1)
        #if len(P.chip_list) == 0:
        #    L.l.warning("Unable to init spi, probably not spi not enabled, last err={}".format(last_err))
        #else:
        #    L.l.info('Found {} piface chips {}'.format(len(P.chip_list), P.chip_list))
        #last_err = ''
        # pftest = PiFaceDigitalMulti(hardware_addr=0, bus=bus, chip_select=0, init_board=True, gpio=24)
        for chip in chip_range:
            last_err = ''
            board_count = len(P.pfd)
            for board in board_range:
                try:
                    L.l.info("Try piface pfio on board-hw {} spidev{}.{}".format(board, bus, chip))
                    pfd = pfio.PiFaceDigital(hardware_addr=board, bus=bus, chip_select=chip, init_board=True)
                    # pfd = PiFaceDigitalMulti(
                    #    hardware_addr=board, bus=bus, chip_select=chip, init_board=True, gpio=P.gpio_ports[board])
                    gpio = pifacecommon.interrupts.GPIO_INTERRUPT_DEVICE_VALUE
                    L.l.info('Default gpio on board {} is {}'.format(board, gpio))
                    # monkey patch
                    # pifacecommon.interrupts.GPIO_INTERRUPT_DEVICE_VALUE = gpio.replace('25', str(P.gpio_ports[board]))
                    P.listener[board] = pfio.InputEventListener(chip=pfd)
                    P.pfd[board] = pfd
                    P.input_pin_val[board] = [None] * 8
                    P.input_pin_dir[board] = [None] * 8
                    gpio = pifacecommon.interrupts.GPIO_INTERRUPT_DEVICE_VALUE
                    L.l.info("Initialised piface pfio listener board-hw {} spidev{}.{} interrupt {}".format(
                        board, bus, chip, gpio))
                except Exception as ex2:
                    last_err += "{}".format(ex2)
                    # L.l.info('Piface detect returned exception {}'.format(ex2))
            if board_count == len(P.pfd):
                L.l.info('No board at index {}, errs={}'.format(board, last_err))
        if len(P.pfd) == 0:
            L.l.warning('Piface setup failed, no boards found')
        else:
            L.l.info('Initialised {} piface listeners'.format(len(P.pfd)))
            P.board_init = True
    except Exception as ex:
        L.l.critical('Piface setup board failed, err={}'.format(ex), exc_info=True)


# not used
def thread_run():
    # polling inputs
    for board in P.pfd.keys():
        for pin in range(0, 8):
            pin_val = _get_in_pin_value(pin, board)
            if pin_val != P.input_pin_val[board][pin]:
                L.l.info('Pooled event piface board {} pin={} val={}'.format(board, pin, pin_val))
                gpio_pin_code = format_piface_pin_code(
                    board_index=board, pin_direction=Constant.GPIO_PIN_DIRECTION_IN, pin_index=pin)
                dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=gpio_pin_code,
                                direction=Constant.GPIO_PIN_DIRECTION_IN,
                                pin_value=pin_val, pin_connected=(pin_val == 1))
                P.input_pin_val[board][pin] = pin_val


def unload():
    L.l.info('Piface unloading')
    if P.import_ok:
        pass
        # pfio.deinit_board()


def post_init_relay_value(gpio_pin_code):
    if P.board_init:
        board, direction, pin = io_common.decode_piface_pin(gpio_pin_code)
        return get_out_pin_value(pin_index=pin, board_index=board)
    else:
        return None


def post_init_alarm_value(gpio_pin_code):
    board, direction, pin = io_common.decode_piface_pin(gpio_pin_code)
    pin_val = _get_in_pin_value(pin_index=pin, board_index=board)
    if pin_val is not None:
        pin_connected = (pin_val == 1)
        return pin_connected
    else:
        return None


def post_init():
    if P.initialised:
        L.l.info('Running post_init piface !!!!!!!!!!!!!!!!!!!!!!!!!!')
        # read default values
        if False:
            for board in P.pfd.keys():
                for pin in range(8):
                    gpio_pin_code = format_piface_pin_code(board_index=board, pin_direction=Constant.GPIO_PIN_DIRECTION_OUT,
                                                           pin_index=pin)
                    pin_out_val = get_out_pin_value(pin_index=pin, board_index=board)
                    L.l.info('Read out pin {} value={}'.format(gpio_pin_code, pin_out_val))
                    io_common.update_custom_relay(
                        pin_code=gpio_pin_code, pin_value=pin_out_val, notify=True, ignore_missing=True)
                    gpio_pin_code = format_piface_pin_code(board_index=board, pin_direction=Constant.GPIO_PIN_DIRECTION_IN,
                                                           pin_index=pin)
                    pin_in_val = _get_in_pin_value(pin_index=pin, board_index=board)
                    L.l.info('Read input pin {} value={}'.format(gpio_pin_code, pin_in_val))
                    io_common.update_custom_relay(
                        pin_code=gpio_pin_code, pin_value=pin_in_val, notify=True, ignore_missing=True)
                    # resend to ensure is received by other late init modules like openhab
                    dispatcher.send(Constant.SIGNAL_GPIO, gpio_pin_code=gpio_pin_code,
                                    direction=Constant.GPIO_PIN_DIRECTION_IN,
                                    pin_value=pin_in_val, pin_connected=(pin_in_val == 1))
        if not P.listeners_active:
            for li in P.listener.values():
                li.activate()
                P.listeners_active = True
            L.l.info('Activating listeners done')


def init():
    L.l.info('Piface initialising')
    if P.import_ok:
        try:
            _setup_board()
            if P.board_init:
                # thread_pool.add_interval_callable(thread_run, run_interval_second=10)
                dispatcher.connect(_setup_in_ports_pif, signal=Constant.SIGNAL_GPIO_INPUT_PORT_LIST,
                                   sender=dispatcher.Any)
                # thread_pool.add_interval_callable(thread_run, run_interval_second=1)
                P.initialised = True
                L.l.info('Piface initialised OK')
        except Exception as ex1:
            L.l.info('Piface not initialised, err={}'.format(ex1))

        if Constant.HOST_NAME == 'netbook':
            P.initialised = True
    else:
        L.l.info('Piface not initialised, module pifacedigitalio unavailable on this system')
