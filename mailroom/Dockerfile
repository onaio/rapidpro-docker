## Dockerfile to build a multi-architecture mailroom image by downloading the mailroom go binary from the mailroom GitHub repository, and copying it to the /usr/local/bin directory in the final image.
FROM debian:bookworm-slim as build

    ARG MAILROOM_REPO
    ENV MAILROOM_REPO ${MAILROOM_REPO:-nyaruka/mailroom}
    ARG MAILROOM_VERSION
    ENV MAILROOM_VERSION ${MAILROOM_VERSION:-9.0.1}

    RUN apt update && apt install -y wget

    # Determine the target architecture and download the mailroom binary from the mailroom GitHub repository
    RUN TARGETARCH=$(dpkg --print-architecture) && \
    DOWNLOAD_URL="https://github.com/${MAILROOM_REPO}/releases/download/v${MAILROOM_VERSION}/mailroom_${MAILROOM_VERSION}_linux_${TARGETARCH}.tar.gz" && \
    echo "Downloading mailroom Linux/$TARGETARCH v${MAILROOM_VERSION} from $MAILROOM_REPO URL: $DOWNLOAD_URL ..." && \
    wget -q -O mailroom.tar.gz "${DOWNLOAD_URL}"
    RUN mkdir mailroom
    RUN tar -xzC mailroom -f mailroom.tar.gz

    FROM debian:bookworm-slim

    RUN set -ex; \
        addgroup --system mailroom; \
        adduser --system --ingroup mailroom mailroom

    RUN apt-get update && \
        apt-get install -y --no-install-recommends ca-certificates && \
        rm -rf /var/lib/apt/lists/*

    COPY --from=build mailroom/mailroom /usr/local/bin
    COPY --from=build mailroom/docs /docs

    EXPOSE 8090

    RUN mkdir _storage && chown mailroom _storage
    USER mailroom

    ENTRYPOINT []
    CMD ["mailroom"]
