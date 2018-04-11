import os
import logging

# the server ip
SERVER_IP = ''
# do not be empty!
PROXY_PORT = 2000

# the port run server
REPORT_PORT = 2021

BUFFER = 40960

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logfile = '/tmp/logger.txt'
fh = logging.FileHandler(logfile, mode='w')
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
fh.setFormatter(formatter)

ch.setFormatter(formatter)
logger.addHandler(ch)

logger.addHandler(fh)


def getbid():
    if not os.path.isfile('/tmp/node_id'):
        from utils import id_generator
        logger.info('can not find node_id, create a tmp node_id')
        id = id_generator(12)
        with open('/tmp/node_id', 'w') as f:
            f.write(id)
        return id

    with open('/tmp/node_id') as f:
        return f.read()[:-1]

# unique id of this computer
BID = getbid()
