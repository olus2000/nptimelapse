#!/usr/bin/bash

gunicorn --access-logfile "instance/server.log" --timeout 3600 -w 2 wsgi:app
