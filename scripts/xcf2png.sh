#!/bin/bash
# Copyright (C) 2021 Alexandre Drummond
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
# Street, Fifth Floor, Boston, MA 02110-1301, USA. 

# Invoke The GIMP with Script-Fu convert-xcf-png
# No error checking.

if [ "$#" -lt 1 ]; then
  echo "Usage: $(basename "$0") gimpfile1.xcf ..."
  exit 1
fi
for image in "$@"; do
  if [ -f "$image" ] && [ "$image" != "${image%%.xcf}" ]; then
    {
      cat <<- EOF
	;;;; Don't remove tabs from this heredoc because of <<- usage
	(define (convert-xcf-png filename outpath)
	  (let* (
	          (image (car (gimp-xcf-load RUN-NONINTERACTIVE filename filename )))
	          (drawable (car (gimp-image-merge-visible-layers image CLIP-TO-IMAGE)))
	        )
	    (begin (display "Exporting ")(display filename)(display " -> ")(display outpath)(newline))
	    (file-png-save2 RUN-NONINTERACTIVE image drawable outpath outpath 0 9 0 0 0 0 0 0 0)
	    (gimp-image-delete image)
	  )
	)
	
	(gimp-message-set-handler 1) ; Messages to standard output
	EOF
      echo "(convert-xcf-png \"$image\" \"${image%%.xcf}.png\")"
      echo "(gimp-quit 0)"
    } | gimp --no-data -i -b -

    copyrights=$(git log --pretty=format:"%an %ad" --date=short packages.yml |
                 awk 'match($0, /^(.*) ([0-9]{4})-.*$/, a) { print a[1] ":" a[2] }' | sort |
                 awk -F: '!a[$1]++ { print "©" $2 " " $1  }' | grep -v "©2021 Alexandre Drummond")
    authors=$(git log --pretty=format:'%an' | sort | uniq | sed -z 's/\n/, /g;s/, $/\n/')
    exiftool -CaptionWriter="Alexandre Drummond" \
        -CopyrightNotice="©2021$([ $(date '+%Y') -eq 2021 ] || date '+-%Y') Alexandre Drummond based on ©2019 Wayne Dowsent original work" \
        -Creator="Alexandre Drummond" \
        -Description="This is a derivative work based on art \"The good, the bad & the ugly\" by Wayne Dowsent that can be viewed in his site https://www.waynedowsent.com.au, his Youtube channel https://www.youtube.com/user/WayneDowsentArt, his Instagram @waynedowsent and his twitter @waynedowsentart" \
        -Rights="©2021$([ $(date '+%Y') -eq 2021 ] || date '+-%Y') Alexandre Drummond, all rights reserved" \
        -UsageTerms="This work is lincensed under Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) <https://creativecommons.org/licenses/by-nc-sa/4.0/>" \
        -Title="$(echo $image | awk -F. '{ sub(/^.*\//, "", $1); sub(/-/, " ", $1); sub(/_/, " ", $1); print $1 }')" \
        -Author="$authors" \
        "${image%%.xcf}.png"
    if [ $? -eq 0 ]; then
      echo $image converted to ${image%%.xcf}.png
    fi
  else
    echo "$image not a Gimp file"
  fi
done
