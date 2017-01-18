import random as _random
import struct as _struct
from . import bencode


def randomid(length=20):
    return b''.join([_struct.pack('B', _random.randint(0, 255)) for _ in range(length)])
