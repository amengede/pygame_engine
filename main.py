################ 3D Game ######################################################
import pygame
import numpy as np
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import pyrr
import random
import pywavefront as pwf
import pathlib
import os

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

################ Shader #######################################################

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
            print(line)
            beginning = line.find('(')
            tag = line[0:beginning]
            if line[0]=='#':
                #comment
                line = f.readline()
                continue
            elif line[0]=='s':
                #sector definition
                #sector: x_top_left, y_top_left,z_top_left, length(x), width(y), height(z), bottom_wall, right_wall, top_wall, left_wall, ground_model, ceiling_model
                line = line[beginning+1:-2].replace('\n','').split(',')
                l = [float(item) for item in line]
                top_left = np.array([l[0],l[1],l[2]],dtype=np.float32)*32
                length_width_height = np.array([l[3],l[4],l[5]],dtype=np.float32)*32
                bottom_wall = int(l[6])
                right_wall = int(l[7])
                top_wall = int(l[8])
                left_wall = int(l[9])
                floor = int(l[10])
                ceiling = int(l[11])
                obj = Sector(top_left, length_width_height, bottom_wall, right_wall, top_wall, left_wall, floor, ceiling)
                GAME_OBJECTS.append(obj)
                SECTORS.append(obj)
            elif line[0]=='p':
                #player
                # p(x,y,direction)
                line = line[2:-2].replace('\n','').split(',')
                l = [float(item) for item in line]
                player = Player(np.array([l[0],l[1],0.5],dtype=np.float32)*32,l[2])
                obj = None
                GAME_OBJECTS.append(player)
            if obj:
                obj.tag = tag
            line = f.readline()
        """
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
            elif line[0]=='b':
                #bouncing cube
                # b(x,y,z)
                line = line[2:-2].replace('\n','').split(',')
                l = [int(item) for item in line]
                obj = AnimationTester(np.array([l[0],l[1],l[2]],dtype=np.float32))
                GAME_OBJECTS.append(obj)
            elif line[0]=='g':
                #ghost
                # g(x,y,z)
                line = line[2:-2].replace('\n','').split(',')
                l = [int(item) for item in line]
                obj = Ghost(np.array([l[0],l[1],l[2]],dtype=np.float32))
                GAME_OBJECTS.append(obj)
                ENEMIES.append(obj)
            """
        """
        for obj in FLOORS:
            print("Made Floor: "+str(obj))
        for obj in CEILINGS:
            print("Made Ceiling: "+str(obj))
        """
        #find how sectors connect
        for obj in SECTORS:
            #print("Checking: " + str(obj))
            A = obj.pos_a
            B = obj.pos_b
            C = obj.pos_c
            D = obj.pos_d
            for obj2 in SECTORS:
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
        for obj in SECTORS:
            if obj.inSegment(player.position):
                #print("Player is on " + str(obj))
                player.setCurrentSector(obj)
        """
        #find which segment each light is in
        for obj in LIGHTS:
            for obj2 in FLOORS:
                if obj2.inSegment(obj.position):
                    obj.setCurrentSector(obj2)
                    obj2.addLight(obj)
                    break
        #find which segment each enemy is in
        for obj in ENEMIES:
            for obj2 in FLOORS:
                if obj2.inSegment(obj.position):
                    obj.sector = obj2
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
        """
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
                target = TEXTURES["misc"]
            elif line[0]=='e':
                target = TEXTURES["enemies"]
            else:
                target = TEXTURES["ceiling"]
            beginning = line.find('(')
            line = line[beginning+1:-2].replace('\n','').split(',')
            ambient = float(line[0])
            diffuse = line[1]
            specular = line[2]
            shininess = int(line[3])
            emissive = int(line[4])

            target.append(Material(ambient,diffuse,specular,shininess,emissive))
            
            line = f.readline()

def createModels():
    #ceilings
    for f in pathlib.Path("models/ceiling").iterdir():
        if f.suffix == ".obj":
            model = ObjModel("models/ceiling/"+f.name)
            model.texture = TEXTURES["ceiling"][0]
            CEILING_MODELS.append(model)
    #walls
    for f in pathlib.Path("models/wall").iterdir():
        if f.suffix == ".obj":
            model = ObjModel("models/wall/"+f.name)
            model.texture = TEXTURES["wall"][0]
            WALL_MODELS.append(model)
    #floors
    for f in pathlib.Path("models/floor").iterdir():
        if f.suffix == ".obj":
            model = ObjModel("models/floor/"+f.name)
            model.texture = TEXTURES["floor"][0]
            FLOOR_MODELS.append(model)

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

        attributeMap = {'V':0,'N':1,'T':2}
        datatypeMap = {'F':GL_FLOAT}

        attributes = []

        scene = pwf.Wavefront(filepath)
        for name, material in scene.materials.items():
            vertex_format = material.vertex_format.split("_")
            vertices = material.vertices
            #print(vertex_format)
            #print(vertices)

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
        
        self.texture = None

    def draw(self):
        self.texture.use()
        glBindVertexArray(self._VAO)
        glDrawArrays(GL_TRIANGLE_FAN,0,self._vertexCount)

class AnimatedObjModel:
    def __init__(self,folderpath,modelName):

        self.attributeMap = {'V':0,'N':1,'T':2}
        self.datatypeMap = {'F':GL_FLOAT}

        self.attributes = []
        self.folderpath = folderpath
        self.modelName = modelName
        self.framecount = 0
        for f in pathlib.Path("./"+folderpath).iterdir():
            if f.is_file():
                self.framecount += 0.5
        self.framecount = int(self.framecount)

        scene = pwf.Wavefront(folderpath+"/"+self.modelName+"_000001.obj")
        for name, material in scene.materials.items():
            vertex_format = material.vertex_format.split("_")
            vertices = material.vertices

        stride = 0
        for item in vertex_format:
            attributeLocation = self.attributeMap[item[0]]
            attributeStart = stride
            attributeLength = int(item[1])
            attributeDataType = self.datatypeMap[item[2]]
            stride += attributeLength
            self.attributes.append((attributeLocation,attributeLength,attributeDataType,attributeStart*4))
        
        self._VAO = glGenVertexArrays(1)
        glBindVertexArray(self._VAO)

        vertices = np.array(vertices,dtype=np.float32)

        self._VBO = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER,self._VBO)
        glBufferData(GL_ARRAY_BUFFER,vertices.nbytes,vertices,GL_STATIC_DRAW)
        self._vertexCount = int(len(vertices)/stride)

        for a in self.attributes:
            glEnableVertexAttribArray(a[0])
            glVertexAttribPointer(a[0],a[1],a[2],GL_FALSE,vertices.itemsize*stride,ctypes.c_void_p(a[3]))

    def fetchFrame(self,frameNumber):
        frame = int(frameNumber)%self.framecount
        frame = max(frame,1)
        filepath = f"{self.folderpath}/{self.modelName}_{frame:06}.obj"

        scene = pwf.Wavefront(filepath)
        for name, material in scene.materials.items():
            vertices = material.vertices
        
        glBindVertexArray(self._VAO)

        vertices = np.array(vertices,dtype=np.float32)

        glBindBuffer(GL_ARRAY_BUFFER,self._VBO)
        glBufferData(GL_ARRAY_BUFFER,vertices.nbytes,vertices,GL_STATIC_DRAW)

    def getFrameCount(self):
        return self.framecount

    def getVAO(self,frameNumber):
        self.fetchFrame(frameNumber)
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
        self.sky = ObjModel("models/skybox.obj")
        self.walk_t = 0
        #0: ready, 1: reloading
        self.gun_state = 0
        self.gun_t = 0
        self.focusing = False
        self.focus_t = 0
        self.walk_t2 = 0
        self.walk_v = 1
        self.walking = False
        self.bullets = []
    
    def setCurrentSector(self,newSector):
        self.currentSector = newSector
        #print("Player is on " + str(self.currentSector))

    def update(self):
        #take inputs
        keystate = pygame.key.get_pressed()
        walk_direction = 0
        self.walking = False

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
            self.walking = True
            walk_direction = 90
        if keystate[pygame.K_d]:
            walk_direction = -90
            self.walking = True
        if keystate[pygame.K_w]:
            walk_direction = 0
            self.walking = True
        if keystate[pygame.K_s]:
            walk_direction = 180
            self.walking = True
        
        if self.walking:
            self.walk(walk_direction)
            self.walk_t += self.walk_v*t/2
            if self.walk_t>45 or self.walk_t<-45:
                self.walk_v *= -1
            self.walk_t2 += t/20
            if self.walk_t2 >= 1:
                self.walk_t2 = 1
        else:
            self.walk_t = 0
            self.walk_t2 -= t/20
            if self.walk_t2 <= 0:
                self.walk_t2 = 0
        
        if self.currentSector == None:
            for obj in SECTORS:
                if obj.inSegment(self.position):
                    self.currentSector = obj
                    break
        
        if self.currentSector != None:
            addLights(self.currentSector)

        projection_matrix = pyrr.matrix44.create_perspective_projection(45,SCREEN_WIDTH/SCREEN_HEIGHT,1,350,dtype=np.float32)
        glUniformMatrix4fv(glGetUniformLocation(shader,"projection"),1,GL_FALSE,projection_matrix)
        glUniform3fv(glGetUniformLocation(shader,"viewPos"),1,self.position)

        if self.gun_state==1:
            self.gun_t += t/2
            if self.gun_t >=0:
                self.gun_t = 0
                self.gun_state = 0
        
        if self.focusing:
            self.focus_t += t/20
            if self.focus_t >= 1:
                self.focus_t = 1
        else:
            self.focus_t -= t/20
            if self.focus_t <= 0:
                self.focus_t = 0
        
        for b in self.bullets:
            b.update()
    
    def walk(self,walk_direction):
        self.focusing = False
        actual_direction = self.theta + walk_direction
        cos_ad = np.cos(np.radians(actual_direction),dtype=np.float32)
        sin_ad = np.sin(np.radians(actual_direction),dtype=np.float32)

        temp = np.array([0,0,0],dtype=np.float32)
        #walltoCheck = self.currentSector.checkCollisions(self.position+8*np.array([cos_ad,0,0],dtype=np.float32))
        #if not walltoCheck or (walltoCheck.position[2]+walltoCheck.height)<(self.position[2]-self.height+4) or (walltoCheck.position[2]>self.position[2]):
        temp += self.speed*t*np.array([cos_ad,sin_ad,0],dtype=np.float32)/20
        
        #walltoCheck = self.currentSector.checkCollisions(self.position+8*np.array([0,sin_ad,0],dtype=np.float32))
        #if not walltoCheck or (walltoCheck.position[2]+walltoCheck.height)<(self.position[2]-self.height+4) or (walltoCheck.position[2]>self.position[2]):
        #    temp += self.speed*t*np.array([0,sin_ad,0],dtype=np.float32)/20

        self.position += temp
        """
        if self.currentSector:
            self.currentSector = self.currentSector.newSector(self.position)
            if self.currentSector:
                self.position[2] = self.currentSector.z + self.height
        
        if self.currentSector != self.lastSector:
            #print("Player is on " + str(self.currentSector))
            self.lastSector = self.currentSector
            """
    
    def look(self):
        cos_phi = np.cos(np.radians(self.phi),dtype=np.float32)
        sin_phi = np.sin(np.radians(self.phi),dtype=np.float32)
        cos_theta = np.cos(np.radians(self.theta),dtype=np.float32)
        sin_theta = np.sin(np.radians(self.theta),dtype=np.float32)

        #get lookat
        look_direction = np.array([cos_phi*cos_theta, cos_phi*sin_theta, sin_phi],dtype=np.float32)
        self.look_direction = 3*look_direction
        up = np.array([0,0,1],dtype=np.float32)
        camera_right = pyrr.vector3.cross(up,look_direction)
        camera_up = pyrr.vector3.cross(look_direction,camera_right)
        look_target = self.position + look_direction

        lookat_matrix = pyrr.matrix44.create_look_at(self.position,look_target, camera_up, dtype=np.float32)
        glUniformMatrix4fv(glGetUniformLocation(shader,"view"),1,GL_FALSE,lookat_matrix)

        #gun model transform
        self.gun_model = pyrr.matrix44.create_identity(dtype=np.float32)
        #if the player is walking spin the gun into holding position
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,pyrr.matrix44.create_from_y_rotation(theta = np.radians(self.walk_t2*-90),dtype=np.float32))
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_z_rotation(theta = np.radians(self.walk_t2*-45),dtype=np.float32))

        #basic position of gun
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_translation(np.array([-1,1,-1],dtype=np.float32),dtype=np.float32))
        #with walking animation
        #walk_cos = np.cos(np.radians(self.walk_t))
        #walk_sin = np.sin(np.radians(self.walk_t))
        #self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_translation(np.array([(-2+walk_cos)*self.walk_t2,(-2+walk_sin)*self.walk_t2,-self.walk_t2],dtype=np.float32),dtype=np.float32))
        #with mouse focus
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_translation(np.array([self.focus_t,-self.focus_t,self.focus_t],dtype=np.float32),dtype=np.float32))
        #with gun recoil
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_translation(np.array([0,-np.sin(np.radians(self.gun_t)),0],dtype=np.float32),dtype=np.float32))
        #rotate gun to match player's direction
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_x_rotation(theta = np.radians(self.phi),dtype=np.float32))
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_z_rotation(theta = np.radians(270-self.theta),dtype=np.float32))
        #move gun to player's position
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_translation(look_target,dtype=np.float32))

        #sky model transform
        self.sky_model = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)

    def draw(self):
        pass
        """
        #draw gun
        TEXTURES["misc"][0].use()
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.gun_model)
        glBindVertexArray(self.gun._VAO
        glDrawArrays(GL_TRIANGLES,0,self.gun._vertexCount())

        #draw sky
        glDisable(GL_CULL_FACE)
        TEXTURES["misc"][1].use()
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.sky_model)
        glBindVertexArray(self.sky.getVAO())
        glDrawArrays(GL_TRIANGLES,0,self.sky.getVertexCount())
        glEnable(GL_CULL_FACE)

        for b in self.bullets:
            b.draw()
        """

    def shoot(self):
        if self.gun_state==0 and not self.walking:
            self.gun_state = 1
            self.gun_t = -90
            self.bullets.append(Bullet(self.position+2*self.look_direction,self.look_direction,self.currentSector,self))

    def focus(self):
        if not self.walking:
            self.focusing = True

class Sector:
    def __init__(self,top_left, length_width_height, bottom_wall, right_wall, top_wall, left_wall, floor, ceiling):
        self.tag = ""
        self.length = length_width_height[0]
        self.width = length_width_height[1]
        self.height = length_width_height[2]
        #positions
        self.position = top_left
        self.model = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)
        self.pos_a = top_left + np.array([0,-length_width_height[1],0],dtype=np.float32)
        self.pos_b = top_left + np.array([length_width_height[0],-length_width_height[1],0],dtype=np.float32)
        self.pos_c = top_left + np.array([length_width_height[0],0,0],dtype=np.float32)
        self.pos_d = top_left
        self.top_position = top_left + np.array([0,0,length_width_height[2]],dtype=np.float32)

        #models
        if bottom_wall < 0:
            self.bottom_wall = None
        else:
            self.bottom_wall = WALL_MODELS[bottom_wall]
            self.bottom_wall_model_transform = pyrr.matrix44.create_from_translation(self.pos_a)
        
        if right_wall < 0:
            self.right_wall = None
        else:
            self.right_wall = WALL_MODELS[right_wall]
            self.right_wall_model_transform = pyrr.matrix44.multiply(pyrr.matrix44.create_from_z_rotation(theta=np.radians(-90)),
                                                                        pyrr.matrix44.create_from_translation(self.pos_b))
        
        if top_wall < 0:
            self.top_wall = None
        else:
            self.top_wall = WALL_MODELS[top_wall]
            self.top_wall_model_transform = pyrr.matrix44.multiply(pyrr.matrix44.create_from_z_rotation(theta=np.radians(-180)),
                                                                        pyrr.matrix44.create_from_translation(self.pos_c))
        
        if left_wall < 0:
            self.left_wall = None
        else:
            self.left_wall = WALL_MODELS[left_wall]
            self.left_wall_model_transform = pyrr.matrix44.multiply(pyrr.matrix44.create_from_z_rotation(theta=np.radians(-270)),
                                                                        pyrr.matrix44.create_from_translation(self.pos_d))
        
        if floor < 0:
            self.floor = None
        else:
            self.floor = FLOOR_MODELS[floor]
            self.floor_model_transform = pyrr.matrix44.create_from_translation(self.position)
        
        if ceiling < 0:
            self.ceiling = None
        else:
            self.ceiling = CEILING_MODELS[ceiling]
            self.ceiling_model_transform = pyrr.matrix44.create_from_translation(self.top_position)
        
        #connection info
        self.corners = [self.pos_a,self.pos_b,self.pos_c,self.pos_d]
        self.connectsAB = None
        self.connectsBC = None
        self.connectsCD = None
        self.connectsDA = None
        self.lights = []
    
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
        if pos[1]<self.pos_a[1]:
            return False
        
        #check boundary BC
        if pos[0]>self.pos_b[0]:
            return False
        
        #check boundary CD
        if pos[1]>self.pos_c[1]:
            return False
        
        #check boundary DA
        if pos[0]<self.pos_d[0]:
            return False
        
        return True

    def newSector(self,pos):
        """
            Check the new position, if it's outside the sector, return
            which sector it is in, otherwise return self
        """
        #check boundary AB
        if pos[1]<self.pos_a[1]:
            return self.connectsAB
        
        #check boundary BC
        if pos[0]>self.pos_b[0]:
            return self.connectsBC
        
        #check boundary CD
        if pos[1]>self.pos_c[1]:
            return self.connectsCD
        
        #check boundary DA
        if pos[0]<self.pos_d[0]:
            return self.connectsDA
        
        return self

    def checkCollisions(self,pos):
        if self.wallAB:
            #check boundary AB
            if pos[1]<self.pos_a[1]:
                return self.wallAB
        
        if self.wallBC:
            #check boundary BC
            if pos[0]>self.pos_b[0]:
                return self.wallBC
        
        if self.wallCD:
            #check boundary CD
            if pos[1]>self.pos_c[1]:
                return self.wallCD
        
        if self.wallDA:
            #check boundary DA
            if pos[0]<self.pos_d[0]:
                return self.wallDA
        
        return None

    def update(self):
        pass

    def draw(self):
        glDisable(GL_CULL_FACE)
        #floor
        if self.floor:
            for x in range(int(self.length)//32):
                for y in range(int(self.width)//32):
                    pos = np.array([32*x,-32*y,self.position[2]],dtype=np.float32)
                    self.floor_model_transform = pyrr.matrix44.create_from_translation(self.position+pos,dtype=np.float32)
                    glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.floor_model_transform)
                    self.floor.draw()
        #bottom wall
        if self.bottom_wall:
            glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.bottom_wall_model_transform)
            self.bottom_wall.draw()
        #right wall
        if self.right_wall:
            for y in range(int(self.width)//32):
                pos = np.array([0,32*y,self.position[2]],dtype=np.float32)
                self.right_wall_model_transform = pyrr.matrix44.multiply(pyrr.matrix44.create_from_z_rotation(theta=np.radians(-90)),
                                                                        pyrr.matrix44.create_from_translation(self.pos_b + pos))
                glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.right_wall_model_transform)
                self.right_wall.draw()
        #top wall
        if self.top_wall:
            glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.top_wall_model_transform)
            self.top_wall.draw()
        #left wall
        if self.left_wall:
            glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.left_wall_model_transform)
            self.left_wall.draw()
        #ceiling
        if self.ceiling:
            glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.ceiling_model_transform)
            self.ceiling.draw()

    def __str__(self):
        return self.tag
    
    def __repr__(self):
        return self.tag

class Light:
    def __init__(self,position,colour):
        self.position = position
        self.colour = colour
        self.active = True
        self.height = 1
        self.velocity = np.array([1 - 2*random.random(),1 - 2*random.random(),1 - 2*random.random()],dtype=np.float32)
        self.tag = ""
        self.currentSector = None
    
    def setCurrentSector(self,newSector):
        self.currentSector = newSector

    def update(self):
        global current_lights
        if self.active and current_lights<MAX_LIGHTS:
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].isOn'),1,True)

            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].position'),1,self.position)
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].strength'),1,2)

            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].constant'),1,1.0)
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].linear'),1,0)
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].quadratic'),1,1.0)

            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].ambient'),1,0.4*self.colour)
            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].diffuse'),1,0.4*self.colour)
            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{current_lights}].specular'),1,0.2*self.colour)
            current_lights += 1
    
    def draw(self):
        pass

    def __str__(self):
        return self.tag
    
    def __repr__(self):
        return self.tag

class Material:
    def __init__(self,ambient,diffuse,specular,shininess,emissive):
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
        self.shininess = shininess

        self.emissive = emissive

    def use(self):
        glUniform3fv(glGetUniformLocation(shader,"material.ambient"),1,self.ambient)
        glUniform1fv(glGetUniformLocation(shader,"material.shininess"),1,self.shininess)
        glUniform1iv(glGetUniformLocation(shader,"material.emissive"),1,self.emissive)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D,self.diffuse)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D,self.specular)

class Bullet:
    def __init__(self,position,velocity,sector,parent):
        self.position = position.copy()
        self.velocity = velocity.copy()
        self.sector = sector
        self.graphics_model = BULLET_MODEL
        self.parent = parent
        self.rotation = np.array([1-2*random.random() for i in range(3)],dtype=np.float32)
        self.angle = np.array([0,0,0],dtype=np.float32)
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
    
    def update(self):
        #position
        self.angle += t*self.rotation/20
        self.position += t*self.velocity/20
        self.sector = self.sector.newSector(self.position)
        if self.sector==None:
            self.destroy()
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_x_rotation(theta = self.angle[0],dtype=np.float32))
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_y_rotation(theta = self.angle[1],dtype=np.float32))
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_z_rotation(theta = self.angle[2],dtype=np.float32))
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_translation(self.position,dtype=np.float32))
    
    def draw(self):
        TEXTURES["misc"][2].use()
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.transform_model)
        glBindVertexArray(self.graphics_model.getVAO())
        glDrawArrays(GL_TRIANGLES,0,self.graphics_model.getVertexCount())
    
    def destroy(self):
        self.parent.bullets.pop(self.parent.bullets.index(self))

class AnimationTester:
    def __init__(self,position):
        self.position = position
        self.graphics_model = BOUNCE_MODEL
        self.animation_frame = 1
        self.frame_count = self.graphics_model.getFrameCount()
    
    def update(self):
        #self.vertices = x*self.vertices_last + (1-x)*self.vertices_next
        #animation frame
        #1000 milliseconds/60fps = about 16.67 milliseconds per frame
        self.animation_frame += t/16.67
        if self.animation_frame > self.frame_count:
            self.animation_frame -= self.frame_count
        #model matrix
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_translation(self.position,dtype=np.float32))
    
    def draw(self):
        TEXTURES["floor"][1].use()
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.transform_model)
        glBindVertexArray(self.graphics_model.getVAO(self.animation_frame))
        glDrawArrays(GL_TRIANGLES,0,self.graphics_model.getVertexCount())

class Ghost:
    def __init__(self,position):
        self.position = position
        self.graphics_model = GHOST_MODEL
        self.health = 12
        self.direction = pyrr.vector.normalise(np.array([1-2*random.random() for i in range(3)],dtype=np.float32))
        self.speed = 1
        self.sector = None
        self.t = 0
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        # 0:wander, 1: chase, 2: retreat
        self.state = 0
    
    def update(self):
        test_x = np.array([self.direction[0],0,0],dtype=np.float32)
        walltoCheck = self.sector.checkCollisions(self.position+test_x)
        if walltoCheck:
            self.direction[0] *= -1
        test_y = np.array([0,self.direction[1],0],dtype=np.float32)
        walltoCheck = self.sector.checkCollisions(self.position+test_y)
        if walltoCheck:
            self.direction[1] *= -1
        if self.position[2] < 4 or self.position[1] > 36:
            self.direction[2] *= -1
        self.position += t/800*self.direction

        if self.state==0:
            #wander
            self.position += t*self.speed/40*self.direction
            
            toPlayer = player.position - self.position
            distance = pyrr.vector.length(toPlayer)
            if distance <= 32:
                self.direction = pyrr.vector.normalise(toPlayer)
                self.state = 1

        elif self.state==1:
            #chase
            self.position += t*self.speed/20*self.direction
            #check which sector we're in, if possible
            if self.sector != None:
                self.sector = self.sector.newSector(self.position)
            else:
                for obj in FLOORS:
                    if obj.inSegment(self.position):
                        self.sector = obj
                        break
            
            #three cases for missing player, either hitting a wall or a ceiling or floor
            #if we miss, then wander
            if self.sector==None or self.position[2] < 4 or self.position[2] > 36:
                self.direction = np.array([1-2*random.random() for i in range(3)],dtype=np.float32)
                if self.position[2]<4:
                    self.direction[2] = 1
                elif self.position[2]>36:
                    self.direction[2] = -1
                self.direction = pyrr.vector.normalise(self.direction)
                self.state = 0

            else:
                #hit player?
                # ghost has radius of 4 and player has radius of 8,
                # so if the ghost gets within 12 units they've hit.
                # in that case, reverse direction and retreat
                toPlayer = player.position - self.position
                distance = pyrr.vector.length(toPlayer)
                if distance <= 12:
                    #attack player
                    self.direction *= -1
                    self.state = 2
                    self.t = 0
        
        else:
            #retreat
            self.t += t/20
            self.position += t*self.speed/20*self.direction
            if self.t > 120:
                #after some time the ghost is ready to attack again
                self.state = 0
            
            if self.sector != None:
                self.sector = self.sector.newSector(self.position)
            else:
                for obj in FLOORS:
                    if obj.inSegment(self.position):
                        self.sector = obj
                        break
            
            if self.sector==None or self.position[2] < 4 or self.position[2] > 36:
                self.direction = np.array([1-2*random.random() for i in range(3)],dtype=np.float32)
                if self.position[2]<4:
                    self.direction[2] = 1
                elif self.position[2]>36:
                    self.direction[2] = -1
                self.direction = pyrr.vector.normalise(self.direction)

        #model matrix
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_translation(self.position,dtype=np.float32))
    
    def draw(self):
        TEXTURES["enemies"][0].use()
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.transform_model)
        glBindVertexArray(self.graphics_model.getVAO())
        glDrawArrays(GL_TRIANGLES,0,self.graphics_model.getVertexCount())
        print(self.position)

################ Game Objects #################################################
GAME_OBJECTS = []
SECTORS = []
CEILING_MODELS = []
WALL_MODELS = []
FLOOR_MODELS = []
LIGHTS = []
ENEMIES = []
TEXTURES = {"floor":[],"wall":[],"ceiling":[],"misc":[],"enemies":[]}
BULLET_MODEL = ObjModel("models/bullet.obj")
GHOST_MODEL = ObjModel("models/ghastly.obj")
BOUNCE_MODEL = AnimatedObjModel("models/wobble","wobble")
#print("Importing textures")
importTextures('textures.txt')
#print("Creating models")
createModels()
#print("Importing data")
player = importData('level.txt')
################ Game Loop ####################################################
running = True
t = 0
while running:
    ################ Events ###################################################
    for event in pygame.event.get():
        if event.type==pygame.QUIT or (event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE):
            running = False
        if event.type==pygame.MOUSEBUTTONDOWN:
            if event.button==1:
                player.shoot()
            elif event.button == 3:
                player.focus()
        if event.type == pygame.MOUSEBUTTONUP and event.button==3:
            player.focusing = False
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
