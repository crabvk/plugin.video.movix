import json
import xbmcgui
import xbmcplugin
import resources.lib.api as api
import resources.lib.utils as utils
from resources.lib.translation import _


def index(router, _params=None):
    handle = router.session.handle
    token = router.session.token

    if not token:
        resp = api.token()
        if not resp.ok:
            utils.show_error(resp.data)
            return xbmcplugin.endOfDirectory(handle)
        token = resp.data
        utils.write_file('token.json', json.dumps(token, separators=(',', ':')))

    items = []

    def add_channels_item(label):
        li = xbmcgui.ListItem(label=label)
        li.setInfo('video', dict(plot=_('text.tv_channels')))
        url = router.channels_url('index')
        items.append((url, li, True))

    if token['is_bound']:
        resp = api.status(
            token['token'],
            invalidate_cache=(handle == 1),
            cache_condition=lambda d: d.get('is_bound')
        )
        if not resp.ok:
            utils.show_error(resp.data)
            return xbmcplugin.endOfDirectory(handle)

        # TODO: handle case with no slot available for device
        if not resp.data['is_bound']:
            resp = api.bind_device(token['token'])
            if not resp.ok:
                if utils.show_error(resp.data, ask=_('button.try_again')):
                    return index(router)
                return xbmcplugin.endOfDirectory(handle)

        # Channels
        add_channels_item(_('text.channels'))

        # Channel packages
        li = xbmcgui.ListItem(label=_('text.channel_packages'))
        li.setInfo('video', dict(plot=_('text.channel_packages')))
        url = router.channel_packages_url('index')
        items.append((url, li, True))

        # Movies
        li = xbmcgui.ListItem(label=_('text.movies'))
        url = router.movies_url('index')
        items.append((url, li, True))

        # Serials
        li = xbmcgui.ListItem(label=_('text.serials'))
        url = router.serials_url('index')
        items.append((url, li, True))
    else:
        # Sign in
        url = router.root_url('sign_in')
        li = xbmcgui.ListItem(label=_('li.sign_in'))
        items.append((url, li, True))

        # Channels
        add_channels_item(_('li.public_channels'))

    xbmcplugin.addDirectoryItems(handle, items, len(items))
    xbmcplugin.endOfDirectory(handle, updateListing=router.session.is_redirect)


def sign_in(router, params):
    dialog = xbmcgui.Dialog()

    username = dialog.input(_('label.username'), type=xbmcgui.INPUT_ALPHANUM)
    if not username:
        return router.redirect('root', 'index')

    password = dialog.input(_('label.password'), type=xbmcgui.INPUT_ALPHANUM)
    if not password:
        return router.redirect('root', 'index')

    token = router.session.token
    resp = api.regions(token['token'])
    if not resp.ok:
        utils.show_error(resp.data)
        return router.redirect('root', 'index')

    # Try to get region from contract number
    region = None
    if len(username) == 12:
        code = None
        try:
            code = int(username[0:3])
        except ValueError:
            pass
        if code:
            region = next((r for r in resp.data if r['code'] == code), None)

    # User selects a region
    if not region:
        pos = dialog.select(_('label.city'), list(map(lambda r: r['title'], resp.data)))
        if pos < 0:
            return router.redirect('root', 'index')
        region = resp.data[pos]

    resp = api.auth(token['token'], username, password, region['extid'])
    if not resp.ok:
        utils.show_error(resp.data)
        return router.redirect('root', 'index')

    utils.write_file('token.json', json.dumps(resp.data, separators=(',', ':')))
    router.redirect('root', 'index', token=resp.data)


def play(router, params):
    resp = api.playlist_url(router.session.token['token'], params['id'], params['hls_id'])
    url = resp.data if resp.ok else None
    li = xbmcgui.ListItem(path=url)
    xbmcplugin.setResolvedUrl(router.session.handle, bool(resp.ok), li)
    if not resp.ok:
        utils.show_error(resp.data)
