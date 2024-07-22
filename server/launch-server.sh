#!/bin/bash

#########################
### LAUNCH THE SERVER ###
#########################

export SERVER_REGISTRY_IMAGE="ghcr.io/attuneintelligence/redis-agent-server"

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

### HANDLE REDIS CONTAINER
REDIS_CONTAINER_ID=$(docker ps -a --filter "name=redis" --format "{{.ID}}")
if [ -z "$REDIS_CONTAINER_ID" ]; then
  echo "No Redis container found. Starting a new one..."
  docker run -d --name redis --network redis-network redis:7.4-rc2-alpine
else
  REDIS_STATE=$(docker inspect -f '{{.State.Running}}' $REDIS_CONTAINER_ID)
  if [ "$REDIS_STATE" = "true" ]; then
    echo "Redis container is already running."
  else
    echo "Redis container exists but is not running. Starting it..."
    docker start $REDIS_CONTAINER_ID
  fi
  docker network connect redis-network redis 2>/dev/null
fi

### HANDLE REDIS-AGENT-SERVER CONTAINER
CONTAINER_ID=$(docker ps -a --filter "name=redis-agent-server" --format "{{.ID}}")

if [ -n "$CONTAINER_ID" ]; then
  CONTAINER_STATE=$(docker inspect -f '{{.State.Running}}' $CONTAINER_ID)
  if [ "$CONTAINER_STATE" = "true" ]; then
    echo "Container is already running. Connecting to it..."
    if [ "$1" == "--jupyter" ]; then
      docker exec -it $CONTAINER_ID bash -c "source bin/jupyter.sh"
    elif [ "$1" == "--bash" ]; then
      docker exec -it $CONTAINER_ID bash -c "cowsay namaste; bash"
    else
      docker exec -it $CONTAINER_ID bash -c "python main.py"
    fi
  else
    echo "Removing stopped redis-agent-server container..."
    docker rm $CONTAINER_ID
    echo "Starting a new redis-agent-server container..."
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
else
  echo "No redis-agent-server container found. Starting a new one..."
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