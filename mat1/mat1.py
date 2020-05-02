from binary_io import read_uint32, read_uint16, read_int8_at, read_int16_at
    
class StringTable(object):
    def __init__(self):
        self.strings = []
    
    @classmethod
    def from_file(cls, f):
        stringtable = cls()
        
        start = f.tell()
        
        string_count = read_uint16(f)
        f.read(2) # 0xFFFF
        
        offsets = []
        
        print("string count", string_count)
        
        for i in range(string_count):
            hash = read_uint16(f)
            string_offset = read_uint16(f)
            
            offsets.append(string_offset)
        
        for offset in offsets:
            f.seek(start+offset)
            
            # Read 0-terminated string 
            string_start = f.tell()
            string_length = 0
            
            while f.read(1) != b"\x00":
                string_length += 1 
            
            f.seek(start+offset)
            
            if string_length == 0:
                stringtable.strings.append("")
            else:
                stringtable.strings.append(f.read(string_length).decode("shift-jis"))
            
        return stringtable 
            
    def hash_string(self, string):
        hash = 0
        
        for char in string:
            hash *= 3 
            hash += ord(char)
            hash = 0xFFFF & hash  # cast to short 
        
        return hash

    def write(self, f):
        start = f.tell()
        f.write(struct.pack(">HH", len(self.strings), 0xFFFF))
        
        for string in self.strings:
            hash = self.hash_string(string)
            
            f.write(struct.pack(">HH", hash, 0xABCD))
        
        offsets = []
        
        for string in self.strings:
            offsets.append(f.tell())
            f.write(string.encode("shift-jis"))
            f.write(b"\x00")

        end = f.tell()

        for i, offset in enumerate(offsets):
            f.seek(start+4 + (i*4) + 2)
            write_uint16(f, offset-start)

        f.seek(end)


def read_index_array(f, offset, size, count):
    values = []
    if size == 1:
        read_at = read_int8_at 
    elif size == 2:
        read_at = read_int16_at 
    
    for i in range(count):
        value = read_at(f, offset + i*size)
        values.append(value)
    
    return values 
    

class MaterialInitData(object):
    def __init__(self):
        pass 
        
        
    @classmethod
    def from_array(cls, f, i):
        initdata = cls()
        start = f.tell()
        
        f.seek(start + i * 0xE8) # 0xE8 is size of Material Init Data entry
        initdatastart = f.tell()
        f.seek(start)
        
        cullmodeIndex = read_int8_at(f, initdatastart + 0x1)
        colorChannelNumIndex = read_int8_at(f, initdatastart + 0x2)
        texGenNumIndex = read_int8_at(f, initdatastart + 0x3)
        tevStageNumIndex = read_int8_at(f, initdatastart + 0x4)
        ditherIndex = read_int8_at(f, initdatastart + 0x5) 
        unk = read_int8_at(f, initdatastart + 0x6) 
        
        # 0x7 padding 
        
        # 2 Mat Colors starting at 0x8 (2 byte index)
        matColorIndices = read_index_array(f, initdatastart + 0x8, 2, 2)
        
        # 4 ColorChans starting at 0xC (2 byte index) 
        colorChanIndices = read_index_array(f, initdatastart + 0xC, 2, 4)
        
        # 8 texcoords starting at 0x14 (2 byte index)
        texCoordIncides = read_index_array(f, initdatastart + 0x14, 2, 8)
        
        # 8 tex matrices starting at 0x24 (2 byte index) 
        texMatrixIndices = read_index_array(f, initdatastart + 0x24, 2, 8)
        # 0x34-0x37 padding
        
        # Textures?
        texcount = 0
        
        textureIndices = read_index_array(f, initdatastart + 0x38, 2, 8)
        
        for i in range(8):
            if read_int16_at(f, initdatastart + 0x38 + i*2) != -1: # Up to 0x48
                texcount += 1 
                
        fontIndex = read_int16_at(f, initdatastart + 0x48) 
        
        tevkcolor_indices = read_index_array(f, initdatastart + 0x4A, 2, 4)
        #for offset in (0x4A, 0x4C, 0x4E, 0x50):
        #    tevkcolor_indices.append(read_int16_at(f, initdatastart + offset))
        
        TevKColorSels_indices = read_index_array(f, initdatastart + 0x52, 1, 16)
        
        TevKAlphaSels_indices = read_index_array(f, initdatastart + 0x62, 1, 16)
        
        tevOrderIndices = read_index_array(f, initdatastart + 0x72, 2, 16)
        #for i in range(16):
        #    tevOrderIndex = read_int16_at(f, initdatastart + 0x72 + i*2) # (Up to 0x92)
        #    tevOrderIndices.append(tevOrderIndex) 
        
        tevcolor_indices = read_index_array(f, initdatastart + 0x92, 2, 4)
        #for i in range(4):
        #    tevcolor_indices.append(read_int16_at(f, initdatastart + 0x92+i*2)) # up to excluding 0x9A
        
        tevstageIndices = read_index_array(f, initdatastart + 0x9A, 2, 16)
        #for i in range(16):
        #    tevstageindex = read_int16_at(f, initdatastart + 0x9a + i*2) #up to 0xba
        tevstageSwapModes = read_index_array(f, initdatastart + 0xBA, 2, 16)
        
        # 4 tevswapmodes starting at 0xDA (2 byte index) 
        tevswapmodeTableIndices = read_index_array(f, initdatastart + 0xDA, 2, 4)
        alphacompIndex = read_int16_at(f, initdatastart + 0xE2)
        blendIndex = read_int16_at(f, initdatastart + 0xE4) 
        
        # 2 byte padding
        
        return initdata 
        
        
class MAT1(object):
    def __init__(self):
        self.material_names = StringTable()
        self.material_count = 0
        
    @classmethod
    def from_file(cls, f):
        start = f.tell()
        
        magic = f.read(4)
        if magic != b"MAT1":
            raise RuntimeError("Not a MAT1 section!")
        mat1 = cls()    
        sectionsize = read_uint32(f)
        mat1.material_count = read_uint16(f)
        
        f.read(2) # padding 
        
        # Material Index Remap:
        # If iterating over material count, take i, multiply by 2, get index in remap table, that's the index into
        # materialinitdata
        
        offsets = {}
        for datatype in ("MaterialInitData", "MaterialIndexRemapTable", "MaterialNames", "IndirectInitData", "GXCullMode", "MaterialColor",
                        "UcArray2_ColorChannelCount", "ColorChannelInfo", "UcArray3", "TexCoordInfo", "TexMatrixInfo", "UsArray4_TextureIndices", 
                        "UsArray5", "TevOrderInfo", "GXColorS10", "GXColor2_TevKColors", "UCArray6_Tevstagenums", "TevStageInfo2", 
                        "TevSwapModeInfo", "TevSwapModeTableInfo", "AlphaCompInfo", "BlendInfo", "UcArray7"):
            
            offsets[datatype] = start + read_uint32(f)
        
        if offsets["IndirectInitData"] == start or offsets["IndirectInitData"]-offsets["MaterialNames"] < 5:
            offsets["IndirectInitData"] = 0
        
        f.seek(offsets["MaterialNames"])
        mat1.material_names = StringTable.from_file(f)
        
        for i in range(mat1.material_count):
            f.seek(offsets["MaterialIndexRemapTable"] + i*2)
            initdataindex = read_uint16(f)
            
            f.seek(offsets["MaterialInitData"])
            materialinitdata = MaterialInitData.from_array(f, initdataindex)
        
        return mat1