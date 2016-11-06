from time import sleep
import pifacedigitalio


def door_open(event):
    print "Hello"
    pifacedigital.leds[0].value = 1


def door_closed(event):
    print "Bebop"
    pifacedigital.leds[0].value = 0


def switch_pressed(event):
    print "Hello2"
    pifacedigital.leds[1].value = 1


def switch_unpressed(event):
    print "Bebop2"
    pifacedigital.leds[1].value = 0


pifacedigital = pifacedigitalio.PiFaceDigital()
print 'Doorbell Server Started\r'

listener = pifacedigitalio.InputEventListener(chip=pifacedigital)
listener.register(1, pifacedigitalio.IODIR_OFF, door_open)
listener.register(1, pifacedigitalio.IODIR_ON, door_closed)
listener.register(4, pifacedigitalio.IODIR_ON, switch_pressed)
listener.register(4, pifacedigitalio.IODIR_OFF, switch_unpressed)
listener.activate()

while True:
    sleep(3600)  # or any very long time
