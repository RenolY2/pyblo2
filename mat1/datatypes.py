from binary_io import *
from mat1.enums import *


class Color(object):
    def __init__(self, r, g, b, a):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    @classmethod
    def from_array(cls, f, start, i):
        f.seek(start + i*4)
        r, g, b, a = read_uint8(f), read_uint8(f), read_uint8(f), read_uint8(f)

        return cls(r, g, b, a)

    def write(self, f):
        write_uint8(f, self.r)
        write_uint8(f, self.g)
        write_uint8(f, self.b)
        write_uint8(f, self.a)


class ChannelControl(object):
    def __init__(self):
        self.enabled = False
        self.material_source_color = ColorSource()
        self.light_mask = LightId()
        self.diffuse_function = DiffuseFunction()
        self.attentuation_function = J3DAttentuationFunction()
        self.ambient_source_color = ColorSource()

    @classmethod
    def from_file(cls, f):
        channel_control = cls()
        channel_control.enabled = read_uint8(f) != 0
        channel_control.material_source_color = ColorSource.from_file(f)
        channel_control.light_mask = LightId.from_file(f)
        channel_control.diffuse_function = DiffuseFunction.from_file(f)
        channel_control.attentuation_function = J3DAttentuationFunction.from_file(f)
        channel_control.ambient_source_color = ColorSource.from_file(f)
        f.read(2) # Padding

        return channel_control

    @classmethod
    def from_array(cls, f, start, i):
        f.seek(start + i * 8)
        return cls.from_file(f)

    def write(self, f):
        write_uint8(f, int(self.enabled != 0))
        self.material_source_color.write(f)
        self.light_mask.write(f)
        self.diffuse_function.write(f)
        self.attentuation_function.write(f)
        self.ambient_source_color.write(f)
        f.write(b"\xFF\xFF")

