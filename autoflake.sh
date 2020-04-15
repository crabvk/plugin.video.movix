#!/usr/bin/env bash
poetry run autoflake -r --remove-all-unused-imports --remove-unused-variables "$@" *
