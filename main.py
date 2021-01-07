""" Engine for making 3D games in python """
################ Imports ######################################################
from config import *
from assets import *
from game_objects import *
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
                SECTORS.append(obj)
            elif line[0]=='p':
                #player
                # p(x,y,direction)
                line = line[beginning+1:-2].replace('\n','').split(',')
                l = [float(item) for item in line]
                player = Player(np.array([l[0],l[1],0],dtype=np.float32)*32,l[2])
                obj = None
                player.setSector(player.recalculateSector())
            elif line[0]=='g':
                #ghost
                # g(x,y,z)
                line = line[beginning+1:-2].replace('\n','').split(',')
                l = [float(item)*32 for item in line]
                obj = Ghost(np.array([l[0],l[1],l[2]],dtype=np.float32))
                obj.setModel(GHOST_MODEL)
                obj.setSector(obj.recalculateSector())
                obj.setPlayer(player)
            elif line[0]=='b':
                #box
                # b(x,y,z)
                line = line[beginning+1:-2].replace('\n','').split(',')
                l = [float(item)*32 for item in line]
                obj = Box(np.array([l[0],l[1],l[2]],dtype=np.float32))
                obj.setModel(BOX_MODEL)
                obj.setSector(obj.recalculateSector())
            line = f.readline()

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

    return player

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

################ Game Objects #################################################
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
        sector.update(t)
    ################ Render ###################################################
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    for sector in SECTORS:
        sector.draw()
    ################ Framerate ################################################
    t = min(33,CLOCK.get_time())
    CLOCK.tick()
    fps = CLOCK.get_fps()
    pygame.display.set_caption("Running at "+str(int(fps))+" fps")
    pygame.display.flip()
