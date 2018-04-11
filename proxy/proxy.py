import json
import time
import gevent
import httplib

from gevent import monkey
from gevent.pool import Pool
from gevent import select
from gevent.server import StreamServer
from gevent import socket

from config import *
from utils import send_to_server
monkey.patch_all()


SOCK_V5 = 5
RSV = 0
ATYP_IP_V4 = 1
ATYP_DOMAINNAME = 3
CMD_CONNECT = 1
IMPLEMENTED_METHODS = (2,)  # only username-password is supported


class SockV5Server(object):

    def __init__(self, ip, port, usr):
        self.ip = ip
        self.usr = usr
        self.port = port

        self.pool = Pool(1000)
        self.server = StreamServer((self.ip, self.port),
                                   self.handler)

    def close_sock_and_exit(self, client_sock=None, server_sock=None):
        if client_sock:
            if not client_sock.closed:
                client_sock.close()

        if server_sock:
            if not server_sock.closed:
                server_sock.close()

        g = gevent.getcurrent()
        g.kill()

    def process_version_and_auth(self, client_sock):
        recv = client_sock.recv(BUFFER)
        if len(recv) < 2 or ord(recv[0]) != SOCK_V5:
            self.close_sock_and_exit(client_sock)

        method = None
        num_methods = ord(recv[1])
        methods = [ord(recv[i + 2]) for i in range(num_methods)]
        for imp_method in IMPLEMENTED_METHODS:
            if imp_method in methods:
                method = imp_method
                break

        if method is None:
            self.close_sock_and_exit(client_sock)

        send_msg = '\x05' + chr(method)
        client_sock.send(send_msg)
        self.auth(client_sock)

    def auth(self, client_sock):
        recv = client_sock.recv(BUFFER)
        if len(recv) < 2 or ord(recv[0]) != 1:
            self.close_sock_and_exit(client_sock)

        ulen = ord(recv[1])
        uname = recv[2: (2 + ulen)]
        plen = ord(recv[2 + ulen])
        passwd = recv[(3 + ulen):]

        if uname not in self.usr.keys() or passwd != self.usr[uname]['passwd']:
            self.close_sock_and_exit(client_sock)

        send_msg = '\x01\x00'
        client_sock.send(send_msg)

    def process_sock_request(self, client_sock):
        recv = client_sock.recv(BUFFER)
        if len(recv) < 3 or ord(recv[0]) != SOCK_V5 or ord(recv[2]) != RSV:
            self.close_sock_and_exit(client_sock)

        addr_type = ord(recv[3])
        if addr_type == ATYP_IP_V4:
            addr = socket.inet_ntoa(recv[4:8])
        elif addr_type == ATYP_DOMAINNAME:
            addr_len = ord(recv[4])
            addr = socket.gethostbyname(recv[5:5 + addr_len])
        else:
            # only ipv4 addr or domain name is supported.
            self.close_sock_and_exit(client_sock)

        port = ord(recv[-2]) * 256 + ord(recv[-1])

        cmd = ord(recv[1])
        if cmd == CMD_CONNECT:
            # Only connect cmd is supported.
            server_sock = self.connect_target_server_and_reply(client_sock,
                                                               addr, port, cmd)
        else:
            self.close_sock_and_exit(client_sock)

        return server_sock

    def connect_target_server_and_reply(self, client_sock, addr, port, cmd):
        sock_name = client_sock.getsockname()
        server_hex_addr = socket.inet_aton(sock_name[0])
        server_hex_port = self.port_to_hex_string(sock_name[1])
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            server_sock.connect((addr, port))
            send_msg = '\x05\x00\x00\x01' + server_hex_addr + server_hex_port
            client_sock.send(send_msg)
        except Exception:
            send_msg = '\x05\x01\x00\x01' + server_hex_addr + server_hex_port
            client_sock.send(send_msg)
            self.close_sock_and_exit(client_sock)

        return server_sock

    def piping_client_and_target(self, client_sock, server_sock):
        inputs = [client_sock, server_sock]
        while True:
            try:
                in_ready, out_ready, ex_ready = select.select(inputs, [], [])
                for sock in in_ready:
                    if sock == client_sock:
                        self.recv_and_send_msg(client_sock, server_sock)
                    elif sock == server_sock:
                        self.recv_and_send_msg(server_sock, client_sock)
            except Exception:
                self.close_sock_and_exit(client_sock, server_sock)

    def recv_and_send_msg(self, recv_sock, send_sock):
        # recv() is a block I/O in the views of programmer, it returns '' when
        # remote has been closed.
        msg = recv_sock.recv(BUFFER)
        if msg == '':
            # NOTE(deliang) there exists a bug here
            # the thread exits if either of the sockets is closed, which may
            # lose some packages sometimes.
            self.close_sock_and_exit(recv_sock, send_sock)

        send_sock.sendall(msg)

    def port_to_hex_string(self, int_port):
        port_hex_string = chr(int_port / 256) + chr(int_port % 256)
        return port_hex_string

    def handler(self, client_sock, address):
        server_sock = None
        try:
            self.process_version_and_auth(client_sock)
            server_sock = self.process_sock_request(client_sock)
        except Exception as e:
            self.close_sock_and_exit(client_sock)

        self.piping_client_and_target(client_sock, server_sock)

    def start(self):
        self.server.start()


class Proxy(object):
    """docstring for Proxy"""

    def __init__(self, ip='0.0.0.0', port=1080):
        super(Proxy, self).__init__()
        self.ip = ip
        self.port = port
        self.user = {}

        self.sock_v5_server = SockV5Server(self.ip, self.port, self.user)

    def add_usr(self, usr, msg):
        '''note: it may cover its old user'''
        logger.debug('add usr')
        self.user[usr] = {'passwd': msg['passwd'],
                          'tid': msg['tid'],
                          'end_time': int(time.time()) + int(msg['tm']),
                          'connection': []
                          }

    def delete_usr(self, usr):
        if usr not in self.user.keys():
            return

        for con in self.user[usr]['connection']:
            if not con[0].closed:
                con[0].close()
            if not con[1].closed:
                con[1].close()

        del self.user[usr]

    def start(self):
        self.sock_v5_server.start()

    def get_users(self):
        return self.user

    def get_usr_num(self):
        return len(self.user.keys())

    def close(self):
        self.sock_v5_server.socket.close()
        logger.info('proxy is closed')


if '__main__' == __name__:
    sock_v5_server = SockV5Server('0.0.0.0', 1080, 'abc', '123')
    sock_v5_server.start()
    gevent.wait()
