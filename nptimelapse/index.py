from flask import Blueprint, render_template, url_for, flash, request, send_file, \
                  current_app, abort
from werkzeug.utils import redirect
from sqlalchemy.sql import func
from celery.exceptions import TimeoutError

from nptimelapse.extensions import db
from nptimelapse.model import Game, Star, Owner
from nptimelapse.tasks import make_timelapse, TimelapseTmpFolderExistsError
from nptimelapse.map_maker import COLS

import requests
import glob
import os
import os.path


bp = Blueprint('index', __name__, url_prefix='')


@bp.route('/', methods=('GET', 'POST'))
def browse_games():
    # A new game request
    if request.method == 'POST':
        game_id = request.form['game_id']
        api_key = request.form['api_key']

        # Check if game already exists
        exists = Game.query.filter(Game.id == game_id).one_or_none()
        if exists:
            return redirect(url_for('index.game_info', game_id=game_id))

        # Fetch game data from ironhelmet API
        params = {'game_number': game_id,
                         'code': api_key,
                  'api_version': '0.1'}
        payload = requests.post('https://np.ironhelmet.com/api', params).json()

        # Handle API errors
        if 'error' in payload:
            error = payload['error']
            if error == 'code not found in game':
                flash('Incorrect API key')
            elif error == 'api_version not supported':
                flash('API error. Contact the administartor')
            else:
                flash('Incorrect game number')
        # Handle invalid games
        elif payload['scanning_data']['game_over']:
            flash('Game has already finished')
        elif payload['scanning_data']['total_stars'] > len(payload['scanning_data']['stars']):
            flash('Dark games are not yet supported')
        else:
            # Register the new game in DB
            data = payload['scanning_data']
            db.session.add(Game(id=game_id, api_key=api_key, name=data['name']))
            new_stars = [Star(id=int(star_id),
                              game_id=game_id,
                              x=float(star['x']),
                              y=float(star['y']))
                         for star_id, star in data['stars'].items()]
            db.session.add_all(new_stars)
            new_owners = [Owner(tick=data['tick'],
                                star_id=int(star_id),
                                game_id=game_id,
                                player=star['puid'])
                          for star_id, star in data['stars'].items() if star['puid'] >= 0]
            db.session.add_all(new_owners)
            db.session.commit()
            return redirect(url_for('index.game_info', game_id=game_id))

        # If an error happened the normal page is displayed

    # Query games
    games = db.session.query(func.min(Owner.tick), func.max(Owner.tick), Game) \
        .join(Game.owners).group_by(Game.id) \
        .order_by(Game.close_date, Game.name, Game.id).all()

    games = [{'start_tick': g[0],
                'end_tick': g[1],
                  'number': g[2].id,
                    'name': g[2].name,
              'close_date': g[2].close_date}
             for g in games]
    return render_template('browse_games.html', games=games)


@bp.route('/game/<int:game_id>')
def game_info(game_id):
    # Query games
    game_data = db.session.query(func.min(Owner.tick), func.max(Owner.tick), Game) \
        .filter(Game.id == game_id).join(Game.owners).group_by(Game.id).one_or_none()
    if game_data is None:
        flash(f'Game {game_id} is not registered')
        return redirect(url_for('index.browse_games'))
    start_tick, end_tick, game = game_data

    return render_template('game_info.html',
                           game=game,
                           game_length=end_tick - start_tick + 1)


@bp.route('/game/<int:game_id>/timelapse_request')
def timelapse_request(game_id):
    # Query game
    game_data = db.session.query(func.min(Owner.tick), func.max(Owner.tick), Game) \
        .filter(Game.id == game_id).join(Game.owners).group_by(Game.id).one_or_none()
    if game_data is None:
        flash(f'Game {game_id} is not registered!')
        return redirect(url_for('index.browse_games'))
    start_tick, end_tick, game = game_data

    # Get request arguments
    if 'star' in request.args:
        star = request.args['star']
    else:
        star = 'none'
    if 'border' in request.args:
        border = request.args['border']
    else:
        border = 'none'
    if 'rescale' in request.args:
        smoothness = int(request.args['rescale']) + 1
        rescale = 7 - smoothness
        if rescale > 6:
            rescale = 10
    else:
        smoothness = 1
        rescale = 6

    # Timelapse status
    video_cache = os.path.join(current_app.instance_path, 'video_cache')
    tl_name = f'{game.name.replace(" ", "_")}_{game.id}_{star}_{border}_{rescale}.mp4'
    tl_path = os.path.join(video_cache, tl_name)
    tmp_folder = os.path.join(video_cache, 'tmp')
    game_length = end_tick - start_tick + 1
    if os.path.exists(tl_path):
        tl_status = 'READY'
        progress = game_length
    elif os.path.exists(tmp_folder):
        tl_status = 'IN_PROGRESS'
        # An integer from the highest image name
        files = glob.glob(os.path.join(tmp_folder, '*.png'))
        if files:
            progress = int(max(files)[-8:-4]) - start_tick
        else:
            progress = 0
    else:
        tl_status = 'NOT_READY'
        progress = 0

    if tl_status == 'NOT_READY':
        # Prepare map parameters
        draw_params = {'rescale': rescale, 'pix_per_cell': 60 // rescale}
        if star != 'none' :
            if star == 'white':
                draw_params['star_cols'] = tuple((255, 255, 255) for i in range(64))
            elif star == 'black':
                draw_params['star_cols'] = tuple((0, 0, 0) for i in range(64))
            elif star == 'contrast':
                draw_params['star_cols'] = tuple(
                    (0, 0, 0) if c[0]*.299 + c[1]*.587 + c[2]*.114 > 128
                    else (255, 255, 255) for c in COLS
                )
        if border != 'none':
            draw_params['border'] = rescale / 100

        # Make the timelapse
        make_timelapse.delay(game_id, tl_name, draw_params)
        tl_status = 'IN_PROGRESS'

    return render_template('timelapse_request.html',
                           star=star, border=border,
                           smoothness=smoothness,
                           tl_name=tl_name,
                           tl_status=tl_status,
                           progress=progress,
                           game_length=game_length,
                           game=game)


@bp.route('/game/<int:game_id>/timelapse/<string:tl_name>')
def timelapse(game_id, tl_name):
    game = Game.query.filter(Game.id == game_id).one_or_none()
    if game is None:
        abort(404)
    tl_path = os.path.join(current_app.instance_path, f'video_cache/{tl_name}')
    if not os.path.exists(tl_path):
        abort(404)
    return send_file(tl_path, as_attachment=True)


@bp.route('/help')
def site_help():
    return render_template('help.html')
