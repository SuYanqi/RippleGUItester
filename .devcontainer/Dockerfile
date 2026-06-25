# RippleGUItester Dev Container
# Based on Microsoft's official Python dev container base image

FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

# -----------------------------------------------------------------------------
#  Fix yarn signature issue, open bug with microsoft images
#   https://github.com/devcontainers/images/issues/1752
# -----------------------------------------------------------------------------
RUN curl -fsSL https://dl.yarnpkg.com/debian/pubkey.gpg \
  | sudo gpg \
        --batch \
        --yes \
        --dearmor \
        -o /usr/share/keyrings/yarn-archive-keyring.gpg

# -----------------------------------------------------------------------------
#  Install Xvfb for virtual display (required for GUI testing)
# -----------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    xvfb \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*
