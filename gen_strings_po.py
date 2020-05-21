#!/usr/bin/env python2

import shutil
import re
import os
import sys
import polib
from tempfile import mkstemp
from collections import OrderedDict

sys.tracebacklimit = 1

# NOTE: en_gb must be first, others not required
LANGS = ['en_gb', 'ru_ru']
trans = []
for lang in LANGS:
    module = __import__('resources.lib.translation.' + lang, fromlist=[lang])
    trans.append(getattr(module, lang))

OFFSET = 30000
DIR = os.path.join(os.getcwd(), sys.argv[1])
# en = trans.pop(0) and ordered
en = OrderedDict(((v[0], (i, v[1])) for i, v in enumerate(trans.pop(0))))
for idx, tran in enumerate(trans):
    trans[idx] = dict(tran)

# Find all .py files
pyfiles = []
for path, dirs, files in os.walk(DIR):
    fnames = filter(lambda f: f.endswith('.py'), files)
    fpaths = map(lambda f: os.path.join(path, f), fnames)
    pyfiles.extend(list(fpaths))

po_entries = {}
for lang in LANGS:
    po_entries[lang] = {}


def key_to_id(key):
    pair = en.get(key)
    if not pair:
        raise Exception("No translation entry for key '%s' in en_gb.py" % key)
    idx, msgid = en[key]
    num = OFFSET + idx
    msgid = msgid.decode('utf-8')
    po_entries['en_gb'][idx] = polib.POEntry(
        msgctxt='#%i' % num,
        msgid=msgid
    )
    for i, lang in enumerate(LANGS[1:]):
        msgstr = trans[i].get(key)
        if not msgstr:
            raise Exception("No translation entry for key '%s' in %s" % (key, lang + '.py'))
        po_entries[lang][idx] = polib.POEntry(
            msgctxt='#%i' % num,
            msgid=msgid,
            msgstr=msgstr.decode('utf-8')
        )
    return num


def repl_py(match):
    key = match.group(0)[3:-2]
    return '_(%i)' % key_to_id(key)


def repl_settings(match):
    key = match.group(0)[8:-1]
    return ' label="%i"' % key_to_id(key)


def patch_file(path, regex, repl):
    fin = open(path, 'r')
    dest = mkstemp()[1]
    fout = open(dest, 'w')
    for line in fin:
        out = re.sub(regex, repl, line)
        fout.write(out)
    fin.close()
    fout.close()
    shutil.move(dest, path)


for path in pyfiles:
    patch_file(path, r'_\((?:\'|").+?(?:\'|")\)', repl_py)

settings_path = os.path.join(DIR, 'resources/settings.xml')
patch_file(settings_path, r'\slabel="(.+?)"', repl_settings)

# Save strings.po for each language
for lang in LANGS:
    po = polib.POFile()
    po_data = po_entries[lang]
    for idx in range(0, len(po_data)):
        entry = po_data.get(idx)
        if not entry:
            raise Exception('Abandoned translation entry in %s at index %i' % (lang + '.py', idx))
        po.append(po_data[idx])
    po.save(os.path.join(DIR, 'resources/language/resource.language.%s/strings.po' % lang))
