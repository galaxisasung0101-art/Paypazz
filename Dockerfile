FROM python:3.11-slim

# Install dependensi sistem + sqlmap dari git
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git /opt/sqlmap && \
    ln -s /opt/sqlmap/sqlmap.py /usr/local/bin/sqlmap && \
    chmod +x /usr/local/bin/sqlmap && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency dulu supaya caching oke
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua file proyek
COPY . .

CMD ["python", "bot.py"]