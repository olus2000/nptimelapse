from flask import Blueprint, render_template, url_for, flash, request, send_file, \
                  current_app
from werkzeug.utils import redirect
from sqlalchemy.sql import func

from nptimelapse.extensions import db
from nptimelapse.model import Game, Star, Owner

import requests
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
        elif payload['scanning_data']['game_over']:
            flash('Game has already ended')
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
        .join(Game.owners).group_by(Game.id).order_by(Game.id.desc()).all()

    games = [{'start_tick': g[0],
                'end_tick': g[1],
                  'number': g[2].id,
                    'name': g[2].name,
              'close_date': g[2].close_date}
             for g in games]
    return render_template('browse_games.html', games=games)


@bp.route('/game/<int:game_id>', methods=('GET', 'POST')
def game_info(game_id):
    # Query games
    game = db.session.query(func.min(Owner.tick), func.max(Owner.tick), Game) \
        .filter(Game.id == game_id).join(Game.owners).group_by(Game.id).one_or_none()
    if game is None:
        flash(f'Game {game_id} is not registered')
        return redirect(url_for('index.browse_games'))
    
    # Prepare data for the template
    game = {'start_tick': game[0],
              'end_tick': game[1],
                'number': game[2].id,
                  'name': game[2].name,
            'close_date': game[2].close_date}
    
    # Timelapse status
    video_cache = os.path.join(current_app.instance_path, 'video_cache')
    tl_path = os.path.join(video_cache, f'{game[2].name.replace(" ", "_")}_{game[2].id}.mp4')
    tmp_folder = os.path.join(video_cache, 'tmp')
    if os.path.exists(tl_path):
        tl_status = 'READY'
    elif os.path.exists(tmp_folder):
        tl_status = 'IN_PROGRESS'
    else:
        tl_status = 'NOT_READY'

    if request.method == 'POST':
        if tl_status != 'NOT_READY':
            flash('A timelapse is already being generated.')
        else:
            

    return render_template('game_info.html', game=game, tl_status=tl_status)


'''

        flash(f'Game {game_id} is not registered')
        return redirect(url_for('index.browse_games'))

    
    # Check if the timelapse is cached
    tl_path = os.path.join(video_cache, f'{game.name.replace(" ", "_")}_{game.id}.mp4')
    if os.path.exists(tl_path):
        return send_file(tl_path, as_attachment=True)


        flash('An error occured during timelapse generation. Try again in a few minutes '
            'and contact the administartor if the problem persists.')
        return redirect(url_for('index.game_info', game_id=game_id))

'''
