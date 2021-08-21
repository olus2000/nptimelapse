import os
import os.path
import re
import time

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

from nptimelapse import index
# from nptimelapse.model import
from nptimelapse.cli import init_db, fetch_owners
from nptimelapse.db import db


def create_app(test_config=None):
    global db
    app = Flask(__name__, instance_relative_config=True)

    # load config and overwrite if testing
    app.config.from_pyfile('config.py', silent=True)
    if test_config is not None:
        app.config.from_mapping(test_config)


    # ensure the instance folder exists
    if not os.path.exists(app.instance_path):
        os.mkdir(app.instance_path)

    # connect to database
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'] \
        .format(instance=app.instance_path)
    db.init_app(app)

    # the simplest page
    @app.route('/hello')
    def hello():
        return 'Henlo warld!'

    # the long wait page
    @app.route('/stop')
    def wait_a_minute():
        time.sleep(20)
        return 'Hammer time!'

    # pages
    app.register_blueprint(index.bp)

    # model
    # app.register_blueprint(user.bp)

    # commandline arguments
    app.cli.add_command(init_db)
    app.cli.add_command(fetch_owners)

    return app


def config_from_env(variable, default=None):
    ans = os.environ.get(variable)
    if not ans:
        return default
    return ans


app = create_app()
