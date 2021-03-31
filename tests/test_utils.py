import os
import time
import shutil
import json
from functools import wraps
from mock import patch
import resources.lib.utils as utils
import resources.lib.translation.ru_ru as ru

STORAGE_PATH = '/tmp/movix_test/'
CACHE_PATH = STORAGE_PATH + 'cache/'

shutil.rmtree(STORAGE_PATH, ignore_errors=True)
os.makedirs(CACHE_PATH)


class Stat:
    def __init__(self, filepath):
        self.filepath = filepath

    def st_mtime(self):
        return os.stat(self.filepath).st_mtime


def cached_resp(cache_key, max_age):
    cached = utils._get_cache(cache_key, max_age)
    if cached:
        return json.loads(cached)


def patch_cache(func):
    @patch('xbmcvfs.File', new=open)
    @patch('xbmcvfs.Stat', new=Stat)
    @patch('xbmcvfs.exists', new=os.path.isfile)
    @patch('resources.lib.utils.CACHE_PATH', new=CACHE_PATH)
    @patch('resources.lib.utils.STORAGE_PATH', new=STORAGE_PATH)
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def test_show_progress():
    assert utils.show_progress('message')(lambda a: 'test' + a)('ing') == 'testing'


@patch('xbmcgui.Dialog')
@patch('resources.lib.utils.LANG', new='en')
def test_show_error_default_en(dialog):
    utils.show_error({})
    dialog().ok.assert_called_with('Data request error', 'Unknown reason')

    utils.show_error({'header_ui': 'header1', 'message': 'message1'})
    dialog().ok.assert_called_with('header1', 'Message1')


@patch('xbmcgui.Dialog')
@patch('resources.lib.utils._', new=lambda k: dict(ru.ru_ru)[k])
@patch('resources.lib.utils.LANG', new='ru')
def test_show_error_default_ru(Dialog):
    utils.show_error({})
    Dialog().ok.assert_called_with('Ошибка при запросе данных', 'Причина неизвестна')


def func1(arg):
    return {'item': arg}


cached_func1 = utils.cache(300)(func1)


@patch_cache
def test_cache():
    assert cached_func1('test1') == func1('test1')

    key = utils._cache_key('func1', ['test1'])
    filepath = os.path.join(CACHE_PATH, key)
    st_mtime = os.stat(filepath).st_mtime

    # Get cached resp
    assert cached_resp(key, 300) == cached_func1('test1')
    assert st_mtime == os.stat(filepath).st_mtime

    # Cache expired
    assert cached_resp(key, -1) == None

    # Cache invalidated - new cache file created
    time.sleep(0.01)
    assert cached_func1('test1', invalidate_cache=True) == func1('test1')
    assert st_mtime < os.stat(filepath).st_mtime


@patch_cache
def test_cache_condition():
    key = utils._cache_key('func1', ['test2'])

    # Do not cache when cache_condition returns False
    assert cached_func1('test2', cache_condition=lambda _: False) == func1('test2')
    assert cached_resp(key, 300) == None

    # Cache with cache_condition
    assert cached_func1('test2', cache_condition=lambda _: True) == func1('test2')
    assert cached_resp(key, 300) == func1('test2')


def test_subset():
    assert utils.subset({'a': 1, 'b': 2, 'c': 3}, 'a', 'c') == {'a': 1, 'c': 3}
    assert utils.subset({'a': 1, 'b': 2, 'c': 3}, 'a', ('c', 'y')) == {'a': 1, 'y': 3}
    assert utils.subset({'a': 1, 'b': 2, 'c': 3}, 'a', (lambda d: d['c'], 'y')) == {'a': 1, 'y': 3}
