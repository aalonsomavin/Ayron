#!/bin/bash
set -e

if [ "$1" = "python" ] && [ "$2" = "manage.py" ]; then
    python manage.py migrate --noinput
fi

exec "$@"
