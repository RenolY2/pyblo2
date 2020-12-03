from enum import Enum, IntEnum
from binary_io import *


class CullModeSetting(object):
    enum = IntEnum("CullMode", ["NONE", "FRONT", "BACK", "ALL"], start=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = self.enum.NONE

    @classmethod
    def from_array(cls, f, start, i):
        f.seek(start + i)
        value = read_uint8(f)
        cullmode = cls()
        cullmode.value = cls.enum(value)
        return cullmode

    def write(self, f):
        write_uint8(f, self.value)

    def __eq__(self, other):
        return type(self) == type(other) and self.value == other.value


if __name__ == "__main__":
    from io import BytesIO

    data = BytesIO()
    data.write(b"\x03")
    data.seek(0)
    setting = CullModeSetting.from_file(data)
    print(setting.value)
    setting.value = CullModeSetting.enum.NONE
    setting.write(data)

    data.seek(0)
    print(data.read())