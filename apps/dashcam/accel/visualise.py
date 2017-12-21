import pygame
import time
import urllib
from OpenGL.GL import *
from OpenGL.GLU import *
from math import radians
from pygame.locals import *

import filter

#  http://blog.bitify.co.uk/2013/11/3d-opengl-visualisation-of-data-from.html

SCREEN_SIZE = (800, 600)
SCALAR = .5
SCALAR2 = 0.2

value_store = [
    [0.5626373901367188, -9.923965881347655],
    [0.5363011718749999, -10.077194787597655],
    [0.5267243652343749, -9.95987890625],
    [0.634463439941,-9.82819781494],
[0.612915625,-9.95509050293],
[0.603338818359,-9.95987890625],
[0.572214196777,-10.0771947876],
[0.486022937012,-9.92636008301],
[0.737414111328,-9.99818613281]
]

new_store = [
[{'y': -0.49320554199218747, 'x': -9.528922607421874, 'z': 1.0414777221679687}, {'y': -0.8625954198473282, 'x': -3.0839694656488548, 'z': 0.7938931297709924}, 28.577058823529413]
,[{'y': -0.5267243652343749, 'x': -9.497797985839844, 'z': 0.9816226806640624}, {'y': -0.6183206106870229, 'x': -3.122137404580153, 'z': 0.5572519083969466}, 28.671176470588236]
,[{'y': -0.5147533569335937, 'x': -9.605537060546874, 'z': 0.9888052856445312}, {'y': -0.5343511450381679, 'x': -3.213740458015267, 'z': 0.7709923664122137}, 28.76529411764706]
,[{'y': -0.5195417602539062, 'x': -9.68454571533203, 'z': 0.9816226806640624}, {'y': -0.5038167938931297, 'x': -3.1526717557251906, 'z': 0.6335877862595419}, 28.671176470588236]
,[{'y': -0.4955997436523437, 'x': -9.665392102050781, 'z': 1.005564697265625}, {'y': -0.6870229007633588, 'x': -2.8931297709923665, 'z': 0.7557251908396947}, 28.624117647058824]
,[{'y': -0.4477157104492187, 'x': -9.598354455566406, 'z': 1.0271125122070313}, {'y': -0.8320610687022901, 'x': -3.1603053435114505, 'z': 0.7175572519083969}, 28.718235294117648]
,[{'y': -0.316034619140625, 'x': -9.562441430664062, 'z': 1.0127473022460938}, {'y': -0.7404580152671756, 'x': -3.1297709923664123, 'z': 0.7633587786259542}, 28.76529411764706]


]

def resize(width, height):
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, float(width) / height, 0.001, 10.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    gluLookAt(0.0, 1.0, -5.0,
              0.0, 0.0, 0.0,
              0.0, 1.0, 0.0)


def init():
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_BLEND)
    glEnable(GL_POLYGON_SMOOTH)
    glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
    glEnable(GL_COLOR_MATERIAL)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.3, 0.3, 0.3, 1.0));


def read_values(i):
    return value_store[i][0], value_store[i][1]


def run():
    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE, HWSURFACE | OPENGL | DOUBLEBUF)
    resize(*SCREEN_SIZE)
    init()
    clock = pygame.time.Clock()
    cube = Cube((0.0, 0.0, 0.0), (.5, .5, .7))
    angle = 0
    i = 0
    filter.filter_init(new_store[i][1]['x'], new_store[i][1]['y'], new_store[i][1]['z'],
                       new_store[i][0]['x'], new_store[i][0]['y'], new_store[i][0]['z'])
    i += 1
    while True:
        time.sleep(0.2)
        then = pygame.time.get_ticks()
        for event in pygame.event.get():
            if event.type == QUIT:
                return
            if event.type == KEYUP and event.key == K_ESCAPE:
                return

        #values = read_values(i)
        values = filter.filter_clean(new_store[i][1]['x'], new_store[i][1]['y'], new_store[i][1]['z'],
                                     new_store[i][0]['x'], new_store[i][0]['y'], new_store[i][0]['z'])
        i += 1
        x_angle = values[0]
        y_angle = values[1]

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glColor((1., 1., 1.))
        glLineWidth(1)
        glBegin(GL_LINES)

        for x in range(-20, 22, 2):
            glVertex3f(x / 10., -1, -1)
            glVertex3f(x / 10., -1, 1)

        for x in range(-20, 22, 2):
            glVertex3f(x / 10., -1, 1)
            glVertex3f(x / 10., 1, 1)

        for z in range(-10, 12, 2):
            glVertex3f(-2, -1, z / 10.)
            glVertex3f(2, -1, z / 10.)

        for z in range(-10, 12, 2):
            glVertex3f(-2, -1, z / 10.)
            glVertex3f(-2, 1, z / 10.)

        for z in range(-10, 12, 2):
            glVertex3f(2, -1, z / 10.)
            glVertex3f(2, 1, z / 10.)

        for y in range(-10, 12, 2):
            glVertex3f(-2, y / 10., 1)
            glVertex3f(2, y / 10., 1)

        for y in range(-10, 12, 2):
            glVertex3f(-2, y / 10., 1)
            glVertex3f(-2, y / 10., -1)

        for y in range(-10, 12, 2):
            glVertex3f(2, y / 10., 1)
            glVertex3f(2, y / 10., -1)

        glEnd()
        glPushMatrix()
        glRotate(float(x_angle), 1, 0, 0)
        glRotate(-float(y_angle), 0, 0, 1)
        cube.render()
        glPopMatrix()
        pygame.display.flip()


class Cube(object):

    def __init__(self, position, color):
        self.position = position
        self.color = color

    # Cube information
    num_faces = 6

    vertices = [(-1.0, -0.05, 0.5),
                (1.0, -0.05, 0.5),
                (1.0, 0.05, 0.5),
                (-1.0, 0.05, 0.5),
                (-1.0, -0.05, -0.5),
                (1.0, -0.05, -0.5),
                (1.0, 0.05, -0.5),
                (-1.0, 0.05, -0.5)]

    normals = [(0.0, 0.0, +1.0),  # front
               (0.0, 0.0, -1.0),  # back
               (+1.0, 0.0, 0.0),  # right
               (-1.0, 0.0, 0.0),  # left
               (0.0, +1.0, 0.0),  # top
               (0.0, -1.0, 0.0)]  # bottom

    vertex_indices = [(0, 1, 2, 3),  # front
                      (4, 5, 6, 7),  # back
                      (1, 5, 6, 2),  # right
                      (0, 4, 7, 3),  # left
                      (3, 2, 6, 7),  # top
                      (0, 1, 5, 4)]  # bottom

    def render(self):
        then = pygame.time.get_ticks()
        glColor(self.color)

        vertices = self.vertices

        # Draw all 6 faces of the cube
        glBegin(GL_QUADS)

        for face_no in xrange(self.num_faces):
            glNormal3dv(self.normals[face_no])
            v1, v2, v3, v4 = self.vertex_indices[face_no]
            glVertex(vertices[v1])
            glVertex(vertices[v2])
            glVertex(vertices[v3])
            glVertex(vertices[v4])
        glEnd()


if __name__ == "__main__":
    run()