set -e
source $1

if declare -F $2 >/dev/null; then
    $2;
fi
