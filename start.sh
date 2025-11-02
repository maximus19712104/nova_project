#!/bin/bash
cd "$(dirname "$0")"
source nova_env/bin/activate
uvicorn run:app --reload

