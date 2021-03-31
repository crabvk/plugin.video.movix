import xbmcgui
import xbmcplugin
import resources.lib.api as api
import resources.lib.utils as utils
from resources.lib.translation import _


@api.on_error(lambda r: xbmcplugin.endOfDirectory(r.session.handle))
def index(router, _params=None):
    handle = router.session.handle
    token = router.session.token

    if not token:
        token = api.token()
        utils.write_file('token.json', token)

    items = []

    def add_channels_item(label):
        li = xbmcgui.ListItem(label=label)
        li.setInfo('video', dict(plot=_('text.tv_channels')))
        url = router.channels_url('index')
        items.append((url, li, True))

    if token['is_bound']:
        status = api.status(
            token['token'],
            invalidate_cache=(handle == 1),
            cache_condition=lambda d: d.get('is_bound')
        )

        # TODO: handle case with no slot available for device
        if not status['is_bound']:
            api.bind_device(token['token'])

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

        # Free movies
        li = xbmcgui.ListItem(label=_('text.free_movies'))
        url = router.movies_url('index_free')
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

        # Sign in by SMS
        url = router.root_url('sign_in_sms')
        li = xbmcgui.ListItem(label=_('label.sign_in_sms'))
        items.append((url, li, True))

        # Channels
        add_channels_item(_('li.public_channels'))

    xbmcplugin.addDirectoryItems(handle, items, len(items))
    xbmcplugin.endOfDirectory(handle, updateListing=router.session.is_redirect)


@api.on_error(lambda r: r.redirect('root', 'index'))
def sign_in(router, params):
    dialog = xbmcgui.Dialog()

    username = dialog.input(_('label.username'), type=xbmcgui.INPUT_ALPHANUM)
    if not username:
        return router.redirect('root', 'index')

    password = dialog.input(_('label.password'), type=xbmcgui.INPUT_ALPHANUM)
    if not password:
        return router.redirect('root', 'index')

    token = router.session.token
    regions = api.regions(token['token'])

    # Try to get region from contract number
    region = None
    if len(username) == 12:
        code = None
        try:
            code = int(username[0:3])
        except ValueError:
            pass
        if code:
            region = next((r for r in regions if r['code'] == code), None)

    # User selects a region
    if not region:
        pos = dialog.select(_('label.city'), list(map(lambda r: r['title'], regions)))
        if pos < 0:
            return router.redirect('root', 'index')
        region = regions[pos]

    token = api.auth(token['token'], username, password, region['extid'])
    utils.write_file('token.json', token)
    router.redirect('root', 'index', token=token)


def sign_in_sms(router, params):
    dialog = xbmcgui.Dialog()

    phone = dialog.input(_('label.phone_number'), type=xbmcgui.INPUT_ALPHANUM)
    if not phone:
        return router.redirect('root', 'index')

    token = router.session.token
    resp = api.sms_auth(token['token'], phone)

    if not resp['send_sms']:
        utils.show_error(resp)

    code = dialog.input(_('label.sms_code'), type=xbmcgui.INPUT_NUMERIC)
    if not code:
        return router.redirect('root', 'index')

    token = api.sms_check(token['token'], phone, resp['region'], resp['agr_id'], code)
    utils.write_file('token.json', token)
    router.redirect('root', 'index', token=token)


def play(router, params):
    handle = router.session.handle
    try:
        url = api.playlist_url(router.session.token['token'], params['id'], params['hls_id'])
        xbmcplugin.setResolvedUrl(handle, True, xbmcgui.ListItem(path=url))
    except api.ApiResponseError as e:
        xbmcplugin.setResolvedUrl(handle, False, xbmcgui.ListItem())
        utils.show_error(e.error)
