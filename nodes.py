import socket
import struct

from bitstring import BitArray


class Node(object):
    def __init__(self, node_id, addr):
        self.id = BitArray(node_id)
        self.addr = addr

    @property
    def info(self):
        ip, port = self.addr
        info = self.id.bytes
        info += socket.inet_aton(ip)
        info += struct.pack('!H', port)
        return info


def parse_nodes(b_str):
    if len(b_str) % 26:
        return
    nodes = []
    for i in range(len(b_str) // 26):
        info = b_str[i * 26: i * 26 + 26]
        node_id = info[:20]
        ip = socket.inet_ntoa(info[20:24])
        port = struct.unpack('!H', info[24:])[0]
        nodes.append(Node(node_id, (ip, port)))
    return nodes
