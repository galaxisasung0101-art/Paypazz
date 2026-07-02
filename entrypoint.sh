#!/bin/bash
# Ambil port dari environment Railway (PORT), default 8080
if [ -z "$PORT" ]; then
    PORT=8080
fi

# Ganti port di konfigurasi Apache
sed -i "s/Listen 80/Listen $PORT/" /etc/apache2/ports.conf
sed -i "s/:80/:$PORT/" /etc/apache2/sites-available/000-default.conf

# Jalankan Apache
apache2-foreground
