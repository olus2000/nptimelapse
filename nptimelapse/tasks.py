from flask import current_app
from sqlalchemy import func

from nptimelapse.extensions import celery, db
from nptimelapse.map_maker import Map
from nptimelapse.model import Game, Star, Owner

import logging
import os
import os.path
import glob
from math import sqrt
import moviepy.editor as mpy
import requests
import shutil


# Errors
class TimelapseError(Exception):
    pass

class TimelapseGameNotRegisteredError(TimelapseError):
    def __init__(self, game_id):
        self.game_id = game_id
        super().__init__(self, f'Game {game_id} is not registered')

class TimelapseTmpFolderExistsError(TimelapseError):
    def __init__(self, path):
        self.path = path
        super().__init__(self, f'tmp folder already exists at {path}')


@celery.task
def make_timelapse(source_id, tl_path, map_config={}, game_params={}):
    logging.basicConfig(format='%(asctime)s|%(levelname)s| %(message)s',
                        filename=os.path.join(current_app.instance_path, 'vid_gen.log'),
                        level=logging.INFO)
    logging.info(f'Generate timelapse {source_id}')
    
    # Make sure the video cache exists
    video_cache = os.path.join(current_app.instance_path, 'video_cache')
    if not os.path.exists(video_cache):
        os.mkdir(video_cache)

    # Get basic game info
    if source_id.isnumeric():
        game_data = db.session.query(func.min(Owner.tick), func.max(Owner.tick), Game) \
            .filter(Game.id == int(source_id)).join(Game.owners).group_by(Game.id).one_or_none()
        if game_data is None:
            logging.error(f'Attempt to generate unregistered game {source_id}')
            raise TimelapseGameNotRegisteredError(source_id)
        start_tick, end_tick, game = game_data
    elif source_id == 'external':
        payload = requests.get('https://np2stats.dysp.info/api/timelapsedata.php').json()
        start_tick = min(min(int(tick) for tick in star['owners']) for star in payload['stars'].values())
        start_tick = 9
        end_tick = max(max(int(tick) for tick in star['owners']) for star in payload['stars'].values())
        end_tick = 220
#        game = Game(id=payload['id'], name=payload['name'], close_date=payload['close_date'], api_key='')
    elif source_id == 'np2stats':
        incorrect_request = False
        if 'game_id' not in game_params:
            raise Exception(f'Invalid request: no game number!')
        if 'player_id' not in game_params:
            raise Exception(f'Invalid request: no player ID!')
        if 'key' not in game_params:
            raise Exception(f'Invalid request: no authentication key provided!')
        payload = requests.get('https://np2stats.dysp.info/api/timelapsedata.php', params=game_params).json()
        start_tick = min(min(int(tick) for tick in star['owners']) for star in payload['stars'].values())
        end_tick = max(max(int(tick) for tick in star['owners']) for star in payload['stars'].values())
    else:
        logging.error(f'Attempt to generate a game from an unrecognised id {source_id}')
        raise TimelapseGameNotRegisteredError(source_id)
    tl_path = os.path.join(video_cache, f'{tl_path}')

    # Check for tmp folder to see if the timelapse is not being created by another worker
    tmp_folder = os.path.join(video_cache, f'tmp')
    if os.path.exists(tmp_folder):
        logging.error('tmp folder exists. Abort generation.')
        raise TimelapseTmpFolderExistsError(tmp_folder)
    os.mkdir(tmp_folder)

    # Prepare the map
    logging.info('Generation start...')
    if source_id.isnumeric():
        stars = Star.query.filter(Star.game_id == int(source_id)).all()
    elif source_id == 'np2stats':
        stars = [Star(game_id=int(payload['id']), id=int(s_id), x=s['x'], y=s['y'])
                 for s_id, s in payload['stars'].items()]
    m = Map(stars, **map_config)

    # Generate images
    for tick in range(start_tick, end_tick + 1):
        if tick % 24 == 0:
            logging.info(f'Generating tick {tick}')
        if source_id.isnumeric():
            owners = Owner.query.filter(Owner.game_id == int(source_id)) \
            .filter(Owner.tick == tick).all()
        elif source_id == 'np2stats':
            owners = [Owner(tick=tick, player=int(star['owners'][str(tick)]), star_id=int(star_id), game_id=int(payload['id']))
                      for star_id, star in payload['stars'].items()
                      if str(tick) in star['owners']]
        if owners:
            m.update(owners)
        m.save(os.path.join(tmp_folder, f'{tick:04}.png'))

    # Make a video
    logging.info('Rendering video')
    images = glob.glob(os.path.join(tmp_folder, '*.png'))
    images.sort()
    video = mpy.ImageSequenceClip(images, fps=24)
    video.write_videofile(os.path.join(tmp_folder, 'vid.mp4'))
    shutil.move(os.path.join(tmp_folder, 'vid.mp4'), tl_path)
    
    # Cleanup the tmp_folder
    logging.info('Cleanup')
    for image in images:
        os.remove(image)
    os.rmdir(tmp_folder)
    logging.info('Generation successfull')

    return
