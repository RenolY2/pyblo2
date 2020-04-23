from binary_io import *
from binascii import hexlify, unhexlify
from mat1.mat1 import MAT1

class Node(object): 
    def __init__(self):
        self.children = []
        self.materials = None 
        self.textures = None 
        
    def print_hierarchy(self, indent=0):
        for child in self.children:
            if isinstance(child, Node):
                child.print_hierarchy(indent+4)
            else:
                print("{0}{1}".format(indent*"-", child.name))
    
    @classmethod
    def from_file(cls, f, materials=None, textures=None):
        node = cls()
        node.materials = materials 
        node.textures = textures
        
        next = peek_id(f)
        while next != b"EXT1":
            if next == b"BGN1":
                f.read(8)
                childnode = Node.from_file(f, node.materials, node.textures)
                node.children.append(childnode)
            elif next == b"END1" or next == b"EXT1":
                f.read(8)
                return node 
            elif next == b"TEX1":
                
                node.textures = TextureNames.from_file(f)
                print("set the tex1", node.textures)
                node.children.append(node.textures)
            elif next == b"FNT1":
                node.children.append(FontNames.from_file(f))
            elif next == b"MAT1":
                print("Set the materials")
                thing = f.tell()
                mat1 = MAT1.from_file(f)
                f.seek(thing)
                node.materials = Item.from_file(f)
                node.children.append(node.materials)
                print(mat1.material_count, "materials")
                print(mat1.material_names.strings)
            
            elif next == b"PAN2":
                node.children.append(Pane.from_file(f))
            elif next == b"PIC2":
                print("hmmm", node.textures)
                node.children.append(Picture.from_file(f, node.materials, node.textures))
            elif next == b"WIN2":
                node.children.append(Window.from_file(f))
            elif next == b"TBX2":
                node.children.append(Textbox.from_file(f))
            elif not next:
                raise RuntimeError("malformed file?")
            else:
                raise RuntimeError("Unknown: {0}".format(next))
            
            next = peek_id(f)
        
        return node 
    
    def write(self, f):
        pass 
    
    def serialize(self):
        result = []
        for child in self.children:
            result.append(child.serialize())
        
        return result 
    
    @classmethod 
    def deserialize(cls, obj):
        node = cls()
        for item in obj:
            if isinstance(item, list):
                bloitem = Node.deserialize(item)
            elif item["type"] == "TEX1":
                bloitem = TextureNames.deserialize(item)
            else:
                bloitem = item.deserialize(item)
            
            node.children.append(bloitem)
        
        return node 
    
        
class Item(object):
    def __init__(self, name):
        self.name = name 
        self.data = b""
        print(name)
    
    @classmethod 
    def from_file(cls, f):
        
        resname = str(f.read(4), "ascii")
        item = Item(resname)
        size = read_uint32(f)
        item.data = f.read(size-8)
        return item 
    
    def write(self, f):
        f.write(bytes(self.name, "ascii"))
        write_uint32(f, len(self.data) + 8)
    
    def serialize(self):
        result = {"type": self.name,
                "data": str(hexlify(self.data), encoding="ascii")}
        
        return result 
        
    @classmethod 
    def deserialize(cls, obj):
        item = cls(obj["type"])
        item.data = bytes(unhexlify(obj["data"]), encoding="ascii")
        return item 


class Pane(object):
    def __init__(self):
        self.name = "PAN2"
        #self.unk1 = 0
        
    @classmethod
    def from_file(cls, f, blotype=b"PAN2"):
        start = f.tell()
        if f.read(4) != blotype:
            raise RuntimeError("Not a {0} section".format(blotype))
        size = read_uint32(f)
        unk = read_uint16(f)
        assert unk == 0x40
        
        pane = cls()
        pane.unk1 = read_uint16(f) # 0xA
        pane.unk2 = read_uint8(f) # 0xC
        pane.unk3 = read_uint8(f) # 0xD
        
        re = f.read(2)
        assert re == b"RE"
        pane.panename = f.read(0x8+0x8).decode("ascii")
        #unknown = f.read(0x8)
        #assert unknown == b"\x00"*8
        pane.size_x = read_float(f)
        pane.size_y = read_float(f)
        pane.scale_x = read_float(f)
        pane.scale_y = read_float(f)
        unk = read_float(f)
        assert unk == 0.0 
        unk = read_float(f)
        assert unk == 0.0 
        
        pane.rotation = read_float(f)
        pane.offset_x = read_float(f)
        pane.offset_y = read_float(f)
        pane.unk4 = read_float(f)
        
        assert f.tell() == start + 0x48
        return pane 
        
    def serialize(self):
        result = {"type": "PAN2"}
        for key, val in self.__dict__.items():
            if key != "name":
                result[key] = val 
                
        return result 
    
    
class Window(object):
    def __init__(self):
        self.name = "WIN2"
    
    @classmethod
    def from_file(cls, f):
        start = f.tell()
        if f.read(4) != b"WIN2":
            raise RuntimeError("Not a WIN2 section")
        size = read_uint32(f)
        
        window = cls()
        
        window.pane = Pane.from_file(f, b"pan2")
        window_size = read_uint16(f)
        reserved = f.read(6)
        assert reserved == b"RESERV"
        window.padding = f.read(8).decode("ascii", errors="backslashreplace")
        #assert window.padding == "\xFF"*8
        window.subdata = [{}, {}, {}, {}]
        for i in range(4):
            window.subdata[i]["sub_unk1"] = read_uint16(f)
        window.unkbyte1 = read_uint8(f)
        window.unkbyte2 = read_uint8(f)
        window.unk3 = read_uint16(f)
        window.unk4 = read_uint16(f)
        window.unk5 = read_uint16(f)
        window.unk6 = read_uint16(f)
        window.unk7 = read_uint16(f)
        window.unk8 = read_uint16(f)
        
        re = f.read(2)
        assert re == b"RE"
        
        for i in range(4):
            window.subdata[i]["sub_unk2"] = read_uint16(f)
        for i in range(4):
            window.subdata[i]["sub_unk3"] = hex(read_uint32(f))
        assert f.tell() == start+0x90
        return window 
        
    def serialize(self):
        result = {"type": "WIN2"}
        for key, val in self.__dict__.items():
            if key != "name":
                result[key] = val 
        
        result["pane"] = self.pane.serialize()
        
        return result 
    
    
class Picture(Pane):
    def __init__(self):
        self.name = "PIC2"
        pass 
    
    @classmethod
    def from_file(cls, f, materials, textures):
        start = f.tell()
        if f.read(4) != b"PIC2":
            raise RuntimeError("Not a PIC2 section")
        size = read_uint32(f)
        
        picture = cls()
        
        picture.pane = Pane.from_file(f, b"pan2")
        picture_size = read_uint16(f)
        picture.material = read_uint16(f)
        picture._texture = read_uint16(f)
        
        if picture._texture >= len(textures.references):
            picture.texture = "Index out of range"
        else:
            picture.texture = textures.references[picture._texture]
        
        re = f.read(2)
        print(re)
        assert re == b"RE"
        color1 = {}
        color2 = {}
        
        color1["unk1"] = read_uint16(f)
        color1["unk2"] = read_uint16(f)
        color2["unk1"] = read_uint16(f)
        color2["unk2"] = read_uint16(f)
        
        color1["unknowns"] = [read_uint16(f) for x in range(4)]
        color2["unknowns"] = [read_uint16(f) for x in range(4)]
        color1["col1"] = [read_uint8(f) for x in range(4)]
        color1["col2"] = [read_uint8(f) for x in range(4)]
        color2["col1"] = [read_uint8(f) for x in range(4)]
        color2["col2"] = [read_uint8(f) for x in range(4)]
        
        picture.color1 = color1 
        picture.color2 = color2 
        
        assert f.tell() == start+0x80
        return picture 
    
    def serialize(self):
        result = {"type": "PIC2"}
        for key, val in self.__dict__.items():
            if key != "name":
                result[key] = val 
        
        result["pane"] = self.pane.serialize()
        
        return result 


class Textbox(object):
    def __init__(self):
        self.name = "TBX2"
    
    @classmethod
    def from_file(cls, f):
        start = f.tell()
        if f.read(4) != b"TBX2":
            raise RuntimeError("Not a TBX2 section")
        size = read_uint32(f)
        
        textbox = cls()
        
        textbox.pane = Pane.from_file(f, b"pan2")
        textbox_size = read_uint16(f)
        textbox.unk1 = read_uint16(f)
        textbox.unk2 = read_uint16(f)
        textbox.signedunk3 = read_int16(f)
        textbox.signedunk4 = read_int16(f)
        textbox.unk5 = read_uint16(f)
        textbox.unk6 = read_uint16(f)
        textbox.unk7byte = read_uint8(f)
        textbox.unk8byte = read_uint8(f)
        textbox.unk9 = read_uint32(f)
        textbox.unk10 = read_uint32(f)
        textbox.unk11 = read_uint8(f)
        res = f.read(3)
        assert res == b"RES"
        textbox.unk12 = read_uint16(f)
        stringlength = read_uint16(f)
        assert f.tell() == start+0x70
        textbox.text = f.read(stringlength).decode("shift-jis", errors="backslashreplace")
        f.seek(start+size)
        return textbox 
    
    def serialize(self):
        result = {"type": "TBX2"}
        for key, val in self.__dict__.items():
            if key != "name":
                result[key] = val 
        
        result["pane"] = self.pane.serialize()
        
        return result 

class ResourceReference(Item):
    def __init__(self):
        super().__init__(self.ResName())
        self.references = []
    
    @staticmethod
    def ResName():
        raise RuntimeError("Implement this!")
        
    @classmethod
    def from_file(cls, f):
        start = f.tell()
        if f.read(4) != bytes(cls.ResName(), encoding="ascii"):
            raise RuntimeError("Not a {0} section".format(self.ResName()))
        resreference = cls()
        size = read_uint32(f)
        
        rescount = read_uint16(f)
        idk = read_uint16(f)
        assert idk == 0xFFFF 
        headersize = read_uint32(f)
        assert headersize == 0x10
        
        restart = f.tell()
        
        rescount2 = read_uint16(f)
        assert rescount == rescount2 
        
        for i in range(rescount):
            f.seek(restart + 2 + i*2)
            offset = read_uint16(f)
            
            f.seek(restart + offset)
            unk = read_uint8(f)
            length = read_uint8(f)
            assert unk == 0x2 
            name = str(f.read(length), "shift-jis")
            
            resreference.references.append(name)
            
        f.seek(start+size)
        return resreference
    
    def serialize(self):
        result = {"type": self.ResName()}
        result["references"] = self.references 
        
        return result 


class TextureNames(ResourceReference):
    @staticmethod
    def ResName():
        return "TEX1"


class FontNames(ResourceReference):
    @staticmethod
    def ResName():
        return "FNT1"
    

class Information(object):
    def __init__(self, width, height):
        self.width = width 
        self.height = height 
        self.val1 = self.val2 = self.val3 = self.val4 = 0
    
    @classmethod 
    def from_file(cls, f):
        if f.read(4) != b"INF1":
            raise RuntimeError("Not an INF1 section!")
        
        size = read_uint32(f)
        
        width = read_uint16(f)
        height = read_uint16(f)
        inf = cls(width, height)
        inf.val1 = read_uint8(f)
        inf.val2 = read_uint8(f)
        inf.val3 = read_uint8(f)
        inf.val4 = read_uint8(f)
        f.read(size-0x10) # Padding
        
        return inf 
    
    def write(self, f):
        f.write(b"INF1")
        write_uint32(f, 0x20)
        write_uint16(f, self.width)
        write_uint16(f, self.height)
        write_uint8(f, self.val1)
        write_uint8(f, self.val2)
        write_uint8(f, self.val3)
        write_uint8(f, self.val4)
        
    def serialize(self):
        result = {}
        result["type"] = "INF1"
        result["width"] = self.width 
        result["height"] = self.height 
        result["values"] = [self.val1, self.val2, self.val3, self.val4]
        
        return result 
        
    @classmethod
    def deserialize(cls, obj):
        assert obj["type"] == "INF1"
        info = cls(obj["width"], obj["height"])
        info.val1 = obj["values"][0]
        info.val2 = obj["values"][1]
        info.val3 = obj["values"][2]
        info.val4 = obj["values"][3]
        
        return info 
        
        
class ScreenBlo(object):
    def __init__(self):
        self.root = Node()
        self.info = Information(640, 480)
    
    def print_hierarchy(self):
        print("INF1 - {0} {1}".format(self.info.width, self.info.height))
        self.root.print_hierarchy(4)
        
    @classmethod 
    def from_file(cls, f):
        magic = f.read(8)
        if magic != b"SCRNblo2":
            raise RuntimeError("Unsupported magic: {0}".format(magic))
        
        total_size = read_uint32(f)
        count = read_uint32(f)
        
        svr = f.read(0x10) # ignored
        
        blo = cls()
        blo.info = Information.from_file(f)
        
        blo.root = Node.from_file(f)
            
        
        return blo 
    
    def serialize(self):
        result = []
        result.append(self.info.serialize())
        result.append(self.root.serialize())
        
        return result 

if __name__ == "__main__":  
    import json 
    import sys
    inputfile = sys.argv[1]
    #inputfile = "courseselect_under.blo"
    outputfile = inputfile + ".json"
    with open(inputfile, "rb") as f:
    #with open("anim_text.blo", "rb") as f:
    #with open("challenge_modo_1p_2p.blo", "rb") as f:
    #with open("cave_pikmin.blo", "rb") as f:
        blo = ScreenBlo.from_file(f)
    blo.print_hierarchy()
    with open("texnames.txt", "w") as f:
        for name in blo.root.children[0].references:
            f.write(name)
            f.write("\n")
            
    result = blo.serialize()
    with open(outputfile, "w") as f:
        json.dump(result, f, indent=4)