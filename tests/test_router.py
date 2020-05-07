import sys
import pytest
from mock import patch
from resources.lib.router import Router
from tests.helpers import dict_types

this = sys.modules[__name__]
host = 'plugin://test'


def index(_router, params):
    assert params == {}


def resource(_router, params):
    assert type(params['id']) == int
    assert params == {'id': 42}


def nested_with_qs(_router, params):
    assert dict_types(params) == {'id': int, 'number': int, 'q': str, 'value': int}
    assert params == {'id': 8, 'number': 16, 'q': 'hello', 'value': 7}


class TestRouter:
    def setup_method(self, _method):
        r = Router(host)
        r.add('/', this, 'index')
        r.add('/resource/{id}', this, 'resource', id=int)
        r.add('/items/{id}/{number}', this, 'nested_with_qs', id=int, number=int, value=int)
        self.router = r

    @patch('resources.lib.utils.read_token')
    def test_params(self, read_token):
        read_token.return_value = None
        r = self.router
        r.run(host + '/', '1')
        r.run(host + '/resource/42', '1')
        r.run(host + '/items/8/16', '1', '?q=hello&value=7')
        assert r.session.handle == 1
        assert not r.session.is_redirect

    def test_url_method(self):
        r = self.router
        assert r.test_router_url('index') == host + '/'
        assert r.test_router_url('resource', id=43) == host + '/resource/43'
        assert r.test_router_url('nested_with_qs', id=9, number=17) == host + '/items/9/17'
        assert r.test_router_url('nested_with_qs', id=10, number=18, value='world') == host + '/items/10/18?value=world'

    @patch('resources.lib.utils.read_token')
    def test_redirect(self, read_token):
        read_token.return_value = {'token': 'token1'}
        r = self.router
        r.run(host + '/', '1')
        r.redirect('test_router', 'index')
        assert r.session.is_redirect

        r.run(host + '/', '2')
        r.redirect('test_router', 'resource', id=42, token={'token': 'token2'})
        assert r.session.handle == 2
        assert r.session.is_redirect
        assert r.session.token['token'] == 'token2'

    def test_errors(self):
        r = self.router
        with pytest.raises(ValueError, match='^No matching route found for'):
            r.run(host + '/not-found', '1')

        with pytest.raises(TypeError, match="^Can't cast value <abc> to type int for parameter id$"):
            r.run(host + '/resource/abc', '1')

        with pytest.raises(ValueError, match="^Required parameter 'id' is missing"):
            r.test_router_url('resource')

        with pytest.raises(RuntimeError, match='^No route found for error#action1$'):
            r.error_url('action1')
