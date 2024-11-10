FROM debian:11-slim AS base

# Set environment variables
ENV EXTENSION_ID=lgmpfmgeabnnlemejacfljbmonaomfmm
ENV EXTENSION_URL='https://app.nodepay.ai/'
ENV GIT_USERNAME=sryze
ENV GIT_REPO=crx-dl

RUN set -e && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        curl \
        wget \
        git \
        chromium \
        chromium-driver \
        python3 \
        python3-pip \
        python3-requests \
        python3-selenium \
        coreutils \
        bash && \
    apt-get autoremove --purge -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install distro

# Copy the Python script
FROM base
COPY main.py .
COPY start.sh .

# proxy tunnel https://github.com/ginuerzh/gost
COPY --from=ginuerzh/gost /bin/gost /bin

# Run the Python script
ENTRYPOINT [ "bash", "start.sh" ]