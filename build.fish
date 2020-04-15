#!/usr/bin/env fish
# Dependencies: poetry, fd, ripgrep, zip

rm -rf build/
mkdir build

cp addon.xml default.py LICENSE.txt README.md build
cp -r resources build

cd build
rm -rf resources/lib/translation
for f in (fd -tf '.*\.py[c|o]$')
    rm $f
end
for d in (fd -td '__pycache__')
    rm -rf $d
end
cd ..
cp resources/lib/translation/__init__.py build/resources/lib/translation.py

poetry run python2 gen_strings_po.py build >/dev/null
if [ $status = 0 ]
    cp -r build/resources/language resources
end

if [ "$argv[1]" = "--zip" ]
    set name plugin.video.movix
    set ver (rg -or '$1' '<addon.+version="(.+?)"' addon.xml)
    mv build $name
    zip $name-$ver.zip -r $name
    mv $name build
end
