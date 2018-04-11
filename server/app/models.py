from app import db
from datetime import datetime


class Record(db.Model):
    __tablename__ = 'record'

    id = db.Column(db.Integer, primary_key=True)
    bid = db.Column(db.String(100), nullable=False)
    ip = db.Column(db.String(100), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    last_time = db.Column(db.DateTime)
    status = db.Column(db.String(100)) #alive useful
    tasks = db.relationship('Task', backref='record', lazy= True)

    def __init__(self, bid, ip, port, status='on', last_time=datetime.utcnow()):
        self.bid = bid
        self.ip = ip
        self.port = port
        self.status = status
        self.last_time = last_time

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return u"Record<%d>" % self.bid


class Task(db.Model):
    """docstring for Task"""
    __tablename__ = 'task'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # status = ('new', 'send', 'running')
    status = db.Column(db.String(20), nullable=False)
    user = db.Column(db.String(20), nullable=False)
    passwd = db.Column(db.String(100), nullable=False)
    end_time = db.Column(db.DateTime)
    intertm = db.Column(db.Integer)
    record_id = db.Column(db.Integer, db.ForeignKey('record.id'), nullable=False)

    def __init__(self, user, passwd, intertm, record_id, status='new'):
        self.user = user
        self.passwd = passwd
        self.status = status
        self.record_id = record_id
        self.intertm = int(intertm)

class TaskHistory(db.Model):
    """docstring for TaskHistory"""
    __tablename__='taskhistory'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # status = ('success', 'error')
    tid = db.Column(db.Integer)
    status = db.Column(db.String(20), nullable=False)
    record_id = db.Column(db.Integer, db.ForeignKey('record.id'), nullable=False)

    def __init__(self, tid, status, record_id):
        self.tid = tid
        self.status = status
        self.record_id = record_id