import os

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

##from nptimelapse import auth, index
##from nptimelapse.model import
from nptimelapse.cli import init_db
from nptimelapse.db import db


def create_app(test_config=None):
    global db
    app = Flask(__name__)

    # load config from envvars
    app.config['SECRET_KEY'] = config_from_env('SECRET_KEY', 'zmien to')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = \
        config_from_env('SQLALCHEMY_TRACK_MODIFICATIONS', False)
    app.config['SQLALCHEMY_DATABASE_URI'] = \
        config_from_env('DATABASE_URL', False)

    # load testing config if testing
    if test_config is not None:
        app.config.from_mapping(test_config)


    # ensure the instance folder exists
    try:
        os.mkdir(app.instance_path)
    except OSError:
        pass

    # connect to database
    # SQLALCHEMY_DATABASE_URI
    db.init_app(app)

    # the simplest page
    @app.route('/hello')
    def hello():
        return 'Henlo warld!'

    # pages
    # app.register_blueprint(auth.bp)

    # model
    # app.register_blueprint(user.bp)

    # commandline arguments
    app.cli.add_command(init_db)

    return app


def config_from_env(variable, default=None):
    ans = os.environ.get(variable)
    if not ans:
        return default
    return ans


app = create_app()
