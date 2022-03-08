#!/bin/bash -
#   DESCRIPTION: Installs remote binaries using blindspot format
#        AUTHOR: Alexandre "Zandao" Drummond (),

set -o nounset # Treat unset variables as an error

echo "$0"

eval "$(grep -e '^export GITHUB_TOKEN=' ~/.zshrc)"

eval "$(dirname "$0")/blindspot_installer.py"
