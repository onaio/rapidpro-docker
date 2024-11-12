FROM debian:bookworm-slim as build

ARG RP_ARCHIVER_REPO
ENV RP_ARCHIVER_REPO=${RP_ARCHIVER_REPO:-nyaruka/rp-archiver}
ARG RP_ARCHIVER_VERSION
ENV RP_ARCHIVER_VERSION=${RP_ARCHIVER_VERSION:-8.0.0}

RUN apt update && apt install -y wget
RUN TARGETARCH=$(dpkg --print-architecture) && \
  DOWNLOAD_URL="https://github.com/$RP_ARCHIVER_REPO/releases/download/v${RP_ARCHIVER_VERSION}/rp-archiver_${RP_ARCHIVER_VERSION}_linux_${TARGETARCH}.tar.gz" && \
  echo "Downloading rp-archiver Linux/$TARGETARCH v${RP_ARCHIVER_VERSION} from $RP_ARCHIVER_REPO URL: $DOWNLOAD_URL ..." && \
  wget -q -O rp-archiver.tar.gz "${DOWNLOAD_URL}"
RUN mkdir rp-archiver
RUN tar -xzC rp-archiver -f rp-archiver.tar.gz


FROM debian:bookworm-slim

RUN set -ex; \
    addgroup --system rp-archiver; \
    adduser --system --ingroup rp-archiver rp-archiver

# Install ca-certificates so HTTPS works in general
RUN apt-get update && \
  apt-get install -y --no-install-recommends ca-certificates && \
  rm -rf /var/lib/apt/lists/*

COPY --from=build rp-archiver/rp-archiver /usr/local/bin

RUN mkdir _storage && chown rp-archiver _storage
RUN mkdir /var/spool/rp-archiver && chown rp-archiver /var/spool/rp-archiver
USER rp-archiver

ENTRYPOINT []
CMD ["rp-archiver"]