FROM python:3.11-slim
WORKDIR /app

# Install system dependencies and pygame
RUN apt-get update && \
    apt-get install -y python3-pygame && \
    rm -rf /var/lib/apt/lists/*

# Install pygame via pip as well (to ensure latest version)
RUN python3 -m pip install pygame

# Copy your application files
COPY *.py ./
COPY assets/ ./assets/

# Set the DISPLAY environment variable for X11 forwarding
ENV DISPLAY=host.docker.internal:0.0
ENV SDL_AUDIODRIVER=dummy  
# This disables audio
ENV PULSE_SERVER=unix:/dev/null  
# Disable pulseaudio

# Run your main.py file directly (not as a module)
CMD ["/usr/local/bin/python3", "main.py"]