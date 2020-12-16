################ 3D Game ######################################################
import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import pyrr
import random
import pywavefront as pwf


pygame.init()

SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
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

################ Shaders ######################################################

with open("shaders/vertex.txt",'r') as f:
    vertex_src = f.readlines()
with open("shaders/fragment.txt",'r') as f:
    fragment_src = f.readlines()

shader = compileProgram(compileShader(vertex_src,GL_VERTEX_SHADER),
                        compileShader(fragment_src,GL_FRAGMENT_SHADER))

glUseProgram(shader)
MAX_LIGHTS = 8
current_lights = 0

glUniform1i(glGetUniformLocation(shader,"material.diffuse"),0)
glUniform1i(glGetUniformLocation(shader,"material.specular"),1)

################ Helper Functions #############################################

def importData(filename):
    """
        Reads a file and loads all objects, returns a reference to the player
        object.
    """
    with open(filename,'r') as f:
        line = f.readline()
        while line:
            beginning = line.find('(')
            tag = line[0:beginning]
            if line[0]=='w':
                #wall
                # w(a_x,a_y,b_x,b_y,z,height,tex)
                line = line[beginning+1:-2].replace('\n','').split(',')
                l = [int(item) for item in line]
                pos_a = np.array([l[0],l[1],l[4]],dtype=np.float32)
                pos_b = np.array([l[2],l[3],l[4]],dtype=np.float32)
                z = l[4]
                height = l[5]
                tex = TEXTURES["wall"][l[6]]
                obj = Wall(pos_a,pos_b,z,height,tex)
                GAME_OBJECTS.append(obj)
                WALLS.append(obj)
            elif line[0]=='f':
                #floor
                # w(a_x,a_y,b_x,b_y,c_x,c_y,d_x,d_y,z,tex)
                line = line[beginning+1:-2].replace('\n','').split(',')
                l = [int(item) for item in line]
                pos_a = np.array([l[0],l[1],l[8]],dtype=np.float32)
                pos_b = np.array([l[2],l[3],l[8]],dtype=np.float32)
                pos_c = np.array([l[4],l[5],l[8]],dtype=np.float32)
                pos_d = np.array([l[6],l[7],l[8]],dtype=np.float32)
                z = l[8]
                tex = TEXTURES["floor"][l[9]]
                obj = Floor(pos_a,pos_b,pos_c,pos_d,z,tex)
                GAME_OBJECTS.append(obj)
                FLOORS.append(obj)
            elif line[0]=='c':
                #ceiling
                # c(a_x,a_y,b_x,b_y,c_x,c_y,d_x,d_y,z,tex)
                line = line[beginning+1:-2].replace('\n','').split(',')
                l = [int(item) for item in line]
                pos_a = np.array([l[0],l[1],l[8]],dtype=np.float32)
                pos_b = np.array([l[2],l[3],l[8]],dtype=np.float32)
                pos_c = np.array([l[4],l[5],l[8]],dtype=np.float32)
                pos_d = np.array([l[6],l[7],l[8]],dtype=np.float32)
                z = l[8]
                tex = TEXTURES["ceiling"][l[9]]
                obj = Ceiling(pos_a,pos_b,pos_c,pos_d,z,tex)
                GAME_OBJECTS.append(obj)
                CEILINGS.append(obj)
            elif line[0]=='l':
                #light
                # l(x,y,z,r,g,b)
                line = line[beginning+1:-2].replace('\n','').split(',')
                l = [int(item) for item in line]
                position = np.array([l[0],l[1],l[2]],dtype=np.float32)
                colour = np.array([l[3],l[4],l[5]],dtype=np.float32)
                obj = Light(position,colour)
                LIGHTS.append(obj)
            elif line[0]=='p':
                #player
                # p(x,y,direction)
                line = line[2:-2].replace('\n','').split(',')
                l = [int(item) for item in line]
                player = Player(np.array([l[0],l[1],16],dtype=np.float32),l[2])
                obj = None
                GAME_OBJECTS.append(player)
            if obj:
                obj.tag = tag
            line = f.readline()
        """
        for obj in FLOORS:
            print("Made Floor: "+str(obj))
        for obj in CEILINGS:
            print("Made Ceiling: "+str(obj))
        """
        #find how floors connect
        for obj in FLOORS:
            #print("Checking: " + str(obj))
            A = obj.pos_a
            B = obj.pos_b
            C = obj.pos_c
            D = obj.pos_d
            for obj2 in FLOORS:
                #print("\t against: " + str(obj2))
                hasA = False
                hasB = False
                hasC = False
                hasD = False
                if obj==obj2:
                    continue
                corners = obj2.getCorners()
                #do any corners match?
                for corner in corners:
                    if A[0] == corner[0] and A[1] == corner[1]:
                        #print(str(obj) + " has " + str(A) + " , " + str(obj2) + " has " + str(corner))
                        hasA = True
                        continue
                    elif B[0] == corner[0] and B[1] == corner[1]:
                        #print(str(obj) + " has " + str(B) + " , " + str(obj2) + " has " + str(corner))
                        hasB = True
                        continue
                    elif C[0] == corner[0] and C[1] == corner[1]:
                        #print(str(obj) + " has " + str(C) + " , " + str(obj2) + " has " + str(corner))
                        hasC = True
                        continue
                    elif D[0] == corner[0] and D[1] == corner[1]:
                        #print(str(obj) + " has " + str(D) + " , " + str(obj2) + " has " + str(corner))
                        hasD = True
                        continue
                if hasA and hasB:
                    obj.connectsAB = obj2
                    #print(str(obj) + " connects to " + str(obj2))
                    continue
                elif hasB and hasC:
                    obj.connectsBC = obj2
                    #print(str(obj)+" connects to "+str(obj2))
                    continue
                elif hasC and hasD:
                    obj.connectsCD = obj2
                    #print(str(obj)+" connects to "+str(obj2))
                    continue
                elif hasD and hasA:
                    obj.connectsDA = obj2
                    #print(str(obj)+" connects to "+str(obj2))
                    continue
        #find how ceilings connect
        for obj in CEILINGS:
            #print("Checking: " + str(obj))
            A = obj.pos_a
            B = obj.pos_b
            C = obj.pos_c
            D = obj.pos_d
            for obj2 in CEILINGS:
                #print("\t against: " + str(obj2))
                hasA = False
                hasB = False
                hasC = False
                hasD = False
                if obj==obj2:
                    continue
                corners = obj2.getCorners()
                #do any corners match?
                for corner in corners:
                    if A[0] == corner[0] and A[1] == corner[1]:
                        #print(str(obj) + " has " + str(A) + " , " + str(obj2) + " has " + str(corner))
                        hasA = True
                        continue
                    elif B[0] == corner[0] and B[1] == corner[1]:
                        #print(str(obj) + " has " + str(B) + " , " + str(obj2) + " has " + str(corner))
                        hasB = True
                        continue
                    elif C[0] == corner[0] and C[1] == corner[1]:
                        #print(str(obj) + " has " + str(C) + " , " + str(obj2) + " has " + str(corner))
                        hasC = True
                        continue
                    elif D[0] == corner[0] and D[1] == corner[1]:
                        #print(str(obj) + " has " + str(D) + " , " + str(obj2) + " has " + str(corner))
                        hasD = True
                        continue
                if hasA and hasB:
                    obj.connectsAB = obj2
                    #print(str(obj) + " connects to " + str(obj2))
                    continue
                elif hasB and hasC:
                    obj.connectsBC = obj2
                    #print(str(obj)+" connects to "+str(obj2))
                    continue
                elif hasC and hasD:
                    obj.connectsCD = obj2
                    #print(str(obj)+" connects to "+str(obj2))
                    continue
                elif hasD and hasA:
                    obj.connectsDA = obj2
                    #print(str(obj)+" connects to "+str(obj2))
                    continue
        #find which segment the player is in
        for obj in FLOORS:
            if obj.inSegment(player.position):
                #print("Player is on " + str(obj))
                player.setCurrentSector(obj)
        #find which segment each light is in
        for obj in LIGHTS:
            for obj2 in FLOORS:
                if obj2.inSegment(obj.position):
                    obj.setCurrentSector(obj2)
                    obj2.addLight(obj)
                    break
        #add walls to sectors
        for obj in FLOORS:
            #print("Checking: " + str(obj))
            A = obj.pos_a
            B = obj.pos_b
            C = obj.pos_c
            D = obj.pos_d
            for obj2 in WALLS:
                #print("\t against: " + str(obj2))
                hasA = False
                hasB = False
                hasC = False
                hasD = False
                corners = obj2.getCorners()
                #do any corners match?
                for corner in corners:
                    if A[0] == corner[0] and A[1] == corner[1]:
                        #print(str(obj) + " has " + str(A) + " , " + str(obj2) + " has " + str(corner))
                        hasA = True
                        continue
                    elif B[0] == corner[0] and B[1] == corner[1]:
                        #print(str(obj) + " has " + str(B) + " , " + str(obj2) + " has " + str(corner))
                        hasB = True
                        continue
                    elif C[0] == corner[0] and C[1] == corner[1]:
                        #print(str(obj) + " has " + str(C) + " , " + str(obj2) + " has " + str(corner))
                        hasC = True
                        continue
                    elif D[0] == corner[0] and D[1] == corner[1]:
                        #print(str(obj) + " has " + str(D) + " , " + str(obj2) + " has " + str(corner))
                        hasD = True
                        continue
                if hasA and hasB:
                    obj.wallAB = obj2
                    #print(str(obj) + " connects to " + str(obj2))
                    continue
                elif hasB and hasC:
                    obj.wallBC = obj2
                    #print(str(obj)+" connects to "+str(obj2))
                    continue
                elif hasC and hasD:
                    obj.wallCD = obj2
                    #print(str(obj)+" connects to "+str(obj2))
                    continue
                elif hasD and hasA:
                    obj.wallDA = obj2
                    #print(str(obj)+" connects to "+str(obj2))
                    continue

        return player

def importTextures(filename):
    with open(filename,'r') as f:
        line = f.readline()
        while line:
            if line[0]=='w':
                target = TEXTURES["wall"]
            elif line[0]=='f':
                target = TEXTURES["floor"]
            elif line[0]=='m':
                target = TEXTURES["metal"]
            else:
                target = TEXTURES["ceiling"]
            beginning = line.find('(')
            line = line[beginning+1:-2].replace('\n','').split(',')
            ambient = float(line[0])
            diffuse = line[1]
            specular = line[2]
            shininess = int(line[3])

            target.append(Material(ambient,diffuse,specular,shininess))
            
            line = f.readline()

def clearLights():
    for i in range(MAX_LIGHTS):
        glUniform1fv(glGetUniformLocation(shader,f'pointLights[{i}].isOn'),1,False)

def addLights(sector):
    #look at lights in current sector
    nextSearch = []
    searched = []
    expanded = []
    alreadyAdded = 0
    nextSearch.append(sector)
    while alreadyAdded < MAX_LIGHTS:
        #print("Next search: "+str(nextSearch))
        #print("Searched: "+str(searched))
        #print("Expanded: "+str(expanded))
        if len(nextSearch)!=0:
            #search a sector
            sector = nextSearch.pop()
            for light in sector.getLights():
                light.update()
                alreadyAdded += 1
            searched.append(sector)
        else:
            for sector in searched:
                if sector not in expanded:
                    expanded.append(sector)
                    for newSector in sector.getSectors():
                        if newSector not in searched:
                            nextSearch.append(newSector)
            if (len(nextSearch)==0):
                break

################ Classes ######################################################

class ObjModel:
    def __init__(self,filepath):

        attributeMap = {'V':0,'T':1,'N':2}
        datatypeMap = {'F':GL_FLOAT}

        attributes = []

        scene = pwf.Wavefront(filepath)
        for name, material in scene.materials.items():
            vertex_format = material.vertex_format.split("_")
            vertices = material.vertices

        stride = 0
        for item in vertex_format:
            attributeLocation = attributeMap[item[0]]
            attributeStart = stride
            attributeLength = int(item[1])
            attributeDataType = datatypeMap[item[2]]
            stride += attributeLength
            attributes.append((attributeLocation,attributeLength,attributeDataType,attributeStart*4))
        
        self._VAO = glGenVertexArrays(1)
        glBindVertexArray(self._VAO)

        vertices = np.array(vertices,dtype=np.float32)

        self._VBO = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER,self._VBO)
        glBufferData(GL_ARRAY_BUFFER,vertices.nbytes,vertices,GL_STATIC_DRAW)
        self._vertexCount = int(len(vertices)/stride)

        for a in attributes:
            glEnableVertexAttribArray(a[0])
            glVertexAttribPointer(a[0],a[1],a[2],GL_FALSE,vertices.itemsize*stride,ctypes.c_void_p(a[3]))

    def getVAO(self):
        return self._VAO

    def getVertexCount(self):
        return self._vertexCount

class Player:
    def __init__(self,position,direction):
        self.position = position
        self.theta = direction
        self.phi = 0
        pygame.mouse.set_pos(SCREEN_WIDTH/2,SCREEN_HEIGHT/2)
        self.speed = 1
        self.height = 16
        self.currentSector = None
        self.lastSector = None
        self.gun = ObjModel("models/rifle.obj")
    
    def setCurrentSector(self,newSector):
        self.currentSector = newSector
        #print("Player is on " + str(self.currentSector))

    def update(self):
        #take inputs
        keystate = pygame.key.get_pressed()
        walk_direction = 0
        walking = False

        #mouse
        new_pos = pygame.mouse.get_pos()
        pygame.mouse.set_pos(SCREEN_WIDTH/2,SCREEN_HEIGHT/2)
        self.theta -= t*(new_pos[0] - SCREEN_WIDTH/2)/15
        self.theta = self.theta%360
        self.phi -= t*(new_pos[1] - SCREEN_HEIGHT/2)/15
        self.phi = min(max(self.phi,-90),90)

        self.look()

        #keys
        if keystate[pygame.K_a]:
            walking = True
            walk_direction = 90
        if keystate[pygame.K_d]:
            walk_direction = -90
            walking = True
        if keystate[pygame.K_w]:
            walk_direction = 0
            walking = True
        if keystate[pygame.K_s]:
            walk_direction = 180
            walking = True
        
        if walking:
            self.walk(walk_direction)
        
        if self.currentSector == None:
            for obj in FLOORS:
                if obj.inSegment(self.position):
                    self.currentSector = obj
                    break
        
        if self.currentSector != None:
            addLights(self.currentSector)

        projection_matrix = pyrr.matrix44.create_perspective_projection(45,SCREEN_WIDTH/SCREEN_HEIGHT,1,280,dtype=np.float32)
        glUniformMatrix4fv(glGetUniformLocation(shader,"projection"),1,GL_FALSE,projection_matrix)
        glUniform3fv(glGetUniformLocation(shader,"viewPos"),1,self.position)
    
    def walk(self,walk_direction):
        actual_direction = self.theta + walk_direction
        cos_ad = np.cos(np.radians(actual_direction),dtype=np.float32)
        sin_ad = np.sin(np.radians(actual_direction),dtype=np.float32)

        temp = np.array([0,0,0],dtype=np.float32)
        walltoCheck = self.currentSector.checkCollisions(self.position+8*np.array([cos_ad,0,0],dtype=np.float32))
        if not walltoCheck or (walltoCheck.position[2]+walltoCheck.height)<(self.position[2]-self.height+4) or (walltoCheck.position[2]>self.position[2]):
            temp += self.speed*t*np.array([cos_ad,0,0],dtype=np.float32)/20
        
        walltoCheck = self.currentSector.checkCollisions(self.position+8*np.array([0,sin_ad,0],dtype=np.float32))
        if not walltoCheck or (walltoCheck.position[2]+walltoCheck.height)<(self.position[2]-self.height+4) or (walltoCheck.position[2]>self.position[2]):
            temp += self.speed*t*np.array([0,sin_ad,0],dtype=np.float32)/20

        self.position += temp

        if self.currentSector:
            self.currentSector = self.currentSector.newSector(self.position)
            if self.currentSector:
                self.position[2] = self.currentSector.z + self.height
        
        if self.currentSector != self.lastSector:
            #print("Player is on " + str(self.currentSector))
            self.lastSector = self.currentSector
    
    def look(self):
        self.cos_phi = np.cos(np.radians(self.phi),dtype=np.float32)
        self.sin_phi = np.sin(np.radians(self.phi),dtype=np.float32)
        self.cos_theta = np.cos(np.radians(self.theta),dtype=np.float32)
        self.sin_theta = np.sin(np.radians(self.theta),dtype=np.float32)

        #get lookat
        look_direction = np.array([self.cos_phi*self.cos_theta,self.cos_phi*self.sin_theta,self.sin_phi],dtype=np.float32)
        up = np.array([0,0,1],dtype=np.float32)
        camera_right = pyrr.vector3.cross(up,look_direction)
        camera_up = pyrr.vector3.cross(look_direction,camera_right)

        lookat_matrix = pyrr.matrix44.create_look_at(self.position,self.position + look_direction, camera_up, dtype=np.float32)
        glUniformMatrix4fv(glGetUniformLocation(shader,"view"),1,GL_FALSE,lookat_matrix)

    def draw(self):
        self.gun_translate = pyrr.matrix44.create_from_translation(self.position+np.array([0.5*self.cos_phi*self.cos_theta,0.5*self.cos_phi*self.sin_theta,-1],dtype=np.float32))
        self.gun_rotate = pyrr.matrix44.create_from_z_rotation(theta = np.radians(270-self.theta),dtype=np.float32)
        self.gun_rotate2 = pyrr.matrix44.create_from_x_rotation(theta = np.radians(self.phi),dtype=np.float32)
        self.gun_model = pyrr.matrix44.multiply(self.gun_rotate2,self.gun_rotate)
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,self.gun_translate)
        TEXTURES["metal"][0].use()

        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.gun_model)
        glBindVertexArray(self.gun.getVAO())
        glDrawArrays(GL_TRIANGLES,0,self.gun.getVertexCount())

class Wall:
    def __init__(self,pos_a,pos_b,z,height,texture):
        self.z = z
        self.position = pos_a
        a_length = pyrr.vector.length(np.array([pos_a[0],pos_a[1]]))
        b_length = pyrr.vector.length(np.array([pos_b[0],pos_b[1]]))
        self.model = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)
        self.pos_a = pos_a
        self.pos_b = pos_b
        self.corners = [self.pos_a, self.pos_b]
        self.height = height
        self.texture = texture
        self.tag = ""

        #calculate normal by hand
        u = pos_b - pos_a
        u[2] = 1
        v = pos_b - pos_a
        v[2] = 0
        self.normal = pyrr.vector.normalise(pyrr.vector3.cross(u,v))

        self.vertices = (0,                                0,                                self.height, self.normal[0], self.normal[1], self.normal[2], a_length/TEXTURE_RESOLUTION,    (self.z+self.height)/TEXTURE_RESOLUTION,
                         self.pos_b[0] - self.position[0], self.pos_b[1] - self.position[1], self.height, self.normal[0], self.normal[1], self.normal[2], b_length/TEXTURE_RESOLUTION,               (self.z+self.height)/TEXTURE_RESOLUTION,
                         self.pos_b[0] - self.position[0], self.pos_b[1] - self.position[1], 0,           self.normal[0], self.normal[1], self.normal[2], b_length/TEXTURE_RESOLUTION,               self.z/TEXTURE_RESOLUTION,
                         0,                                0,                                0,           self.normal[0], self.normal[1], self.normal[2], a_length/TEXTURE_RESOLUTION,    self.z/TEXTURE_RESOLUTION)
        self.vertices = np.array(self.vertices,dtype=np.float32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER,self.vbo)
        glBufferData(GL_ARRAY_BUFFER,self.vertices.nbytes,self.vertices,GL_STATIC_DRAW)

        #position
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(0))
        #normal
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(self.vertices.itemsize*3))
        #texture coordinates
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2,2,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(self.vertices.itemsize*6))
    
    def getCorners(self):
        return self.corners

    def update(self):
        self.model = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)

    def draw(self):
        self.texture.use()
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.model)
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLE_FAN,0,4)

    def __str__(self):
        return self.tag
    
    def __repr__(self):
        return self.tag

class Floor:
    def __init__(self,pos_a,pos_b,pos_c,pos_d,z,texture):
        self.z = z
        self.position = pos_a
        self.model = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)
        self.pos_a = pos_a
        self.pos_b = pos_b
        self.pos_c = pos_c
        self.pos_d = pos_d
        self.texture = texture
        self.tag = ""
        #important geometric info
        self.corners = [self.pos_a,self.pos_b,self.pos_c,self.pos_d]
        self.connectsAB = None
        self.connectsBC = None
        self.connectsCD = None
        self.connectsDA = None
        self.wallAB = None
        self.wallBC = None
        self.wallCD = None
        self.wallDA = None
        self.lights = []
        #normal directions to describe boundaries of edges
        #print("Making normals for " + self.tag)
        u = pos_b - pos_a
        u[2] = 1
        v = pos_b - pos_a
        v[2] = 0
        self.normalAB = pyrr.vector.normalise(pyrr.vector3.cross(u,v))
        #print("AB normal is " + str(self.normalAB))

        u = pos_c - pos_b
        u[2] = 1
        v = pos_c - pos_b
        v[2] = 0
        self.normalBC = pyrr.vector.normalise(pyrr.vector3.cross(u,v))
        #print("BC normal is " + str(self.normalBC))

        u = pos_d - pos_c
        u[2] = 1
        v = pos_d - pos_c
        v[2] = 0
        self.normalCD = pyrr.vector.normalise(pyrr.vector3.cross(u,v))
        #print("CD normal is " + str(self.normalCD))

        u = pos_a - pos_d
        u[2] = 1
        v = pos_a - pos_d
        v[2] = 0
        self.normalDA = pyrr.vector.normalise(pyrr.vector3.cross(u,v))
        #print("DA normal is " + str(self.normalDA))

        #model data
        self.vertices = (self.pos_a[0] - self.position[0], self.pos_a[1] - self.position[1], self.z - self.position[2], 0.0, 0.0, 1.0,  self.pos_a[0]/TEXTURE_RESOLUTION, self.pos_a[1]/TEXTURE_RESOLUTION,
                         self.pos_b[0] - self.position[0], self.pos_b[1] - self.position[1], self.z - self.position[2], 0.0, 0.0, 1.0,  self.pos_b[0]/TEXTURE_RESOLUTION, self.pos_b[1]/TEXTURE_RESOLUTION,
                         self.pos_c[0] - self.position[0], self.pos_c[1] - self.position[1], self.z - self.position[2], 0.0, 0.0, 1.0,  self.pos_c[0]/TEXTURE_RESOLUTION, self.pos_c[1]/TEXTURE_RESOLUTION,
                         self.pos_d[0] - self.position[0], self.pos_d[1] - self.position[1], self.z - self.position[2], 0.0, 0.0, 1.0,  self.pos_d[0]/TEXTURE_RESOLUTION, self.pos_d[1]/TEXTURE_RESOLUTION,)
        self.vertices = np.array(self.vertices,dtype=np.float32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER,self.vbo)
        glBufferData(GL_ARRAY_BUFFER,self.vertices.nbytes,self.vertices,GL_STATIC_DRAW)

        #position
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(0))
        #normal
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(self.vertices.itemsize*3))
        #texture coordinates
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2,2,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(self.vertices.itemsize*6))
    
    def getCorners(self):
        return self.corners

    def getSectors(self):
        sectors = []
        if self.connectsAB:
            sectors.append(self.connectsAB)
        if self.connectsBC:
            sectors.append(self.connectsBC)
        if self.connectsCD:
            sectors.append(self.connectsCD)
        if self.connectsDA:
            sectors.append(self.connectsDA)
        return sectors

    def getLights(self):
        return self.lights

    def addLight(self,light):
        self.lights.append(light)

    def inSegment(self,pos):
        #check boundary AB
        testPos = pos - self.pos_a
        if np.dot(testPos,self.normalAB)<0:
            return False
        
        #check boundary BC
        testPos = pos - self.pos_b
        if np.dot(testPos,self.normalBC)<0:
            return False
        
        #check boundary CD
        testPos = pos - self.pos_c
        if np.dot(testPos,self.normalCD)<0:
            return False
        
        #check boundary DA
        testPos = pos - self.pos_d
        if np.dot(testPos,self.normalDA)<0:
            return False
        
        return True

    def newSector(self,newPos):
        """
            Check the new position, if it's outside the sector, return
            which sector it is in, otherwise return self
        """
        #check boundary AB
        testPos = newPos - self.pos_a
        if np.dot(testPos,self.normalAB)<0:
            return self.connectsAB
        
        #check boundary BC
        testPos = newPos - self.pos_b
        if np.dot(testPos,self.normalBC)<0:
            return self.connectsBC
        
        #check boundary CD
        testPos = newPos - self.pos_c
        if np.dot(testPos,self.normalCD)<0:
            return self.connectsCD
        
        #check boundary DA
        testPos = newPos - self.pos_d
        if np.dot(testPos,self.normalDA)<0:
            return self.connectsDA
        
        return self

    def checkCollisions(self,pos):
        if self.wallAB:
            #check boundary AB
            testPos = pos - self.pos_a
            if np.dot(testPos,self.normalAB)<0:
                return self.wallAB
        
        if self.wallBC:
            #check boundary BC
            testPos = pos - self.pos_b
            if np.dot(testPos,self.normalBC)<0:
                return self.wallBC
        
        if self.wallCD:
            #check boundary CD
            testPos = pos - self.pos_c
            if np.dot(testPos,self.normalCD)<0:
                return self.wallCD
        
        if self.wallDA:
            #check boundary DA
            testPos = pos - self.pos_d
            if np.dot(testPos,self.normalDA)<0:
                return self.wallDA
        
        return None

    def update(self):
        self.model = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)

    def draw(self):
        self.texture.use()
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.model)
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLE_FAN,0,4)

    def __str__(self):
        return self.tag
    
    def __repr__(self):
        return self.tag

class Ceiling:
    def __init__(self,pos_a,pos_b,pos_c,pos_d,z,texture):
        self.z = z
        self.position = pos_a
        self.model = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)
        self.pos_a = pos_a
        self.pos_b = pos_b
        self.pos_c = pos_c
        self.pos_d = pos_d
        self.texture = texture
        self.tag = ""
        self.corners = [self.pos_a,self.pos_b,self.pos_c,self.pos_d]
        self.connectsAB = None
        self.connectsBC = None
        self.connectsCD = None
        self.connectsDA = None

        self.vertices = (self.pos_a[0] - self.position[0], self.pos_a[1] - self.position[1], self.z - self.position[2], 0.0, 0.0, -1.0,  self.pos_a[0]/TEXTURE_RESOLUTION, self.pos_a[1]/TEXTURE_RESOLUTION,
                         self.pos_b[0] - self.position[0], self.pos_b[1] - self.position[1], self.z - self.position[2], 0.0, 0.0, -1.0,  self.pos_b[0]/TEXTURE_RESOLUTION, self.pos_b[1]/TEXTURE_RESOLUTION,
                         self.pos_c[0] - self.position[0], self.pos_c[1] - self.position[1], self.z - self.position[2], 0.0, 0.0, -1.0,  self.pos_c[0]/TEXTURE_RESOLUTION, self.pos_c[1]/TEXTURE_RESOLUTION,
                         self.pos_d[0] - self.position[0], self.pos_d[1] - self.position[1], self.z - self.position[2], 0.0, 0.0, -1.0,  self.pos_d[0]/TEXTURE_RESOLUTION, self.pos_d[1]/TEXTURE_RESOLUTION,)
        self.vertices = np.array(self.vertices,dtype=np.float32)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER,self.vbo)
        glBufferData(GL_ARRAY_BUFFER,self.vertices.nbytes,self.vertices,GL_STATIC_DRAW)

        #position
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(0))
        #normal
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(self.vertices.itemsize*3))
        #texture coordinates
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2,2,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(self.vertices.itemsize*6))
    
    def getCorners(self):
        return self.corners

    def update(self):
        self.model = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)

    def draw(self):
        self.texture.use()
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.model)
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLE_FAN,0,4)

    def __str__(self):
        return self.tag
    
    def __repr__(self):
        return self.tag

class Light:
    def __init__(self,position,colour):
        self.position = position
        self.colour = np.array([256*random.random(),256*random.random(),256*random.random()],dtype=np.float32)
        self.lightVelocity = np.array([1 - 2*random.random(),1 - 2*random.random(),1 - 2*random.random()],dtype=np.float32)
        self.active = True
        self.height = 1
        self.velocity = np.array([1 - 2*random.random(),1 - 2*random.random(),1 - 2*random.random()],dtype=np.float32)
        self.tag = ""
        self.currentSector = None
    
    def setCurrentSector(self,newSector):
        self.currentSector = newSector

    def update(self):
        global current_lights
        """
        checkX = self.position + np.array([self.velocity[0],0,0],dtype=np.float32)
        if checkCollisions(self,self.position,checkX):
            self.velocity[0] *= -1
        
        checkY = self.position + np.array([0,self.velocity[1],0],dtype=np.float32)
        if checkCollisions(self,self.position,checkY):
            self.velocity[1] *= -1
        
        if self.velocity[2]<0 and self.position[2]<0:
            self.velocity[2] *= -1
        elif self.velocity[2]>0 and self.position[2]>40:
            self.velocity[2] *= -1
        
        self.position += min(t,10)*self.velocity/20
        
        self.colour += t*self.lightVelocity/20
        if self.colour[0]<0:
            self.colour[0] += 256
        elif self.colour[0]>256:
            self.colour[0] -= 256
        if self.colour[1]<0:
            self.colour[1] += 256
        elif self.colour[1]>256:
            self.colour[1] -= 256
        if self.colour[2]<0:
            self.colour[2] += 256
        elif self.colour[2]>256:
            self.colour[2] -= 256
        """
        if self.active and current_lights<MAX_LIGHTS:
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].isOn'),1,True)

            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].position'),1,self.position)
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].strength'),1,1)

            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].constant'),1,1.0)
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].linear'),1,0.2)
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].quadratic'),1,0.1)

            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].ambient'),1,0)
            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].diffuse'),1,1.0*self.colour)
            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].specular'),1,0.8*self.colour)
            current_lights += 1
    
    def draw(self):
        pass

    def __str__(self):
        return self.tag
    
    def __repr__(self):
        return self.tag

class Material:
    def __init__(self,ambient,diffuse,specular,shininess):
        #ambient
        self.ambient = np.array([ambient,ambient,ambient],dtype=np.float32)

        #diffuse
        self.diffuse = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D,self.diffuse)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        image = pygame.image.load(diffuse)
        image_width, image_height = image.get_rect().size
        image_data = pygame.image.tostring(image,"RGBA")
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,image_width,image_height,0,GL_RGBA,GL_UNSIGNED_BYTE,image_data)

        #specular
        self.specular = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D,self.specular)

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        image = pygame.image.load(diffuse)
        image_width, image_height = image.get_rect().size
        image_data = pygame.image.tostring(image,"RGBA")
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,image_width,image_height,0,GL_RGBA,GL_UNSIGNED_BYTE,image_data)

        #shininess
        self.shininess = 32

    def use(self):
        glUniform3fv(glGetUniformLocation(shader,"material.ambient"),1,self.ambient)
        glUniform1fv(glGetUniformLocation(shader,"material.shininess"),1,self.shininess)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D,self.diffuse)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D,self.specular)

################ Game Objects #################################################
GAME_OBJECTS = []
FLOORS = []
CEILINGS = []
WALLS = []
LIGHTS = []
TEXTURES = {"floor":[],"wall":[],"ceiling":[],"metal":[]}
importTextures('textures.txt')
player = importData('level.txt')
################ Game Loop ####################################################
running = True
t = 0
while running:
    ################ Events ###################################################
    for event in pygame.event.get():
        if event.type==pygame.QUIT or (event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE):
            running = False
    ################ Update ###################################################
    current_lights = 0
    clearLights()
    for obj in GAME_OBJECTS:
        obj.update()
    ################ Render ###################################################
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    for obj in GAME_OBJECTS:
        obj.draw()
    ################ Framerate ################################################
    t = CLOCK.get_time()
    CLOCK.tick()
    fps = CLOCK.get_fps()
    pygame.display.set_caption("Running at "+str(int(fps))+" fps")
    pygame.display.flip()
