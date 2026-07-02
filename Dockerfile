FROM php:8.2-apache

# Install libcurl
RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    && docker-php-ext-install curl

# Matikan mpm_event, aktifkan mpm_prefork (biar ga error AH00534)
RUN a2dismod mpm_event && a2enmod mpm_prefork

# Copy semua file ke webroot
COPY . /var/www/html/

# Copy entrypoint dan beri izin eksekusi
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port 8080 (Railway default)
EXPOSE 8080

# Jalankan entrypoint
ENTRYPOINT ["/entrypoint.sh"]
