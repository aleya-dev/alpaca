#!/usr/bin/env bash

set -euo pipefail

source $1

@ALPACA_VARIABLES@

if declare -F $2 >/dev/null; then
    $2;
fi
