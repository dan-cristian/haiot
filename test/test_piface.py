from time import sleep
import pifacedigitalio

def input_event(event):
    print ('Piface switch event={}'.format(event))

pifacedigital = pifacedigitalio.PiFaceDigital()
print 'Doorbell Server Started\r'

listener = pifacedigitalio.InputEventListener(chip=pifacedigital)
for i in range(8):
    listener.register(i, pifacedigitalio.IODIR_OFF, input_event)
    listener.register(i, pifacedigitalio.IODIR_ON, input_event)
listener.activate()

while True:
    sleep(3600)  # or any very long time
