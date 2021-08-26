#!/usr/bin/bash

celery -A nptimelapse.tasks worker --loglevel=INFO &
gunicorn --access-logfile "instance/server.log" --timeout 3600 -w 2 wsgi:app
