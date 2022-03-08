#!/usr/bin/env bash

set -o nounset                              # Treat unset variables as an error

GREEN=$(printf "\e[0;49;32m")
GRAY=$(printf "\e[2;49;39m")
RESET=$(printf "\e[0m")
YELLOW=$(printf "\e[0;49;33m")
HELP="
Diffing modified key values of dconf database

${YELLOW}Usage:${RESET}
  $(basename "$0") [options]

${YELLOW}META OPTIONS
  ${GREEN}-h, --help       ${RESET}show this list of command-line options

${YELLOW}input/output OPTIONS
  ${GREEN}--input=${GRAY}INPUTFILE        ${RESET} input file of key/value pairs, defaults to
                            key/value pair from dconf database
  ${GREEN}--compare-to=${GRAY}COMPAREFILE  ${RESET}a file to be compared to ${GRAY}INPUTFILE${RESET}, defaults to
                            key/default value pair from dconf database
  ${GREEN}--output=${GRAY}OUTPUTFILE      ${RESET} output file, defaults to stdout
  ${GREEN}--quiet                   ${RESET}supress output to stdout, ${GREEN}--output${RESET} must be specified
  ${GREEN}--show-type               ${RESET}show key type
"

compare_to="dconf"
input="dconf"
output="stdout"
quiet="false"

for arg in "$@"; do
    case $arg in
        --compare-to=*)
            compare_to="${arg#*=}"
            shift
            ;;
        -h|--help)
            echo "$HELP"
            exit
            ;;
        --input=*)
            input="${arg#*=}"
            shift
            ;;
        --output=*)
            output="${arg#*=}"
            shift
            ;;
        --quiet)
            quiet="true"
            shift
            ;;
    esac
done

# shellcheck disable=SC2016
get_default='XDG_CONFIG_HOME=/tmp/ gsettings get $schema $key | tr "\n" " "'
if [ "$input" = "dconf" ] ; then
    get_schemas='gsettings list-schemas | sort'
    # shellcheck disable=SC2016
    get_keys='gsettings list-keys $schema | sort'
    # shellcheck disable=SC2016
    get_key_type='gsettings range $sckema $key | tr "\n" " "'
    # shellcheck disable=SC2016
    get_value='gsettings get $schema $key | tr "\n" " "'
else
    if [ -f "$input" ] ; then
        # shellcheck disable=SC2016
        get_schemas='awk -F" :: " '\''{print $1}'\'' "$input" | sort | uniq'
        # shellcheck disable=SC2016
        get_keys='awk -F" :: " '\''{if($1 == "'\''$schema'\''")print $2}'\'' "$input" | sort | uniq'
        # shellcheck disable=SC2016
        get_key_type='awk -F" :: " '\''{if($1 == "'\''$schema'\''" && $2 == "'\''$key'\''")print $3}'\'' "$input"'
        # shellcheck disable=SC2016
        get_value='awk -F" :: " '\''{if($1 == "'\''$schema'\''" && $2 == "'\''$key'\''")print $5}'\'' "$input"'
    else
        echo "File $input not found"
        exit 1
    fi
fi

# 

for schema in $("$get_schemas"); do
    for key in $("$get_keys"); do
        key_type=$("$get_key_type")
        default=$("$get_default")
        value=$("$get_value")
        if [ "$default" != "$value" ] ; then

            echo "$schema :: $key :: $key_type :: $default :: $value" 
        fi
    done
done
