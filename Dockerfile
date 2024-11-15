# Stage 1: Builder
FROM python:3.10-bookworm as builder

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
    gettext \
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
RUN /venv/bin/pip install -U pip && /venv/bin/pip install -U poetry packaging

# Install npm dependencies
RUN npm install -g less && npm install

# Install Python dependencies using poetry
RUN poetry install --no-interaction -vv

RUN /venv/bin/pip install "django-getenv==1.3.2" \
    "django-cache-url==3.2.3" \
    "uwsgi==2.0.20" \
    "whitenoise==5.3.0" \
    "flower==1.0.0" \
    "sentry-sdk==2.5.1"
# Set permissions for the startup script
COPY stack/startup.sh /

# Create a non-root user and group
RUN groupadd -g 1000 rapidpro && useradd -r -u 1000 -g rapidpro rapidpro

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

