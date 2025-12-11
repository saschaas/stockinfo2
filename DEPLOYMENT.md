# Deployment Guide

## Quick Start

After starting the application with `docker-compose up -d`, access it at:

**Frontend**: http://localhost:8080
**Backend API**: http://localhost:8000
**Dagster UI**: http://localhost:3001

## GPU vs CPU Setup

The application uses Ollama for AI inference, which can run on either GPU or CPU.

### CPU-Only Systems (Default)

The default `docker-compose.yml` is configured for CPU-only systems. Simply run:

```bash
docker-compose up -d
```

**Note**: Ollama will run on CPU, which is slower but works on any system.

### GPU-Accelerated Systems (NVIDIA)

If you have an NVIDIA GPU and want GPU acceleration:

#### Prerequisites
1. NVIDIA GPU with CUDA support
2. NVIDIA drivers installed
3. NVIDIA Container Toolkit installed ([Installation Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html))

#### Enable GPU Support

Edit `docker-compose.yml` and uncomment the GPU configuration (lines 50-56):

```yaml
ollama:
  # ... other config ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

Then start the services:

```bash
docker-compose up -d
```

#### Verify GPU is Being Used

```bash
# Check if Ollama container can see GPU
docker exec stockinfo-ollama nvidia-smi

# Check Ollama logs
docker logs stockinfo-ollama
```

### Performance Comparison

- **CPU**: Slower inference (~5-30 seconds per analysis)
- **GPU**: Faster inference (~1-5 seconds per analysis)

Both configurations produce identical results; GPU just runs faster.

## Troubleshooting

### Error: "could not select device driver nvidia with capabilities: [[gpu]]"

**Cause**: Docker cannot access NVIDIA GPU (GPU not present or nvidia-container-toolkit not installed)

**Solution**: Use CPU-only mode (default configuration with GPU settings commented out)

### Error: "net.ipv4.ip_unprivileged_port_start: permission denied"

**Cause 1**: Trying to bind to privileged port (< 1024) without sufficient permissions

**Solution**: The default configuration now uses port 8080 instead of port 80. Access the frontend at http://localhost:8080

If you need to use port 80 (requires root/sudo):
1. Run Docker with elevated privileges, OR
2. Set up a reverse proxy (nginx/caddy) that runs on port 80 and forwards to 8080

**Cause 2**: Docker security restrictions (AppArmor/SELinux) preventing sysctl modifications during network namespace creation

**Solution**: Use the provided `docker-compose.override.yml` file which uses host networking mode to bypass these restrictions:

```bash
# The override file is automatically used by docker-compose
docker-compose up -d
```

The `docker-compose.override.yml` file adds these settings to all services:
- `network_mode: host` - **Uses host networking (bypasses network namespaces entirely)**
- `security_opt: [apparmor=unconfined, seccomp=unconfined]` - Disables AppArmor and seccomp
- `userns_mode: host` - Uses host user namespace

**Important**: With host networking mode:
- All services bind directly to the host's network interfaces
- Services are accessible on their respective ports: postgres (5432), redis (6379), ollama (11434), backend (8000), frontend (8080), dagster (3001)
- Container-to-container communication works via `localhost` instead of service names
- The application is pre-configured to work with both modes (it connects to localhost by default)

**Note**: These settings significantly reduce container isolation but are necessary on systems with strict security policies. Only use on trusted development/internal servers.

### Ollama Not Responding

```bash
# Restart Ollama
docker-compose restart ollama

# Check logs
docker logs stockinfo-ollama --tail 50

# Verify Ollama is accessible
curl http://localhost:11434/api/tags
```

### Pull Ollama Model Manually

```bash
# Enter Ollama container
docker exec -it stockinfo-ollama bash

# Pull the model
ollama pull llama3.2

# Or pull mistral
ollama pull mistral:7b
```
