import machine
from machine import UART
import time

tx_uart = None
rx_uart = None
last_resp = None
last_duty = 0
max_watts = 2400
max_threshold = -120
min_threshold = -20
drop_next_reading = False

# https://docs.micropython.org/en/latest/esp8266/tutorial/pwm.html


def update(power):
    global tx_uart, drop_next_reading, last_resp
    print("power={} last={}".format(power, last_resp))
    if tx_uart is None:
        init()
    if power < max_threshold:
        # we have export, divert to PWM
        divert_power = -power
        required_duty = float(100 * 0.8 * divert_power / max_watts)
        print("          delta +d={}".format(required_duty))
        # increase duty with the power export
        new_duty = min(required_duty + last_duty, 100)
        # set_duty(new_duty)
    elif power >= min_threshold:
        # need to lower pwm diverted power as we risk to import from grid
        divert_power = abs(power)
        required_duty = float(100 * divert_power / max_watts)
        print("          delta -d={}".format(required_duty))
        new_duty = max(last_duty - required_duty, 0)
        # set_duty(new_duty)


def init():
    global tx_uart, rx_uart, last_resp
    try:
        print("Trying TX UART init")
        # tx_uart = UART(1, 4800)
        print("TX init ok, sleeping for 20 sec")
        for i in range(0, 20):
            time.sleep(1)
        print("Trying RX UART init")
        rx_uart = UART(0, 4800)
        # https://docs.micropython.org/en/latest/esp8266/quickref.html?highlight=dht
        # Two UARTs are available. UART0 is on Pins 1 (TX) and 3 (RX).
        # UART0 is bidirectional, and by default is used for the REPL.
        # UART1 is on Pins 2 (TX) and 8 (RX) however Pin 8 is used to connect the flash chip, so UART1 is TX only.
        # Available pins are: 0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16,
        # which correspond to the actual GPIO pin numbers of ESP8266 chip.
        # Note that Pin(1) and Pin(3) are REPL UART TX and RX respectively.
        # D1/GPIO5 - SerBrTx (71) - connect to Drok pin T
        # D2/GPIO4 - SerVrRx (72) - connect to Drok pin R
        print("Trying TX full UART init")
        tx_uart.init(4800, bits=8, parity=None, stop=1)
        print("TX UART init ok")
        print("Trying RX full UART init")
        rx_uart.init(4800, bits=8, parity=None, stop=1)
        print("RX UART init ok")
        # time.sleep(30)
        print("Writing to read status")
        count = tx_uart.write('aro\r\n')
        if count is None:
            print("Timeout writing to uart")
        else:
            print("Written ok {} bytes".format(count))
        time.sleep(3)
        print("Reading response")
        # last_resp = rx_uart.readline()
        for r in range(0, 60):
            val = rx_uart.read()
            print("read={}".format(val))
            time.sleep(1)
        print("UART response={}".format(last_resp))
    except Exception as ex:
        print("Error init UART")
        last_resp = "{}".format(ex)
        tx_uart = None
        rx_uart = None

