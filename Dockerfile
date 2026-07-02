FROM php:8.2-apache

# Install dependencies & clean up
RUN apt-get update && \
    apt-get install -y libcurl4-openssl-dev && \
    docker-php-ext-install curl && \
    rm -rf /var/lib/apt/lists/*

# Fix: Hapus semua konfigurasi MPM sebelum enable prefork
RUN rm -f /etc/apache2/mods-enabled/mpm_*.load && \
    a2enmod mpm_prefork

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY index.php /var/www/html/

ENV PORT=80
ENTRYPOINT ["/entrypoint.sh"]
CMD ["apache2-foreground"]
