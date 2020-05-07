import types
import os
import time
import json
import hashlib
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui
from functools import wraps
from resources.lib.translation import _

addon = xbmcaddon.Addon()
PLUGIN_VERSION = addon.getAddonInfo('version')
LANG = xbmc.getLanguage(xbmc.ISO_639_1)
STORAGE_PATH = xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
CACHE_PATH = os.path.join(STORAGE_PATH, 'cache/')
if not xbmcvfs.exists(CACHE_PATH):
    xbmcvfs.mkdir(CACHE_PATH)


class Resp():
    def __init__(self, ok, data, meta=None):
        self.ok = ok
        self.data = data
        self.meta = meta

    def __str__(self):
        return json.dumps({'data': self.data, 'meta': self.meta}, separators=(',', ':'))

    def __eq__(self, resp):
        if not isinstance(resp, Resp):
            return False
        return self.ok == resp.ok and self.data == resp.data and self.meta == resp.meta

    @property
    def data_str(self):
        return json.dumps(self.data, separators=(',', ':'))

    @staticmethod
    def from_string(string):
        resp = json.loads(string)
        return Resp(1, resp['data'], resp['meta'])


def subset(data, *keys):
    """
    Gets subset of data with given keys
    """
    result = {}
    for key in keys:
        if type(key) in [list, tuple]:
            if type(key[0]) == types.FunctionType:
                result[key[1]] = key[0](data)
            else:
                result[key[1]] = data[key[0]]
        else:
            result[key] = data[key]
    return result


def write_file(path, string):
    filepath = os.path.join(STORAGE_PATH, path)
    file = xbmcvfs.File(filepath, 'w')
    file.write(string)
    file.close()


def read_token():
    filepath = os.path.join(STORAGE_PATH, 'token.json')
    if xbmcvfs.exists(filepath):
        file = xbmcvfs.File(filepath)
        token = json.loads(file.read())
        file.close()
        if token['expires'] > time.time():
            return token
        # TODO: request new token
        # ? need an expired token in Movix Android app to sniff how to request a new token
        raise RuntimeError('Not implemented')


def _get_cache(key, max_age):
    filepath = os.path.join(CACHE_PATH, key)
    def is_valid(): return xbmcvfs.Stat(filepath).st_mtime() + max_age > time.time()
    if xbmcvfs.exists(filepath) and is_valid():
        file = xbmcvfs.File(filepath)
        string = file.read()
        file.close()
        return string


def _cache_key(func_name, args):
    key = PLUGIN_VERSION + func_name
    key += reduce(lambda a, b: str(a) + str(b), args, '')
    return hashlib.sha1(key.encode('utf-8')).hexdigest()


def cache(max_age):
    """
    Cache function result based on called function name and arguments.
    """
    def decorator(func):

        # Only non-keyword arguments passed to `func`, because keyword arguments unordered,
        # and we can't ensure the same cache key for the same keyword arguments in
        # different order. Also, non-keyword and keyword arguments could be mixed in different ways.
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = _cache_key(func.__name__, args)
            m_age = 0 if kwargs.get('invalidate_cache') else max_age
            string = _get_cache(key, m_age)
            if string:
                return Resp.from_string(string)
            resp = func(*args)
            if resp.ok:
                cond = kwargs.get('cache_condition')
                if cond == None or cond(resp.data):
                    write_file('cache/' + key, str(resp))
            return resp

        return wrapper
    return decorator


def show_error(error, ask=None):
    default_header = _('error.default_header')
    default_message = _('error.default_message')
    if LANG == 'ru':
        header = error.get('header_ui') or default_header
        message = error.get('message_rus') or error.get('message') or default_message
    else:
        header = error.get('header_ui') or default_header
        message = error.get('reason') or error.get('message') or error.get('message_rus') or default_message
        message = message.capitalize()

    dialog = xbmcgui.Dialog()
    if ask:
        return dialog.yesno(header, message, nolabel=_('button.cancel'), yeslabel=ask)
    return dialog.ok(header, message)


def show_progress(message):
    def decorator(func):

        # Only non-keyword arguments are here, see cache function comment for more info.
        @wraps(func)
        def wrapper(*args):
            dialog = xbmcgui.DialogProgressBG()
            dialog.create(_('header.loading'), message)
            try:
                resp = func(*args)
            finally:
                dialog.close()
            return resp

        return wrapper
    return decorator


def log(*args):
    msg = reduce(lambda a, b: str(a) + ' ' + str(b), args)
    xbmc.log('===> ' + msg, xbmc.LOGNOTICE)
