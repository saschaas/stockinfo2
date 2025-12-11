# Deployment Guide

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
