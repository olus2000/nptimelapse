import os
import os.path
import re
import time

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

from nptimelapse import index, api
# from nptimelapse.model import
from nptimelapse.cli import init_db, fetch_owners, purge_videos
from nptimelapse.extensions import db, celery


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

    # initialise celery
    init_celery(app)

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
    app.register_blueprint(api.bp)

    # model
    # app.register_blueprint(user.bp)

    # commandline arguments
    app.cli.add_command(init_db)
    app.cli.add_command(fetch_owners)
    app.cli.add_command(purge_videos)

    return app


# That's what an online tutorial told me
def init_celery(app):
    app = app or create_app()
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# I don't think that's used 
##def config_from_env(variable, default=None):
##    ans = os.environ.get(variable)
##    if not ans:
##        return default
##    return ans


app = create_app()
