# Stage 1: Builder
FROM python:3.10-slim-bookworm as builder

# Set up environment variables
ENV PIP_RETRIES=120 \
    PIP_TIMEOUT=400 \
    PIP_DEFAULT_TIMEOUT=400 \
    C_FORCE_ROOT=1

# Install system and build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    tar \
    build-essential \
    postgresql-client \
    libmagic-dev \
    libpcre3 \
    libgeos-c1v5 \
    libgdal32 \
    libproj25 \
    libffi-dev \
    libssl-dev \
    npm \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /rapidpro

# Set default values for build-time variables
ARG RAPIDPRO_VERSION=master
ARG RAPIDPRO_REPO=rapidpro/rapidpro

# Download and unpack RapidPro
RUN echo "Downloading RapidPro ${RAPIDPRO_VERSION} from https://github.com/${RAPIDPRO_REPO}/archive/${RAPIDPRO_VERSION}.tar.gz" && \
    wget -O rapidpro.tar.gz "https://github.com/${RAPIDPRO_REPO}/archive/${RAPIDPRO_VERSION}.tar.gz" && \
    tar -xf rapidpro.tar.gz --strip-components=1 && \
    rm rapidpro.tar.gz

# Build Python virtual environment
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"
ENV VIRTUAL_ENV="/venv"

# Install pip and poetry within the virtual environment
RUN /venv/bin/pip install -U pip && /venv/bin/pip install -U poetry

# Install npm dependencies
RUN npm install -g yarn

# Install Python dependencies using poetry
RUN poetry install --no-interaction -vvv

# Install yarn dependencies
RUN yarn install
RUN yarn global add less

# Stage 2: Final Image
FROM python:3.10-slim-bookworm

# Create a non-root user and group
RUN groupadd -g 1000 rapidpro && useradd -r -u 1000 -g rapidpro rapidpro

# Create necessary directories with correct permissions
RUN mkdir -p /rapidpro /venv && chown -R rapidpro:rapidpro /rapidpro /venv

# Copy application code and virtual environment from the builder stage
COPY --from=builder /rapidpro /rapidpro
COPY --from=builder /venv /venv
COPY --from=builder /usr/bin/node /usr/bin/
COPY --from=builder /usr/bin/npm /usr/bin/

# Set permissions for the startup script
COPY stack/startup.sh /
RUN chmod +x /startup.sh && chown rapidpro:rapidpro /startup.sh

# Set ownership to the non-root user
RUN chown -R rapidpro:rapidpro /rapidpro /venv

# Switch to the non-root user
USER rapidpro

ENV PATH="/venv/bin:$PATH:/usr/bin"
ENV VIRTUAL_ENV="/venv"

WORKDIR /rapidpro

# Configure uWSGI
ENV UWSGI_VIRTUALENV=/venv UWSGI_WSGI_FILE=temba/wsgi.py UWSGI_HTTP=:8000 UWSGI_MASTER=1 UWSGI_WORKERS=8 UWSGI_HARAKIRI=20
ENV STARTUP_CMD="/venv/bin/uwsgi --http-auto-chunked --http-keepalive"

# Configure application settings
COPY settings.py /rapidpro/temba/
COPY stack/500.html /rapidpro/templates/
COPY stack/init_db.sql /rapidpro/
COPY stack/clear-compressor-cache.py /rapidpro/

# Expose the port uWSGI will listen on
EXPOSE 8000

# Set metadata labels
LABEL org.label-schema.name="RapidPro" \
      org.label-schema.description="RapidPro allows organizations to visually build scalable interactive messaging applications." \
      org.label-schema.url="https://www.rapidpro.io/" \
      org.label-schema.vcs-url="https://github.com/${RAPIDPRO_REPO}" \
      org.label-schema.vendor="Nyaruka, UNICEF, and individual contributors." \
      org.label-schema.version=${RAPIDPRO_VERSION} \
      org.label-schema.schema-version="1.0"

# Set the default command to run the application
CMD ["/startup.sh"]