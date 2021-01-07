"""
    Configuration file, stores all the global variables, imports etc that every module needs
"""
################ Dependencies #################################################
import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import pyrr
import random
import pathlib
import os
################ Pygame Setup #################################################
pygame.init()

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
SCREEN = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT),
                                    pygame.DOUBLEBUF|pygame.OPENGL)
CLOCK = pygame.time.Clock()
pygame.mouse.set_visible(False)
################ OpenGL Setup #################################################
glClearColor(0.5,0.5,0.5,1)
glEnable(GL_BLEND)
glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
glEnable(GL_DEPTH_TEST)
glEnable(GL_CULL_FACE)
glCullFace(GL_BACK)
TEXTURE_RESOLUTION = 32
################ Shader Setup #################################################
with open("shaders/vertex.txt",'r') as f:
    vertex_src = f.readlines()
with open("shaders/fragment.txt",'r') as f:
    fragment_src = f.readlines()

shader = compileProgram(compileShader(vertex_src,GL_VERTEX_SHADER),
                        compileShader(fragment_src,GL_FRAGMENT_SHADER))

with open("shaders/vertex2D.txt",'r') as f:
    vertex_src = f.readlines()
with open("shaders/fragment2D.txt",'r') as f:
    fragment_src = f.readlines()

shader2D = compileProgram(compileShader(vertex_src,GL_VERTEX_SHADER),
                        compileShader(fragment_src,GL_FRAGMENT_SHADER))

glUseProgram(shader)
MAX_LIGHTS = 8
CURRENT_LIGHTS = 0

glUniform1i(glGetUniformLocation(shader,"material.diffuse"),0)
glUniform1i(glGetUniformLocation(shader,"material.specular"),1)
################ Global variables #############################################
SECTORS = []
CEILING_MODELS = []
WALL_MODELS = []
FLOOR_MODELS = []
LIGHTS = []
TEXTURES = {"sector":[],"misc":[],"enemies":[]}
###############################################################################
