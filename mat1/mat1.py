import struct
from binary_io import *
from mat1.enums import *
from mat1.datatypes import *

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
    read_at = None
    if size == 1:
        read_at = read_int8_at 
    elif size == 2:
        read_at = read_int16_at 
    
    for i in range(count):
        value = read_at(f, offset + i*size)
        values.append(value)
    
    return values


def write_index_array(f, array, offset, size, count):
    assert len(array) == count

    values = []
    write_at = None
    if size == 1:
        write_at = write_int8_at
    elif size == 2:
        write_at = write_int16_at

    for i in range(count):
        write_at(f, array[i], offset + i * size)


class MaterialInitData(object):
    def __init__(self):
        pass
        
    @classmethod
    def from_array(cls, f, i, offsets):
        initdata = cls()
        start = f.tell()
        
        f.seek(start + i * 0xE8) # 0xE8 is size of Material Init Data entry
        initdatastart = f.tell()
        f.seek(start)
        
        cullmodeIndex = read_int8_at(f, initdatastart + 0x1)
        initdata.cullmode = CullModeSetting.from_array(f, offsets["GXCullMode"], cullmodeIndex)

        colorChannelNumIndex = read_int8_at(f, initdatastart + 0x2)
        initdata.color_channel_count = read_int8_at(f, offsets["UcArray3_TexGenCount"]+colorChannelNumIndex)

        texGenNumIndex = read_int8_at(f, initdatastart + 0x3)
        initdata.tex_gen_count = read_int8_at(f, offsets["UcArray2_ColorChannelCount"]+texGenNumIndex)

        tevStageNumIndex = read_int8_at(f, initdatastart + 0x4)
        initdata.tev_stage_count = read_int8_at(f, offsets["UCArray6_Tevstagenums"] + tevStageNumIndex)

        ditherIndex = read_int8_at(f, initdatastart + 0x5)
        initdata.dither = read_int8_at(f, offsets["UcArray7_Dither"] + ditherIndex)
        unk = read_int8_at(f, initdatastart + 0x6)
        initdata.unk = unk
        
        # 0x7 padding 
        
        # 2 Mat Colors starting at 0x8 (2 byte index)
        matColorIndices = read_index_array(f, initdatastart + 0x8, 2, 2)
        initdata.matcolors = []
        for index in matColorIndices:
            if index == -1:
                initdata.matcolors.append(None)
            else:
                color = Color.from_array(f, offsets["MaterialColor"], index)
                initdata.matcolors.append(color)
        
        # 4 ColorChans starting at 0xC (2 byte index) 
        colorChanIndices = read_index_array(f, initdatastart + 0xC, 2, 4)
        initdata.color_channels = []
        for i in range(4):
            index = colorChanIndices[i]
            if index == -1:
                initdata.color_channels.append(None)
            else:
                if i < 2 or initdata.color_channel_count != 0:
                    initdata.color_channels.append(ChannelControl.from_array(f, "ColorChannelInfo", index))
                else:
                    initdata.color_channels.append(None)



        # 8 texcoords starting at 0x14 (2 byte index)
        texCoordIndices = read_index_array(f, initdatastart + 0x14, 2, 8)
        initdata.tex_coord_generators = []
        for index in texCoordIndices:
            if index == -1:
                initdata.tex_coord_generators.append(None)
            else:
                texcoord = TexCoordInfo.from_array(f, offsets["TexCoordInfo"], index)
                initdata.tex_coord_generators.append(texcoord)

        # 8 tex matrices starting at 0x24 (2 byte index) 
        texMatrixIndices = read_index_array(f, initdatastart + 0x24, 2, 8)
        initdata.tex_matrices = []
        for index in texMatrixIndices:
            texmatrix = None if index == -1 else TexMatrix.from_array(f, offsets["TexMatrixInfo"], index)
            initdata.tex_matrices.append(texmatrix)

        # 0x34-0x37 padding
        
        # Textures?
        texcount = 0
        
        textureIndices = read_index_array(f, initdatastart + 0x38, 2, 8)
        initdata.texture_indices = []

        for i in range(8):
            index = read_int16_at(f, initdatastart + 0x38 + i*2)
            if index != -1: # Up to 0x48
                texcount += 1
                initdata.texture_indices.append(read_int16_at(f, offsets["UsArray4_TextureIndices"] + index*2))
            else:
                initdata.texture_indices.append(None)

        font_index = read_int16_at(f, initdatastart + 0x48)

        initdata.font = None if font_index != -1 else FontNumber.from_array(f, offsets["UsArray5"], font_index)
        
        tevkcolor_indices = read_index_array(f, initdatastart + 0x4A, 2, 4)
        initdata.tevkcolors = []
        for index in tevkcolor_indices:
            tevkcolor = None if index == -1 else TevKColor.from_array(f, offsets["GXColor2_TevKColors"], index)

        TevKColorSels = read_index_array(f, initdatastart + 0x52, 1, 16)
        initdata.tevkcolor_selects = TevKColorSels

        TevKAlphaSels = read_index_array(f, initdatastart + 0x62, 1, 16)
        initdata.tevkalpha_selects = TevKAlphaSels

        tevOrderIndices = read_index_array(f, initdatastart + 0x72, 2, 16)
        initdata.tevorders = []
        for index in tevOrderIndices:
            tevorder = None if index == -1 else TevOrder.from_array(f, offsets["TevOrderInfo"], index)
            initdata.tevorders.append(tevorder)

        tevcolor_indices = read_index_array(f, initdatastart + 0x92, 2, 4)
        initdata.tevcolors = []
        for index in tevcolor_indices:
            tevcolor = None if index == -1 else TevColor.from_array(f, offsets["GXColorS10_TevColor"], index)
            initdata.tevcolors.append(tevcolor)
        
        tevstageIndices = read_index_array(f, initdatastart + 0x9A, 2, 16)
        initdata.tevstages = []
        for index in tevstageIndices:
            tevstage = None if index == -1 else TevStage.from_array(f, offsets["TevStageInfo2"], index)
            initdata.tevstages.append(tevstage)

        tevstageSwapModes = read_index_array(f, initdatastart + 0xBA, 2, 16)
        initdata.tevstage_swapmodes = []
        for index in tevstageSwapModes:
            swapmode = None if index == -1 else TevSwapMode.from_array(f, offsets["TevSwapModeInfo"], index)
            initdata.tevstage_swapmodes.append(swapmode)


        # 4 tevswapmode tables starting at 0xDA (2 byte index)
        tevswapmodeTableIndices = read_index_array(f, initdatastart + 0xDA, 2, 4)
        initdata.tev_swapmode_tables = []
        for index in tevswapmodeTableIndices:
            swapmode_table = None if index == -1 else TevSwapModeTable.from_array(f, offsets["TevSwapModeTableInfo"], index)
            initdata.tev_swapmode_tables.append(swapmode_table)


        alphacompIndex = read_int16_at(f, initdatastart + 0xE2)
        initdata.alphacomp = AlphaCompare.from_array(f, offsets["AlphaCompInfo"], alphacompIndex)
        blendIndex = read_int16_at(f, initdatastart + 0xE4)
        initdata.blend = Blend.from_array(f, offsets["BlendInfo"], blendIndex)

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
                        "UcArray2_ColorChannelCount", "ColorChannelInfo", "UcArray3_TexGenCount", "TexCoordInfo", "TexMatrixInfo", "UsArray4_TextureIndices",
                        "UsArray5", "TevOrderInfo", "GXColorS10_TevColor", "GXColor2_TevKColors", "UCArray6_Tevstagenums", "TevStageInfo2",
                        "TevSwapModeInfo", "TevSwapModeTableInfo", "AlphaCompInfo", "BlendInfo", "UcArray7_Dither"):
            
            offsets[datatype] = start + read_uint32(f)
        
        if offsets["IndirectInitData"] == start or offsets["IndirectInitData"]-offsets["MaterialNames"] < 5:
            offsets["IndirectInitData"] = 0
        assert offsets["IndirectInitData"] == 0

        f.seek(offsets["MaterialNames"])
        mat1.material_names = StringTable.from_file(f)
        
        for i in range(mat1.material_count):
            f.seek(offsets["MaterialIndexRemapTable"] + i*2)
            initdataindex = read_uint16(f)
            
            f.seek(offsets["MaterialInitData"])
            materialinitdata = MaterialInitData.from_array(f, initdataindex)
        
        return mat1