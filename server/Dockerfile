ARG ONTOLOGY_VERSION="latest"

FROM eclipse-temurin:8 as converter

WORKDIR /rdf2rdf
COPY server/*.jar ./

WORKDIR /dpn

# Include the local ontology files in TTL->RDF conversion efforts
ARG ONTOLOGY_VERSION
COPY dpn*.ttl ./${ONTOLOGY_VERSION}/

# Perform TTL -> RDF conversions
SHELL ["/bin/bash", "-c"]
RUN for TTL_PATH in $(find ./ -type f -name '*.ttl'); do \
        TTL_PATH=$(realpath "${TTL_PATH}"); \
        RDF_PATH="${TTL_PATH%.ttl}.rdf"; \
        RESULT=$(java -jar /rdf2rdf/rdf2rdf-1.0.1-2.3.1.jar "${TTL_PATH}" "${RDF_PATH}" 2>&1);\
        if [[ "${RESULT}" =~ Exception ]]; then >&2 echo "${RESULT}"; exit -1; fi; \
        echo "${RESULT}"; \
    done

# Install some historically-significant versions of the precompiled ontology
# that have been released elsewhere
ARG CSIRO_COASTS_VERSIONS="v0.7.2.26 v0.7.1.9 v0.6.1.24 v0.4.0.19"
RUN CCVS="${CSIRO_COASTS_VERSIONS}"; \
    for CCV in $CCVS; do \
        mkdir "/dpn/${CCV}" \
        && curl -s "https://build.csiro-coasts.net/archive/DPN-ontology/dpn_ontology_${CCV}.tar.gz" | tar -zxvf - -C "/dpn/${CCV}"; \
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
ENV CONTACT_EMAIL="admin@example.com" \
    CURRENT_VERSION="latest" \
    ENABLE_ACCESS_LOGGING="true" \
    ENDPOINT="" \
    FAVICON_URL="/favicon.ico" \
    LODE_BASEURL="" \
    LOG_LEVEL="warn"
