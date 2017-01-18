import socket
import logging

from routetab import RouteTable
from worker import *
from config import addr
from util import randomid
from config import start_url


class Spider(object):
    def __init__(self):
        self.node_id = randomid()
        self.routetab = RouteTable(self.node_id)

        self.send_worker = SendWorker(self)
        self.recv_worker = RecvWorker(self)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(addr)
        self.info_hashes = []

    def start(self):
        self.join_dht()
        self.send_worker.start()
        self.recv_worker.start()
        self.main_loop()

    def join_dht(self):
        for address in start_url:
            self.send_worker.req_find_node(self.node_id, address)

    def main_loop(self):
        while True:
            for node in self.routetab.nodes():
                for info_hash in self.info_hashes:
                    self.send_worker.req_get_peers(info_hash, node.addr)

    def dispose(self, info_hash):
        logging.info(info_hash)
