FROM python:3.10.16-slim-bookworm AS builder

ENV PIP_RETRIES=120 \
    PIP_TIMEOUT=400 \
    PIP_DEFAULT_TIMEOUT=400 \
    C_FORCE_ROOT=1

RUN apt update && apt install -y wget tar build-essential git

WORKDIR /rapidpro

ARG RAPIDPRO_VERSION
ARG RAPIDPRO_REPO
ENV RAPIDPRO_VERSION=${RAPIDPRO_VERSION:-master}
ENV RAPIDPRO_REPO=${RAPIDPRO_REPO:-rapidpro/rapidpro}
RUN echo "Downloading RapidPro ${RAPIDPRO_VERSION} from https://github.com/$RAPIDPRO_REPO/archive/${RAPIDPRO_VERSION}.tar.gz" && \
    wget -O rapidpro.tar.gz "https://github.com/$RAPIDPRO_REPO/archive/${RAPIDPRO_VERSION}.tar.gz" && \
    tar -xf rapidpro.tar.gz --strip-components=1 && \
    rm rapidpro.tar.gz

RUN pip install -U pip && pip install -U poetry packaging

# Build Python virtualenv
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"
ENV VIRTUAL_ENV="/venv"

# Install configuration related dependencies
RUN /venv/bin/pip install --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --trusted-host pypi.org --upgrade pip && \
/venv/bin/pip install --no-cache-dir \
"django-getenv==1.3.2" \
"django-cache-url==3.2.3" \
"uwsgi==2.0.22" \
"whitenoise==5.3.0" \
"flower==1.2.0" \
"sentry-sdk==2.5.1" \
"regex==2023.10.3"

RUN poetry install --no-interaction --no-ansi --only main

# Install the Ona OIDC pip package.
ARG OIDC_VERSION=v2.6.0
ENV OIDC_VERSION=${OIDC_VERSION:-v2.6.0}
RUN /venv/bin/pip install "Django>=4.2,<5" -e "git+https://github.com/onaio/ona-oidc.git@${OIDC_VERSION}#egg=ona-oidc"

# ona-oidc v2.6.0 still calls the old RapidPro user.get_settings() helper.
# RapidPro v9 stores this as temba.orgs.models.UserSettings instead.
RUN sed -i 's/user_settings = user.get_settings()/from temba.orgs.models import UserSettings\n        user_settings, _ = UserSettings.objects.get_or_create(user=user)/' \
    /venv/src/ona-oidc/oidc/viewsets.py

FROM node:20-bookworm-slim AS frontend

WORKDIR /rapidpro

COPY --from=builder /rapidpro /rapidpro

RUN corepack enable && \
    yarn install --frozen-lockfile && \
    npm install -g less

FROM python:3.10.16-slim-bookworm

ARG RAPIDPRO_VERSION
ARG RAPIDPRO_REPO
ENV RAPIDPRO_VERSION=${RAPIDPRO_VERSION:-master}
ENV RAPIDPRO_REPO=${RAPIDPRO_REPO:-rapidpro/rapidpro}

# Copy rapidpro and venv from builder
COPY --from=builder /rapidpro /rapidpro
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"
ENV VIRTUAL_ENV="/venv"

# Install `psql` for `manage.py dbshell`
# `magic` is needed since rapidpro v3.0.64
# `pcre` is needed for uwsgi
# `geos`, `gdal`, and `proj` are needed for `manage.py download_geojson` and `manage.py import_geojson`
# `node` and `lessc` are copied from the frontend stage for static compression
RUN apt-get update -q && \
    apt-get install -y --no-install-recommends \
        postgresql-client \
        libmagic-dev \
        libpcre3 \
        libgeos-dev \
        libgdal-dev \
        libproj-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /rapidpro

COPY --from=frontend /rapidpro/node_modules /rapidpro/node_modules
COPY --from=frontend /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules/less/bin/lessc /usr/local/bin/lessc

ENV UWSGI_VIRTUALENV=/venv UWSGI_WSGI_FILE=temba/wsgi.py UWSGI_HTTP=:8000 UWSGI_MASTER=1 UWSGI_WORKERS=8 UWSGI_HARAKIRI=20
# Enable HTTP 1.1 Keep Alive options for uWSGI (http-auto-chunked needed when ConditionalGetMiddleware not installed)
# These options don't appear to be configurable via environment variables, so pass them in here instead
ENV STARTUP_CMD="/venv/bin/uwsgi --http-auto-chunked --http-keepalive"

COPY settings.py /rapidpro/temba/
COPY patches/omnibox.py /rapidpro/temba/contacts/search/omnibox.py
COPY patches/apply-oidc-logout-menu.py /tmp/apply-oidc-logout-menu.py
RUN /venv/bin/python /tmp/apply-oidc-logout-menu.py && rm /tmp/apply-oidc-logout-menu.py
COPY patches/apply-oidc-logout-session-hardening.py /tmp/apply-oidc-logout-session-hardening.py
RUN /venv/bin/python /tmp/apply-oidc-logout-session-hardening.py && rm /tmp/apply-oidc-logout-session-hardening.py
COPY patches/apply-oidc-rp-initiated-logout.py /tmp/apply-oidc-rp-initiated-logout.py
RUN /venv/bin/python /tmp/apply-oidc-rp-initiated-logout.py && rm /tmp/apply-oidc-rp-initiated-logout.py
# 500.html needed to keep the missing template from causing an exception during error handling
COPY stack/500.html /rapidpro/templates/
COPY stack/init_db.sql /rapidpro/
COPY stack/clear-compressor-cache.py /rapidpro/

EXPOSE 8000
COPY stack/startup.sh /

# Drop privileges — run as a non-root user (uid 1000) with a real $HOME and
# no login shell. uid 1000 is what Kubernetes' restricted Pod Security
# Standard expects (runAsUser >= 1000) so the container's UID does not
# overlap with privileged host system accounts.
RUN groupadd -g 1000 rapidpro && \
    useradd -m -u 1000 -g rapidpro -s /sbin/nologin rapidpro && \
    chmod +x /startup.sh && \
    chown rapidpro:rapidpro /startup.sh && \
    chown -R rapidpro:rapidpro /rapidpro /venv
USER rapidpro

LABEL org.label-schema.name="RapidPro" \
      org.label-schema.description="RapidPro allows organizations to visually build scalable interactive messaging applications." \
      org.label-schema.url="https://www.rapidpro.io/" \
      org.label-schema.vcs-url="https://github.com/$RAPIDPRO_REPO" \
      org.label-schema.vendor="Nyaruka, UNICEF, and individual contributors." \
      org.label-schema.version=$RAPIDPRO_VERSION \
      org.label-schema.schema-version="1.0"

CMD ["/startup.sh"]
