from flask_script import Manager

from app import db, creat_app

manager = Manager(creat_app())


@manager.command
def create_db():
    db.create_all(app=creat_app())


if __name__ == '__main__':
    manager.run()
