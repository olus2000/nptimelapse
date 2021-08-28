#!/usr/bin/bash

if [ $# -lt 1 ]
then
    port=8000
else
    port=$1
fi

celery -A nptimelapse.tasks worker --loglevel=INFO --concurrency=1 &
gunicorn -b "localhost:$port" --access-logfile "instance/server.log" --timeout 3600 -w 2 wsgi:app
