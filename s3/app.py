"""
SFU CMPT 756
Sample application---playlist service.
"""

# Standard library modules
import logging
import sys
import time

# Installed packages
from flask import Blueprint
from flask import Flask
from flask import request
from flask import Response

import jwt

from prometheus_flask_exporter import PrometheusMetrics

import requests

import simplejson as json

# The application

app = Flask(__name__)

metrics = PrometheusMetrics(app)
metrics.info('app_info', 'Playlist process')

bp = Blueprint('app', __name__)

db = {
    "name": "http://cmpt756db:30002/api/v1/datastore",
    "endpoint": [
        "read",
        "write",
        "delete",
        "update",
        "read_all"
    ]
}

NOT_AUTHENTICATED = Response(
    json.dumps({"error": "missing auth"}),
    status=401,
    mimetype='application/json'
)


@bp.route('/', methods=['GET'])
@metrics.do_not_track()
def hello_world():
    return ("If you are reading this in a browser, your service is "
            "operational. Switch to curl/Postman/etc to interact using the "
            "other HTTP verbs.")


@bp.route('/health')
@metrics.do_not_track()
def health():
    return Response("", status=200, mimetype="application/json")


@bp.route('/readiness')
@metrics.do_not_track()
def readiness():
    return Response("", status=200, mimetype="application/json")


def get_user_from_auth(headers):
    return None


def get_playlist_from_id(id, headers):
    user_id = get_user_from_auth(headers)
    if not user_id:
        return NOT_AUTHENTICATED
    payload = {"objtype": "playlist", "objkey": id, "uid": user_id}
    url = db['name'] + '/' + db['endpoint'][0]
    response = requests.get(url, params=payload)
    if len(response.json()) == 0:
        return Response("Playlist not found for this user", status=404, mimetype="application/json")
    playlist_data = response.json()
    music_list = playlist_data['music_list'][:] # make a new copy.
    payload = {"objtype": "music"}
    url = db['name'] + '/' + db['endpoint'][4]
    response = requests.get(url, params=payload)
    playlist_data['music_list'] = list()
    for song in response.json():
        if song['objkey'] in music_list:
            playlist_data['music_list'].append(song)
    return (playlist_data)


@bp.route('/all', methods=['GET'])
def list_playlists():
    user_id = get_user_from_auth(request.headers)
    if not user_id:
        return NOT_AUTHENTICATED
    payload = {"objtype": "playlist", "uid": user_id}
    url = db['name'] + '/' + db['endpoint'][0]
    response = requests.get(url, params=payload)
    return (response.json())


@bp.route('/<playlist_id>', methods=['GET'])
def get_playlist(playlist_id):
    return get_playlist_from_id(playlist_id, request.headers)


@bp.route('/', methods=['POST'])
def create_playlist():
    """
    Create a playlist.
    """
    user_id = get_user_from_auth(request.headers)
    if not user_id:
        return NOT_AUTHENTICATED
    try:
        content = request.get_json()
        playlist_name = content['playlist_name']
        music_list = content['music_list']
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][1]
    response = requests.post(
        url,
        json={"objtype": "playlist",
              "playlist_name": playlist_name,
              "music_list": music_list,
              "uid": user_id})
    return (response.json())


@bp.route('/add_song', methods=['POST'])
def add_songs_to_playlist():
    """
    Add songs to a playlist.
    """
    try:
        content = request.get_json()
        playlist_id = content['playlist_id']
        music_list = content['music_list']
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    
    playlist_data = get_playlist_from_id(playlist_id, request.headers)
    if playlist_data == NOT_AUTHENTICATED: return playlist_data
    # we have playlist data. now update the music list
    user_id = get_user_from_auth(request.headers)

    updated_music_list = list(set(music_list.append(playlist_data['music_list'])))
    
    url = db['name'] + '/' + db['endpoint'][1]
    response = requests.put(
        url,
        json={"objtype": "playlist",
              "objkey": playlist_id,
              "music_list": updated_music_list,
              "uid": user_id})
    return (response.json())

'''
@bp.route('/<playlist_id>', methods=['PUT'])
def update_user(playlist_id):
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}), status=401,
                        mimetype='application/json')
    try:
        content = request.get_json()
        email = content['email']
        fname = content['fname']
        lname = content['lname']
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][3]
    response = requests.put(
        url,
        params={"objtype": "user", "objkey": user_id},
        json={"email": email, "fname": fname, "lname": lname})
    return (response.json())


@bp.route('/', methods=['POST'])
def create_user():
    """
    Create a user.
    If a record already exists with the same fname, lname, and email,
    the old UUID is replaced with a new one.
    """
    try:
        content = request.get_json()
        lname = content['lname']
        email = content['email']
        fname = content['fname']
    except Exception:
        return json.dumps({"message": "error reading arguments"})
    url = db['name'] + '/' + db['endpoint'][1]
    response = requests.post(
        url,
        json={"objtype": "user",
              "lname": lname,
              "email": email,
              "fname": fname})
    return (response.json())


@bp.route('/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    headers = request.headers
    # check header here
    if 'Authorization' not in headers:
        return Response(json.dumps({"error": "missing auth"}),
                        status=401,
                        mimetype='application/json')
    url = db['name'] + '/' + db['endpoint'][2]

    response = requests.delete(url,
                               params={"objtype": "user", "objkey": user_id})
    return (response.json())
'''

# All database calls will have this prefix.  Prometheus metric
# calls will not---they will have route '/metrics'.  This is
# the conventional organization.
app.register_blueprint(bp, url_prefix='/api/v1/playlist/')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        logging.error("Usage: app.py <service-port>")
        sys.exit(-1)

    p = int(sys.argv[1])
    # Do not set debug=True---that will disable the Prometheus metrics
    app.run(host='0.0.0.0', port=p, threaded=True)
