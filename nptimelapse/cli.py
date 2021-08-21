import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import func
# from werkzeug.security import generate_password_hash

from nptimelapse.db import db
from nptimelapse.model import *
from nptimelapse.map_maker import Map

from datetime import datetime
import requests
import logging

import os
import os.path
import glob
from math import sqrt
import moviepy.editor as mpy


# Errors
class TimelapseError(Exception):
    pass


# CLI

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


@click.command('make-timelapse')
@click.argument('game_id')
@with_appcontext
def make_timelapse(game_id):
    logging.basicConfig(format='%(asctime)s|%(levelname)s| %(message)s',
                        filename=os.path.join(current_app.instance_path, 'vid_gen.log'),
                        level=logging.INFO)
    logging.info(f'Generat timelapse {game_id}')
    
    # Make sure the video cache exists
    video_cache = os.path.join(current_app.instance_path, 'video_cache')
    if not os.path.exists(video_cache):
        os.mkdir(video_cache)

    # Get basic game info
    game_data = db.session.query(func.min(Owner.tick), func.max(Owner.tick), Game) \
        .filter(Game.id == game_id).join(Game.owners).group_by(Game.id).one_or_none()
    if game_data is None:
        logging.error(f'Attempt to generate unregistered game {game_id}')
        raise TimelapseError(f'Game {game_id} is not registered')
    start_tick, end_tick, game = game_data
    tl_path = os.path.join(video_cache, f'{game.name.replace(" ", "_")}_{game.id}.mp4')

    # Check for tmp folder to see if the timelapse is not being created by another worker
    tmp_folder = os.path.join(video_cache, f'tmp')
    if os.path.exists(tmp_folder):
        logging.error('tmp folder exists. Abort generation.')
        raise TimelapseError(f'Generation already in progress')
    os.mkdir(tmp_folder)

    # Prepare the map
    logging.info('Generation start...')
    stars = Star.query.filter(Star.game_id == game_id).all()
    m = Map(stars)

    # Generate images
    for tick in range(start_tick, end_tick + 1):
        if tick % 24 == 0:
            logging.info(f'Generating tick {tick}')
        owners = Owner.query.filter(Owner.game_id == game_id) \
            .filter(Owner.tick == tick).all()
        if owners:
            m.update(owners)
        m.save(os.path.join(tmp_folder, f'{tick:04}.png'))

    # Make a video
    logging.info('Rendering video')
    images = glob.glob(os.path.join(tmp_folder, '*.png'))
    images.sort()
    video = mpy.ImageSequenceClip(images, fps=24)
    video.write_videofile(tl_path)
    
    # Cleanup the tmp_folder
    logging.info('Cleanup')
    for image in images:
        os.remove(image)
    os.rmdir(tmp_folder)
    logging.info('Generation successfull')

    return tl_path
