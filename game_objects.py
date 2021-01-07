"""
    Stores the game objects (player,physics objects etc)
"""
from config import *
from assets import *

######################## helper functions #####################################

def random_3d():
    """
        Generate a 3d Vector in a random direction
    """
    return pyrr.vector.normalise(np.array([1-2*random.random() for i in range(3)],dtype=np.float32))

######################## classes ##############################################
class physicsObject:
    """ Basic 3D rectangle with movement and collision """
    def __init__(self,position,size,velocity=np.array([0,0,0],dtype=np.float32)):
        self.position = position
        self.size = size
        self.velocity = velocity
        self.sector = None
        self.last_sector = None
        self.bounce = False
        self.acceleration = np.array([0,0,0],dtype=np.float32)
        self.on_ground = False
        self.ground_z = 0
        self.graphics_model = None
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        self.sector = None

    def setSector(self,sector):
        if sector != self.sector:
            if self.sector is not None:
                #remove self from the previous sector
                self.sector.removeObject(self)
        self.last_sector = self.sector
        self.sector = sector
        #add self to new sector
        if self.sector:
            self.sector.addObject(self)

    def recalculateSector(self):
        for sector in SECTORS:
            if sector.inSector(self.position):
                return sector
        return None

    def setModel(self,model):
        self.graphics_model = model

    def update(self,t):
        #failsafe: if the object is not in a sector, attempt to recalculate
        if not self.sector:
            self.setSector(self.recalculateSector())

        if self.sector:
            self.velocity += self.acceleration*t/16
            self.on_ground = (self.position[2]==self.ground_z)
            # check collisions with walls, floors and ceilings
            # return whether something was hit
            speed = pyrr.vector.length(self.velocity)
            if speed != 0:
                if self.bounce:
                    return self.moveBounce(t)
                else:
                    return self.moveSquish(t)

    def moveSquish(self,t):
        """ Attempt to move the object with its velocity.
        If an obstacle is hit, stop/slide.
        Return whether an obstacle was hit """

        hit_something = False

        #movements are checked and summed up.
        temp = np.array([0,0,0],dtype=np.float32)

        check = np.array([self.velocity[0],0,0],dtype=np.float32)
        if self.sector.checkCollisions(self.position + check, self.size):
            hit_something = True
        else:
            collided = self.sector.hitMember(self,self.sector.objects,check)
            if len(collided)==0:
                temp += check

        check = np.array([0,self.velocity[1],0],dtype=np.float32)
        if self.sector.checkCollisions(self.position + check, self.size):
            hit_something = True
        else:
            collided = self.sector.hitMember(self,self.sector.objects,check)
            if len(collided)==0:
                temp += check

        check = np.array([0,0,self.velocity[2]],dtype=np.float32)
        if self.sector.checkCollisions(self.position + check, self.size):
            hit_something = True
            #did we hit the ground?
            if self.velocity[2] < 0:
                self.position[2] = self.ground_z
        else:
            temp += check

        self.position += temp*t/16

        #get new sector based on new position
        if self.sector:
            self.setSector(self.sector.newSector(self.position))

        return hit_something

    def moveBounce(self,t):
        """ Attempt to move the object with its velocity.
        If an obstacle is hit, rebound.
        Return whether an obstacle was hit """

        hit_something = False

        #movements are checked and summed up.
        temp = np.array([0,0,0],dtype=np.float32)

        check = np.array([self.velocity[0],0,0],dtype=np.float32)
        if self.sector.checkCollisions(self.position + check, self.size):
            hit_something = True
            check *= -0.5
        temp += check

        check = np.array([0,self.velocity[1],0],dtype=np.float32)
        if self.sector.checkCollisions(self.position + check, self.size):
            hit_something = True
            check *= -0.5
        temp += check

        check = np.array([0,0,self.velocity[2]],dtype=np.float32)
        if self.sector.checkCollisions(self.position + check, self.size):
            hit_something = True
            check *= -0.5
        temp += check

        self.position += temp*t/16

        #get new sector based on new position
        if self.sector:
            self.setSector(self.sector.newSector(self.position))

        return hit_something

    def draw(self):
        glUseProgram(shader)
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.transform_model)
        self.graphics_model.draw()
    
    def destroy(self):
        self.sector.removeObject(self)
        self.active = False

class Player(physicsObject):
    def __init__(self,position,direction):
        glUseProgram(shader)
        super().__init__(position,np.array([4,4,16],dtype=np.float32))
        self.tag='p'
        self.theta = direction
        self.phi = 0
        pygame.mouse.set_pos(SCREEN_WIDTH/2,SCREEN_HEIGHT/2)
        self.speed = 1.2
        self.height_vec = np.array([0,0,16],dtype=np.float32)

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
        self.up = np.array([0,0,1],dtype=np.float32)
        projection_matrix = pyrr.matrix44.create_perspective_projection(45,SCREEN_WIDTH/SCREEN_HEIGHT,1,430,dtype=np.float32)
        glUniformMatrix4fv(glGetUniformLocation(shader,"projection"),1,GL_FALSE,projection_matrix)
        self.makeSun()
        self.ground_z = 0
        self.camera_pos = np.array([self.size[0]/2,self.size[1]/2,self.size[2]-1],dtype=np.float32)

    def makeSun(self):
        glUseProgram(shader)
        glUniform3fv(glGetUniformLocation(shader,'sun.direction'),1,np.array([0,-0.866,-0.5],dtype=np.float32))
        glUniform3fv(glGetUniformLocation(shader,'sun.colour'),1,np.array([1,0.99,0.65],dtype=np.float32))
        glUniform3fv(glGetUniformLocation(shader,'sun.ambient'),1,np.array([1,0.55,0.24],dtype=np.float32))

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

    def handle_mouse(self,t):
        new_pos = pygame.mouse.get_pos()
        pygame.mouse.set_pos(SCREEN_WIDTH//2,SCREEN_HEIGHT//2)
        self.theta -= t*(new_pos[0] - SCREEN_WIDTH/2)/16
        self.theta = self.theta%360
        self.phi -= t*(new_pos[1] - SCREEN_HEIGHT/2)/16
        self.phi = min(max(self.phi,-90),90)

    def handle_event(self,event):
        if event.type==pygame.MOUSEBUTTONDOWN:
            if event.button==1:
                self.shoot()
            elif event.button == 3:
                self.focus()
        if event.type == pygame.MOUSEBUTTONUP and event.button==3:
            self.focusing = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and self.on_ground:
                self.jump()

    def jump(self):
        self.velocity[2] = 10
        self.acceleration = np.array([0,0,-0.7],dtype=np.float32)

    def walk(self,t):
        #physics stuff
        actual_direction = self.theta + self.walk_direction
        cos_ad = np.cos(np.radians(actual_direction),dtype=np.float32)
        sin_ad = np.sin(np.radians(actual_direction),dtype=np.float32)
        self.velocity = np.array([cos_ad,sin_ad,0],dtype=np.float32)*self.speed

        #animation stuff

        self.walk_t += self.speed*self.walk_v*t/16
        if self.walk_t>45 or self.walk_t<-45:
            self.walk_v *= -1
        self.walk_t2 += t/16
        if self.walk_t2 >= 1:
            self.walk_t2 = 1

    def update(self,t):
        glUseProgram(shader)

        #send camera position to shader
        self.height_vec = np.array([0,0,4*np.sin(np.radians(10*self.walk_t))],dtype=np.float32)
        self.view_pos = self.position + self.camera_pos + self.height_vec
        glUniform3fv(glGetUniformLocation(shader,"viewPos"),1,self.view_pos)

        #keys
        self.handle_keys()

        #mouse
        self.handle_mouse(t)
        self.look()

        if self.walking:
            if self.on_ground:
                self.walk(t)
        else:
            self.idle(t)

        #physics behaviour
        super().update(t)
        self.ground_z = self.sector.position[2]

        #lighting
        """
        if self.currentSector != None:
            addLights(self.currentSector)
        """

        self.updateGun(t)
        self.updateSky()

    def updateGun(self,t):
        if self.gun_state==1:
            self.gun_t += 2*t/16
            if self.gun_t >=0:
                self.gun_t = 0
                self.gun_state = 0

        #gun model transform
        self.gun_model = pyrr.matrix44.create_identity(dtype=np.float32)
        #if the player is walking spin the gun into holding position
        temp = pyrr.matrix44.create_from_y_rotation(theta = np.radians(self.walk_t2*-90),dtype=np.float32)
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,temp)

        temp = pyrr.matrix44.create_from_z_rotation(theta = np.radians(self.walk_t2*-45),dtype=np.float32)
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,temp)

        #basic position of gun
        temp = pyrr.matrix44.create_from_translation(np.array([-1,1,-1],dtype=np.float32),dtype=np.float32)
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,temp)
        #with walking animation
        walk_cos = np.cos(np.radians(self.walk_t))
        walk_sin = np.sin(np.radians(self.walk_t))

        temp2 = np.array([(-2+walk_cos)*self.walk_t2,(-2+walk_sin)*self.walk_t2,-self.walk_t2],dtype=np.float32)

        temp = pyrr.matrix44.create_from_translation(temp2,dtype=np.float32)
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,temp)
        #with mouse focus
        temp2 = np.array([self.focus_t,-self.focus_t,self.focus_t],dtype=np.float32)
        temp = pyrr.matrix44.create_from_translation(temp2,dtype=np.float32)
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,temp)
        #with gun recoil
        temp2 = np.array([0,-np.sin(np.radians(self.gun_t)),0],dtype=np.float32)
        temp = pyrr.matrix44.create_from_translation(temp2,dtype=np.float32)
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,temp)
        #rotate gun to match player's direction
        temp = pyrr.matrix44.create_from_x_rotation(theta = np.radians(self.phi),dtype=np.float32)
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,temp)
        temp = pyrr.matrix44.create_from_z_rotation(theta = np.radians(270-self.theta),dtype=np.float32)
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,temp)
        #move gun to player's position
        temp = pyrr.matrix44.create_from_translation(self.look_target,dtype=np.float32)
        self.gun_model = pyrr.matrix44.multiply(self.gun_model,temp)

    def updateSky(self):
        #sky model transform
        self.sky_model = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)

    def idle(self,t):
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
        
        if self.on_ground:
            #slow down
            if pyrr.vector.length(self.velocity)<0.1:
                self.velocity *= 0
            else:
                self.velocity *= 0.7

    def look(self):
        glUseProgram(shader)
        self.cos_phi = np.cos(np.radians(self.phi),dtype=np.float32)
        self.sin_phi = np.sin(np.radians(self.phi),dtype=np.float32)
        self.cos_theta = np.cos(np.radians(self.theta),dtype=np.float32)
        self.sin_theta = np.sin(np.radians(self.theta),dtype=np.float32)

        #get lookat
        self.look_direction = np.array([self.cos_phi*self.cos_theta,self.cos_phi*self.sin_theta,self.sin_phi],dtype=np.float32)
        self.look_direction *= 3

        camera_right = pyrr.vector3.cross(self.up,self.look_direction)
        camera_up = pyrr.vector3.cross(self.look_direction,camera_right)
        self.look_target = self.view_pos + self.look_direction

        lookat_matrix = pyrr.matrix44.create_look_at(self.view_pos,self.look_target,camera_up,dtype=np.float32)
        glUniformMatrix4fv(glGetUniformLocation(shader,"view"),1,GL_FALSE,lookat_matrix)

    def draw(self):
        glUseProgram(shader)
        #draw gun
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.gun_model)
        self.gun.draw()

        #draw sky
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.sky_model)
        self.sky.draw()

    def shoot(self):
        if self.gun_state==0 and not self.walking:
            self.gun_state = 1
            self.gun_t = -90
            if self.sector:
                self.sector.addObject(Bullet(self.view_pos+2*self.look_direction,self.look_direction,self.sector))

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
        self.player = None
        self.enemies = []
        self.objects = []
        self.bullets = []

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
                    pos = np.array([32*x,-32*y,32],dtype=np.float32)
                    modelMatrix = pyrr.matrix44.create_from_translation(self.position+pos,dtype=np.float32)
                    self.graphics_model.takeVertexInput(modelToStream.getTransformedVertices(modelMatrix))

        self.graphics_model.finaliseModel()
        self.graphics_model.texture = TEXTURES['sector'][0]

    def addObject(self,obj):
        """ Add obj to the sector's set of active objects """
        if obj.tag[0]=='p':
            self.player = obj
        elif obj.tag[0]=='e':
            if obj not in self.enemies:
                self.enemies.append(obj)
        elif obj.tag[0]=='b':
            if obj not in self.bullets:
                self.bullets.append(obj)
        else:
            if obj not in self.objects:
                self.objects.append(obj)

    def removeObject(self,obj):
        """ Remove obj from the sector's set of active objects """
        if obj.tag[0]=='p':
            self.player = None
        elif obj.tag[0]=='e':
            if obj in self.enemies:
                self.enemies.pop(self.enemies.index(obj))
        elif obj.tag[0]=='b':
            if obj in self.bullets:
                self.bullets.pop(self.bullets.index(obj))
        else:
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

    def checkCollisions(self,pos,size):

        west = pos[0]
        east = pos[0] + size[0]
        north = pos[1] + size[1]
        south = pos[1]
        top = pos[2] + size[2]
        bottom = pos[2]

        if self.has_bottom_wall:
            if south<self.pos_a[1]:
                return True

        if self.has_right_wall:
            if east>self.pos_b[0]:
                return True

        if self.has_top_wall:
            if north>self.pos_c[1]:
                return True

        if self.has_left_wall:
            if west<self.pos_d[0]:
                return True

        if self.has_floor:
            if bottom<self.position[2]:
                return True

        if self.has_ceiling:
            if top>self.top_position[2]:
                return True

        return False

    def hitMember(self,obj,group,offset=np.array([0,0,0],dtype=np.float32)):
        members_hit = []
        for obj2 in group:
            if self.rectCheck(obj,obj2,offset):
                members_hit.append(obj2)
        return members_hit

    def rectCheck(self,obj1,obj2,offset):
        """
            check if two objects' hitboxes collide, return true if so
        """

        #bounds for obj1
        north1 = obj1.position[1] + obj1.size[1] + offset[1]
        south1 = obj1.position[1] + offset[1]
        east1 = obj1.position[0] + obj1.size[0] + offset[0]
        west1 = obj1.position[0] + offset[0]
        top1 = obj1.position[2] + obj1.size[2] + offset[2]
        bottom1 = obj1.position[2] + offset[2]

        #bounds for obj1
        north2 = obj2.position[1] + obj2.size[1]
        south2 = obj2.position[1]
        east2 = obj2.position[0] + obj2.size[0]
        west2 = obj2.position[0]
        top2 = obj2.position[2] + obj2.size[2]
        bottom2 = obj2.position[2]

        #checks
        if north1 < south2:
            return False
        if south1 > north2:
            return False
        if east1 < west2:
            return False
        if west1 > east1:
            return False
        if top1 < bottom2:
            return False
        if bottom1 > top2:
            return False

        return True

    def update(self,t):
        if self.player is not None:
            if not self.player.updated:
                #store a reference to the player before updating,
                # as its update may take it out of the sector
                obj = self.player
                self.player.update(t)
                obj.updated = True
        
        for obj in self.enemies:
            if not obj.updated:
                obj.update(t)
                obj.updated = True
        
        for obj in self.bullets:
            if not obj.updated:
                obj.update(t)
                obj.updated = True

        for obj in self.objects:
            if not obj.updated:
                obj.update(t)
                obj.updated = True

    def clearUpdate(self):
        if self.player is not None:
            self.player.updated = False
        
        for obj in self.enemies:
            obj.updated = False
        
        for obj in self.bullets:
            obj.updated = False

        for obj in self.objects:
            obj.updated = False

    def draw(self):
        glUseProgram(shader)
        glUniformMatrix4fv(glGetUniformLocation(shader,"model"),1,GL_FALSE,self.model)
        self.graphics_model.draw()

        if self.player is not None:
            self.player.draw()
        
        for obj in self.enemies:
            obj.draw()
        
        for obj in self.bullets:
            obj.draw()

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

class Bullet(physicsObject):
    def __init__(self,position,velocity,sector):
        super().__init__(position.copy(),[1,1,1],velocity.copy())
        self.tag = 'b'
        self.sector = sector
        self.rotation = random_3d()
        self.angle = np.array([0,0,0],dtype=np.float32)
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        self.updated = False
        self.active = True
        self.graphics_model = BULLET_MODEL

    def update(self,t):
        if self.active:
            self.angle += t*self.rotation/16
            self.updateModel()

            hit = super().update(t)
            if hit:
                self.destroy()

    def updateModel(self):
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        temp = pyrr.matrix44.create_from_x_rotation(theta = self.angle[0],dtype=np.float32)
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,temp)
        temp = pyrr.matrix44.create_from_y_rotation(theta = self.angle[1],dtype=np.float32)
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,temp)
        temp = pyrr.matrix44.create_from_z_rotation(theta = self.angle[2],dtype=np.float32)
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,temp)
        temp = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,temp)

class Ghost(physicsObject):
    def __init__(self,position):
        super().__init__(position,[4,4,8])
        self.tag = 'e'
        self.health = 12
        self.direction = random_3d()
        self.speed = 1
        self.sector = None
        self.t = 0
        self.transform_model = pyrr.matrix44.create_identity(dtype=np.float32)
        # 0:wander, 1: chase, 2: retreat
        self.state = 0
        self.radius = 8

    def setPlayer(self,reference):
        self.player_reference = reference

    def update(self,t):
        player = self.player_reference

        if self.position[2] > 40:
            self.velocity[2] = -1

        if self.state==0:
            #wander
            self.speed = 0.5
            self.velocity = self.speed*self.direction
            hitSomething = super().update(t)
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
            self.velocity = self.speed*self.direction
            hitSomething = super().update(t)

            #did we hit the player?
            toPlayer = (player.position + player.height_vec/2) - self.position
            distance = pyrr.vector.length(toPlayer)
            if distance <= self.radius + 8:
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
            self.t += t/16
            self.speed = 0.5
            self.velocity = self.speed*self.direction
            hitSomething = super().update(t)
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
        temp = pyrr.matrix44.create_from_z_rotation(theta = theta,dtype=np.float32)
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,temp)
        temp = pyrr.matrix44.create_from_translation(self.position,dtype=np.float32)
        self.transform_model = pyrr.matrix44.multiply(self.transform_model,temp)

class Box(physicsObject):
    def __init__(self,position):
        super().__init__(position,np.array([16,16,3.2]))
        self.tag = 'o'
        self.transform_model = pyrr.matrix44.create_from_translation(self.position)
