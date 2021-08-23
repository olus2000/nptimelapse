import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import func
# from werkzeug.security import generate_password_hash

from nptimelapse.extensions import db
from nptimelapse.model import *

from datetime import datetime
import requests
import logging
import os
import os.path
import glob


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


@click.command('fetch-owners')
@click.option('--test/--no-test', default=False)
@with_appcontext
def fetch_owners(test):
    logging.basicConfig(format='%(asctime)s|%(levelname)s| %(message)s', level=logging.INFO)
    games = Game.query.filter(Game.close_date == None).all()
    new_owners = []
    for game in games:
        logging.info(f'Fetching game {game.name}:{game.id}...')
        # Fetch current star owners
        params = {'game_number': game.id,
                         'code': game.api_key,
                  'api_version': 0.1}
        payload = requests.post('https://np.ironhelmet.com/api', params).json()
        if 'error' in payload:
            logging.warning(f'Fetch error on game {game.id}: {payload["error"]}')
            continue
        data = payload['scanning_data']
        # Close a finished game
        if data['game_over']:
            game.close_date = datetime.now()
            logging.info(f'Closed a finished game {game.id}')
        # Compare and update
        for star_id, star_data in data['stars'].items():
            owner = Owner.query.filter(Owner.game_id == game.id) \
                   .filter(Owner.star_id == int(star_id)) \
                   .order_by(Owner.tick.desc()).first()
            if owner is None and star_data['puid'] != -1 \
            or owner is not None and owner.player != star_data['puid']:
                new_owners.append(Owner(tick=data['tick'], star_id=int(star_id),
                                        game_id=game.id, player=star_data['puid']))
    db.session.add_all(new_owners)
    if not test:
        db.session.commit()
    logging.info('Fetching complete')


@click.command('purge-videos')
@with_appcontext
def purge_videos():
    video_cache = os.path.join(current_app.instance_path, 'video_cache')
    if os.path.exists(video_cache):
        videos = glob.glob(os.path.join(video_cache, '*.mp4'))
        for video in videos:
            os.remove(video)
