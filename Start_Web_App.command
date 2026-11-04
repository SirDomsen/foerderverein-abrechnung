#!/bin/bash
# Startet den Python-Webserver auf macOS
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
python3 apps/web/app_web.py
