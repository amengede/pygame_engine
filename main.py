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

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 540
#os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (SCREEN_WIDTH//2,SCREEN_HEIGHT//2)
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

################ Helper Functions #############################################

def import_data(filename):
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
                #sector: x_top_left, y_top_left,z_top_left,
                # length(x), width(y), height(z), bottom_wall,
                # right_wall, top_wall, left_wall, ground_model, ceiling_model
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
                obj = Sector(top_left, length_width_height, bottom_wall,
                                right_wall, top_wall, left_wall, floor, ceiling)
                GAME_OBJECTS.append(obj)
                SECTORS.append(obj)
            elif line[0]=='p':
                #player
                # p(x,y,direction)
                line = line[beginning+1:-2].replace('\n','').split(',')
                l = [float(item) for item in line]
                player = Player(np.array([l[0],l[1],0],dtype=np.float32)*32,l[2])
                obj = None
                GAME_OBJECTS.append(player)
            elif line[0]=='g':
                #ghost
                # g(x,y,z)
                line = line[beginning+1:-2].replace('\n','').split(',')
                l = [float(item)*32 for item in line]
                obj = Ghost(np.array([l[0],l[1],l[2]],dtype=np.float32))
                GAME_OBJECTS.append(obj)
                ENEMIES.append(obj)
            if obj:
                obj.tag = tag
            line = f.readline()
        
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
    player.setSector(player.recalculateSector())
    #find which segment each enemy is in
    for obj in ENEMIES:
        obj.setSector(obj.recalculateSector())
    return player

def import_textures(filename):
    """
        Read a texture file and create textures

        Parameters:
            filename (string): path to the texture file.
    """

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

def create_models():
    """
        Search through some folders in the model folder and load the models.
    """
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

def clear_lights():
    """
        Reset system by disabling all lights.
        Call this at the start of the game loop before update calls.
    """
    glUseProgram(shader)
    for i in range(MAX_LIGHTS):
        glUniform1fv(glGetUniformLocation(shader,f'pointLights[{i}].isOn'),1,False)

def add_lights(sector):
    """
        Perform a breadth-first search to add lights.

        Starts at the given sector and spreads out until the
        maximum amount of lights have been added.

        Parameters:
            sector (Sector): a reference to the sector to branch out from
    """
    glUseProgram(shader)
    #look at lights in current sector
    next_search = []
    searched = []
    expanded = []
    already_added = 0
    next_search.append(sector)
    while already_added < MAX_LIGHTS:
        if len(next_search)!=0:
            #search a sector
            sector = next_search.pop()
            for light in sector.getLights():
                light.update()
                already_added += 1
            searched.append(sector)
        else:
            for sector in searched:
                if sector not in expanded:
                    expanded.append(sector)
                    for new_sector in sector.getSectors():
                        if new_sector not in searched:
                            next_search.append(new_sector)
            if len(next_search)==0:
                break

def random_3d():
    """
        Generate a 3d Vector in a random direction
    """
    return pyrr.vector.normalise(np.array([1-2*random.random() for i in range(3)],dtype=np.float32))
################ Classes ######################################################

class ObjModel:
    def __init__(self,folderpath,filename):
        glUseProgram(shader)
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
                    #print(v)
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
                        #print(theseVertices)
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

    def getTransformedVertices(self,model):
        """ Return a the set of vertices from the object, after applying the model transformation """
        result = np.empty(0,dtype=np.float32)
        #for normal transformations
        model33 = pyrr.matrix33.create_from_matrix44(model,dtype=np.float32)

        #each vertex has position (3), normal (3) and texture (2), so 8 elements
        vertex_count = int(len(self.vertices)/8)
        for v in range(vertex_count):
            position = np.array([self.vertices[v*8],self.vertices[v*8+1],self.vertices[v*8+2]],dtype=np.float32)
            normal = np.array([self.vertices[v*8+3],self.vertices[v*8+4],self.vertices[v*8+5]],dtype=np.float32)
            texture = np.array([self.vertices[v*8+6],self.vertices[v*8+7]],dtype=np.float32)

            #apply full model matrix to position
            pos4 = np.append(position,np.array([1],dtype=np.float32))
            pos4 = pyrr.matrix44.multiply(pos4,model)
            position = np.delete(pos4,3)
            result = np.append(result,position)
            #apply reduced transform to normals
            normal = pyrr.matrix33.multiply(normal,model33)
            result = np.append(result,normal)
            #no transform needed for texture coordinates
            result = np.append(result,texture)
        vertex_count = int(len(result)/8)
        return result

    def draw(self):
        glUseProgram(shader)
        self.texture.use()
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES,0,self.vertexCount)

class StreamModel:
    # can accept streams of vertex data, rather than a file
    def __init__(self):
        glUseProgram(shader)

        #set up model variables, ready to accept data
        self.vertices = np.empty(0,dtype=np.float32)

        self.vao = glGenVertexArrays(1)

        self.vbo = glGenBuffers(1)

        self.texture = None
    
    def takeVertexInput(self,vertices):
        self.vertices = np.append(self.vertices,vertices)
    
    def finaliseModel(self):
        glUseProgram(shader)
        glBindVertexArray(self.vao)

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
    
    def draw(self):
        glUseProgram(shader)
        self.texture.use()
        glBindVertexArray(self.vao)
        glDrawArrays(GL_TRIANGLES,0,self.vertexCount)

class physicsObject:
    def __init__(self,position,size,velocity=np.array([0,0,0],dtype=np.float32)):
        self.position = position
        self.radius = size[0]
        self.height = size[1]
        self.velocity = velocity
        self.sector = None
        self.lastSector = None
        self.bounce = False

    def setSector(self,sector):
        self.sector = sector
        if sector != self.sector:
            if self.sector != None:
                #remove self from the previous sector
                self.sector.removeObject(self)
        self.lastSector = self.sector
        self.sector = sector
        #add self to new sector
        self.sector.addObject(self)

    def recalculateSector(self):
        for sector in SECTORS:
            if sector.inSector(self.position):
                return sector
        return None

    def update(self):
        #failsafe: if the object is not in a sector, attempt to recalculate
        if not self.sector:
            self.setSector(self.recalculateSector())
            if not self.sector and self.lastSector:
                self.setSector(self.lastSector.newSector(self.position))
                if not self.sector:
                    self.setSector(self.lastSector)

        if self.sector:
            # check collisions with walls, floors and ceilings
            # return whether something was hit
            if self.bounce:
                return self.moveBounce()
            else:
                return self.moveSquish()

    def moveSquish(self):
        """ Attempt to move the object with its velocity.
        If an obstacle is hit, stop/slide.
        Return whether an obstacle was hit """

        hitSomething = False

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
            check =  np.array([0,0,self.velocity[2]],dtype=np.float32)
            if self.sector.checkCollisions(self.position + self.height + check):
                self.velocity[2] *= -0.5
                hitSomething = True

        elif self.velocity[2] < 0:
            check = np.array([0,0,self.velocity[2]],dtype=np.float32)
            if self.sector.checkCollisions(self.position + check):
                hitSomething = True
                #if the object is going slowly enough
                # we can conclude that they've hit the ground
                if self.velocity[2]>-0.5:
                    check[2] = 0
                    self.position[2] = self.sector.position[2]
                else:
                    #bounce
                    check[2] *= -0.5
            # height colisions are a bit different, the object can't control them as much and
            # must bounce
            temp += check

        self.position += temp*t/20
        #get new sector based on new position
        if self.sector:
            self.setSector(self.sector.newSector(self.position))

        return hitSomething

    def moveBounce(self):
        """ Attempt to move the object with its velocity.
        If an obstacle is hit, rebound.
        Return whether an obstacle was hit """

        hitSomething = False

        temp = np.array([0,0,0],dtype=np.float32)

        check = np.array([self.velocity[0],0,0],dtype=np.float32)
        if self.sector.checkCollisions(self.position + self.radius*check):
            hitSomething = True
            check *= -0.5
        temp += check

        check = np.array([0,self.velocity[1],0],dtype=np.float32)
        if self.sector.checkCollisions(self.position + self.radius*check):
            hitSomething = True
            check *= -0.5
        temp += check

        if self.velocity[2] > 0:
            check =  np.array([0,0,self.velocity[2]],dtype=np.float32)
            if self.sector.checkCollisions(self.position + self.height + check):
                self.velocity[2] *= -0.5
                hitSomething = True

        elif self.velocity[2] < 0:
            check = np.array([0,0,self.velocity[2]],dtype=np.float32)
            if self.sector.checkCollisions(self.position + check):
                hitSomething = True
                #if the object is going slowly enough
                # we can conclude that they've hit the ground
                if self.velocity[2]>-0.5:
                    check[2] = 0
                    self.position[2] = self.sector.position[2]
                else:
                    #bounce
                    check *= -0.5
            temp += check

        self.position += temp
        #get new sector based on new position
        self.setSector(self.sector.newSector(self.position))

        self.velocity *= 0.5

        return hitSomething

class Player(physicsObject):
    def __init__(self,position,direction):
        glUseProgram(shader)
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

        self.walk_t = 0
        self.walk_v = 1
        #0: ready, 1: reloading
        self.gun_state = 0
        self.gun_t = 0
        self.focusing = False
        self.focus_t = 0
        self.walk_t2 = 0
        self.walking = False
        self.bullets = []
        self.up = np.array([0,0,1],dtype=np.float32)
        projection_matrix = pyrr.matrix44.create_perspective_projection(45,
                                                                        SCREEN_WIDTH/SCREEN_HEIGHT,
                                                                        1,350,dtype=np.float32)
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

    def handle_event(self,event):
        if event.type==pygame.MOUSEBUTTONDOWN:
            if event.button==1:
                self.shoot()
            elif event.button == 3:
                self.focus()
        if event.type == pygame.MOUSEBUTTONUP and event.button==3:
            self.focusing = False
    
    def walk(self):
        #physics stuff
        actual_direction = self.theta + self.walk_direction
        cos_ad = np.cos(np.radians(actual_direction),dtype=np.float32)
        sin_ad = np.sin(np.radians(actual_direction),dtype=np.float32)
        self.velocity = np.array([cos_ad,sin_ad,0],dtype=np.float32)*t*self.speed/20

        #animation stuff

        self.walk_t += self.speed*self.walk_v*t/20
        if self.walk_t>45 or self.walk_t<-45:
            self.walk_v *= -1
        self.walk_t2 += t/20
        if self.walk_t2 >= 1:
            self.walk_t2 = 1

    def updateGun(self):
        if self.gun_state==1:
            self.gun_t += t/2
            if self.gun_t >=0:
                self.gun_t = 0
                self.gun_state = 0

        #gun model transform
        self.gun_model = pyrr.matrix44.create_identity(dtype=np.float32)
        #if the player is walking spin the gun into holding position
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,
                            pyrr.matrix44.create_from_y_rotation(\
                                theta = np.radians(self.walk_t2*-90),
                                dtype=np.float32))

        self.gun_model = pyrr.matrix44.multiply(self.gun_model,\
                            pyrr.matrix44.create_from_z_rotation(\
                                theta = np.radians(self.walk_t2*-45),
                                dtype=np.float32))

        #basic position of gun
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,\
                            pyrr.matrix44.create_from_translation(\
                                np.array([-1,1,-1],dtype=np.float32),
                                dtype=np.float32))
        #with walking animation
        walk_cos = np.cos(np.radians(self.walk_t))
        walk_sin = np.sin(np.radians(self.walk_t))

        self.gun_model = pyrr.matrix44.multiply(self.gun_model,\
                            pyrr.matrix44.create_from_translation(\
                                np.array(\
                                    [(-2+walk_cos)*self.walk_t2,
                                    (-2+walk_sin)*self.walk_t2,
                                    -self.walk_t2],
                                dtype=np.float32),
                            dtype=np.float32))
        #with mouse focus
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,\
                            pyrr.matrix44.create_from_translation(\
                                np.array(\
                                    [self.focus_t,
                                    -self.focus_t,
                                    self.focus_t],
                                dtype=np.float32),
                            dtype=np.float32))
        #with gun recoil
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,\
                            pyrr.matrix44.create_from_translation(\
                                np.array(\
                                    [0,-np.sin(np.radians(self.gun_t)),0],
                                dtype=np.float32),
                            dtype=np.float32))
        #rotate gun to match player's direction
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,\
                            pyrr.matrix44.create_from_x_rotation(\
                                theta = np.radians(self.phi),
                            dtype=np.float32))
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,\
                            pyrr.matrix44.create_from_z_rotation(\
                                theta = np.radians(270-self.theta),
                            dtype=np.float32))
        #move gun to player's position
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,\
                            pyrr.matrix44.create_from_translation(\
                                self.look_target,
                            dtype=np.float32))

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
        
        #slow down
        if pyrr.vector.length(self.velocity)<0.1:
            self.velocity *= 0
        else:
            self.velocity *= 0.7
        

    def update(self):
        glUseProgram(shader)
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
        self.height_vec = np.array([0,0,self.height + 4*np.sin(np.radians(10*self.walk_t))],dtype=np.float32)
        glUniform3fv(glGetUniformLocation(shader,"viewPos"),1,self.position + self.height_vec)

        self.updateGun()
        self.updateSky()

    def look(self):
        glUseProgram(shader)
        self.cos_phi = np.cos(np.radians(self.phi),dtype=np.float32)
        self.sin_phi = np.sin(np.radians(self.phi),dtype=np.float32)
        self.cos_theta = np.cos(np.radians(self.theta),dtype=np.float32)
        self.sin_theta = np.sin(np.radians(self.theta),dtype=np.float32)

        #get lookat
        self.look_direction = np.array(\
                                        [self.cos_phi*self.cos_theta,
                                        self.cos_phi*self.sin_theta,
                                        self.sin_phi],
                                    dtype=np.float32)
        self.look_direction *= 3

        camera_right = pyrr.vector3.cross(self.up,self.look_direction)
        camera_up = pyrr.vector3.cross(self.look_direction,camera_right)
        self.look_target = self.position + self.height_vec + self.look_direction

        lookat_matrix = pyrr.matrix44.create_look_at(self.position + self.height_vec,
                                                    self.look_target,
                                                    camera_up,
                                                    dtype=np.float32)
        glUniformMatrix4fv(glGetUniformLocation(shader,"view"),1,GL_FALSE,lookat_matrix)
        projection_matrix = pyrr.matrix44.create_perspective_projection(45,
                                                                        SCREEN_WIDTH/SCREEN_HEIGHT,
                                                                        1,
                                                                        350,
                                                                        dtype=np.float32)
        glUniformMatrix4fv(glGetUniformLocation(shader,"projection"),1,GL_FALSE,projection_matrix)

    def draw(self):
        glUseProgram(shader)
        #draw gun
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.gun_model)
        self.gun.draw()

        #draw sky
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.sky_model)
        self.sky.draw()

        #draw bullets
        for b in self.bullets:
            b.draw()

    def shoot(self):
        if self.gun_state==0 and not self.walking:
            self.gun_state = 1
            self.gun_t = -90
            if self.sector:
                self.sector.addObject(Bullet(self.position+self.height_vec+2*self.look_direction,self.look_direction,self.sector))

    def focus(self):
        if not self.walking:
            self.focusing = True

class Sector:
    def __init__(self,top_left, length_width_height,
                    bottom_wall, right_wall, top_wall, left_wall, floor, ceiling):
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
        self.graphics_model = StreamModel()
        self.buildPieces(bottom_wall,right_wall,top_wall,left_wall,floor,ceiling)

        #connection info
        self.corners = [self.pos_a,self.pos_b,self.pos_c,self.pos_d]
        self.connectsAB = None
        self.connectsBC = None
        self.connectsCD = None
        self.connectsDA = None

        #data stored/managed by sector
        self.lights = []
        self.objects = []

    def buildPieces(self,bottom_wall,right_wall,top_wall,left_wall,floor,ceiling):
        length_grid = int(self.length)//32
        width_grid = int(self.width)//32
        height_grid = int(self.height)//32

        if bottom_wall < 0:
            self.has_bottom_wall = False
        else:
            modelToStream = WALL_MODELS[bottom_wall]
            self.has_bottom_wall = True
            for x in range(length_grid):
                for z in range(height_grid):
                    pos = np.array([32*x,0,32*z],dtype=np.float32)
                    rotation = pyrr.matrix44.create_from_z_rotation(theta=np.radians(0),dtype=np.float32)
                    translation = pyrr.matrix44.create_from_translation(self.pos_a + pos,dtype=np.float32)
                    modelMatrix = pyrr.matrix44.multiply(rotation,translation)
                    self.graphics_model.takeVertexInput(modelToStream.getTransformedVertices(modelMatrix))

        if right_wall < 0:
            self.has_right_wall = False
        else:
            modelToStream = WALL_MODELS[right_wall]
            self.has_right_wall = True
            for y in range(width_grid):
                for z in range(height_grid):
                    pos = np.array([0,32*y,32*z],dtype=np.float32)
                    rotation = pyrr.matrix44.create_from_z_rotation(theta=np.radians(-90),dtype=np.float32)
                    translation = pyrr.matrix44.create_from_translation(self.pos_b + pos,dtype=np.float32)
                    modelMatrix = pyrr.matrix44.multiply(rotation,translation)
                    self.graphics_model.takeVertexInput(modelToStream.getTransformedVertices(modelMatrix))

        if top_wall < 0:
            self.has_top_wall = False
        else:
            modelToStream = WALL_MODELS[top_wall]
            self.has_top_wall = True
            for x in range(length_grid):
                for z in range(height_grid):
                    pos = np.array([-32*x,0,32*z],dtype=np.float32)
                    rotation = pyrr.matrix44.create_from_z_rotation(theta=np.radians(-180),dtype=np.float32)
                    translation = pyrr.matrix44.create_from_translation(self.pos_c + pos,dtype=np.float32)
                    modelMatrix = pyrr.matrix44.multiply(rotation,translation)
                    self.graphics_model.takeVertexInput(modelToStream.getTransformedVertices(modelMatrix))

        if left_wall < 0:
            self.has_left_wall = False
        else:
            modelToStream = WALL_MODELS[left_wall]
            self.has_left_wall = True
            for y in range(width_grid):
                for z in range(height_grid):
                    pos = np.array([0,-32*y,32*z],dtype=np.float32)
                    rotation = pyrr.matrix44.create_from_z_rotation(theta=np.radians(-270),dtype=np.float32)
                    translation = pyrr.matrix44.create_from_translation(self.pos_d + pos,dtype=np.float32)
                    modelMatrix = pyrr.matrix44.multiply(rotation,translation)
                    self.graphics_model.takeVertexInput(modelToStream.getTransformedVertices(modelMatrix))

        if floor < 0:
            self.has_floor = False
        else:
            modelToStream = FLOOR_MODELS[floor]
            self.has_floor = True
            for x in range(length_grid):
                for y in range(width_grid):
                    pos = np.array([32*x,-32*y,0],dtype=np.float32)
                    modelMatrix = pyrr.matrix44.create_from_translation(self.position+pos,dtype=np.float32)
                    self.graphics_model.takeVertexInput(modelToStream.getTransformedVertices(modelMatrix))

        if ceiling < 0:
            self.has_ceiling = False
        else:
            modelToStream = CEILING_MODELS[ceiling]
            self.has_ceiling = True
            self.ceiling_models = []
            for x in range(length_grid):
                for y in range(width_grid):
                    pos = np.array([32*x,-32*y,0],dtype=np.float32)
                    modelMatrix = pyrr.matrix44.create_from_translation(self.position+pos,dtype=np.float32)
                    self.graphics_model.takeVertexInput(modelToStream.getTransformedVertices(modelMatrix))
        
        self.graphics_model.finaliseModel()
        self.graphics_model.texture = TEXTURES['floor'][0]

    def addObject(self,obj):
        """ Add obj to the sector's set of active objects """
        if obj not in self.objects:
            self.objects.append(obj)
    
    def removeObject(self,obj):
        """ Remove obj from the sector's set of active objects """
        if obj in self.objects:
            self.objects.pop(self.objects.index(obj))
    
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
            if pos[0]<self.pos_d[0]:
                return True

        if self.has_floor:
            if pos[2]<self.position[2]:
                return True

        if self.has_ceiling:
            if pos[2]>self.top_position[2]:
                return True

        return False

    def update(self):
        for obj in self.objects:
            if not obj.updated:
                obj.update()
                obj.updated = True

    def clearUpdate(self):
        for obj in self.objects:
            obj.updated = False
    
    def draw(self):

        glUseProgram(shader)
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.model)
        self.graphics_model.draw()

        for obj in self.objects:
            obj.draw()

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
        self.velocity = random_3d()
        self.tag = ""
        self.currentSector = None

    def setCurrentSector(self,newSector):
        self.currentSector = newSector

    def update(self):
        glUseProgram(shader)
        global CURRENT_LIGHTS
        if self.active and CURRENT_LIGHTS<MAX_LIGHTS:
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{CURRENT_LIGHTS}].isOn'),1,True)

            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{CURRENT_LIGHTS}].position'),1,self.position)
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{CURRENT_LIGHTS}].strength'),1,2)

            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{CURRENT_LIGHTS}].constant'),1,1.0)
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{CURRENT_LIGHTS}].linear'),1,0)
            glUniform1fv(glGetUniformLocation(shader,f'pointLights[{CURRENT_LIGHTS}].quadratic'),1,1.0)

            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{CURRENT_LIGHTS}].ambient'),1,0.4*self.colour)
            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{CURRENT_LIGHTS}].diffuse'),1,0.4*self.colour)
            glUniform3fv(glGetUniformLocation(shader,f'pointLights[{CURRENT_LIGHTS}].specular'),1,0.2*self.colour)
            CURRENT_LIGHTS += 1

    def draw(self):
        pass

    def __str__(self):
        return self.tag

    def __repr__(self):
        return self.tag

class Material:
    def __init__(self,ambient,diffuse,specular,shininess,emissive):
        glUseProgram(shader)
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
        glUseProgram(shader)
        glUniform3fv(glGetUniformLocation(shader,"material.ambient"),1,self.ambient)
        glUniform1fv(glGetUniformLocation(shader,"material.shininess"),1,self.shininess)
        glUniform1iv(glGetUniformLocation(shader,"material.emissive"),1,self.emissive)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D,self.diffuse)
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D,self.specular)

class Bullet(physicsObject):
    def __init__(self,position,velocity,sector):
        super().__init__(position.copy(),[1,1],velocity.copy())
        self.sector = sector
        self.graphics_model = BULLET_MODEL
        self.rotation = random_3d()
        self.angle = np.array([0,0,0],dtype=np.float32)
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        self.updated = False

    def update(self):
        #position
        self.angle += t*self.rotation/20
        #self.position += t*self.velocity/20
        if super().update():
            self.destroy()
        if self.sector==None:
            self.destroy()
        self.updateModel()

    def updateModel(self):
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_x_rotation(theta = self.angle[0],dtype=np.float32))
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_y_rotation(theta = self.angle[1],dtype=np.float32))
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_z_rotation(theta = self.angle[2],dtype=np.float32))
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_translation(self.position,dtype=np.float32))

    def draw(self):
        glUseProgram(shader)
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.transform_model)
        self.graphics_model.draw()

    def destroy(self):
        self.sector.removeObject(self)

class Ghost(physicsObject):
    def __init__(self,position):
        super().__init__(position,[8,8])
        self.graphics_model = GHOST_MODEL
        self.health = 12
        self.direction = random_3d()
        self.speed = 1
        self.sector = None
        self.t = 0
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        # 0:wander, 1: chase, 2: retreat
        self.state = 0

    def update(self):

        if self.state==0:
            #wander
            self.speed = 0.5
            self.velocity = t*self.speed/20*self.direction
            hitSomething = super().update()
            #if we hit something, randomise the direction again
            if hitSomething:
                self.direction = random_3d()

            #go into attack mode if we're close enough to player
            toPlayer = (player.position + player.height_vec/2) - self.position
            distance = pyrr.vector.length(toPlayer)
            if distance <= 128:
                self.direction = pyrr.vector.normalise(toPlayer)
                self.state = 1
            #to make sure the rest of the code doesn't update
            self.updateModel()
            return

        elif self.state==1:
            #chase
            self.speed = 1
            self.velocity = t*self.speed/20*self.direction
            hitSomething = super().update()

            #did we hit the player?
            toPlayer = (player.position + player.height_vec/2) - self.position
            distance = pyrr.vector.length(toPlayer)
            if distance <= self.radius + player.radius:
                self.direction *= -1
                self.state = 2
                self.t = 0
            #did we hit the wall?
            elif hitSomething:
                self.direction = random_3d()
                self.state = 0
            self.updateModel()
            return

        else:
            #retreat
            self.t += t/20
            self.speed = 0.5
            self.velocity = t*self.speed/20*self.direction
            hitSomething = super().update()
            if hitSomething:
                self.direction = random_3d()

            if self.t > 120:
                #after some time the ghost is ready to attack again
                self.state = 0
            self.updateModel()
            return

    def updateModel(self):
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        theta = np.arctan2(self.direction[1],self.direction[2])+np.radians(180,dtype=np.float32)
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_z_rotation(theta = theta,dtype=np.float32))
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,pyrr.matrix44.create_from_translation(self.position,dtype=np.float32))

    def draw(self):
        glUseProgram(shader)
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.transform_model)
        self.graphics_model.draw()

################ Game Objects #################################################
GAME_OBJECTS = []
SECTORS = []
CEILING_MODELS = []
WALL_MODELS = []
FLOOR_MODELS = []
LIGHTS = []
ENEMIES = []
TEXTURES = {"floor":[],"wall":[],"ceiling":[],"misc":[],"enemies":[]}
import_textures('textures.txt')
create_models()
BULLET_MODEL = ObjModel("models/","bullet.obj")
BULLET_MODEL.texture = TEXTURES["misc"][2]
GHOST_MODEL = ObjModel("models/","ghastly.obj")
GHOST_MODEL.texture = TEXTURES["enemies"][0]
player = import_data('level.txt')
################ Game Loop ####################################################
running = True
t = 0
while running:
    ################ Events ###################################################
    for event in pygame.event.get():
        if event.type==pygame.QUIT or (event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE):
            running = False
        player.handle_event(event)
    ################ Update ###################################################
    CURRENT_LIGHTS = 0
    clear_lights()
    for sector in SECTORS:
        sector.clearUpdate()
    for sector in SECTORS:
        sector.update()
    ################ Render ###################################################
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    for sector in SECTORS:
        sector.draw()
    ################ Framerate ################################################
    t = min(50,CLOCK.get_time())
    CLOCK.tick()
    fps = CLOCK.get_fps()
    pygame.display.set_caption("Running at "+str(int(fps))+" fps")
    pygame.display.flip()
