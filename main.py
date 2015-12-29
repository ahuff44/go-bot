#!/usr/bin/env python

from pprint import pprint
import utils
import os
from time import sleep
import operator as ops
import copy

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
        )

    def spost(self, url_stub, *args, **kwargs):
        return self.post(self.stub(url_stub), *args, **kwargs).fmap_left(
            (lambda resp: "Request failed: %s"%resp.text)
        )

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
    def sort_by(klass, game_list, fields):
        key_func = lambda game: map(lambda field: ops.itemgetter(field)(game), fields)
        return sorted(map(key_func, game_list))

    def get_game(self, game_id):
        return self.sget("games/%d"%game_id)

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
    def from_api(klass, size, coord_str):
        if len(coord_str) != 2:
            raise Exception, "Bad length coord"
        cx, cy = coord_str
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
    def from_numeric(klass, size, coord):
        if len(coord) != 2:
            raise Exception, "Bad length coord"
        cx, cy = coord
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
        print "in __eq__"
        print "self.size == other.size", self.size == other.size
        print "self.numeric_repr() == other.numeric_repr()", self.numeric_repr() == other.numeric_repr()
        print "self.size == other.size and self.numeric_repr() == other.numeric_repr()", self.size == other.size and self.numeric_repr() == other.numeric_repr()
        return self.size == other.size and self.numeric_repr() == other.numeric_repr()

    def __ne__(self, other):
        return not (self == other)

    __str__ = visual_repr

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
        return self.spost("games/%d/move"%self.game_id,
            data='{"move": "%s"}'%coord.api_repr(),
            headers={"Content-Type": "application/json"}
        ).fmap(
            (lambda json: self.board.play(coord)),
            (lambda error: "Could not play move: %s"%error),
        ).extract()

    def wait_for_opponent_move(self, last_coord, poll_period=5, max_poll_attempts=10):
        for attempt_num in xrange(max_poll_attempts):
            self.log("Poll attempt #%d..."%attempt_num)
            game = self.get_game(self.game_id)
            x, y, time = game["gamedata"]["moves"][-1]
            # TODO: -1, -1 means pass apparently... hmm this is awkward to implement...
            # TODO: maybe just use requests.request(timeout=60) instead
            # TODO: look into the ggs.ogs real-time api
            coord = Coord.from_numeric(self.size, (x, y))
            if last_coord != coord:
                print "Recieved opponent's move:", coord
                return utils.Either(True, coord)
            sleep(poll_period)
        return utils.Either(False, "Gave up polling for opponent response")

    # Convenience method:
    def vplay(self, coord_str):
        coord = Coord.from_visual(self.size, coord_str)
        # print self.board
        # raw_input("about to play()")
        self.play(coord)
        his_coord = self.wait_for_opponent_move(coord).extract()
        # print self.board
        # print his_coord
        # raw_input("got response; about to play()")
        self.board.play(his_coord)

    def pass_(self):
        return self.spost("games/%d/pass"%self.game_id,
            data="",
            headers={"Content-Type": "application/json"}
        ).fmap(
            (lambda json: self.board.toggle_player()),
            (lambda error: "Could not pass: %s"%error),
        ).extract()

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
            board.play(Coord.from_numeric(size, (x, y)))
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
        return coord

    def set(self, (x, y), value):
        self.rows[y][x] = value

    def get(self, x, y):
        return self.rows[y][x]

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

class Go_Strategy(object):
    def __init__(self, arg):
        self.arg = arg
    # TODO: implement 2 strategies, one for player input, one for waiting for the billy gnu go bot

def manual_game(agent):
    while True:
        print agent.board
        inp = raw_input("> ").strip()
        if inp == "q":
            break
        agent.vplay(inp)

gid = 3581924
p = OGS_Game_Agent(gid)
manual_game(p)
