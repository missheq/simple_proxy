from flask import Blueprint, request, url_for, jsonify
from datetime import datetime, timedelta
from models import Record, Task, TaskHistory
from app import db
import json
import atexit

DELTA_TM = 3600
record = Blueprint('record', __name__)

clear_time = datetime.utcnow() - timedelta(seconds=DELTA_TM)

def clear_record():
    global clear_time
    rds = Record.query.all()
    for rd in rds:
        if rd.last_time > clear_time:
            continue

        for task in rd.tasks:
            th = TaskHistory(task.id, 'error', task.record_id)
            db.session.add(th)
            db.session.delete(task)

        db.session.delete(rd)


@record.route('/getall', methods=['GET'])
def get_record():
    result = {'total': 0, 'alive': 0, 'useful': 0, 'serving': 0}
    rds = Record.query.all()
    now = datetime.utcnow()

    for rd in rds:
        if rd.last_time + timedelta(seconds=600) < now:
            continue
        result['total'] += 1
        result[rd.status] += 1

    return jsonify(result)

import string
import random


def id_generator(size=8, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


@record.route('/apply', methods=['POST'])
def allocation():
    '''alloc rds for each apply'''
    data = json.loads(request.data)
    num = data.get('num', 0)
    seconds = data.get('time', 0)

    result = []

    rds = Record.query.filter(Record.status != 'alive').order_by(
        Record.last_time.desc()).limit(num)
    user = id_generator(5)
    passwd = id_generator(16)

    for rd in rds:
        db.session.add(Task(user, passwd, seconds, rd.id))
        result.append({'ip': rd.ip, 'port': rd.port,
                       'username': user, 'passwd': passwd})

    try:
        db.session.commit()
        return jsonify(result)
    except Exception as e:
        return jsonify({'msg': 'error'})


@record.route('/ask', methods=['POST'])
def ask():
    '''heart attack request and get new task'''
    global clear_time
    result = []
    data = json.loads(request.data)
    bid = data['bid']
    port = data['port']
    status = data['status']
    ip = request.remote_addr

    record = Record.query.filter(Record.bid == bid).first()
    now = datetime.utcnow()
    if record is None:
        # create when there is no record of this node
        db.session.add(Record(bid, ip, port, status))
    else:
        record.ip = ip
        record.port = port
        record.status = status
        record.last_time =  now# check whether have new task

        for task in record.tasks:
            if task.status == 'new':
                task.status = 'send'
                task.end_time = now + timedelta(seconds=task.intertm * 1.5)
                result.append({
                    'tid': task.id,
                    'username': task.user,
                    'passwd': task.passwd,
                    'tm': task.intertm
                })
            else:
                if task.end_time < record.last_time:
                    th = TaskHistory(task.id, 'error', task.record_id)
                    db.session.add(th)
                    db.session.delete(task)

    flag = False
    while now - timedelta(seconds=DELTA_TM) >  clear_time:
        clear_time += timedelta(seconds=DELTA_TM)
        flag = True

    if flag:
        print 'call clear_record'
        clear_record()

    db.session.commit()

    return jsonify(result)


@record.route('/report', methods=['POST'])
def report():
    '''report the status about task
       running, success
    '''
    data = json.loads(request.data)
    tid = data['tid']

    task = Task.query.filter(Task.id == int(tid)).first()
    if task is None:
        return jsonify({'msg': 'no this task'})

    if data['status'] == 'success':
        th = TaskHistory(task.id, data['status'], task.record_id)
        db.session.add(th)
        db.session.delete(task)
        db.session.commit()
        return jsonify({'msg': 'ok'})

    if task.status != data['status']:
        task.status = data['status']
        db.session.commit()

    return jsonify({'msg': 'ok'})
