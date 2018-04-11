import time
import random
import gevent
import httplib

from client import *
from config import *
from proxy import Proxy
from utils import send_to_server


def report_status(proxy):
    users = proxy.get_users()
    status = 'running'

    for usr in users.keys():
        tid = users[usr]['tid']
        if time.time() - users[usr]['end_time'] > 0:
            status = 'success'
            proxy.delete_usr(usr)

        send_to_server('POST', '/report', {'tid': tid, 'status': status})


def main():
    proxy = None
    try:
        proxy = Proxy('0.0.0.0', PROXY_PORT)
        proxy.start()
    except socket.error, msg:
        if msg[0] == 98:
            logger.debug('socket is used, try again')
            return

    logger.info('proxy begin')
    while True:
        status = 'alive'
        if proxy.get_usr_num() > 0:
            status = 'serving'

        data = send_to_server(
            'POST', '/ask', {'bid': BID, 'port': port, 'status': status})

        if data is None:
            time.sleep(60)
            continue

        for d in data:
            proxy.add_usr(d['username'],
                          {'passwd': d['passwd'],
                           'tid': d['tid'],
                           'tm': d['tm']}
                          )

        report_status(proxy)
        time.sleep(60)


if __name__ == '__main__':
    main()
