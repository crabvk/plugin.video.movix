import math
import xbmc
import requests
import hashlib
import uuid
import time
from functools import wraps
from requests.exceptions import RequestException, ConnectionError, ConnectTimeout, ReadTimeout
import resources.lib.utils as utils
from resources.lib.utils import show_progress, cache
from resources.lib.translation import _

CACHE_MAX_AGE = 1800  # 30 minutes
ANDROID_HOST = 'https://discovery-android-26.ertelecom.ru'
STB_HOST = 'https://discovery-stb3.ertelecom.ru'
DEVICE_ID = hashlib.sha1(str(uuid.getnode()).encode('utf8')).hexdigest()[-16:]
HEADERS = {
    'X-Device-Info': DEVICE_ID,
    'View': 'stb3',
    'X-App-Version': '3.12.0',
    'User-Agent': xbmc.getUserAgent()
}


class ApiRequestError(Exception):
    def __init__(self, message):
        super(ApiRequestError, self).__init__(message)
        self.error = {'message': message}


class ApiResponseError(Exception):
    def __init__(self, error):
        super(ApiResponseError, self).__init__(error.get('message'))
        self.error = error


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
    return utils.subset(resp, 'is_bound', 'token', 'expires')


@cache(CACHE_MAX_AGE)
@show_progress(_('progress.regions'))
def regions(token):
    url = ANDROID_HOST + '/er/misc/domains'
    resp = _request('get', url, headers=_headers(token))
    domains = []
    for item in resp['domains']:
        if item['code']:
            domain = utils.subset(item, 'extid', 'code', 'title')
            domains.append(domain)
    return domains


@show_progress(_('progress.auth'))
def auth(token, username, password, region):
    """Requests sso and then requests token is_bound=true"""

    url = ANDROID_HOST + '/er/ssoauth/auth'
    data = dict(username=username, password=password, region=region)
    resp = _request('post', url, headers=_headers(token), data=data)

    url = ANDROID_HOST + '/token/subscriber_device/by_sso'
    params = dict(sso_system='er', sso_key=resp['sso'])
    resp = _request('get', url, params=params, headers=_headers(token))
    return utils.subset(resp, 'is_bound', 'token', 'expires')


@show_progress(_('progress.sms_request'))
def sms_auth(token, phone):
    url = ANDROID_HOST + '/er/ott/get_agreements_by_phone'
    params = {'phone_number': phone}
    resp = _request('get', url, params=params, headers=_headers(token))
    if not resp['principals']:
        raise ApiResponseError({'message': _('error.contract_not_found') % phone})

    url = ANDROID_HOST + '/er/sms/auth'
    region = resp['principals'][0]['domain']
    data = {'phone': phone, 'region': region}
    resp = _request('post', url, headers=_headers(token), data=data)
    result = utils.subset(
        resp['agreements'],
        'send_sms',
        ('sms_error_text', 'message'),
        (lambda d: d['agreement'][0]['agr_id'], 'agr_id')
    )
    result['region'] = region
    return result


@show_progress(_('progress.sms_check'))
def sms_check(token, phone, region, agr_id, sms_code):
    url = ANDROID_HOST + '/er/sms/check'
    data = {'phone': phone, 'region': region, 'agr_id': str(agr_id), 'sms_code': str(sms_code)}
    resp = _request('post', url, headers=_headers(token), data=data)
    if not resp.get('token'):
        raise ApiResponseError({'message': resp['Agreements']['sms_error_text']})
    return utils.subset(resp, 'is_bound', 'token', 'expires')


@cache(7200)
@show_progress(_('progress.status'))
def status(token):
    url = ANDROID_HOST + '/er/multiscreen/status'
    resp = _request('get', url, headers=_headers(token))
    return resp['status']


@show_progress(_('progress.binding'))
def bind_device(token):
    url = ANDROID_HOST + '/er/multiscreen/device/bind'
    _request('post', url, headers=_headers(token), data={'title': 'Kodi'})


# Used only in tests
def devices(token):
    url = ANDROID_HOST + '/er/multiscreen/devices'
    resp = _request('get', url, headers=_headers(token))
    return resp['devices']


def unbind_device(token, id):
    url = ANDROID_HOST + '/er/multiscreen/device/unbind'
    _request('post', url, headers=_headers(token), data={'device_id': id})


@cache(CACHE_MAX_AGE)
@show_progress(_('text.channels'))
def channels(token, limit, page):
    url = STB_HOST + '/api/v3/showcases/library/channels'
    params = {'limit': str(limit), 'page': str(page)}
    resp = _request('get', url, params=params, headers=_headers(token))
    chs, _ = _map_items(resp['data']['items'], ['id', 'title', 'description', 'lcn'], {
        'hls_id': 'hls',
        'poster_id': 'poster_channel_grid_blueprint'
    })
    return {'channels': chs, 'pages': _pages(resp, limit)}


@cache(CACHE_MAX_AGE)
@show_progress(_('text.channels'))
def channels_all(token, public=False):
    url = ANDROID_HOST + '/channel_list/multiscreen'
    resp = _request('get', url, headers=_headers(token))
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
    return {'channels': chs}


def playlist_url(token, channel_id, hls_id):
    url = ANDROID_HOST + '/resource/get_url/%i/%i' % (channel_id, hls_id)
    resp = _request('get', url, headers=_headers(token))
    return resp['url']


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
    pkgs, _ = _map_items(resp['data']['items'],
                         ['id', 'title', 'description', (lambda i: i['adult']['type'], 'adult')], {
        'poster_id': '3_smarttv_package_poster_video_library_blueprint',
        'fanart_id': '3_smarttv_asset_background_banner_fullscreen_blueprint'
    })
    return {'packages': pkgs, 'pages': _pages(resp, limit)}


@cache(CACHE_MAX_AGE)
@show_progress(_('progress.package_channels'))
def package_channels(token, id, adult=0):
    url = STB_HOST + '/api/v3/showcases/children/channel-package/%i/channels' % id
    params = {'adult': 'adult,not-adult'} if adult else None
    resp = _request('get', url, params=params, headers=_headers(token))
    chs, _ = _map_items(resp['data']['items'], ['id', 'title', 'description', 'lcn'], {
        'hls_id': 'hls',
        'poster_id': 'poster_channel_grid_blueprint'
    })
    return {'channels': chs}


@cache(CACHE_MAX_AGE)
@show_progress(_('text.movies'))
def movies(token, limit, offset, free):
    url = STB_HOST + '/api/v3/showcases/library/' + ('freemovies' if free else 'movies')
    params = {'limit': '100', 'offset': str(offset)}
    resp = _request('get', url, params=params, headers=_headers(token))
    movs, offset = _map_items(resp['data']['items'], ['id', 'title', 'description'], {
        'hls_id': 'hls',
        'poster_id': 'poster_blueprint',
        'fanart_id': '3_smarttv_asset_background_video_library_blueprint'
    }, limit, offset)
    return {'movies': movs, 'offset': offset, 'total': resp['data']['total']}


@cache(CACHE_MAX_AGE)
@show_progress(_('text.serials'))
def serials(token, limit, offset):
    params = {'limit': '100', 'offset': str(offset)}
    url = STB_HOST + '/api/v3/showcases/library/serials'
    resp = _request('get', url, params=params, headers=_headers(token))
    srls, offset = _map_items(resp['data']['items'], ['id', 'title', 'description'], {
        'hls_id': 'hls',
        'poster_id': 'poster_blueprint',
        'fanart_id': '3_smarttv_serial_background_video_library_blueprint'
    }, limit, offset)
    return {'serials': srls, 'offset': offset, 'total': resp['data']['total']}


@cache(CACHE_MAX_AGE)
@show_progress(_('text.seasons'))
def seasons(token, serial_id):
    url = STB_HOST + '/api/v3/showcases/seasons/serial/%i/seasons' % serial_id
    resp = _request('get', url, headers=_headers(token))
    sns, _ = _map_items(resp['data']['items'], ['id', 'title', 'description', 'number'], {
        'poster_id': 'poster_blueprint',
        'fanart_id': '3_smarttv_season_background_video_library_blueprint'
    })
    return {'seasons': sns}


@cache(CACHE_MAX_AGE)
@show_progress(_('text.episodes'))
def episodes(token, season_id):
    url = STB_HOST + '/api/v3/showcases/episodes/season/%i/episodes' % season_id
    resp = _request('get', url, headers=_headers(token))
    epds, _ = _map_items(resp['data']['items'], ['id', 'title', 'description', 'number'], {
        'hls_id': 'hls',
        'poster_id': [
            '3_smarttv_episode_poster_video_library_blueprint',
            '3_smarttv_tvshow_poster_video_library_blueprint',
            'poster_blueprint'
        ]
    })
    return {'episodes': epds}


def _map_items(items, keys, res_map, limit=100, offset=0):
    mapped = []
    for item in items:
        offset += 1
        mi = utils.subset(item, *keys)
        resources = {r['type']: r for r in item['resources']}
        res = {'available': item['available']['type'] != 'not-available'}
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
        kwargs.setdefault('timeout', 30)
        resp = requests.request(method, url, **kwargs)
    except ConnectTimeout:
        msg = _('error.connect_timeout')
    except ConnectionError:
        msg = _('error.connection_error')
    except ReadTimeout:
        msg = _('error.read_timeout')
    except RequestException:
        msg = _('error.request_exception')
    if resp == None:
        raise ApiRequestError(msg)

    data = resp.json()
    if 'error' in data:
        raise ApiResponseError(data['error'])
    return data


def _pages(resp, limit):
    return int(math.ceil(resp['data']['total'] / float(limit)))


def on_error(callback):
    def decorator(func):

        @wraps(func)
        def wrapper(router, params):
            try:
                func(router, params)
            except (ApiRequestError, ApiResponseError) as e:
                utils.show_error(e.error)
                args = [router] if callback.func_code.co_argcount == 1 else [router, params]
                callback(*args)

        return wrapper
    return decorator
