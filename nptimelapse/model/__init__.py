from nptimelapse.py import db


class Game(db.Model):
    __tablename__ = 'game'
    id = db.Column('id', db.BigInteger(), primary_key=True)
    api_key = db.Column('apikey', db.String(6), nullable=False)
    name = db.Column('name', db.String(40), nullable=False)
    close_date = db.Column('closedate', db.DateTime())
    stars = db.relationship('Star')


class Star(db.Model):
    __tablename__ = 'star'
    id = db.Column('id', db.Integer(), primary_key=True)
    game_id = db.Column('gameid', db.BigInteger(), db.ForeignKey('game.id'),
                        primary_key=True)
    x = db.Column('x', db.Float(), nullable=False)
    y = db.Column('y', db.Float(), nullable=False)
    owners = db.relationship('Owner')


class Owner(db.Model):
    __tablename__ = 'owner'
    tick = db.Column('tick', db.Integer(), primary_key=True)
    star_id = db.Column('starid', db.Integer(), primary_key=True)
    game_id = db.Column('gameid', db.BigInteger(), db.ForeignKey('game.id'),
                        primary_key = True)
    player = db.Column('player', db.SmallInteger(), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ['star_id', 'game_id'],
            ['star.id', 'star.game_id'],
        ),
    )
