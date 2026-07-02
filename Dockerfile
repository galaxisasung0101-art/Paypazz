FROM php:8.2-apache

# Install libcurl dan dependencies lain
RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    && docker-php-ext-install curl

COPY . /var/www/html/

EXPOSE 80
