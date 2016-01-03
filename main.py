#!/usr/bin/env python

from pprint import pprint
import utils
import os
from time import sleep
import operator as ops
import copy
import random

import requests
from urllib import urlencode

class OGS_API_Agent(object):
    def __init__(self):
        self.access_token = self.load_access_token()
        self.ensure_config_files_exist()

    @classmethod
    def ensure_config_files_exist(klass):
        for path in [
                "client_id.txt",
                "client_secret.txt",
                "username.txt",
                "app_specific_password.txt",
            ]:
            if not os.path.exists(path):
                raise Exception, "You are missing some config files (specifically, ./%s)"%path

    @classmethod
    def stub(klass, api_endpoint):
        return "https://online-go.com/api/v1/%s/"%api_endpoint.strip("/")

    @classmethod
    def load_access_token(klass):
        if os.path.exists("access_token.txt"):
            return utils.file_to_string("access_token.txt")
        else:
            # Generate and cache the token
            # TODO: the token expires after a year
            token = klass._generate_access_token()
            with open("access_token.txt", "w") as file_:
                file_.write(token)
            return token

    @classmethod
    def _generate_access_token(klass, user_file="gobot_user.cfg"):
        print "Generating a new access token..."

        # 1) Prepare parameters
        url = "https://online-go.com/oauth2/access_token"

        # Important: the files we read here should NOT be checked into source-control (e.g. git).
        # You'll have to create them yourself and add them to your .gitignore file
        # That's why we're reading them from local files, rather than having them be hard-coded strings
        client_config = utils.config_as_dict("client.cfg")["client"]
        user_config = utils.config_as_dict(user_file)["user"]
        values = urlencode({
            "client_id":     client_config["id"], # generated on https://online-go.com/developer
            "client_secret": client_config["secret"], # generated on https://online-go.com/developer
            "grant_type":    "password",
            "username":      user_config["username"], # contains your username
            "password":      user_config["app_specific_password"], # generated on your user settings page
        })

        headers = {
          'Content-Type': 'application/x-www-form-urlencoded'
        }

        # 2) Send request
        response = requests.post(url, data=values, headers=headers)

        # 3) Read response
        return utils.Either.from_response(response).fmap_right(
            (lambda value: value["access_token"])
        )

    def log(self, msg):
        print msg

    def basic_headers(self):
        return {
            "Authorization": "Bearer %s"%self.access_token,
        }

    def get(self, url, params={}, headers={}):
        # 1) Prepare parameters
        if params:
            url = "{}?{}".format(url, urlencode(params))
        headers = utils.dict_merge(
            self.basic_headers(),
            headers,
        )

        self.log("GET:\n\turl={}\n\theaders={}".format(repr(url), repr(headers)))

        # 2) Send request
        response = requests.get(url, headers=headers)

        # 3) Read response
        return utils.Either.from_response(response)

    def post(self, url, data, params={}, headers={}):
        # 1) Prepare parameters
        if params:
            url = "{}?{}".format(url, urlencode(params))
        headers = utils.dict_merge(
            self.basic_headers(),
            headers,
        )

        self.log("POST:\n\turl={}\n\tdata={}\n\theaders={}".format(repr(url), repr(data), repr(headers)))

        # 2) Send request
        response = requests.post(url, data=data, headers=headers)

        # 3) Read response
        return utils.Either.from_response(response)

    # Convinience / testing functions
    def sget(self, url_stub, all=False, *args, **kwargs):
        proc = self.get_all if all else self.get
        return proc(self.stub(url_stub), *args, **kwargs).fmap_left(
            (lambda resp: "Request failed: %s"%resp.text)
        ).contents()

    def spost(self, url_stub, *args, **kwargs):
        return self.post(self.stub(url_stub), *args, **kwargs).fmap_left(
            (lambda resp: "Request failed: %s"%resp.text)
        ).contents()

    def get_all(self, url, params={}, headers={}, LIMIT=1000):
        data = self.get(url, params=params, headers=headers)
        if data["count"] > LIMIT:
            return utils.Either(False, "You are not allowed to retrieve more than %d records at once"%LIMIT)
        else:
            aggregate = copy.copy(data["results"])
            while data["next"]:
                next_url = data["next"]
                data = self.get(next_url, headers=headers) # TODO: include headers here?
                aggregate.extend(data["results"])
            return utils.Either(True, aggregate)

    @classmethod
    def sort_key(klass, fields):
        return lambda game: map(lambda field: ops.itemgetter(field)(game), fields)

    @classmethod
    def sort_map(klass, game_list, fields):
        key = klass.sort_key(fields)
        return map(key, sorted(games, key=key))

    def get_game(self, game_id):
        return self.sget("games/%d"%game_id)

# TODO: add a Move = Coord | Pass datatype?
class Coord(object):
    API_STRINGS = {
        9: ("abcdefghi", "abcdefghi"),
        13: ("abcdefghijklm", "abcdefghijklm"),
        19: ("abcdefghijklmnopqrs", "abcdefghijklmnopqrs"),
    }
    VISUAL_STRINGS = {
        9: ("ABCDEFGHJ", map(str, range(9, 0, -1))),
        13: ("ABCDEFGHJKLMN", map(str, range(13, 0, -1))),
        19: ("ABCDEFGHJKLMNOPQRST", map(str, range(19, 0, -1))),
    }

    @classmethod
    def from_api(klass, size, (cx, cy)):
        return klass(size,
            klass.API_STRINGS[size][0].index(cx),
            klass.API_STRINGS[size][1].index(cy)
        )

    @classmethod
    def from_visual(klass, size, coord_str):
        if len(coord_str) not in [2, 3]:
            raise Exception, "Bad length coord_str"
        cx, cy = coord_str[0], coord_str[1:]
        return klass(size,
            klass.VISUAL_STRINGS[size][0].index(cx.upper()),
            klass.VISUAL_STRINGS[size][1].index(cy)
        )

    @classmethod
    def from_numeric(klass, size, (cx, cy)):
        return klass(size, cx, cy)

    def __init__(self, size, x, y):
        self.size = size
        self.x = x
        self.y = y

    def api_repr(self):
        return "%s%s"%(
            self.API_STRINGS[self.size][0][self.x],
            self.API_STRINGS[self.size][1][self.y],
        )

    def visual_repr(self):
        return "%s%s"%(
            self.VISUAL_STRINGS[self.size][0][self.x],
            self.VISUAL_STRINGS[self.size][1][self.y],
        )

    def numeric_repr(self):
        return self.x, self.y

    def __eq__(self, other):
        return self.size == other.size and self.numeric_repr() == other.numeric_repr()

    def __ne__(self, other):
        return not (self == other)

    __str__ = visual_repr

class Board(object):
    NONE = 0
    BLACK = 1
    WHITE = 2

    @classmethod
    def empty_board(klass, size):
        rows = []
        for i in xrange(size):
            rows.append([klass.NONE]*size)
        return klass(rows)

    @classmethod
    def from_game_api(klass, game):
        # dirty_moves is directly from the API, unsanitized.
        # it will be 0-based elements of the form [x, y, time] TODO: is this time? I assume it is
        board = klass.empty_board(game["width"])
        for x, y, time in game["gamedata"]["moves"]:
            board.play(Coord.from_numeric(board.size, (x, y)))
        return board

    def __init__(self, rows):
        self.rows = rows
        self.size = len(rows)
        assert all(self.size == len(r) for r in rows) # TODO: not an assert?
        self.player = self.BLACK

    def toggle_player(self):
        if self.player == self.WHITE:
            self.player = self.BLACK
        elif self.player == self.BLACK:
            self.player = self.WHITE
        else:
            assert False, "Internal"

    def play(self, coord):
        # Plays the given move and toggles the current player (white <-> black)
        self.set(coord.numeric_repr(), self.player)
        self.toggle_player()
        return coord

    def set(self, (x, y), value):
        self.rows[y][x] = value

    def get(self, (x, y)):
        return self.rows[y][x]

    def legal_coords(self):
        return filter(self.is_legal, self._all_coords())

    def is_legal(self, coord):
        # TODO: implement properly
        return self.get(coord.numeric_repr()) == self.NONE

    def _all_coords(self):
        for rr, row in enumerate(self.rows):
            for cc, entry in enumerate(row):
                yield Coord.from_numeric(self.size, (rr, cc))

    @utils.pipeto("\n".join)
    def __str__(self):
        size = len(self.rows)
        symbols = {self.BLACK: "B", self.WHITE: "W", self.NONE: "+"}
        yield "  ABCDEFGHJKLMNOPQRST"[:size+2]
        for i, row in enumerate(self.rows):
            yield "%2d"%(size-i) + "".join(map(lambda entry: symbols[entry], row))
        yield "--------------"
        yield "current player: %s"%symbols[self.player]
        yield "--------------"

class Go_Strategy(object):
    # TODO: look into making this an ABC maybe: https://docs.python.org/2/library/abc.html
    def play(self, board):
        # Board -> Either(Move)
        raise NotImplementedError( "Should have implemented this" )

class Always_Pass(Go_Strategy):
    def play(self, board):
        # TODO: s/Coord(...)/Pass()
        return utils.Either(True, Coord.from_numeric(board.size, (-1, -1)))

class OGS_Reciever_Strategy(Go_Strategy):
    def __init__(self, game_id):
        super(self.__class__, self).__init__()
        self.game_id = game_id
        self.api = OGS_API_Agent()

    def play(self, board, last_move):
        POLL_PERIOD = 5
        MAX_POLL_ATTEMPTS = 10
        for attempt_num in xrange(MAX_POLL_ATTEMPTS):
            api.log("Poll attempt #%d..."%attempt_num)
            game = self.api.get_game(self.game_id)

            x, y, time = game["gamedata"]["moves"][-1]
            coord = Coord.from_numeric(board.size, (x, y))

            if last_move != coord:
                print "Recieved opponent's move:", coord
                return utils.Either(True, coord)
            sleep(POLL_PERIOD)
        return utils.Either(False, "Gave up polling for opponent response")

class OGS_Sender_Strategy(Go_Strategy):
    def __init__(self, game_id):
        self.game_id = game_id
        self.api = OGS_API_Agent()

    def send_move(self, coord):
        self.api.spost("games/%d/move"%self.game_id,
            data='{"move": "%s"}'%coord.api_repr(),
            headers={"Content-Type": "application/json"}
        )

    def send_pass(self):
        self.api.spost("games/%d/pass"%self.game_id,
            data="",
            headers={"Content-Type": "application/json"}
        )

class User_Input_Strategy(OGS_Sender_Strategy):
    def __init__(self, game_id):
        super(self.__class__, self).__init__(game_id)

    def play(self, board, last_move):
        print board
        inp = raw_input("> ")
        if inp in ["p", "pass"]:
            self.send_pass()
            # TODO: return Pass()
            return utils.Either(True, Coord.from_numeric(board.size, (-1, 1)))
        else:
            coord = Coord.from_visual(board.size, inp)
            self.send_move(coord)
            return utils.Either(True, coord)

class Random_Strategy(OGS_Sender_Strategy):
    def __init__(self, game_id):
        super(self.__class__, self).__init__(game_id)

    def play(self, board, last_move):
        legal = board.legal_coords()
        print "legal moves: {}".format(map(str, legal))
        if legal:
            coord = random.choice(list(legal))
            print "randomly chose {}".format(coord)
            self.send_move(coord)
            return utils.Either(True, coord)
        else:
            # TODO: return Pass()
            self.send_pass()
            return utils.Either(True, Coord.from_numeric(board.size, (-1, 1)))



MINUTES = 60
HOURS = 60*MINUTES
DAYS = 24*HOURS
YEARS = 365*DAYS

LIVE_CUTOFF = 1*HOURS # Any game with less than an hour per move on average is considered "live"
BLITZ_CUTOFF = 20 # Any game with less than a 20 seconds per move on average is considered "blitz"

def print_current_interesting_games():
    agent = OGS_API_Agent()
    games = agent.get_all(
        agent.stub("/games/"),
        params={
            "started__isnull": False,
            "ended__isnull": True,
            "width": 19,
            "height": 19,
            # "time_per_move__lt": 10*MINUTES,
            "time_per_move__gt": 0,
            "ranked": True,
            "white_player_rank__gt": 0,
            "black_player_rank__gt": 0,
        },
    )
    sort_fields = (
        "time_per_move",
        "started",
        "white_player_rank",
        "black_player_rank",
        "id",
    )
    pprint(agent.sort_by(games, sort_fields))

def tapprint(msg, continuation):
    def res(*args, **kwargs):
        print msg
        return continuation(*args, **kwargs)
    return res

def play_game(p1, p2, fetch_board):
    # assumes p1 will go first
    board = fetch_board()
    e_p2_move = utils.Either(True, None)
    while True:
        e_p1_move = p1.play(board, e_p2_move.contents())
        if type(e_p1_move) != type(utils.Either(True, 0)):
            raise Exception, "Bad return type from Go_Strategy interface; must return an Either"
        # TODO: also enforce that board has one new move... another reason to make a Game() object
        print "Got p1's move: {}".format(e_p1_move.contents())

        # TODO: replace with if board != fetch_board(): raise Error
        board = fetch_board()

        e_p2_move = p2.play(board, e_p1_move.contents())
        if type(e_p1_move) != type(utils.Either(True, 0)): # TODO: this is ugly
            raise Exception, "Bad return type from Go_Strategy interface; must return an Either"
        # TODO: also enforce that board has one new move... another reason to make a Game() object
        print "Got p2's move: {}".format(e_p2_move.contents())

        # TODO: replace with if board != fetch_board(): raise Error
        board = fetch_board()

        # TODO: end if both pass

def play_ogs_game(gid, p1, p2):
    # TODO: decouple api and game
    api = OGS_API_Agent()
    def fetch_board():
        game = api.get_game(gid)
        size = game["width"]
        return Board.from_game_api(game)
    play_game(p1, p2, fetch_board)

api = OGS_API_Agent()
games = api.sget(
    "me/games",
    all=True,
    params={
        "started__isnull": False,
        "ended__isnull": True,
    },
)
gid = sorted(games, key=api.sort_key(("started",)))[0]["id"]
# gid = 3581924
go = lambda: play_ogs_game(gid, Random_Strategy(gid), OGS_Reciever_Strategy(gid))

g = OGS_API_Agent().get_game(gid)
b = Board.from_game_api(g)
