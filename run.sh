#!/usr/bin/env bash

# Run Luigi daemon
luigid &

# Run API server
python ./api/api.py