import json
import string
import random
import httplib

from config import SERVER_IP, REPORT_PORT, logger


def id_generator(size=8, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def send_to_server(method, url, data):
    conn = httplib.HTTPConnection(SERVER_IP, REPORT_PORT)

    try:
        conn.request(method,
                     url,
                     json.dumps(data),
                     {'Content-Type': 'application/json'}
                     )
        return json.loads(conn.getresponse().read())
    except Exception as e:
        logger.info('send to server error:' + str(e))
    finally:
        conn.close()

    return None
