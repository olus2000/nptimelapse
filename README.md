# NPTimelapse
A web tool for recording Neptune's Pride games and generating timelapse videos from them.
Designed to run on my Raspberry Pi. To run the server execute `start_server.sh`


### Desciption
This is a [Python3](python.org) web application made with
[Flask](flask.palletsprojects.com). It uses [SQLAlchemy](sqlalchemy.org) to communicate
with database and [Celery](docs.celeryproject.org) to manage its task queue which means
compatibility with many DB engines and message brokers adjustable via config.

On the front end it uses [UIkit](getuikit.com) CSS for styling with no JS logic as of
version 1.0.

### Config
All configuration is located in the `config.py` file in Flask's instance folder. Check out
`sample_instance` for reference.

App specific config:
 - `SECRET_KEY`
    Flask will use this value to cipher sessions. _Make sure you don't share
    this with anyone!_ It's recommended to use an urandom value, for example output of
    `python -c 'import os; print(os.urandom(16))'`.

All other config is specific to SQLAlchemy or Celery. Check out their respective docs for
more info.

### Requirements
All python packages required to run this app are listed in `requirements.txt` and can be
easily installed by running `python3 -m pip install -r requirements.txt`.

The app requires a database and a message broker to function properly. These can be picked
from a long list of databases supported by SQLAlchemy and message brokers supported by
Celery. Usage of a proxy server like nginx is highly advised.

For fully automated functionality a task scheduler is required, for example cron.
Command `flask fetch-owners` should be called at least once per hour to ensure all data
is collected on time and `flask purge-videos` is recommended at least once a day to clear
old cached timelapses.

### Command Line Interface 
NPTimelapse app defines the following commands using Flask CLI:
 - `flask init-db [ --reset/--no-reset ]`
    Sets up tables in the database. If `--reset` is passed the tables are dropped and
    reset, else existing tables are unmodified.

 - `flask fetch-owners [ --test/--no-test ]`
    Makes a call to the Neptune's Pride API fetching star owners for all registered games.
    Updates the database with newly fetched information unless `--test` is pased.

 - `flask purge-videos`
    Clears the video cache freeing the disk space and allowing for new timelapses to be
    generated.

These commands should either be called from the directory containing `wsgi.py` or with an
environment variable `FLASK_APP` set up properly.
