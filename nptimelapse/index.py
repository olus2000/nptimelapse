from flask import Blueprint, render_template
from sqlalchemy.sql import func

from nptimelapse.db import db
from nptimelapse.model import Game, Owner


bp = Blueprint('index', __name__, url_prefix='')


@bp.route('/')
def browse_games():
    # Query games
    games = db.session.query(func.min(Owner.tick), func.max(Owner.tick), Game) \
        .join(Game.owners).group_by(Game.id).order_by(Game.id.desc()).all()

    games = [{'start_tick': g[0],
                'end_tick': g[1],
                  'number': g[2],
                    'name': g[4],
              'close_date': g[5]}
             for g in games]
    return render_template('browse_games.html', games=games)
