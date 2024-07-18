#!/bin/bash

##########################################
### LAUNCH JUPYTER LAB IN DOCKER BUILD ###
##########################################

### LAUNCH JUPYTER LAB
jupyter lab \
    --ServerApp.allow_origin='*' \
    --ip="0.0.0.0" \
    --ServerApp.token="" \
    --no-browser \
    --notebook-dir=/workspace/redis-agent