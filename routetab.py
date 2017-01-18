import threading
import time

from nodes import Node
from bitstring import BitArray
from config import k


class RouteTable(object):
    def __init__(self, node_id):
        self.node_id = BitArray(node_id)
        self.gen = Bucket(self.node_id)
        self.__size = 0
        self.lock = threading.Lock()

    def insert(self, node):
        self.lock.acquire()
        try:
            self.gen = self.gen.insert(node)
            self.__size += 1
        except Trash:
            pass
        self.lock.release()

    def find_node(self, info_hash):
        self.lock.acquire()
        if isinstance(self.gen, Bucket):
            result = list(self.gen)
        else:
            result = self.gen.find_node(BitArray(info_hash))
        self.lock.release()
        return result

    def nodes(self):
        self.lock.acquire()
        for node in self.gen.nodes():
            yield node
        self.lock.release()

    def buckets(self):
        self.lock.acquire()
        if isinstance(self.gen, Bucket):
            yield self.gen
        else:
            for bucket in self.gen.buckets():
                yield bucket
        self.lock.release()

    def __len__(self):
        return self.__size


class Branch(object):
    def __init__(self, bucket):
        self.node_id = bucket.node_id
        self.depth = bucket.depth
        self.left = Bucket(self.node_id, self.depth + 1)
        self.right = Bucket(self.node_id, self.depth + 1)

        self.left.me_in = bucket.me_in and not self.node_id[self.depth]
        self.right.me_in = bucket.me_in and self.node_id[self.depth]

        for node in bucket:
            self.insert(node)

    def insert(self, node):
        if node.id[self.depth]:
            self.right = self.right.insert(node)
        else:
            self.left = self.left.insert(node)
        return self

    def nodes(self):
        for node in self.left:
            yield node
        for node in self.right:
            yield node

    def buckets(self):
        if isinstance(self.left, Bucket):
            yield self.left
        else:
            for bucket in self.left.buckets():
                yield bucket
        if isinstance(self.right, Bucket):
            yield self.right
        else:
            for bucket in self.right.buckets():
                yield bucket

    def find_node(self, info_hash):
        if not info_hash[self.depth]:
            son = self.left
            other = self.right
        else:
            son = self.right
            other = self.left
        if isinstance(son, Bucket):
            nodes = []
            nodes.extend(list(son))
            others = iter(other)
            for i in range(k - len(nodes)):
                nodes.append(next(others))
            return nodes
        else:
            return son.find_node(info_hash)


class Bucket(object):
    def __init__(self, node_id, depth=0):
        self.node_id = node_id
        self.__nodes = {}
        self.depth = depth
        self.me_in = True
        self.lastchange = time.time()

    def insert(self, node):
        if len(self) < k:
            if self.__nodes.get(node.id.bytes):
                self.__nodes[node.id.bytes] = node.addr
                raise Trash()
            self.__nodes[node.id.bytes] = node.addr
            self.lastchange = time.time()
            return self
        elif self.me_in:
            branch = Branch(self)
            branch.insert(node)
            return branch
        else:
            raise Trash()

    def __iter__(self):
        for _id, addr in self.__nodes.items():
            yield Node(_id, addr)

    def nodes(self):
        for _id, addr in self.__nodes.items():
            yield Node(_id, addr)

    def __len__(self):
        return len(self.__nodes)


class Trash(Exception):
    pass
