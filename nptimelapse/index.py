from flask import Blueprint
from sqlalchemy.sql import func

from nptimelapse.db import db
from nptimelapse.model import Game, Owner


bp = Blueprint('index', __name__, url_prefix='')


@bp.route('/')
def browse_games():
    # Query games
    games = db.session.query(func.min(Owner.tick), func.max(Owner.tick), Game) \
        .join(Game.owners)
    return str(games)
