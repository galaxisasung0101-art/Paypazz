#!/bin/bash
if [ -z "$PORT" ]; then
    PORT=8080
fi

sed -i "s/Listen 80/Listen $PORT/" /etc/apache2/ports.conf
sed -i "s/:80/:$PORT/" /etc/apache2/sites-available/000-default.conf

apache2-foreground
