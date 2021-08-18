#!/usr/bin/bash

gunicorn --access-logfile "instance/server.log" wsgi:app
