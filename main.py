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
    #read data from file
    with open(filename,'r') as f:
        line = f.readline()
        while line:
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
                player = Player(np.array([l[0],l[1],0],dtype=np.float32)*32,l[2])
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
        if obj.inSector(player.position):
            player.setSector(obj)
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
            model = ObjModel("models/ceiling/",f.name)
            model.texture = TEXTURES["ceiling"][0]
            CEILING_MODELS.append(model)
    #walls
    for f in pathlib.Path("models/wall").iterdir():
        if f.suffix == ".obj":
            model = ObjModel("models/wall/",f.name)
            model.texture = TEXTURES["wall"][0]
            WALL_MODELS.append(model)
    #floors
    for f in pathlib.Path("models/floor").iterdir():
        if f.suffix == ".obj":
            model = ObjModel("models/floor/",f.name)
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
    def __init__(self,folderpath,filename):
        v = []
        vt = []
        vn = []
        self.vertices = []

        #open the obj file and read the data
        with open(f"{folderpath}/{filename}",'r') as f:
            line = f.readline()
            while line:
                firstSpace = line.find(" ")
                flag = line[0:firstSpace]
                if flag=="mtllib":
                    #declaration of material file
                    materialFile = line.replace("mtllib ","")
                elif flag=="v":
                    #vertex
                    line = line.replace("v ","")
                    line = line.split(" ")
                    l = [float(x) for x in line]
                    v.append(l)
                elif flag=="vt":
                    #texture coordinate
                    line = line.replace("vt ","")
                    line = line.split(" ")
                    l = [float(x) for x in line]
                    vt.append(l)
                elif flag=="vn":
                    #normal
                    line = line.replace("vn ","")
                    line = line.split(" ")
                    l = [float(x) for x in line]
                    vn.append(l)
                elif flag=="f":
                    #face, four vertices in v/vt/vn form
                    line = line.replace("f ","")
                    line = line.replace("\n","")
                    line = line.split(" ")
                    theseVertices = []
                    theseTextures = []
                    theseNormals = []
                    for vertex in line:
                        l = vertex.split("/")
                        position = int(l[0]) - 1
                        theseVertices.append(v[position])
                        texture = int(l[1]) - 1
                        theseTextures.append(vt[texture])
                        normal = int(l[2]) - 1
                        theseNormals.append(vn[normal])
                    # obj file uses triangle fan format for each face individually.
                    # unpack each face
                    triangles_in_face = len(line) - 2

                    vertex_order = []
                    for i in range(triangles_in_face):
                        vertex_order.append(0)
                        vertex_order.append(i+1)
                        vertex_order.append(i+2)
                    
                    for i in vertex_order:
                        for x in theseVertices[i]:
                            self.vertices.append(x)
                        for x in theseNormals[i]:
                            self.vertices.append(x)
                        for x in theseTextures[i]:
                            self.vertices.append(x)
                    
                line = f.readline()
        self.vertices = np.array(self.vertices,dtype=np.float32)

        #vertex array object, all that stuff
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER,self.vbo)
        glBufferData(GL_ARRAY_BUFFER,self.vertices.nbytes,self.vertices,GL_STATIC_DRAW)
        self.vertexCount = int(len(self.vertices)/8)

        #position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(0))
        #normal attribute
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(12))
        #texture attribute
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2,2,GL_FLOAT,GL_FALSE,self.vertices.itemsize*8,ctypes.c_void_p(24))
        self.texture = None
        """
        #open the mtl file and read the data
        with open(f"{folderpath}/{materialFile}",'r') as f:
            line = f.readline()
            while line:
                firstSpace = line.find(" ")
                flag = line[0:firstSpace]
                if flag=="mtllib":
                    #declaration of material file
                    materialFile = line.replace("mtllib ","")
                elif flag=="v":
                    #vertex
                    line = line.replace("v ","")
                    line = line.split(" ")
                    l = [float(x) for x in line]
                    v.append(l)
                elif flag=="vt":
                    #texture coordinate
                    line = line.replace("vt ","")
                    line = line.split(" ")
                    l = [float(x) for x in line]
                    vt.append(l)
                elif flag=="vn":
                    #normal
                    line = line.replace("vn ","")
                    line = line.split(" ")
                    l = [float(x) for x in line]
                    vn.append(l)
                elif flag=="f":
                    #face, four vertices in v/vt/vn form
                    line = line.replace("f ","")
                    line = line.split(" ")
                    for vertex in line:
                        l = vertex.split("/")
                        position = int(l[0]) - 1
                        texture = int(l[1]) - 1
                        normal = int(l[2]) - 1
                        self.vertices.append(v[position])
                        self.vertices.append(vn[normal])
                        self.vertices.append(vt[texture])
                line = f.readline()
        self.vertices = np.array(self.vertices,dtype=np.float32)
        """
    def draw(self):
        self.texture.use()
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES,0,self.vertexCount)

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

class physicsObject:
    def __init__(self,position,size,velocity=np.array([0,0,0],dtype=np.float32)):
        self.position = position
        self.radius = size[0]
        self.height = size[1]
        self.velocity = velocity
        self.sector = None
        self.lastSector = None
    
    def setSector(self,sector):
        self.sector = sector
    
    def recalculateSector(self):
        for sector in SECTORS:
            if sector.inSector(self.position):
                return sector
        return None
    
    def update(self):
        #failsafe: if the object is not in a sector, attempt to recalculate
        if not self.sector:
            self.sector = self.recalculateSector()
            if not self.sector and self.lastSector:
                self.sector = self.lastSector.newSector(self.position)
                if not self.sector:
                    self.sector = self.lastSector
        
        if self.sector:
            # check collisions with walls, floors and ceilings
            # return whether something was hit
            hitSomething = False
            #check each component of the object's velocity, if there's a collision then don't move in that direction
            temp = np.array([0,0,0],dtype=np.float32)

            check = np.array([self.velocity[0],0,0],dtype=np.float32)
            if self.sector.checkCollisions(self.position + self.radius*check):
                hitSomething = True
            else:
                temp += check
            
            check = np.array([0,self.velocity[1],0],dtype=np.float32)
            if self.sector.checkCollisions(self.position + self.radius*check):
                hitSomething = True
            else:
                temp += check
            
            if self.velocity[2] > 0:
                check = self.position + np.array([0,0,self.velocity[2] + self.height],dtype=np.float32)
                if self.sector.checkCollisions(check):
                    self.velocity[2] *= -0.5
                    hitSomething = True

            elif self.velocity[2] < 0:
                check = self.position + np.array([0,0,self.velocity[2]],dtype=np.float32)
                if self.sector.checkCollisions(check):
                    #if the object is going slowly enough we can conclude that they've hit the ground
                    if self.velocity[2]>-0.5:
                        self.velocity[2] = 0
                        self.position[2] = self.sector.position[2]
                    else:
                        #bounce
                        self.velocity[2] *= -0.5
                        hitSomething = True
            
            self.position += temp
            #get new sector based on new position
            self.sector = self.sector.newSector(self.position)
            if self.lastSector != self.sector:
                self.lastSector = self.sector

            self.velocity *= 0.5

            return hitSomething

class Player(physicsObject):
    def __init__(self,position,direction):
        super().__init__(position,[16,16])
        self.theta = direction
        self.phi = 0
        pygame.mouse.set_pos(SCREEN_WIDTH/2,SCREEN_HEIGHT/2)
        self.speed = 1.2
        self.height_vec = np.array([0,0,self.height],dtype=np.float32)

        self.gun = ObjModel("models/","rifle.obj")
        self.gun.texture = TEXTURES["misc"][0]

        self.sky = ObjModel("models/","skybox.obj")
        self.sky.texture = TEXTURES["misc"][1]

        print(self.sky.vertexCount)

        self.walk_t = 0
        #0: ready, 1: reloading
        self.gun_state = 0
        self.gun_t = 0
        self.focusing = False
        self.focus_t = 0
        self.walk_t2 = 0
        self.walking = False
        self.bullets = []
        self.up = np.array([0,0,1],dtype=np.float32)
        projection_matrix = pyrr.matrix44.create_perspective_projection(45,SCREEN_WIDTH/SCREEN_HEIGHT,1,350,dtype=np.float32)
        glUniformMatrix4fv(glGetUniformLocation(shader,"projection"),1,GL_FALSE,projection_matrix)

    def handle_keys(self):
        keystate = pygame.key.get_pressed()
        self.walk_direction = 0
        self.walking = False

        if keystate[pygame.K_a]:
            self.walking = True
            self.walk_direction = 90
        if keystate[pygame.K_d]:
            self.walk_direction = -90
            self.walking = True
        if keystate[pygame.K_w]:
            self.walk_direction = 0
            self.walking = True
        if keystate[pygame.K_s]:
            self.walk_direction = 180
            self.walking = True

    def handle_mouse(self):
        new_pos = pygame.mouse.get_pos()
        pygame.mouse.set_pos(SCREEN_WIDTH/2,SCREEN_HEIGHT/2)
        self.theta -= t*(new_pos[0] - SCREEN_WIDTH/2)/15
        self.theta = self.theta%360
        self.phi -= t*(new_pos[1] - SCREEN_HEIGHT/2)/15
        self.phi = min(max(self.phi,-90),90)
    
    def walk(self):
        #physics stuff
        actual_direction = self.theta + self.walk_direction
        cos_ad = np.cos(np.radians(actual_direction),dtype=np.float32)
        sin_ad = np.sin(np.radians(actual_direction),dtype=np.float32)
        self.velocity = np.array([cos_ad,sin_ad,0],dtype=np.float32)*t*self.speed/20
        
        #animation stuff
        """
        self.walk_t += self.speed*t/2w
        if self.walk_t>45 or self.walk_t<-45:
            self.walk_v *= -1
        self.walk_t2 += t/20
        if self.walk_t2 >= 1:
            self.walk_t2 = 1
        """

    def updateGun(self):
        if self.gun_state==1:
            self.gun_t += t/2
            if self.gun_t >=0:
                self.gun_t = 0
                self.gun_state = 0
        
        #gun model transform
        self.gun_model = pyrr.matrix44.create_identity(dtype=np.float32)
        #if the player is walking spin the gun into holding position
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,pyrr.matrix44.create_from_y_rotation(theta = np.radians(self.walk_t2*-90),dtype=np.float32))
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_z_rotation(theta = np.radians(self.walk_t2*-45),dtype=np.float32))

        #basic position of gun
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_translation(np.array([-1,1,-1],dtype=np.float32),dtype=np.float32))
        #with walking animation
        walk_cos = np.cos(np.radians(self.walk_t))
        walk_sin = np.sin(np.radians(self.walk_t))
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_translation(np.array([(-2+walk_cos)*self.walk_t2,(-2+walk_sin)*self.walk_t2,-self.walk_t2],dtype=np.float32),dtype=np.float32))
        #with mouse focus
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_translation(np.array([self.focus_t,-self.focus_t,self.focus_t],dtype=np.float32),dtype=np.float32))
        #with gun recoil
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_translation(np.array([0,-np.sin(np.radians(self.gun_t)),0],dtype=np.float32),dtype=np.float32))
        #rotate gun to match player's direction
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_x_rotation(theta = np.radians(self.phi),dtype=np.float32))
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_z_rotation(theta = np.radians(270-self.theta),dtype=np.float32))
        #move gun to player's position
        self.gun_model = pyrr.matrix44.multiply(self.gun_model, pyrr.matrix44.create_from_translation(self.look_target,dtype=np.float32))

    def updateSky(self):
        #sky model transform
        self.sky_model = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)

    def idle(self):
        self.walk_t = 0
        self.walk_t2 -= t/20
        if self.walk_t2 <= 0:
            self.walk_t2 = 0
        
        if self.focusing:
            self.focus_t += t/20
            if self.focus_t >= 1:
                self.focus_t = 1
        else:
            self.focus_t -= t/20
            if self.focus_t <= 0:
                self.focus_t = 0

    def update(self):
        #keys
        self.handle_keys()

        #mouse
        self.handle_mouse()
        self.look()

        if self.walking:
            self.walk()
        else:
            self.idle()
        
        #physics behaviour
        super().update()
        
        #lighting
        """
        if self.currentSector != None:
            addLights(self.currentSector)
        """
        
        #send camera position to shader
        glUniform3fv(glGetUniformLocation(shader,"viewPos"),1,self.position)

        self.updateGun()
        self.updateSky()
        
        #update bullets
        for b in self.bullets:
            b.update()
    
    def look(self):
        self.cos_phi = np.cos(np.radians(self.phi),dtype=np.float32)
        self.sin_phi = np.sin(np.radians(self.phi),dtype=np.float32)
        self.cos_theta = np.cos(np.radians(self.theta),dtype=np.float32)
        self.sin_theta = np.sin(np.radians(self.theta),dtype=np.float32)

        #get lookat
        self.look_direction = np.array([self.cos_phi*self.cos_theta, self.cos_phi*self.sin_theta, self.sin_phi],dtype=np.float32)
        self.look_direction *= 3
        
        camera_right = pyrr.vector3.cross(self.up,self.look_direction)
        camera_up = pyrr.vector3.cross(self.look_direction,camera_right)
        self.look_target = self.position + self.height_vec + self.look_direction

        lookat_matrix = pyrr.matrix44.create_look_at(self.position + np.array([0,0,self.height],dtype=np.float32),self.look_target, camera_up, dtype=np.float32)
        glUniformMatrix4fv(glGetUniformLocation(shader,"view"),1,GL_FALSE,lookat_matrix)
        projection_matrix = pyrr.matrix44.create_perspective_projection(45,SCREEN_WIDTH/SCREEN_HEIGHT,1,350,dtype=np.float32)
        glUniformMatrix4fv(glGetUniformLocation(shader,"projection"),1,GL_FALSE,projection_matrix)

    def draw(self):
        #draw gun
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.gun_model)
        self.gun.draw()

        #draw sky
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.sky_model)
        self.sky.draw()

        """
        #draw bullets
        for b in self.bullets:
            b.draw()
        """

    def shoot(self):
        if self.gun_state==0 and not self.walking:
            self.gun_state = 1
            self.gun_t = -90
            self.bullets.append(Bullet(self.position+2*self.look_direction,self.look_direction,self.sector,self))

    def focus(self):
        if not self.walking:
            self.focusing = True

class Sector:
    def __init__(self,top_left, length_width_height, bottom_wall, right_wall, top_wall, left_wall, floor, ceiling):
        self.tag = ""
        self.length = length_width_height[0]
        self.width = length_width_height[1]
        self.height = length_width_height[2]
        self.length_grid = int(self.length)//32
        self.width_grid = int(self.width)//32
        self.height_grid = int(self.height)//32
        #positions
        self.position = top_left
        self.model = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)
        self.pos_a = top_left + np.array([0,-length_width_height[1],0],dtype=np.float32)
        self.pos_b = top_left + np.array([length_width_height[0],-length_width_height[1],0],dtype=np.float32)
        self.pos_c = top_left + np.array([length_width_height[0],0,0],dtype=np.float32)
        self.pos_d = top_left
        self.top_position = top_left + np.array([0,0,length_width_height[2]],dtype=np.float32)

        #models
        self.model = pyrr.matrix44.create_identity(dtype=np.float32)
        if bottom_wall < 0:
            self.bottom_wall = None
            self.has_bottom_wall = False
        else:
            self.bottom_wall = WALL_MODELS[bottom_wall]
            self.has_bottom_wall = True
        
        if right_wall < 0:
            self.right_wall = None
            self.has_right_wall = False
        else:
            self.right_wall = WALL_MODELS[right_wall]
            self.has_right_wall = True
        
        if top_wall < 0:
            self.top_wall = None
            self.has_top_wall = False
        else:
            self.top_wall = WALL_MODELS[top_wall]
            self.has_top_wall = True
        
        if left_wall < 0:
            self.left_wall = None
            self.has_left_wall = False
        else:
            self.left_wall = WALL_MODELS[left_wall]
            self.has_left_wall = True
        
        if floor < 0:
            self.floor = None
            self.has_floor = False
        else:
            self.floor = FLOOR_MODELS[floor]
            self.has_floor = True
        
        if ceiling < 0:
            self.ceiling = None
            self.has_ceiling = False
        else:
            self.ceiling = CEILING_MODELS[ceiling]
            self.has_ceiling = True
        
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

    def inSector(self,pos):
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
        if self.has_bottom_wall:
            #check boundary AB
            if pos[1]<self.pos_a[1]:
                return True
        
        if self.has_right_wall:
            #check boundary BC
            if pos[0]>self.pos_b[0]:
                return True
        
        if self.has_top_wall:
            #check boundary CD
            if pos[1]>self.pos_c[1]:
                return True
        
        if self.has_left_wall:
            #check boundary DA
            if pos[0]<=self.pos_d[0]:
                return True
        
        return False

    def update(self):
        pass

    def draw(self):
        #floor
        if self.has_floor:
            for x in range(self.length_grid):
                for y in range(self.width_grid):
                    pos = np.array([32*x,-32*y,0],dtype=np.float32)
                    self.model = pyrr.matrix44.create_from_translation(self.position+pos,dtype=np.float32)
                    glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.model)
                    self.floor.draw()
        #bottom wall
        if self.has_bottom_wall:
            #start at position a and expand to right
            for x in range(self.length_grid):
                for z in range(self.height_grid):
                    pos = np.array([32*x,0,32*z],dtype=np.float32)
                    self.model = pyrr.matrix44.multiply(pyrr.matrix44.create_from_z_rotation(theta=np.radians(0)),
                                                            pyrr.matrix44.create_from_translation(self.pos_a + pos))
                    glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.model)
                    self.bottom_wall.draw()
        #right wall
        if self.has_right_wall:
            #start at position b and expand up
            for y in range(self.width_grid):
                for z in range(self.height_grid):
                    pos = np.array([0,32*y,32*z],dtype=np.float32)
                    self.model = pyrr.matrix44.multiply(pyrr.matrix44.create_from_z_rotation(theta=np.radians(-90)),
                                                            pyrr.matrix44.create_from_translation(self.pos_b + pos))
                    glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.model)
                    self.right_wall.draw()
        #top wall
        if self.has_top_wall:
            #start at position c and expand to left
            for x in range(self.length_grid):
                for z in range(self.height_grid):
                    pos = np.array([-32*x,0,32*z],dtype=np.float32)
                    self.model = pyrr.matrix44.multiply(pyrr.matrix44.create_from_z_rotation(theta=np.radians(-180)),
                                                            pyrr.matrix44.create_from_translation(self.pos_c + pos))
                    glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.model)
                    self.top_wall.draw()
        #left wall
        if self.has_left_wall:
            #start at position d and expand down
            for y in range(self.width_grid):
                for z in range(self.height_grid):
                    pos = np.array([0,-32*y,32*z],dtype=np.float32)
                    self.model = pyrr.matrix44.multiply(pyrr.matrix44.create_from_z_rotation(theta=np.radians(-270)),
                                                            pyrr.matrix44.create_from_translation(self.pos_d + pos))
                    glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.model)
                    self.left_wall.draw()
        #ceiling
        if self.has_ceiling:
            for x in range(self.length_grid):
                for y in range(self.width_grid):
                    pos = np.array([32*x,-32*y,0],dtype=np.float32)
                    self.model = pyrr.matrix44.create_from_translation(self.position+pos,dtype=np.float32)
                    glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.model)
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
BULLET_MODEL = ObjModel("models/","bullet.obj")
GHOST_MODEL = ObjModel("models/","ghastly.obj")
#BOUNCE_MODEL = AnimatedObjModel("models/wobble","wobble")
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
