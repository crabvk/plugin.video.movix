build:
    @./build.fish

release:
    @./build.fish -z

autoflake:
    @poetry run autoflake -r \
        --remove-all-unused-imports \
        --remove-unused-variables \
        --remove-duplicate-keys \
        --exclude default.py \
        .

set-version version:
    @sed -ri 's/(<addon.+version=)"[^"]+?"/\1"{{version}}"/' addon.xml
    @sed -ri 's/(version = )".+?"/\1"{{version}}"/' pyproject.toml

test:
    poetry run pytest tests/test_{router,utils}.py

test-api username password region='perm':
    poetry run pytest tests/test_api.py --credentials {{username}},{{password}},{{region}}

lint *args:
    fd -tf '\.py$' \
        -E en_gb.py \
        -E ru_ru.py \
        -E conftest.py \
        -x poetry run pylint -f colorized {{args}}
