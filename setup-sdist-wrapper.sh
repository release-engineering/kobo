#!/bin/sh

# Running $ python setup.py sdist on an unclean directory
# may lead to including extra files in a tarball.
# This script makes a clean git export to make sure
# the tarball always matches git content.

set -x
set -e

# get git repo dir
git_repo=$(dirname $(readlink -f $0))
# get git branch
git_branch=$(git rev-parse --abbrev-ref HEAD)

current_dir=$(pwd)
tmp_dir=$(mktemp -d)

cd "$tmp_dir"

# make a clean copy of git content
git archive --remote="$git_repo" "$git_branch" | tar xf -

# create tarball
python setup.py sdist

# copy tarball to current dir
cp dist/* "$current_dir"

rm -rf "$tmp_dir"
