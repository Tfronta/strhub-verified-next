# Evaluator carrier: strhub-documented-install/1; not an upstream Dockerfile.
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN ["bash", "-c", "echo 'APT::Get::Assume-Yes \"true\";' > /etc/apt/apt.conf.d/90strhub && apt-get update"]
COPY [".", "/opt/tool"]
WORKDIR /opt/tool
RUN ["bash", "-lc", "set -eo pipefail\napt install make g++ zlib1g-dev libhts-dev libbz2-dev liblzma-dev\nmake\n"]
ENTRYPOINT ["/bin/bash", "-lc"]
