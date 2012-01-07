#!/bin/bash

python manage.py runfcgi host=127.0.0.1 port=8001 daemonize=false
