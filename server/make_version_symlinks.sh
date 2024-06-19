#!/bin/bash
set -e

for SUBDIR in $(find ./ -maxdepth 1 -type d -name 'v*' | sort); do
  FULL_VERSION=$(basename "${SUBDIR}")
  VERSION1=$(echo $FULL_VERSION | sed 's/.*\(v[[:digit:]]\+\).*/\1/')
  VERSION2=$(echo $FULL_VERSION | sed 's/.*\(v[[:digit:]]\+\.[[:digit:]]\+\).*/\1/')
  VERSION3=$(echo $FULL_VERSION | sed 's/.*\(v[[:digit:]]\+\.[[:digit:]]\+\.[[:digit:]]\+\).*/\1/')
  if [[ -n "${VERSION1}" ]] && [[ "${VERSION1}" != "v0" ]] && [[ "${VERSION1}" != "${FULL_VERSION}" ]]; then
    echo "Linking '${SUBDIR}' as '${VERSION1}'"
    rm -f "${VERSION1}"
    ln -sf "${SUBDIR}" "${VERSION1}"
  fi
  if [[ -n "${VERSION2}" ]] && [[ "${VERSION2}" != "${FULL_VERSION}" ]]; then
    echo "Linking '${SUBDIR}' as '${VERSION2}'"
    rm -f "${VERSION2}"
    ln -sf "${SUBDIR}" "${VERSION2}"
  fi
  if [[ -n "${VERSION3}" ]] && [[ "${VERSION3}" != "${FULL_VERSION}" ]]; then
    echo "Linking '${SUBDIR}' as '${VERSION3}'"
    rm -f "${VERSION3}"
    ln -sf "${SUBDIR}" "${VERSION3}"
  fi
done
