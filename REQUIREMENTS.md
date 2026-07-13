# Requirements

## Hardware

- **Architecture**: x86-64 (AMD64)
- **CPU**: 8+ cores recommended
- **RAM**: 32 GB recommended
- **Disk**: 100 GB free space

## Software

- **Operating System**: Linux (Ubuntu 20.04+), macOS 11+, or Windows 10/11 with WSL 2
- **Docker Desktop**: Version 20.10+
    - Download: https://www.docker.com/products/docker-desktop/
    - Ensure Docker Desktop is running before starting Dev Container
    - Recommended resources: 4+ CPU cores, 8GB+ RAM, 5GB+ Swap
- **Visual Studio Code**: Version 1.70+ with Dev Containers extension

## External Services

- **Anthropic API** (https://console.anthropic.com/)
  
- **OpenAI API** (https://platform.openai.com/)

## Machine-Readable Dependencies

See the following files for complete dependency specifications:
- `.devcontainer/Dockerfile` - Container image and system packages
- `.devcontainer/devcontainer.json` - Dev Container configuration
- `requirements.txt` - Python package dependencies
- `pyproject.toml` - Python project metadata
