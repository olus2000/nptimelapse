from flask import current_app

from nptimelapse.extensions import celery_ext
from nptimelapse.map_maker import Map

import logging
import os
import os.path
import glob
from math import sqrt
import moviepy.editor as mpy


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


@celery_ext.celery.task
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
        raise TimelapseGameNotRegisteredError(game_id)
    start_tick, end_tick, game = game_data
    tl_path = os.path.join(video_cache, f'{game.name.replace(" ", "_")}_{game.id}.mp4')

    # Check for tmp folder to see if the timelapse is not being created by another worker
    tmp_folder = os.path.join(video_cache, f'tmp')
    if os.path.exists(tmp_folder):
        logging.error('tmp folder exists. Abort generation.')
        raise TimelapseTmpFolderExistsError(tmp_folder)
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

    return
