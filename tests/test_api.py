import os
import sys
import pytest
import resources.lib.api as api
from tests.helpers import has_keys

token = None  # is_bound=False
auth = None   # is_bound=True


def assert_channels_resp(resp):
    assert isinstance(resp, dict)
    assert has_keys(resp['channels'][0], ['id', 'title', 'description', 'lcn', 'hls_id'])


def test_token():
    global token
    token = api.token()
    assert has_keys(token, ['is_bound', 'token', 'expires'])
    assert not token['is_bound']


def test_regions():
    assert token is not None
    regions = api.regions(token['token'])
    assert has_keys(regions[0], ['extid', 'code', 'title'])


def test_all_public_channels():
    assert token is not None
    resp = api.channels_all(token['token'], True)
    assert_channels_resp(resp)


def test_auth(credentials):
    global auth
    assert token is not None

    auth = api.auth(token['token'], *credentials.split(','))
    assert has_keys(auth, ['is_bound', 'token', 'expires'])
    assert auth['is_bound']


def test_status():
    assert auth is not None
    status = api.status(auth['token'])
    assert has_keys(status, ['is_bound', 'slot_count', 'state'])
    if status['is_bound']:
        devices = api.devices(auth['token'])
        plugin = next(d for d in devices if d['extid'] == api.DEVICE_ID)
        api.unbind_device(auth['token'], plugin['id'])


def test_bind_device():
    assert auth is not None
    api.bind_device(auth['token'])


def test_channels():
    assert auth is not None
    resp = api.channels(auth['token'], 16, 2)
    assert_channels_resp(resp)
    assert resp['pages'] > 0


def test_all_channels():
    assert auth is not None
    resp = api.channels_all(auth['token'])
    assert_channels_resp(resp)


def test_playlist_url():
    assert auth is not None
    url = api.playlist_url(auth['token'], 817710, 965033)
    assert url.endswith('playlist.m3u8')


def test_channel_packages():
    assert auth is not None
    resp = api.channel_packages(auth['token'], 8, 1)
    assert 'packages' in resp
    # Can't do further assertions, Dom.ru cut free subscriptions on my plan :(
    # assert has_keys(resp['packages'][0], ['id', 'title', 'description', 'adult'])
    # assert resp['pages'] > 0


def test_package_channels():
    assert auth is not None
    resp = api.package_channels(auth['token'], 278621)
    assert 'channels' in resp
    # assert has_keys(resp['channels'][0], ['id', 'title', 'description', 'lcn', 'hls_id'])


# TODO: fix tests for movies and serials
@pytest.mark.skip(reason='Returned list of movies is empty')
def test_movies():
    assert auth is not None
    resp = api.movies(auth['token'], 100, 500, False)
    assert has_keys(resp['movies'][0], ['id', 'title', 'description', 'hls_id'])
    assert resp['total'] > 0
    # Free movies
    resp = api.movies(auth['token'], 10, 0, True)
    assert has_keys(resp['movies'][0], ['id', 'title', 'description', 'hls_id'])
    assert resp['total'] > 0


@pytest.mark.skip(reason='Returned list of serials is empty')
def test_serials():
    assert auth is not None
    resp = api.serials(auth['token'], 100, 2)
    assert has_keys(resp['serials'][0], ['id', 'title', 'description', 'hls_id'])
    assert resp['total'] > 0


def test_seasons():
    assert auth is not None
    resp = api.seasons(auth['token'], 1121330)
    assert has_keys(resp['seasons'][0], ['id', 'title', 'description', 'number'])


def test_episodes():
    assert auth is not None
    resp = api.episodes(auth['token'], 1122169)
    assert has_keys(resp['episodes'][0], ['id', 'title', 'description', 'number', 'hls_id'])


def test_api_request_error():
    with pytest.raises(api.ApiRequestError):
        api._request('get', 'https://ggoole.com')


def test_api_response_error():
    with pytest.raises(api.ApiResponseError) as e:
        api.channels('fake-token', 100, 1)
    assert str(e.value) == 'no valid token'
