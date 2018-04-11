import gevent
from gevent import socket
from config import BUFFER, logger


class Client(object):
    """docstring for Client"""

    def __init__(self):
        super(Client, self).__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, ip, port):
        try:
            self.sock.connect((ip, port))
        except Exception as e:
            logger.info('error connect to ip: ' + str(ip) + ' error:' + str(e))

    def send(self, msg):
        try:
            self.sock.send(msg)
        except Exception as e:
            logger.info('error send msg' + str(e))

    def receive(self):
        data = self.sock.recv(BUFFER)
        return data

    def close(self):
        if self.sock is not None:
            self.sock.close()

        g = gevent.getcurrent()
        g.kill()
