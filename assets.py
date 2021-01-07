"""
    stores the class definitions of models and textures
"""
from config import *

################ helper functions #############################################

def import_textures(filename):
    """
        Read a texture file and create textures

        Parameters:
            filename (string): path to the texture file.
    """

    with open(filename,'r') as f:
        line = f.readline()
        while line:
            if line[0]=='s':
                target = TEXTURES["sector"]
            elif line[0]=='m':
                target = TEXTURES["misc"]
            else:
                target = TEXTURES["enemies"]
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
            CEILING_MODELS.append(model)
    #walls
    for f in pathlib.Path("models/wall").iterdir():
        if f.suffix == ".obj":
            model = ObjModel("models/wall/",f.name)
            WALL_MODELS.append(model)
    #floors
    for f in pathlib.Path("models/floor").iterdir():
        if f.suffix == ".obj":
            model = ObjModel("models/floor/",f.name)
            FLOOR_MODELS.append(model)

################ classes ######################################################
class Model:
    def __init__(self):
        glUseProgram(shader)
        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
        self.texture = None
        self.vertices = np.empty(0,dtype=np.float32)
        self.vertexCount = 0

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

class ObjModel(Model):
    def __init__(self,folderpath,filename):
        super().__init__()
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
        super().finaliseModel()

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
        return result

class StreamModel(Model):
    # can accept streams of vertex data, rather than a file
    def __init__(self):
        super().__init__()
        self.vertices = np.empty(0,dtype=np.float32)

    def takeVertexInput(self,vertices):
        self.vertices = np.append(self.vertices,vertices)

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

################ assets #######################################################

import_textures('textures.txt')
create_models()
BULLET_MODEL = ObjModel("models/","bullet.obj")
BULLET_MODEL.texture = TEXTURES["misc"][2]
GHOST_MODEL = ObjModel("models/","ghastly.obj")
GHOST_MODEL.texture = TEXTURES["enemies"][0]
BOX_MODEL = ObjModel("models/","box.obj")
BOX_MODEL.texture = TEXTURES["misc"][3]

###############################################################################