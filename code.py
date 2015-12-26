#!/usr/bin/env python

from pprint import pprint
import utils

import requests
from urllib import urlencode

class OGS_API_Agent(object):
    base_url = "https://online-go.com/api/v1"

    def __init__(self):
        self.access_token = self.create_access_token()

    @staticmethod
    def create_access_token():
        # 1) Prepare parameters
        url = "https://online-go.com/oauth2/access_token"

        # Important: the files we read here should NOT be checked into source-control (e.g. git).
        # You'll have to create them yourself and add them to your .gitignore file
        # That's why we're reading them from local files, rather than having them be hard-coded strings
        values = urlencode({
            "client_id":     utils.file_to_string("client_id.txt"), # generated on https://online-go.com/developer
            "client_secret": utils.file_to_string("client_secret.txt"), # generated on https://online-go.com/developer
            "grant_type":    "password",
            "username":      utils.file_to_string("username.txt"), # your username
            "password":      utils.file_to_string("app_specific_password.txt"), # generated on your user settings page
        })

        headers = {
          'Content-Type': 'application/x-www-form-urlencoded'
        }

        # 2) Send request
        response = requests.post(url, data=values, headers=headers)

        # 3) Read response
        # all we want is the access token:
        return response.json()["access_token"]

    def get(self, url_stub, params={}, headers={}):
        # 1) Prepare parameters
        url = "{}{}?{}".format(self.base_url, url_stub, urlencode(params))
        headers = utils.dict_merge(
            {"Authorization": "Bearer " + self.access_token},
            headers,
        )

        # 2) Send request
        response = requests.get(url, headers=headers)

        # 3) Read response
        # TODO: error handling
        return response.json()

    def post(self, url_stub, body, params={}, headers={}):
        # 1) Prepare parameters
        url = "{}{}?{}".format(self.base_url, url_stub, urlencode(params))
        headers = utils.dict_merge(
            {"Authorization": "Bearer " + self.access_token},
            headers,
        )

        # 2) Send request
        response = requests.post(url, data=body, headers=headers)

        # 3) Read response
        # TODO: error handling
        return response.json()

agent = OGS_API_Agent()
current_games = agent.get(
    "/games/",
    params={
        "started__isnull": False,
        "ended__isnull": True,
    } ,
)
first_page = current_games["results"]
pprint(map(lambda game: game["id"], first_page))
