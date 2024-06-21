#!/bin/bash
set -e
set -o pipefail

RDF2RDF_JAR="${JAR_DIR:-.}/rdf2rdf-1.0.1-2.3.1.jar"

owl_current_version(){
    cat "${1}" | grep owl:versionIRI | sed 's|.*\(v[[:digit:]]*[.[:digit:]]*\).*|\1|'
}

owl_prior_version(){
    cat "${1}" | grep owl:priorVersion | sed 's|.*\(v[[:digit:]]*[.[:digit:]]*\).*|\1|'
}

# Verify that the prior version of the ontology (if configured) has been installed
PRIOR_VERSION=$(owl_prior_version dpn.ttl);
PRIOR_PATTERN="^|[[:space:]]$( echo "${PRIOR_VERSION}" | sed 's|\.|\\\.|g')"
INSTALLED_PRIOR_VERSIONS=$(find ./ -type d -name 'v*' -mindepth 1 -maxdepth 1 -printf "%P ")

if [[ -z "${PRIOR_VERSION}" ]] && [[ -z "${INSTALLED_PRIOR_VERSIONS}" ]]; then
    echo "OK: this is the first version of the ontology (priorVersion not set)"
elif [[ -z "${PRIOR_VERSION}" ]] && [[ -n "${INSTALLED_PRIOR_VERSIONS}" ]]; then
    >&2 echo "ERROR: dpn.ttl priorVersion is not set, but prior versions have been installed: ${INSTALLED_PRIOR_VERSIONS}"
    exit 1
elif [[ -n "${PRIOR_VERSION}" ]] && [[ -z "${INSTALLED_PRIOR_VERSIONS}" ]]; then
    >&2 echo "WARNING: dpn.ttl priorVersion is '${PRIOR_VERSION}', but no prior versions have been installed"
elif [[ "${INSTALLED_PRIOR_VERSIONS}" =~ $PRIOR_PATTERN ]]; then
    echo "OK: dpn.ttl priorVersion '${PRIOR_VERSION}' is satisfied by one of '${INSTALLED_PRIOR_VERSIONS}'"
else
    >&2 echo "ERROR: dpn.ttl priorVersion '${PRIOR_VERSION}' is not satisfied by any of '${INSTALLED_PRIOR_VERSIONS}'"
fi

# Verify that the current version of the ontology is acceptable and has NOT yet been installed
# (i.e. it does not clash with one of the prior versions)
CURRENT_VERSION=$(owl_current_version dpn.ttl);
if [ -z "${CURRENT_VERSION}" ]; then
    >&2 echo "ERROR: dpn.ttl version is not set!"
    exit 1
elif [[ -n "${EXPECTED_VERSION:-}" ]]; then
    if [[ "${CURRENT_VERSION}" != "${EXPECTED_VERSION}" ]]; then
        >&2 echo "ERROR: dpn.ttl version '${CURRENT_VERSION}' does not match '${EXPECTED_VERSION}'"
        exit 1
    else
        echo "OK: dpn.ttl version '${CURRENT_VERSION}' matches '${EXPECTED_VERSION}'"
    fi
else
    echo "OK: dpn.ttl version '${CURRENT_VERSION}' is acceptable"
fi
if [ -d "./${CURRENT_VERSION}" ]; then
    >&2 echo "ERROR: dpn.ttl version '${CURRENT_VERSION}' has already been installed. (Did you forget to increment the version numbers?)"
    exit 1
fi

# Compile the ontology definition for the identified version
mkdir -p "./${CURRENT_VERSION}"
for TTL_PATH in $(find ./ -mindepth 1 -maxdepth 1 -type f -name '*.ttl'); do
    echo
    echo "Processing ${TTL_PATH}..."

    # Verify that the ontology version is consistent
    OTHER_CURRENT_VERSION=$(owl_current_version "${TTL_PATH}")
    if [[ "${OTHER_CURRENT_VERSION}" != "${CURRENT_VERSION}" ]]; then \
        >&2 echo "ERROR: ${TTL_PATH} version '${OTHER_CURRENT_VERSION}' does not match ontology version '${CURRENT_VERSION}'";
        exit 1
    fi
    echo "OK: ${TTL_PATH} version '${CURRENT_VERSION}' is correct"

    # Verify that the ontology priorVersion is consistent
    OTHER_PRIOR_VERSION=$(owl_prior_version "${TTL_PATH}");
    if [[ "${OTHER_PRIOR_VERSION}" != "${PRIOR_VERSION}" ]]; then \
        >&2 echo "ERROR: ${TTL_PATH} priorVersion '${OTHER_PRIOR_VERSION}' does not match ontology priorVersion '${PRIOR_VERSION}'";
        exit 1
    fi
    echo "OK: ${TTL_PATH} priorVersion '${PRIOR_VERSION}' is correct"

    # Compile the .ttl file to RDF
    TTL_FILE=$(basename "${TTL_PATH}")
    RDF_PATH=$(realpath "./${CURRENT_VERSION}/${TTL_FILE%.ttl}.rdf")
    COMPILE_RESULT=$(java -jar "${JAR_DIR:-server}/rdf2rdf-1.0.1-2.3.1.jar" "${TTL_PATH}" "${RDF_PATH}" 2>&1)
    if [[ "${COMPILE_RESULT}" =~ Exception ]]; 
        then >&2 echo "${COMPILE_RESULT}"
        exit 1
    fi
    echo "${COMPILE_RESULT}"

    # Move the compiled .ttl file into the output directory
    mv "${TTL_PATH}" "./${CURRENT_VERSION}/"
done

# Make a tarball from all the compiled ontology files, with no path information included
# This is suitable for use as a release artefact
find "./${CURRENT_VERSION}" -type f -printf "%P\n" | tar -zcvf "dpn_ontology_${CURRENT_VERSION}.tar.gz" -C "./${CURRENT_VERSION}/" -T -
