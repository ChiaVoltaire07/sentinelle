FROM postgis/postgis:16-3.4

# Installer les dépendances pour compiler pgvector
RUN apt-get update && apt-get install -y \
    postgresql-server-dev-16 \
    git \
    make \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Cloner et compiler pgvector
RUN git clone --branch v0.7.4 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make \
    && make install \
    && rm -rf /tmp/pgvector
