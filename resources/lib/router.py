from future import standard_library
standard_library.install_aliases()  # noqa: E402

from urllib.parse import parse_qsl, urlencode, urlparse
import re
import resources.lib.utils as utils


class Session:
    def __init__(self, handle, token, is_redirect=False):
        self.handle = handle
        self.token = token
        self.is_redirect = is_redirect


class Router:
    def __init__(self, host):
        self.host = host
        self.routes = {}

    # NOTE: only int and optional str types supported
    def add(self, path, controller, action, **types):
        key = controller.__name__.split('.')[-1] + '#' + action
        self.routes[key] = dict(path=path, controller=controller, action=action, types=types)

    def run(self, url, handle, qs='', _=None):
        utils.log(url + qs)
        url = urlparse(url + qs)
        route = None
        for r in self.routes.values():
            regex = self._path_to_regex(r['path'])
            match = re.match(regex, url.path)
            if match:
                route = r
                break
        if route == None:
            raise ValueError('No matching route found for ' + url.geturl())

        types = route['types']
        params = self._cast_types(match.groupdict(), types)
        query_params = self._cast_types(parse_qsl(url.query), types)
        query_params.update(params)

        self.session = Session(int(handle), token=utils.read_token())
        getattr(route['controller'], route['action'])(
            self,
            query_params
        )

    def redirect(self, controller_name, action, **kwargs):
        route = self._route(controller_name, action)
        token = kwargs.pop('token', None)
        if token:
            self.session.token = token
        self.session.is_redirect = True
        getattr(route['controller'], route['action'])(
            self,
            kwargs
        )

    def _url(self, controller_name, action, **params):
        return self.host + self._path(controller_name, action, **params)

    def _path(self, controller_name, action, **params):
        path = self._route(controller_name, action)['path']
        path_params = re.findall(r'{(\w+)}', path)
        if path_params:
            try:
                path = path.format(**params)
            except KeyError as e:
                raise ValueError('Required parameter %s is missing for %s' % (e, path))
            for pp in path_params:
                params.pop(pp, None)
        if params:
            path += '?' + urlencode(params)
        return path

    def _route(self, controller_name, action):
        key = controller_name + '#' + action
        route = self.routes.get(key)
        if not route:
            raise RuntimeError('No route found for ' + key)
        return route

    def __getattr__(self, name):
        if name.endswith('_url'):
            def func(*args, **kwargs): return self._url(name[:-4], *args, **kwargs)
            return func
        else:
            raise AttributeError("Router instance has no attribute '%s'" % name)

    # NOTE: Arrays in query string are not supported
    @staticmethod
    def _cast_types(params, types):
        """
        [('a': '1'), ('b': 'value')], {'a': int} => {'a': 1, 'b': 'value'}
        """
        params = dict(params)
        for key, value in params.items():
            ptype = types.get(key)
            if ptype:
                try:
                    params[key] = ptype(value)
                except ValueError:
                    msg = "Can't cast value <%s> to type %s for parameter %s" % (params[key], ptype.__name__, key)
                    raise TypeError(msg)
        return params

    @staticmethod
    def _path_to_regex(path):
        regex = re.sub(r'{(\w+)}', r'(?P<\1>\\w+)', path)
        regex = '^' + regex
        if not path.endswith('/'):
            regex += '/'
        regex += '?$'
        return regex
