import click
from flask import current_app
from flask.cli import with_appcontext
# from werkzeug.security import generate_password_hash

from nptimelapse.db import db
from nptimelapse.model import *

from datetime import datetime


@click.command('init-db')
@click.option('--reset/--no-reset', default=False)
@with_appcontext
def init_db(reset):
    print(current_app.config['SQLALCHEMY_DATABASE_URI'])
    if reset:
        print('Clearing the database.')
        db.drop_all()

    db.create_all()
    print('Database initialised.')

##    if not User.query.filter(User.email == 'root@root').one_or_none():
##        db.session.add(User(email='root@root', name='root', password=generate_password_hash('root')))
##        db.session.add(Role(user_email='root@root', name=RoleName['Administrator']))
##        db.session.commit()

