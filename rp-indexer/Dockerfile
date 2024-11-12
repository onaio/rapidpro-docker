FROM debian:bookworm-slim as build

ARG RP_INDEXER_REPO
ENV RP_INDEXER_REPO=${RP_INDEXER_REPO:-nyaruka/rp-indexer}
ARG RP_INDEXER_VERSION
ENV RP_INDEXER_VERSION=${RP_INDEXER_VERSION:-8.0.0}

RUN apt update && apt install -y wget
RUN TARGETARCH=$(dpkg --print-architecture) && \
  DOWNLOAD_URL="https://github.com/$RP_INDEXER_REPO/releases/download/v${RP_INDEXER_VERSION}/rp-indexer_${RP_INDEXER_VERSION}_linux_${TARGETARCH}.tar.gz" && \
  echo "Downloading rp-indexer Linux/$TARGETARCH v${RP_INDEXER_VERSION} from $RP_INDEXER_REPO URL: $DOWNLOAD_URL ..." && \
  wget -q -O rp-indexer.tar.gz "${DOWNLOAD_URL}"
RUN mkdir rp-indexer
RUN tar -xzC rp-indexer -f rp-indexer.tar.gz


FROM debian:bookworm-slim

RUN set -ex; \
    addgroup --system rp-indexer; \
    adduser --system --ingroup rp-indexer rp-indexer

# Install ca-certificates so HTTPS works in general
RUN apt-get update && \
  apt-get install -y --no-install-recommends ca-certificates && \
  rm -rf /var/lib/apt/lists/*

COPY --from=build rp-indexer/rp-indexer /usr/local/bin

RUN mkdir _storage && chown rp-indexer _storage
RUN mkdir /var/spool/rp-indexer && chown rp-indexer /var/spool/rp-indexer
USER rp-indexer

ENTRYPOINT []
CMD ["rp-indexer"]