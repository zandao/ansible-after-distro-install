#!/usr/bin/env bash

noto_font_directories=$(fc-list | grep -E '\/Noto[A-Z]' | awk -F '/Noto' '{$NF=""; print $0}' | sort | uniq | tr "\n" " ")

# shellcheck disable=SC2086
echo $noto_font_directories | xargs ls |
    awk -F '-' '{print $1}' |
    awk '{ gsub("/^NotoSerif|^NotoSans|^NotoColorEmoji.+|^NotoMusic.+|.+Symbols.*|.+Math.*|.+Gothic.+|Noto|Mono|CJK|Serif","");
           if ($0 ~ /^[A-Za-z]/) { print}}' |
    sort | uniq | tr "\n" " "
