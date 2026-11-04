#!/bin/bash
# Öffnet die Offline-Webapp im Standard-Browser auf macOS
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
open "$DIR/apps/pwa/index.html"
