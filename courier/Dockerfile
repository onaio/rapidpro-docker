FROM debian:bookworm-slim as build

ARG COURIER_REPO
ENV COURIER_REPO=${COURIER_REPO:-nyaruka/courier}
ARG COURIER_VERSION
ENV COURIER_VERSION=${COURIER_VERSION:-8.0.2}

RUN apt update && apt install -y wget
RUN TARGETARCH=$(dpkg --print-architecture) && \
  DOWNLOAD_URL="https://github.com/$COURIER_REPO/releases/download/v${COURIER_VERSION}/courier_${COURIER_VERSION}_linux_${TARGETARCH}.tar.gz" && \
  echo "Downloading courier Linux/$TARGETARCH v${COURIER_VERSION} from $COURIER_REPO URL: $DOWNLOAD_URL ..." && \
  wget -q -O courier.tar.gz "${DOWNLOAD_URL}"
RUN mkdir courier
RUN tar -xzC courier -f courier.tar.gz


FROM debian:bookworm-slim

RUN set -ex; \
    addgroup --system courier; \
    adduser --system --ingroup courier courier

# Install ca-certificates so HTTPS works in general
RUN apt-get update && \
  apt-get install -y --no-install-recommends ca-certificates && \
  rm -rf /var/lib/apt/lists/*

COPY --from=build courier/courier /usr/local/bin

EXPOSE 8080

RUN mkdir _storage && chown courier _storage
RUN mkdir /var/spool/courier && chown courier /var/spool/courier
USER courier

ENTRYPOINT []
CMD ["courier"]
