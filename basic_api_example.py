import requests
from urllib import urlencode

def file_to_string(filename):
    with open(filename, "r") as file_:
        return '\n'.join(file_.readlines())

# 1) Prepare parameters
oauth_url = "https://online-go.com/oauth2/access_token"

# Important: the files we read here should NOT be checked into source-control (e.g. git).
# You'll have to create them yourself and add them to your .gitignore file
# That's why we're reading them from local files, rather than having them be hard-coded strings
oauth_values = urlencode({
    "client_id":     file_to_string("client_id.txt"), # generated on https://online-go.com/developer
    "client_secret": file_to_string("client_secret.txt"), # generated on https://online-go.com/developer
    "grant_type":    "password",
    "username":      file_to_string("username.txt"), # your username
    "password":      file_to_string("app_specific_password.txt"), # generated on your user settings page
})

oauth_headers = {
  'Content-Type': 'application/x-www-form-urlencoded'
}

# 2) Send request
oauth_response = requests.post(oauth_url, data=oauth_values, headers=oauth_headers)

# 3) Read response
# all we want is the access token:
access_token = oauth_response.json()["access_token"]

print "Access token:\n\t", access_token



# 4) Use the access token to interact with the API
# For example: print the url of one of your currently active games:
games_url = "https://online-go.com/api/v1/me/games/?started__isnull=False&ended__isnull=True"
games_headers = {"Authorization": "Bearer " + access_token}
games_response = requests.get(games_url, headers=games_headers)
game_id = games_response.json()["results"][0]["id"] # Yeah, this is confusing, sorry. It's not too hard to figure out when you dig into it
print "One of your active games:\n\thttps://online-go.com/game/%d"%game_id

