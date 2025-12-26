#!/usr/bin/env bash

set -euo pipefail

source "$1"

emit() {
    # key value
    printf '%s\0' "$1=$2"
}

emit_array() {
    local key=$1
    shift
    for val in "$@"; do
        printf '%s\0' "$key[]=$val"
    done
}

emit name "${name:-}"
emit url "${url:-}"
emit_array licenses "${licenses[@]:-}"
emit_array dependencies "${dependencies[@]:-}"
emit_array build_dependencies "${build_dependencies[@]:-}"
emit_array provides "${provides[@]:-}"
emit_array sources "${sources[@]:-}"
emit_array sha256sums "${sha256sums[@]:-}"

if declare -f version >/dev/null; then
    emit version "$(version)"
else
    emit version "${version:-}"
fi

if declare -f build >/dev/null; then
    emit build "$(build)"
else
    emit build "${build:-}"
fi
