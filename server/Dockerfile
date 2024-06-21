ARG ONTOLOGY_VERSION=""

FROM eclipse-temurin:8 as converter

SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

WORKDIR /dpn

# Install some historically-significant versions of the precompiled ontology
# from artefacts that have been added to their github release
ARG PRIOR_VERSIONS="v0.7.2 v0.7.1 v0.6.1.24 v0.4.0.19"
RUN --mount=target=/downloads,type=cache,sharing=locked \
    DOWNLOADS_DIR="/downloads"; \
    PRIOR_VERSIONS="${PRIOR_VERSIONS}"; \
    for VERSION in $PRIOR_VERSIONS; do \ 
        mkdir "./${VERSION}"; \
        URL="https://github.com/eReefs/dpn-ontology/releases/download/${VERSION}/dpn_ontology_${VERSION}.tar.gz"; \
        wget --directory-prefix "${DOWNLOADS_DIR}" --timestamping "${URL}"; \
        tar -zxvf "${DOWNLOADS_DIR}/dpn_ontology_${VERSION}.tar.gz" -C "./${VERSION}"; \
        if [ ! -f "./${VERSION}/dpn.ttl" ]; then >&2 echo "dpn.ttl missing for ${VERSION}"; exit 1; fi; \
    done

# Install the local ontology definition files, and compile them to RDF
# (The compilation script will move them into an appropriately named subdirectory)
ARG ONTOLOGY_VERSION
COPY dpn*.ttl ./
COPY server/compile_ontology.sh server/*.jar /build_tools/
RUN EXPECTED_VERSION="${ONTOLOGY_VERSION:-}"; \
    JAR_DIR="/build_tools/"; \
    . /build_tools/compile_ontology.sh

#------------------------------------------------------------------------------
FROM httpd:2.4 as server

SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]
WORKDIR /usr/local/apache2/htdocs

# Configure the Apache webserver
COPY server/httpd.conf /usr/local/apache2/conf/httpd.conf
COPY server/.htaccess ./

# Install the DPN Ontology files to be served up
COPY --from=converter /dpn/ ./

# Create symlinks for partial version numbers, and prep
# other local files to be served (or not!) by the webserver
COPY server/make_version_symlinks.sh ./
RUN . ./make_version_symlinks.sh \
    && chown -R www-data:www-data . \
    && rm -f index.html \
    && rm make_version_symlinks.sh

# Set default values for the environment variables used in the .htaccess file
ARG ONTOLOGY_VERSION
LABEL ONTOLOGY_VERSION="${ONTOLOGY_VERSION:-snapshot}"

ENV ACCESS_LOG_PATH="/proc/self/fd/1" \
    ERROR_LOG_LEVEL="warn" \
    CONTACT_EMAIL="admin@example.com" \
    FAVICON_URL="/favicon.ico" \
    CURRENT_VERSION="${ONTOLOGY_VERSION}" \
    LATEST_VERSION="${ONTOLOGY_VERSION}" \
    LODE_BASEURL="" \
    LODE_PROXY="true" \
    PATH_PREFIX=""
