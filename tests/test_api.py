import os
import sys
import pytest
import resources.lib.api as api
from tests.helpers import has_keys

token = None  # is_bound=False
auth = None   # is_bound=True


def assert_channels_resp(resp):
    assert resp.ok
    assert isinstance(resp.data, list)
    assert has_keys(resp.data[0], ['id', 'title', 'description', 'lcn', 'hls_id'])


def test_env():
    assert os.getenv('API_TESTS') is not None


def _test_token():
    global token
    resp = api.token()
    token = resp.data
    assert resp.ok
    assert has_keys(resp.data, ['is_bound', 'token', 'expires'])
    assert not resp.data['is_bound']


def _test_regions():
    assert token is not None
    resp = api.regions(token['token'])
    assert resp.ok
    assert has_keys(resp.data[0], ['extid', 'code', 'title'])


def _test_all_public_channels():
    assert token is not None
    resp = api.channels_all(token['token'], True)
    assert_channels_resp(resp)


def _test_auth():
    global auth
    creds = os.getenv('CREDENTIALS')
    assert creds is not None
    assert token is not None

    resp = api.auth(token['token'], *creds.split(','))
    auth = resp.data
    assert resp.ok
    assert has_keys(resp.data, ['is_bound', 'token', 'expires'])
    assert resp.data['is_bound']


def _test_status():
    assert auth is not None
    resp = api.status(auth['token'])
    assert resp.ok
    if resp.data['is_bound']:
        api.unbind_device(auth['token'])


def _test_bind_device():
    assert auth is not None
    resp = api.bind_device(auth['token'])
    assert resp.ok


def _test_channels():
    assert auth is not None
    resp = api.channels(auth['token'], 16, 2)
    assert_channels_resp(resp)
    assert resp.meta['pages'] > 0


def _test_all_channels():
    assert auth is not None
    resp = api.channels_all(auth['token'])
    assert_channels_resp(resp)


def _test_playlist_url():
    assert auth is not None
    resp = api.playlist_url(auth['token'], 817710, 965033)
    assert resp.ok


def _test_channel_packages():
    assert auth is not None
    resp = api.channel_packages(auth['token'], 8, 1)
    assert resp.ok
    # Can't do further assertions, Dom.ru cut free subscriptions on my plan :(
    # assert has_keys(resp.data[0], ['id', 'title', 'description', 'adult'])
    # assert resp.meta['pages'] > 0


def _test_package_channels():
    assert auth is not None
    resp = api.package_channels(auth['token'], 278621)
    assert resp.ok
    # assert has_keys(resp.data[0], ['id', 'title', 'description', 'lcn', 'hls_id'])


def _test_movies():
    assert auth is not None
    resp = api.movies(auth['token'], 100, 500)
    assert resp.ok
    assert has_keys(resp.data[0], ['id', 'title', 'description', 'hls_id'])
    assert resp.meta['total'] > 0


def _test_serials():
    assert auth is not None
    resp = api.serials(auth['token'], 100, 2)
    assert resp.ok
    assert has_keys(resp.data[0], ['id', 'title', 'description', 'hls_id'])
    assert resp.meta['pages'] > 0


def _test_seasons():
    assert auth is not None
    resp = api.seasons(auth['token'], 1121330)
    assert resp.ok
    assert has_keys(resp.data[0], ['id', 'title', 'description', 'number'])


def _test_episodes():
    assert auth is not None
    resp = api.episodes(auth['token'], 1122169)
    assert resp.ok
    assert has_keys(resp.data[0], ['id', 'title', 'description', 'number', 'hls_id'])


if os.getenv('API_TESTS'):
    this = sys.modules[__name__]
    for name in dir(this):
        if name.startswith('_test_'):
            func = getattr(this, name)
            setattr(this, name[1:], func)
