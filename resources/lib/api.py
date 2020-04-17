from future import standard_library
standard_library.install_aliases()  # noqa: E402

import math
import xbmc
import requests
import hashlib
import uuid
import time
from requests.exceptions import RequestException, ConnectionError, ConnectTimeout, ReadTimeout
import resources.lib.utils as utils
from resources.lib.utils import Resp, show_progress, cache
from resources.lib.translation import _

CACHE_MAX_AGE = 1800  # 30 minutes
ANDROID_HOST = 'https://discovery-android-26.ertelecom.ru'
STB_HOST = 'https://discovery-stb3.ertelecom.ru'
DEVICE_ID = hashlib.sha1(str(uuid.getnode())).hexdigest()[-16:]
HEADERS = {
    'X-Device-Info': DEVICE_ID,
    'View': 'stb3',
    'X-App-Version': '3.9.2',
    'User-Agent': xbmc.getUserAgent()
}


def _headers(token):
    headers = dict(HEADERS)
    headers.update({'X-Auth-Token': token})
    return headers


@show_progress(_('progress.device_registration'))
def token():
    """Requests initial token is_bound=false"""

    url = ANDROID_HOST + '/token/device'
    params = dict(
        client_id='er_android_device',
        device_id=DEVICE_ID,
        timestamp=str(int(time.time()))
    )
    resp = _request('get', url, params=params, headers=HEADERS)
    if not resp.get('result'):
        return Resp(0, resp.get('error'))
    return Resp(1, utils.subset(resp, 'is_bound', 'token', 'expires'))


@cache(CACHE_MAX_AGE)
@show_progress(_('progress.regions'))
def regions(token):
    url = ANDROID_HOST + '/er/misc/domains'
    resp = _request('get', url, headers=_headers(token))
    if not resp.get('result'):
        return Resp(0, resp.get('error'))

    domains = []
    for item in resp['domains']:
        if item['code']:
            domain = utils.subset(item, 'extid', 'code', 'title')
            domains.append(domain)
    return Resp(1, domains)


@show_progress(_('progress.auth'))
def auth(token, username, password, region):
    """Requests sso and then requests token is_bound=true"""

    url = ANDROID_HOST + '/er/ssoauth/auth'
    data = dict(username=username, password=password, region=region)
    resp = _request('post', url, headers=_headers(token), data=data)
    if not resp.get('result'):
        return Resp(0, resp.get('error'))

    url = ANDROID_HOST + '/token/subscriber_device/by_sso'
    params = dict(sso_system='er', sso_key=resp['sso'])
    resp = _request('get', url, params=params, headers=_headers(token))
    if not resp.get('result'):
        return Resp(0, resp.get('error'))
    return Resp(1, utils.subset(resp, 'is_bound', 'token', 'expires'))


@cache(7200)
@show_progress(_('progress.status'))
def status(token):
    url = ANDROID_HOST + '/er/multiscreen/status'
    resp = _request('get', url, headers=_headers(token))
    if not resp.get('result'):
        return Resp(0, resp.get('error'))
    return Resp(1, resp['status'])


@show_progress(_('progress.binding'))
def bind_device(token):
    url = ANDROID_HOST + '/er/multiscreen/device/bind'
    resp = _request('post', url, headers=_headers(token), data={'title': 'Kodi'})
    return Resp(resp.get('result'), resp.get('error'))


@cache(CACHE_MAX_AGE)
@show_progress(_('text.channels'))
def channels(token, limit, page):
    url = STB_HOST + '/api/v3/showcases/library/channels'
    params = {'limit': str(limit), 'page': str(page)}
    resp = _request('get', url, params=params, headers=_headers(token))
    if not resp.has_key('data'):
        return Resp(0, resp.get('error'))

    chs, _ = _map_items(resp['data']['items'], ['id', 'title', 'description', 'lcn'], {
        'hls_id': 'hls',
        'poster_id': 'poster_channel_grid_blueprint'
    })
    return Resp(1, chs, {'pages': _pages(resp, limit)})


@cache(CACHE_MAX_AGE)
@show_progress(_('text.channels'))
def channels_all(token, public=False):
    url = ANDROID_HOST + '/channel_list/multiscreen'
    resp = _request('get', url, headers=_headers(token))
    if not resp.get('result'):
        return Resp(0, resp.get('error'))

    chs = []
    for item in resp['collection']:
        ch = utils.subset(item, 'id', 'title', 'description', ('er_lcn', 'lcn'))
        resources = {r['category']: r for r in item['resources']}
        if public and not resources.get('hls', {}).get('is_public'):
            continue
        res = {
            'hls_id': resources['hls']['id'],
            'poster_id': resources['poster_channel_grid_blueprint']['id']
        }
        ch.update(res)
        chs.append(ch)
    return Resp(1, chs)


def playlist_url(token, channel_id, hls_id):
    url = ANDROID_HOST + '/resource/get_url/%i/%i' % (channel_id, hls_id)
    resp = _request('get', url, headers=_headers(token))
    if not resp.get('result'):
        return Resp(0, resp.get('error'))
    return Resp(1, resp['url'])


def art_url(art_id, w=0, h=0):
    url = 'https://er-cdn.ertelecom.ru/content/public/r%i' % art_id
    if w and h:
        url += '/%ix%i:crop' % (w, h)
    return url


@cache(CACHE_MAX_AGE)
@show_progress(_('text.channel_packages'))
def channel_packages(token, limit, page):
    url = STB_HOST + '/api/v3/showcases/library/channel-packages'
    params = {'limit': str(limit), 'page': str(page)}
    resp = _request('get', url, params=params, headers=_headers(token))
    if not resp.has_key('data'):
        return Resp(0, resp.get('error'))

    pkgs, _ = _map_items(resp['data']['items'],
                         ['id', 'title', 'description', (lambda i: i['adult']['type'], 'adult')], {
        'poster_id': '3_smarttv_package_poster_video_library_blueprint',
        'fanart_id': '3_smarttv_asset_background_banner_fullscreen_blueprint'
    })
    return Resp(1, pkgs, {'pages': _pages(resp, limit)})


@cache(CACHE_MAX_AGE)
@show_progress(_('progress.package_channels'))
def package_channels(token, id, adult=0):
    url = STB_HOST + '/api/v3/showcases/children/channel-package/%i/channels' % id
    params = {'adult': 'adult,not-adult'} if adult else None
    resp = _request('get', url, params=params, headers=_headers(token))
    if not resp.has_key('data'):
        return Resp(0, resp.get('error'))

    chs, _ = _map_items(resp['data']['items'], ['id', 'title', 'description', 'lcn'], {
        'hls_id': 'hls',
        'poster_id': 'poster_channel_grid_blueprint'
    })
    return Resp(1, chs)


@cache(CACHE_MAX_AGE)
@show_progress(_('text.movies'))
def movies(token, limit, offset):
    url = STB_HOST + '/api/v3/showcases/library/movies'
    params = {'limit': '100', 'offset': str(offset)}
    resp = _request('get', url, params=params, headers=_headers(token))
    if not resp.has_key('data'):
        return Resp(0, resp.get('error'))

    movs, offset = _map_items(resp['data']['items'], ['id', 'title', 'description'], {
        'hls_id': 'hls',
        'poster_id': 'poster_blueprint',
        'fanart_id': '3_smarttv_asset_background_video_library_blueprint'
    }, limit, offset)
    return Resp(1, movs, {'offset': offset, 'total': resp['data']['total']})


@cache(CACHE_MAX_AGE)
@show_progress(_('text.serials'))
def serials(token, limit, page):
    params = {'limit': str(limit), 'page': str(page)}
    url = STB_HOST + '/api/v3/showcases/library/serials'
    resp = _request('get', url, params=params, headers=_headers(token))
    if not resp.has_key('data'):
        return Resp(0, resp.get('error'))

    srls, _ = _map_items(resp['data']['items'], ['id', 'title', 'description'], {
        'hls_id': 'hls',
        'poster_id': 'poster_blueprint',
        'fanart_id': '3_smarttv_serial_background_video_library_blueprint'
    })
    return Resp(1, srls, {'pages': _pages(resp, limit)})


@cache(CACHE_MAX_AGE)
@show_progress(_('text.seasons'))
def seasons(token, serial_id):
    url = STB_HOST + '/api/v3/showcases/seasons/serial/%i/seasons' % serial_id
    resp = _request('get', url, headers=_headers(token))
    if not resp.has_key('data'):
        return Resp(0, resp.get('error'))

    sns, _ = _map_items(resp['data']['items'], ['id', 'title', 'description', 'number'], {
        'poster_id': 'poster_blueprint',
        'fanart_id': '3_smarttv_season_background_video_library_blueprint'
    })
    return Resp(1, sns)


@cache(CACHE_MAX_AGE)
@show_progress(_('text.episodes'))
def episodes(token, season_id):
    url = STB_HOST + '/api/v3/showcases/episodes/season/%i/episodes' % season_id
    resp = _request('get', url, headers=_headers(token))
    if not resp.has_key('data'):
        return Resp(0, resp.get('error'))

    epds, _ = _map_items(resp['data']['items'], ['id', 'title', 'description', 'number'], {
        'hls_id': 'hls',
        'poster_id': [
            '3_smarttv_episode_poster_video_library_blueprint',
            '3_smarttv_tvshow_poster_video_library_blueprint',
            'poster_blueprint'
        ]
    })
    return Resp(1, epds)


def _map_items(items, keys, res_map, limit=100, offset=0):
    mapped = []
    for item in items:
        offset += 1
        if item['available']['type'] == 'not-available':
            continue
        mi = utils.subset(item, *keys)
        resources = {r['type']: r for r in item['resources']}
        res = {}
        for data_key, res_type in res_map.items():
            if isinstance(res_type, str):
                res[data_key] = resources.get(res_type, {}).get('id')
            else:
                res[data_key] = next((resources[t]['id'] for t in res_type if resources.get(t)), None)
        mi.update(res)
        mapped.append(mi)
        if len(mapped) == limit:
            break
    return [mapped, offset]


def _request(method, url, **kwargs):
    resp = None
    try:
        kwargs.setdefault('timeout', (7, 5))
        resp = requests.request(method, url, **kwargs)
    except ConnectionError:
        msg = _('error.connection_error')
    except ConnectTimeout:
        msg = _('error.connect_timeout')
    except ReadTimeout:
        msg = _('error.read_timeout')
    except RequestException:
        msg = _('error.request_exception')
    if resp == None:
        return {'error': {'message': msg}}
    return resp.json()


def _pages(resp, limit):
    return int(math.ceil(resp['data']['total'] / float(limit)))
