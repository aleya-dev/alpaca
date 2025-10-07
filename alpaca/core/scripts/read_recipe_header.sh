set -e
source $1

for var in \
  name \
  stream \
  version \
  build \
  url \
  licenses \
  dependencies \
  build_dependencies \
  provides \
  sources \
  sha256sums; do
    if declare -p "$var" 2>/dev/null | grep -q 'declare -a'; then
        eval "declare -n array_ref=$var"
        printf '%s=(' "$var"
        for i in "${!array_ref[@]}"; do
            element="${array_ref[$i]%,}"
            printf "'%s'" "$element"
            if [ $i -lt $((${#array_ref[@]} - 1)) ]; then
                printf ", "
            fi
        done
        printf ')\n'
    else
        eval "printf '%s=%q\n' \"$var\" \"\${$var}\""
    fi
done
