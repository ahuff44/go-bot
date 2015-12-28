#!/usr/bin/env python

from pprint import pprint
import utils
import os
import operator as ops

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
                raise Exception, "You are missing some config files (specifically, %s)"%path

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
    def _generate_access_token(klass):
        print "Generating a new access token..."

        # 1) Prepare parameters
        url = "https://online-go.com/oauth2/access_token"

        # Important: the files we read here should NOT be checked into source-control (e.g. git).
        # You'll have to create them yourself and add them to your .gitignore file
        # That's why we're reading them from local files, rather than having them be hard-coded strings
        values = urlencode({
            "client_id":     utils.file_to_string("client_id.txt"), # generated on https://online-go.com/developer
            "client_secret": utils.file_to_string("client_secret.txt"), # generated on https://online-go.com/developer
            "grant_type":    "password",
            "username":      utils.file_to_string("username.txt"), # contains your username
            "password":      utils.file_to_string("app_specific_password.txt"), # generated on your user settings page
        })

        headers = {
          'Content-Type': 'application/x-www-form-urlencoded'
        }

        # 2) Send request
        response = requests.post(url, data=values, headers=headers)

        # 3) Read response
        # all we want is the access token:
        if not response.ok:
            raise Exception, "Token generation failed"
        return response.json()["access_token"]

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
        # TODO: error handling
        if not response.ok:
            raise Exception, "Request failed"
        return response.json()

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
        # TODO: error handling
        if not response.ok:
            raise Exception, "Request failed"
        return response.json()

    # Convinience / testing functions
    def sget(self, url_stub, all=False, *args, **kwargs):
        proc = self.get_all if all else self.get
        return proc(self.stub(url_stub), *args, **kwargs)

    def spost(self, url_stub, *args, **kwargs):
        return self.post(self.stub(url_stub), *args, **kwargs)

    @utils.pipeto(list)
    @utils.pipeto(utils.flatten)
    def get_all(self, url, params={}, headers={}):
        # TODO: clean
        data = self.get(url, params=params, headers=headers)
        if data["count"] > 1000:
            raise Exception, "I won't get that many records; it's just too many"
        else:
            yield data["results"]
            while data["next"]:
                next_url = data["next"]
                print "Fetching next page:", next_url
                data = self.get(next_url, headers=headers) # TODO: include headers here?
                yield data["results"]

    @classmethod
    def sort_by(klass, game_list, fields):
        key_func = lambda game: map(lambda field: ops.itemgetter(field)(game), fields)
        return sorted(map(key_func, game_list))

    def get_game(self, game_id):
        return self.sget("games/%d"%game_id)

class Coord(object):
    # TODO: extend beyond 9x9

    def __init__(self, x, y):
        self.x = x
        self.y = y

    @classmethod
    def from_api(klass, coord):
        if len(coord) != 2:
            raise Exception, "Bad length coord"
        cx, cy = coord
        return klass("abcdefghi".index(cx), "abcdefghi".index(cy))

    @classmethod
    def from_visual(klass, coord):
        if len(coord) != 2:
            raise Exception, "Bad length coord"
        cx, cy = coord
        return klass("ABCDEFGHJ".index(cx.upper()), "987654321".index(cy))

    @classmethod
    def from_numeric(klass, coord):
        if len(coord) != 2:
            raise Exception, "Bad length coord"
        cx, cy = coord
        return klass(cx, cy)

    def api_repr(self):
        return "abcdefghi"[self.x] + "abcdefghi"[self.y]

    def visual_repr(self):
        return "ABCDEFGHJ"[self.x] + "987654321"[self.y]

    def numeric_repr(self):
        return self.x, self.y

class OGS_Game_Agent(OGS_API_Agent):
    def __init__(self, game_id):
        super(self.__class__, self).__init__()
        self.game_id = game_id
        game = self.get_game(game_id)
        self.size = game["width"]
        assert self.size == game["height"]
        assert self.size in [9, 13, 19]
        self.board = Board.from_moves(self.size, game["gamedata"]["moves"])

    def play(self, coord):
        self.spost("games/%d/move"%self.game_id,
            data='{"move": "%s"}'%coord.api_repr(),
            headers={"Content-Type": "application/json"}
        ) # TODO: this could raise an exception
        self.board.play(coord)

    # Convinience method:
    def vplay(self, coord_str):
        self.play(Coord.from_visual(coord_str))

    def pass_(self):
        self.spost("games/%d/pass"%self.game_id,
            data="",
            headers={"Content-Type": "application/json"}
        ) # TODO: this could raise an exception
        self.board.toggle_player()

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
    def from_moves(klass, size, dirty_moves):
        # dirty_moves is directly from the API, unsanitized.
        # it will be 0-based elements of the form [x, y, time] TODO: is this time? I assume it is
        board = klass.empty_board(size)
        for x, y, time in dirty_moves:
            board.play(Coord(x, y))
        return board

    def __init__(self, rows):
        self.rows = rows
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

    def set(self, (x, y), value):
        self.rows[y][x] = value

    def get(self, x, y):
        return self.rows[y][x]
    @utils.pipeto("\n".join)
    def __str__(self):
        symbols = {self.BLACK: "B", self.WHITE: "W", self.NONE: "+"}
        for row in self.rows:
            yield "".join(map(lambda entry: symbols[entry], row))

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

gid = 3578876 # TODO: remove
ag = OGS_API_Agent()
p = OGS_Game_Agent(gid)
