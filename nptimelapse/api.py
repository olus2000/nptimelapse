from flask import Blueprint, abort
from flask.json import jsonify

from nptimelapse.model import Game, Star, Owner


bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/game/<int:game_id>')
def game_info(game_id):
    # Query Game
    game = Game.query.filter(Game.id == game_id).one_or_none()
    if game is None:
        abort(404)

    # Prepare game data
    game = {'id': game.id, 'name': game.name, 'close_date': game.close_date, 'stars': {}}

    # Construct the JSON
    stars = Star.query.filter(Star.game_id == game_id).all()
    for star in stars:
        game['stars'][star.id] = {'x': star.x, 'y': star.y, 'owners': {}}
        owners = Owner.query.filter(Owner.game_id == game_id) \
            .filter(Owner.star_id == star.id).all()
        game['stars'][star.id]['owners'] = {owner.tick: owner.player for owner in owners}

    return jsonify(game)
