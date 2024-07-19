#!/bin/bash

#########################
### LAUNCH THE SERVER ###
#########################

export SERVER_REGISTRY_IMAGE="ghcr.io/attuneintelligence/redis-agent-server"

### BUILD DOCKER
# docker build -f server.Dockerfile -t ${SERVER_REGISTRY_IMAGE}:main .

### PULL DOCKER
# docker pull $SERVER_REGISTRY_IMAGE:main

### FUNCTION TO RUN DOCKER COMMAND
run_docker() {
  docker run -it \
    --name redis-agent-server \
    -p 8888:8888 -p 5001:5000 -p 9181:9181 \
    -v .:/workspace/redis-agent \
    --network redis-network \
    ${SERVER_REGISTRY_IMAGE}:main /bin/bash -c "$1"
}

### CREATE A DOCKER NETWORK IF IT DOESN'T EXIST
docker network create redis-network 2>/dev/null

### CHECK IF REDIS CONTAINER IS ALREADY RUNNING
REDIS_CONTAINER_ID=$(docker ps --filter "name=redis" --format "{{.ID}}")
if [ -z "$REDIS_CONTAINER_ID" ]; then
  echo "No Redis container found. Starting a new one..."
  docker run -d --name redis --network redis-network redis:7.4-rc2-alpine
else
  echo "Redis container is already running."
  docker network connect redis-network redis 2>/dev/null   ### ENSURE REDIS IS CONNECTED TO NETWORK
fi

### CHECK IF REDIS-AGENT IS ALREADY RUNNING
CONTAINER_ID=$(docker ps --filter "name=redis-agent-server" --format "{{.ID}}")

### CONNECT / LAUNCH THE APPLICATION SERVER
if [ -n "$CONTAINER_ID" ]; then
  echo "Container is already running. Connecting to it..."
  
  if [ "$1" == "--server" ]; then
    docker exec -it $CONTAINER_ID bash -c "python main.py"
  elif [ "$1" == "--jupyter" ]; then
    docker exec -it $CONTAINER_ID bash -c "source bin/jupyter.sh"
  elif [ "$1" == "--bash" ]; then
    docker exec -it $CONTAINER_ID bash -c "cowsay namaste; bash"
  else
    echo "No instruction provided for server."
  fi

else
  echo "No running server was found. Starting a new one..."

  if [ "$1" == "--server" ]; then
    run_docker "python main.py"
  elif [ "$1" == "--jupyter" ]; then
    run_docker "source bin/jupyter.sh"
  elif [ "$1" == "--bash" ]; then
    run_docker "cowsay namaste; bash"
  else
    echo "No instruction provided for server."
  fi
fi