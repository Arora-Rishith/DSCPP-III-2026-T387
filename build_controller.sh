#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
g++ -std=c++17 -O2 ModuleBridge.cpp -o ModuleBridge
printf 'Build successful: ModuleBridge\n'
