ARG BASE_IMAGE="debian:trixie-20260610"
FROM ${BASE_IMAGE}

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Enable apt-get cache, see https://stackoverflow.com/a/79936062/14142236
RUN [ -f "/etc/apt/apt.conf.d/docker-clean" ] && \
    mv /etc/apt/apt.conf.d/docker-clean /etc/apt/apt.conf.d/docker-clean.disabled

RUN --mount=type=cache,target=/var/cache/apt \
\
    apt-get update -y --allow-releaseinfo-change && \
    apt-get install -y \
        zsh \
        python3 \
        python3-pip \
        python3-venv

# We have to disable XON/XOFF, due to Ctrl-Q bind
RUN echo "stty -ixon\nsource /data/zsh_favorite_dir.zsh\n" >> ~/.zshrc

ENTRYPOINT "/bin/zsh"
