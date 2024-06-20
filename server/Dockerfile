ARG ONTOLOGY_VERSION="latest"

FROM eclipse-temurin:8 as converter

SHELL ["/bin/bash", "-c"]

WORKDIR /rdf2rdf
COPY server/*.jar ./

WORKDIR /dpn

# Install the latest .ttl files
ARG ONTOLOGY_VERSION
COPY dpn*.ttl ./${ONTOLOGY_VERSION}/

# Compile the latest .ttl files to .rdf
# (Will fail the build if there are any syntax errors)
RUN cd "${ONTOLOGY_VERSION}"; \
    for TTL_PATH in $(find ./ -type f -name '*.ttl'); do \
        TTL_PATH=$(realpath "${TTL_PATH}"); \
        RDF_PATH="${TTL_PATH%.ttl}.rdf"; \
        RESULT=$(java -jar /rdf2rdf/rdf2rdf-1.0.1-2.3.1.jar "${TTL_PATH}" "${RDF_PATH}" 2>&1);\
        if [[ "${RESULT}" =~ Exception ]]; then >&2 echo "${RESULT}"; exit -1; fi; \
        echo "${RESULT}"; \
    done

# Produce a tarball of the latest .ttl and .rdf files
# This is suitable for use as a GitHub release binary
RUN cd "${ONTOLOGY_VERSION}" \
    && tar -zcvf "/dpn/dpn_ontology_${ONTOLOGY_VERSION}.tar.gz" .

# Install some historically-significant versions of the precompiled ontology
# that have been released elsewhere
ARG OLD_VERSIONS="v0.7.2 v0.7.1 v0.6.1.24 v0.4.0.19"
ENV OLD_VERSIONS="${OLD_VERSIONS}"
RUN --mount=target=/downloads,type=cache,sharing=locked \
    cd /downloads && \
    for VERSION in $OLD_VERSIONS; do \
        URL="https://github.com/eReefs/dpn-ontology/releases/download/${VERSION}/dpn_ontology_${VERSION}.tar.gz"; \
        wget --timestamping "${URL}" && \
        mkdir -p "/dpn/${VERSION}" && \
        tar -zxvf "dpn_ontology_${VERSION}.tar.gz" -C "/dpn/${VERSION}"; \
        if [ ! -f "/dpn/${VERSION}/dpn.ttl" ]; then >&2 echo "dpn.ttl missing for ${VERSION}"; exit -1; fi; \
    done

#------------------------------------------------------------------------------
FROM httpd:2.4 as server

WORKDIR /usr/local/apache2/htdocs

# Configure the Apache webserver
COPY server/httpd.conf /usr/local/apache2/conf/httpd.conf
COPY server/.htaccess ./

# Install the DPN Ontology files to be served up
COPY --from=converter /dpn/ ./

# Create symlinks for partial version numbers, and prep
# other local files to be served (or not!) by the webserver
COPY server/make_version_symlinks.sh ./
RUN chmod 0755 ./make_version_symlinks.sh \
    && ./make_version_symlinks.sh \
    && chown -R www-data:www-data . \
    && rm -f index.html \
    && rm -f *.tar.gz \
    && rm make_version_symlinks.sh

# Set default values for the environment variables used in the .htaccess file
ARG ONTOLOGY_VERSION
ENV ACCESS_LOG_PATH="/proc/self/fd/1" \
    ERROR_LOG_LEVEL="warn" \
    CONTACT_EMAIL="admin@example.com" \
    FAVICON_URL="/favicon.ico" \
    CURRENT_VERSION="${ONTOLOGY_VERSION}" \
    LATEST_VERSION="${ONTOLOGY_VERSION}" \
    LODE_BASEURL="" \
    LODE_PROXY="true" \
    PATH_PREFIX=""
