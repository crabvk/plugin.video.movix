#!/usr/bin/env fish

# Check for required dependencies
for cmd in poetry fd rg
    command -q $cmd
    if [ $status != 0 ]
        echo $cmd' command not found'
        exit 1
    end
end

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

# Search for logs in python code
if not contains -- $argv '--ignore-log'
    rg '\.log\('
    if [ $status = 0 ]
        echo -e '\n^^^ The build can\'t contain log calls ^^^'
        exit 1
    end
end

cd ..
cp resources/lib/translation/__init__.py build/resources/lib/translation.py

# Generate strings.po
poetry run python gen_strings_po.py build >/dev/null
if [ $status = 0 ]
    cp -r build/resources/language resources
end

# Create .zip
if contains -- $argv '--zip'
    set name plugin.video.movix
    set ver (rg -or '$1' '<addon.+version="(.+?)"' addon.xml)
    fd -d1 "$name\-[\d\.]+\.zip" -x rm
    mv build $name
    zip $name-$ver.zip -r $name
    mv $name build
end
