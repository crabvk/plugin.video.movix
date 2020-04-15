import xbmc

lang = xbmc.getLanguage(xbmc.ISO_639_1, region=True)
lang = (lang or 'en-GB').split('-')
lang[1] = (lang[1] or 'GB').lower()
LANG = '_'.join(lang)
try:
    module = __import__('resources.lib.translation.' + LANG, fromlist=[LANG])
    trans = dict(getattr(module, LANG))

    def _(key):
        return trans[key]
except ImportError:
    import xbmcaddon

    def _(msgctxt):
        return xbmcaddon.Addon().getLocalizedString(msgctxt)
