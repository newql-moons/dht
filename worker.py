import threading
import queue
import logging

from util import bencode, randomid
from nodes import parse_nodes, Node


class SendWorker(threading.Thread):
    def __init__(self, spider):
        super().__init__()
        self.spider = spider
        self.buf = queue.Queue()

        self.is_stop = True

    def run(self):
        self.is_stop = False
        while not self.is_stop:
            data, addr = self.buf.get()
            self.spider.sock.sendto(data, addr)

    def stop(self):
        self.is_stop = True

    # 发送请求
    def req(self, q, a, addr):
        transaction_id = randomid(2)
        data = {
            b't': transaction_id,
            b'y': b'q',
            b'q': q,
            b'a': a,
        }
        self.buf.put((bencode.dumps(data), addr))

    def req_ping(self, addr):
        q = b'ping'
        a = {b'id': self.spider.node_id}
        self.req(q, a, addr)

    def req_find_node(self, target, addr):
        q = b'find_node'
        a = {
            b'id': self.spider.node_id,
            b'target': target,
        }
        self.req(q, a, addr)

    def req_get_peers(self, info_hash, addr):
        q = b'get_peers'
        a = {
            b'id': self.spider.node_id,
            b'info_hash': info_hash
        }
        self.req(q, a, addr)

    def req_announce_peer(self, addr):
        pass

    # 发送回复
    def resp(self, r, transaction_id, addr):
        data = {
            b't': transaction_id,
            b'y': b'r',
            b'r': r,
        }
        self.buf.put((bencode.dumps(data), addr))

    def resp_ping(self, transaction_id, addr):
        r = {b'id': self.spider.node_id}
        self.resp(r, transaction_id, addr)

    def resp_find_node(self, nodes, transaction_id, addr):
        _nodes = b''.join([node.info for node in nodes])
        r = {
            b'id': self.spider.node_id,
            b'nodes': _nodes,
        }
        self.resp(r, transaction_id, addr)

    def resp_get_peers(self, values, transaction_id, addr):
        r = {b'id': self.spider.node_id, b'values': values}
        self.resp(r, transaction_id, addr)

    def resp_announce_peer(self, transaction_id, addr):
        r = {b'id': self.spider.node_id}
        self.resp(r, transaction_id, addr)

    # 发送错误
    def err(self):
        pass


class RecvWorker(threading.Thread):
    def __init__(self, spider):
        super().__init__()
        self.spider = spider

        self.is_stop = True

    def run(self):
        self.is_stop = False
        while not self.is_stop:
            msg, addr = self.spider.sock.recvfrom(65535)
            self.msg_handler(msg, addr)

    def stop(self):
        self.is_stop = True

    def msg_handler(self, msg, addr):
        data = bencode.loads(msg)
        y = data[b'y']
        if y == b'q':
            q = data[b'q']
            a = data[b'a']
            handler = self.get_req_handler(q, a)
        elif y == b'r':
            r = data[b'r']
            handler = self.get_resp_handler(r)
        else:
            return
        t = data[b't']
        handler(t, addr)

    def get_req_handler(self, q, a):
        def ping(transaction_id, addr):
            self.spider.send_worker.resp_ping(transaction_id, addr)

        def find_node(transaction_id, addr):
            target = a[b'target']
            node_id = a[b'id']
            nodes = self.spider.routetab.find_node(target)
            self.spider.send_worker.resp_find_node(nodes, transaction_id, addr)
            self.spider.send_worker.req_find_node(self.spider.node_id, addr)
            self.spider.routetab.insert(Node(node_id, addr))
            logging.debug('Recv req(find_node) from %s:%d' % addr)

        def get_peers(transaction_id, addr):
            info_hash = a[b'info_hash']
            node_id = a[b'id']
            nodes = self.spider.routetab.find_node(info_hash)

            self.spider.send_worker.resp_find_node(nodes, transaction_id, addr)
            self.spider.send_worker.resp_find_node(nodes, transaction_id, addr)
            self.spider.send_worker.req_find_node(self.spider.node_id, addr)

            self.spider.routetab.insert(Node(node_id, addr))
            self.spider.info_hashes.append(info_hash)
            logging.debug('Recv req(get_peer) from %s:%d' % addr)

        def announce_peer(transaction_id, addr):
            info_hash = a[b'info_hash']
            self.spider.dispose(info_hash)
            self.spider.send_worker.resp_announce_peer(transaction_id, addr)
            logging.debug('Recv req(announce_peer) from %s:%d' % addr)

        handlers = {
            b'ping': ping,
            b'find_node': find_node,
            b'get_peers': get_peers,
            b'announce_peer': announce_peer,
        }
        return handlers[q]

    def get_resp_handler(self, r):
        def ping(transaction_id, addr):
            pass

        def find_node(transaction_id, addr):
            nodes = parse_nodes(r[b'nodes'])
            for node in nodes:
                self.spider.routetab.insert(node)
                self.spider.send_worker.req_find_node(self.spider.node_id, node.addr)
            logging.debug('Recv resp(find_node)')
            # print('Recv resp(find_node)')

        def get_peers(transaction_id, addr):
            logging.debug('Recv resp(get_peers) from %s:%d' % addr)
        if r.get(b'nodes'):
            return find_node
        elif r.get(b'values'):
            return get_peers
        else:
            return ping
