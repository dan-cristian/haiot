import sys
import pygame
import os
import io
import glob
import errno
try:
    from rpusbdisp import Touchscreen
    _disp_initialised = True
except Exception, ex:
    print ex
    _disp_initialised = False

UI_DFROBOT_2_8 = True
TOUCHSCREEN_EVDEV_NAME = 'RoboPeakUSBDisplayTS'
_width = 100
_height = 80
_screen = None

initialised = False
_button_list = []
_ts = None

black = (0, 0, 0)
white = (255, 255, 255)
red = (255, 0, 0)
green = (0, 255, 0)
blue = (0, 0, 255)
bright_red = (255, 0, 0)
bright_green = (100, 255, 0)

#https://pythonprogramming.net/pygame-button-function-events/
# https://www.dfrobot.com/product-1062.html

#https://github.com/adafruit/adafruit-pi-cam/blob/master/cam.py

def _get_touch_device():
    for evdev in glob.glob("/sys/class/input/event*"):
        try:
            with io.open(os.path.join(evdev, 'device', 'name'), 'r') as f:
                if f.read().strip() == TOUCHSCREEN_EVDEV_NAME:
                    dev_name = os.path.join('/dev', 'input', os.path.basename(evdev))
                    print "Device name is: " + dev_name
                    return dev_name
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
    raise RuntimeError('Unable to locate touchscreen device')


if UI_DFROBOT_2_8:
    os.environ["SDL_FBDEV"] = "/dev/fb1"
    os.environ["SDL_MOUSEDRV"] = "TSLIB"
    #os.environ["SDL_MOUSEDEV"] = _get_touch_device()
    _width = 320
    _height = 240


def text_objects(text, font):
    textsurface = font.render(text, True, white)
    return textsurface, textsurface.get_rect()


def status(text):
    pygame.draw.rect(_screen, black, (0, 0, 150, 10))
    #_screen.fill(black)
    font = pygame.font.SysFont("comicsansms", 10)
    textsurface = font.render(text, True, white)
    textrect = textsurface.get_rect()
    textrect.left = 0
    textrect.top = 0
    _screen.blit(textsurface, textrect)
    pygame.display.update()


class Button:
    def __init__(self, msg, x, y, w, h, ic, ac, action=None):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.ic, self.ac = ic, ac
        self.action = action
        self.msg = msg
        self.do_event()

    def do_event(self, clicked = False):
        mouse = pygame.mouse.get_pos()
        #click = pygame.mouse.get_pressed()
        print 'Click {} = {}'.format(self.msg, clicked)

        smalltext = pygame.font.SysFont("comicsansms", 20)
        if self.x + self.w > mouse[0] > self.x and self.y + self.h > mouse[1] > self.y:
            if not clicked and self.action is not None:
                pygame.draw.rect(_screen, self.ac, (self.x, self.y, self.w, self.h))
                smalltext = pygame.font.SysFont("comicsansms", 24)
                pygame.display.update()
            if clicked and self.action is not None:
                self.action()
        pygame.draw.rect(_screen, self.ic, (self.x, self.y, self.w, self.h))
        # draw button label
        textsurf, textrect = text_objects(self.msg, smalltext)
        textrect.center = ((self.x+(self.w/2)), (self.y+(self.h/2)))
        _screen.blit(textsurf, textrect)
        pygame.display.update()


def button1():
    status('butonul 1')


def button2():
    status('al 2-lea buton')
    _ts.stop()
    pygame.quit()
    quit()


def button3():
    status('cele 3 butoane')


def loop():
    global initialised
    print 'Looping dashcam UI'
    clock = pygame.time.Clock()
    try:
        while initialised:
            for event in pygame.event.get():
                print(event)
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                for btn in _button_list:
                    btn.do_event()
            clock.tick(15)
    finally:
        _ts.stop()


def handle_press(event, touch):
    print(["Release", "Press", "Move"][event],
          touch.slot,
          touch.x,
          touch.y)
    for btn in _button_list:
        btn.do_event(False)


def handle_release(event, touch):
    print(["Release", "Press", "Move"][event],
          touch.slot,
          touch.x,
          touch.y)
    for btn in _button_list:
        btn.do_event(True)


def handle_move(event, touch):
    pygame.mouse.set_pos(touch.x, touch.y)


def init():
    print 'Initialising dashcam UI'
    global _screen, initialised, _button_list, _ts

    pygame.init()
    print 'pygame initialised'
    size = width, height = _width, _height
    print 'pygame set mode {}'.format(size)
    _screen = pygame.display.set_mode(size)
    _screen.fill(black)
    largetext = pygame.font.Font('freesansbold.ttf', 20)
    textsurf, textrect = text_objects("A bit Racey", largetext)
    textrect.center = ((_width/2), (_height/2))
    _screen.blit(textsurf, textrect)

    _button_list.append(
        Button("GO", 15, 150, 100, 30, green, blue, button1))
    _button_list.append(
        Button("Quit", 200, 150, 100, 30, red, bright_red, button2))
    _button_list.append(
        Button("Cucu", 100, 30, 100, 30, blue, green, button3))

    if _disp_initialised:
        _ts = Touchscreen()
        for touch in _ts.touches:
            touch.on_press = handle_press
            touch.on_release = handle_release
            touch.on_move = handle_move
        _ts.run()

    pygame.event.set_blocked(pygame.MOUSEMOTION)
    pygame.event.set_blocked(pygame.MOUSEBUTTONDOWN)
    pygame.event.set_blocked(pygame.MOUSEBUTTONUP)
    pygame.mouse.set_visible(False)

    pygame.display.update()
    initialised = True


if __name__ == '__main__':
    init()
    loop()
