#!/bin/bash

rsync -auvc --delete  --exclude="*.sock" --exclude="*.pyc" --exclude=".git" --exclude=".idea" \
--exclude=".elasticbeanstalk" --exclude=".gitignore" ./ flo@rtfcal.de:~/rtfcal/
