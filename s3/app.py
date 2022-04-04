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

NOT_AUTHENTICATED = 'Missing Auth'


@bp.route('/health')
@metrics.do_not_track()
def health():
    return Response("", status=200, mimetype="application/json")


def get_user_from_auth(headers):
    if 'Authorization' not in headers:
        raise(Exception(NOT_AUTHENTICATED))
    decoded = jwt.decode(headers['Authorization'],'secret',algorithms=['HS256'])
    return decoded['user_id']


def get_playlist_from_id(id, headers):
    user_id = get_user_from_auth(headers)
    if not user_id:
        raise(Exception(NOT_AUTHENTICATED))
    payload = {"objtype": "playlist", "objkey": id}
    url = db['name'] + '/' + db['endpoint'][0]
    response = requests.get(url, params=payload).json()

    if len(response['Items']) == 0:
        raise(Exception("Playlist not found for this user"))
    playlist_data = response['Items'][0]
    return (playlist_data)


def get_detailed_playlist_from_id(id, headers):
    playlist_data = get_playlist_from_id(id, headers)

    music_list = playlist_data['music_list'][:] # make a new copy.
    payload = {"objtype": "music"}
    url = db['name'] + '/' + db['endpoint'][4]
    songs = requests.get(url, params=payload).json()['Items']

    playlist_data['music_list'] = list(filter(lambda song: (song['music_id'] in music_list), songs))
    return (playlist_data)


@bp.route('/all', methods=['GET'])
def list_playlists():
    try:
        user_id = get_user_from_auth(request.headers)
    except Exception as ex:
        return Response(str(ex), status=400, mimetype="application/json")
    payload = {"objtype": "playlist"}
    url = db['name'] + '/' + db['endpoint'][4]
    response = requests.get(url, params=payload).json()['Items']
    playlists = list(filter(lambda x: (x['uid'] == user_id), response))
    return ({'playlists' : playlists})


@bp.route('/<playlist_id>', methods=['GET'])
def get_playlist(playlist_id):
    try:
        user_id = get_user_from_auth(request.headers)
        playlist = get_detailed_playlist_from_id(playlist_id, request.headers)
    except Exception as ex:
        return Response(str(ex), status=400, mimetype="application/json")
    
    if playlist['uid'] != user_id:
        return Response('Not authorized to access this playlist', status=401, mimetype="application/json")
    return (playlist)


@bp.route('/', methods=['POST'])
def create_playlist():
    """
    Create a playlist.
    """
    try:
        user_id = get_user_from_auth(request.headers)

        content = request.get_json()
        playlist_name = content['playlist_name']
        music_list = content['music_list']
    except Exception as ex:
        return Response(str(ex), status=400, mimetype="application/json")
    url = db['name'] + '/' + db['endpoint'][1]
    response = requests.post(
        url,
        json={"objtype": "playlist",
              "playlist_name": playlist_name,
              "music_list": music_list,
              "uid": user_id})
    return (response.json())


@bp.route('/add_songs', methods=['PUT'])
def add_songs_to_playlist():
    """
    Add songs to a playlist.
    """
    try:
        user_id = get_user_from_auth(request.headers)

        content = request.get_json()
        playlist_id = content['playlist_id']
        music_list = content['music_list']

        playlist_data = get_playlist_from_id(playlist_id, request.headers)
    except Exception as ex:
        return Response(str(ex), status=400, mimetype="application/json")
    
    # check if song exists in music
    payload = {"objtype": "music"}
    url = db['name'] + '/' + db['endpoint'][4]
    songs = requests.get(url, params=payload).json()['Items']
    all_music_ids = list()
    for song in songs:
        all_music_ids.append(song['music_id'])

    if not all(music_id in all_music_ids  for music_id in music_list):
        return Response('One or more music IDs don\'t exist', status=400, mimetype="application/json")

    music_list.extend(playlist_data['music_list'])
    new_music_list = list(set(music_list))

    url = db['name'] + '/' + db['endpoint'][3]
    payload = {"objtype": "playlist", "objkey": playlist_id}
    response = requests.put(
        url,
        params=payload,
        json={"music_list": new_music_list})
    return (response.json())


@bp.route('/delete_songs', methods=['PUT']) # Check if all music_id exist before adding
def delete_songs_from_playlist():
    """
    Add songs to a playlist.
    """
    try:
        user_id = get_user_from_auth(request.headers)

        content = request.get_json()
        playlist_id = content['playlist_id']
        music_list = content['music_list']

        playlist_data = get_playlist_from_id(playlist_id, request.headers)
    except Exception as ex:
        return Response(str(ex), status=400, mimetype="application/json")
    # we have playlist data. now update the music list

    new_music_list = list(filter(lambda song: (song not in music_list),playlist_data['music_list']))

    url = db['name'] + '/' + db['endpoint'][3]
    payload = {"objtype": "playlist", "objkey": playlist_id}
    response = requests.put(
        url,
        params=payload,
        json={"music_list": new_music_list})
    return (response.json())


@bp.route('/rename', methods=['PUT'])
def rename_playlist():
    """
    Rename playlist.
    """
    try:
        user_id = get_user_from_auth(request.headers)

        content = request.get_json()
        playlist_id = content['playlist_id']
        playlist_name = content['playlist_name']

        playlist_data = get_playlist_from_id(playlist_id, request.headers)
    except Exception as ex:
        return Response(str(ex), status=400, mimetype="application/json")

    url = db['name'] + '/' + db['endpoint'][3]
    payload = {"objtype": "playlist", "objkey": playlist_id}
    response = requests.put(
        url,
        params=payload,
        json={"playlist_name": playlist_name})
    return (response.json())


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
