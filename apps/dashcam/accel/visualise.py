import pygame, sys
from pygame.locals import *
import time
import urllib
import json
import math


def read_values():
    link = "http://127.0.0.1:9000"
    #link = "http://192.168.0.17:9000"
    f = urllib.urlopen(link)
    myfile = f.read()
    var = json.loads(myfile)
    return var


def get_y_rotation(x,y,z):
    radians = math.atan2(x, dist(y,z))
    return -math.degrees(radians)


def get_x_rotation(x,y,z):
    radians = math.atan2(y, dist(x,z))
    return math.degrees(radians)


def dist(a, b):
    return math.sqrt((a * a) + (b * b))


def init():
    pygame.init()
    # set up the graphics window
    WINDOW = pygame.display.set_mode((400, 300), 0, 32)
    pygame.display.set_caption('MPU_6050 Demo')
    # set up the colors
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    # draw on the surface object
    WINDOW.fill(WHITE)

    now = time.time()

    K = 0.98
    K1 = 1 - K
    time_diff = 0.01

    v = read_values()
    last_x = get_x_rotation(v[0]['x'], v[0]['y'], v[0]['z'])
    last_y = get_y_rotation(v[0]['x'], v[0]['y'], v[0]['z'])
    gyro_scaled_x = v[1]['x']
    gyro_scaled_y = v[1]['y']

    gyro_offset_x = gyro_scaled_x
    gyro_offset_y = gyro_scaled_y

    gyro_total_x = last_x - gyro_offset_x
    gyro_total_y = last_y - gyro_offset_y

    # run the loop
    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        time.sleep(time_diff - 0.005)
        v = read_values()
        gyro_scaled_x = v[1]['x']
        gyro_scaled_y = v[1]['y']
        gyro_scaled_z = v[1]['z']
        accel_scaled_x = v[0]['x']
        accel_scaled_y = v[0]['y']
        accel_scaled_z = v[0]['z']

        gyro_scaled_x -= gyro_offset_x
        gyro_scaled_y -= gyro_offset_y

        gyro_x_delta = (gyro_scaled_x * time_diff)
        gyro_y_delta = (gyro_scaled_y * time_diff)

        gyro_total_x += gyro_x_delta
        gyro_total_y += gyro_y_delta

        rotation_x = get_x_rotation(accel_scaled_x, accel_scaled_y, accel_scaled_z)
        rotation_y = get_y_rotation(accel_scaled_x, accel_scaled_y, accel_scaled_z)

        last_x = K * (last_x + gyro_x_delta) + (K1 * rotation_x)
        last_y = K * (last_y + gyro_y_delta) + (K1 * rotation_y)

        # print last_x,last_y on terminal window
        print (last_x), (last_y)

        delta_y = math.radians(last_y)

        # z-is thickness of the line
        z = 2 * int(last_x)
        if z < 0:
            z = -z
            COLOR = RED  # change colour if x-axis reading is negative
        else:
            COLOR = BLUE
        if z == 0:
            z = 1

        x1 = 200 - (100 * math.cos(delta_y))
        y1 = 150 + (100 * math.sin(delta_y))
        x2 = 200 + (100 * math.cos(delta_y))
        y2 = 150 - (100 * math.sin(delta_y))

        # print (x1), (y1) ,(x2), (y2)
        WINDOW.fill(WHITE)  # clear window before redraw

        # simply draw the plane, z-is thickness: change thickness of the line to appear 3D
        pygame.draw.line(WINDOW, COLOR, (x1, y1), (x2, y2), z)
        pygame.display.update()


if __name__ == "__main__":
    init()
