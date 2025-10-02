FROM python:3.13-bookworm AS dev-server

SHELL ["/bin/bash", "-e", "-o", "pipefail", "-c"]

# Upgrade the base-OS
RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
    --mount=target=/var/cache/apt,type=cache,sharing=locked \
    apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get -y upgrade \
    && apt-get clean \
    && DEBIAN_FRONTEND=noninteractive apt-get autoremove --purge \
    && rm -rf /var/lib/apt/lists/*

# Define the ontology server and resources directories
ARG INSTALL_BASE="/opt/dpn-ontology"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING="utf-8" \
    ONTOLOGY_BASE="${INSTALL_BASE}/resources"

WORKDIR "${INSTALL_BASE}/server"

# Install python requirements
COPY server/requirements ./requirements
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements/requirements.txt

# Install some historically-significant versions of the precompiled ontology
# from artefacts that have been added to their github release
ARG PRIOR_VERSIONS="v0.8 v0.7.2 v0.7.1 v0.6.1.24 v0.5.0.17 v0.4.0.19 v0.3 v0.2 v0.1"
RUN --mount=target=/downloads,type=cache,sharing=locked \
    DOWNLOADS_DIR="/downloads"; \
    mkdir -p "${ONTOLOGY_BASE}"; \
    for VERSION in $PRIOR_VERSIONS; do \
        mkdir -p "${ONTOLOGY_BASE}/${VERSION}"; \
        URL="https://github.com/eReefs/dpn-ontology/archive/refs/tags/${VERSION}.tar.gz"; \
        wget --directory-prefix "${DOWNLOADS_DIR}" --timestamping "${URL}"; \
        tar -zxvf "${DOWNLOADS_DIR}/${VERSION}.tar.gz"  -C "${ONTOLOGY_BASE}/${VERSION}" --strip-components=1 --wildcards '*.ttl'; \
    done

# Create symlinks for all partial version numbers
COPY server/make_version_symlinks.sh ./
RUN ./make_version_symlinks.sh

# Validate the prior versions, tweaking them where necessary to correct
# problems that were missed when the original release was made.
COPY server/validate.py  ./
ARG PRIOR_VALIDATE_ARGS="--fix_version --require_prior --fix_missing_title --make_rdf --make_htm --del_lode_subdir"
RUN python validate.py ${PRIOR_VALIDATE_ARGS}

# Install the local ontology definitions into a temporary location,
# Identify the local version and rename the directory to match,
# Use a text file to pass this information to the runtime server
# (hack to workaround not being able to calculate ENV vars values at build time)
# Then validate the local version. Be strict so that issues have to get fixed *before* release, not after...
COPY ./*.ttl "${ONTOLOGY_BASE}/local/"
ARG LOCAL_VALIDATE_ARGS="--require_prior --make_rdf --make_htm"
RUN LOCAL_VERSION=$(cat "${ONTOLOGY_BASE}/local/dpn.ttl" | grep owl:versionIRI | sed 's|.*\(v[[:digit:]]*[.[:digit:]]*\).*|\1|') \
    && if [ -z "${LOCAL_VERSION}" ]; then echo "No version IRI found in local dpn.ttl"; exit 1; fi \
    && if [ -d "${ONTOLOGY_VERSION}/${LOCAL_VERSION}" ]; then echo "Version from local dpn.ttl '${LOCAL_VERSION}' clashes with a prior version"; exit 1; fi \
    && mv "${ONTOLOGY_BASE}/local" "${ONTOLOGY_BASE}/${LOCAL_VERSION}" \
    && echo "${LOCAL_VERSION}" > "${ONTOLOGY_BASE}/local" \
    && python validate.py --target "${LOCAL_VERSION}" ${LOCAL_VALIDATE_ARGS}

# Set up the Falcon-based DPN Ontology server to run by default/
COPY server/server.py ./
ENV \
    # Ontology version to be served if the version is unspecified or 'current'
    CURRENT_VERSION="" \
    # Ontology version to be served for the 'latest' version alias
    LATEST_VERSION="" \
    # Optional prefix that should be pre-pended to redirect locations
    PATH_PREFIX="" \
    # Configuration options for the GUnicorn web server that make it compatible with docker.
    # (Log to stdout and stderr, and ensure workers use tmpfs storage)
    GUNICORN_CMD_ARGS="--access-logfile - --error-logfile - --worker-class gevent --worker-tmp-dir /dev/shm" \
    # Threshold for ontology-server log messages to show up in the log
    LOG_LEVEL="DEBUG" \
    # Port that GUNicorn will bind to
    PORT="8090" \
    # Number of worker processes that the GUnicorn web server will use to handle requests.
    # In production, you should set this to 2-4 x the number of CPU cores.
    WEB_CONCURRENCY=2

ENTRYPOINT ["gunicorn"]
CMD ["--reload", "server:app"]

FROM dev-server AS prod-server

# Update the default runtime configuration to be more appropriate for prod
ENV \
    # Threshold for ontology-server log messages to show up in the log
    LOG_LEVEL="WARN"

ENTRYPOINT ["gunicorn"]
CMD ["server:app"]
