import sys
import pygame
import os

UI_DFROBOT_2_8 = True
_width = 100
_height = 80
_screen = None

initialised = False
_button_list = []

#https://pythonprogramming.net/pygame-button-function-events/
# https://www.dfrobot.com/product-1062.html
if UI_DFROBOT_2_8:
    os.environ["SDL_FBDEV"] = "/dev/fb1"
    _width = 320
    _height = 240


def text_objects(text, font):
    white = (255, 255, 255)
    textsurface = font.render(text, True, white)
    return textsurface, textsurface.get_rect()


def status(text):
    white = (255, 255, 255)
    black = (0, 0, 0)
    _screen.fill(black)
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

    def do_event(self):
        global _screen
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()

        print(click)
        smalltext = pygame.font.SysFont("comicsansms", 20)
        if self.x + self.w > mouse[0] > self.x and self.y + self.h > mouse[1] > self.y:
            pygame.draw.rect(_screen, self.ac, (self.x, self.y, self.w, self.h))
            if click[0] == 1 and self.action is not None:
                smalltext = pygame.font.SysFont("comicsansms", 24)
                self.action()
        else:
            pygame.draw.rect(_screen, self.ic, (self.x, self.y, self.w, self.h))
        textsurf, textrect = text_objects(self.msg, smalltext)
        textrect.center = ((self.x+(self.w/2)), (self.y+(self.h/2)))
        _screen.blit(textsurf, textrect)
        pygame.display.update()


def button1():
    status('butonul 1')


def button2():
    status('al 2-lea buton')
    pygame.quit()
    quit()


def loop():
    global initialised, _button_list
    clock = pygame.time.Clock()
    while initialised:
        for event in pygame.event.get():
            print(event)
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            for btn in _button_list:
                btn.do_event()
            clock.tick(15)


def init():
    global _width, _height, _screen, initialised, _button_list
    black = (0, 0, 0)
    white = (255, 255, 255)
    red = (255, 0, 0)
    green = (0, 255, 0)
    blue = (0, 0, 255)
    bright_red = (255, 0, 0)
    bright_green = (0, 255, 0)
    pygame.init()
    size = width, height = _width, _height
    _screen = pygame.display.set_mode(size)
    _screen.fill(black)
    largetext = pygame.font.Font('freesansbold.ttf', 20)
    textsurf, textrect = text_objects("A bit Racey", largetext)
    textrect.center = ((_width/2), (_height/2))
    _screen.blit(textsurf, textrect)
    _button_list.append(
        Button("GO", 15, 150, 100, 30, green, bright_green, button1))
    _button_list.append(
        Button("Quit", 200, 150, 100, 30, red, bright_red, button2))
    pygame.display.update()
    initialised = True


if __name__ == '__main__':
    init()
    loop()
