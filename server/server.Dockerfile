####################
### SERVER IMAGE ###
####################

FROM gitpod/workspace-python-3.12:latest

### SET ENVIRONMENT
USER root
RUN mkdir -p /workspace/redis-agent/
WORKDIR /workspace/redis-agent/

### INSTALL DEPENDENCIES
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    cowsay \
    tmux \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/*

### COPY CONTENTS
COPY . /workspace/redis-agent/

### PERMISSIONS
RUN chown -R gitpod:gitpod /workspace
USER gitpod

### INSTALL PYTHON DEPENDENCIES
RUN pip install --upgrade pip && \
    python3 -m pip install -U -r /workspace/redis-agent/requirements.txt && \
    rm /workspace/redis-agent/requirements.txt

EXPOSE 8888
EXPOSE 5000

### START THE ENGINE
CMD ["python", "main.py"]
# CMD ["/bin/sh", "-c", "bash"]

########################
########################
################################################
