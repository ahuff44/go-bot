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

    @classmethod
    def stub(klass, api_endpoint):
        return "https://online-go.com/api/v1" + api_endpoint

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

    def get(self, url, params={}, headers={}):
        # 1) Prepare parameters
        if params:
            url = "{}?{}".format(url, urlencode(params))
        headers = utils.dict_merge(
            {"Authorization": "Bearer " + self.access_token},
            headers,
        )

        # 2) Send request
        response = requests.get(url, headers=headers)

        # 3) Read response
        # TODO: error handling
        if not response.ok:
            return response
            raise Exception, "Request failed"
        return response.json()

    def post(self, url, body, params={}, headers={}):
        # 1) Prepare parameters
        if params:
            url = "{}?{}".format(url, urlencode(params))
        headers = utils.dict_merge(
            {"Authorization": "Bearer " + self.access_token},
            headers,
        )

        # 2) Send request
        response = requests.post(url, data=body, headers=headers)

        # 3) Read response
        # TODO: error handling
        if not response.ok:
            raise Exception, "Request failed"
        return response.json()

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

MINUTES = 60
HOURS = 60*MINUTES
DAYS = 24*HOURS
YEARS = 365*DAYS

LIVE_CUTOFF = 1*HOURS # Any game with less than an hour per move on average is considered "live"
BLITZ_CUTOFF = 20 # Any game with less than a 20 seconds per move on average is considered "blitz"

sort_fields = (
    "time_per_move",
    "started",
    "white_player_rank",
    "black_player_rank",
    "id",
)

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
pprint(agent.sort_by(games, sort_fields))
