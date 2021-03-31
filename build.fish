#!/usr/bin/env fish

argparse z/zip -- $argv

# Check for required dependencies
for cmd in poetry fd rg
    command -q $cmd
    if [ $status != 0 ]
        echo $cmd' command not found'
        exit 1
    end
end


set build_dir (mktemp -dt 'movix-build.XXXXXXX')

cp addon.xml default.py LICENSE.txt README.md $build_dir
cp -r resources $build_dir

pushd $build_dir
rm -rf resources/lib/translation
fd -tf '\.py[oc]$' -x rm
fd -td __pycache__ -x rm -rf

# Remove log calls
for file in (rg -l '\.log\(' -g '*.py')
    sed -i '/.log(/d' $file
end

popd
cp resources/lib/translation/__init__.py $build_dir/resources/lib/translation.py

# Generate strings.po
poetry run python gen_strings_po.py $build_dir >/dev/null

if [ $status = 0 ]
    cp -r $build_dir/resources/language resources
else
    echo 'Error occured while running gen_strings_po.py' >&2
    exit 1
end

# Create .zip
if set -q _flag_z
    set name plugin.video.movix
    set ver (rg -or '$1' '<addon.+version="(.+?)"' addon.xml)
    set tmp_dir (mktemp -dt 'movix-build.XXXXXXX')

    mv $build_dir $tmp_dir/$name
    pushd $tmp_dir
    zip -r $name-$ver.zip $name
    popd
    mv $tmp_dir/$name-$ver.zip .
    rm -rf $tmp_dir
else
    echo "Built in $build_dir"
end
