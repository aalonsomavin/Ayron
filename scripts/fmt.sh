#!/bin/bash
set -e
cd "$(dirname "$0")/.."
ruff check backend/ --fix
ruff format backend/
