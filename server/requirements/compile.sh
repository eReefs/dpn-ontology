#!/bin/bash
#
# This script will update requirements/requirements.txt.
# Usage:
#
#     docker compose run --rm recom-api requirements/compile.sh
#
# Any arguments are passed on to `pip-compile`.
# You can upgrade a specific package by either
# updating its version in `requirements.in`,
# or using the `--upgrade-package` flag to `pip-compile`:
#
#     docker compose run --rm recom-api requirements/compile.sh \
#         --upgrade-package some-package==1.2.3
#
# You can update all packages including dependencies
# using the `--upgrade` flag:
#
#     docker compose run --rm recom-api requirements/compile.sh \
#         --upgrade
#
# See `pip-compile` documentation for detailed instructions:
# https://github.com/jazzband/pip-tools#example-usage-for-pip-compile

HERE="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" && pwd )"

export CUSTOM_COMPILE_COMMAND="$0"

if ! command -v pip-compile &>/dev/null ; then
	echo "Installing pip-tools"
	pip install pip-tools
fi

echo "Compiling requirements.in to requirements.txt"
pip-compile \
	"${HERE}/requirements.in" \
	--output-file "${HERE}/requirements.txt" \
	--annotation-style "split" \
	--strip-extras \
	"$@"
