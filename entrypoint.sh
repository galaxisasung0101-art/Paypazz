#!/bin/bash
if [ -n "$PORT" ]; then
    sed -i "s/80/${PORT}/g" /etc/apache2/sites-available/000-default.conf /etc/apache2/ports.conf
fi

# Cek config biar gak crash lagi
apache2ctl -t

exec "$@"
