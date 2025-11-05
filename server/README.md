# DPN Ontology Server

The files in this repository can be used to build a Docker image that
can serve up the latest *and* significant past DPN Ontology
definitions in ttl, rdf or html formats, not just their native .ttl formats.

- [Runtime Usage](#runtime-usage)
  - [Current and Latest version aliases](#current-and-latest-version-aliases)
  - [Support for IRI-stye URL Paths and Permalinks](#support-for-iri-stye-url-paths-and-permalinks)
  - [Runtime Content Negotiation](#runtime-content-negotiation)
  - [TTL -\> Linked Data Type Conversion](#ttl---linked-data-type-conversion)
  - [TTL -\> HTML rendering](#ttl---html-rendering)
- [Configuration](#configuration)
  - [Build-time Configuration: Ontology Version Selection and Validation](#build-time-configuration-ontology-version-selection-and-validation)
  - [Run-time Configuration: Server Behaviour and Appearance](#run-time-configuration-server-behaviour-and-appearance)


## Runtime Usage

When the server is launched, it will be available at <http://localhost:8090/>.

DPN Ontology resources will be available at URLs with a version prefix then an ontology filename like so: `http://localhost:8090/${VERSION}/dpn`

&nbsp;

### Current and Latest version aliases

If you don't want to hard-code (or know) a specific version, then you can use `current` or `latest` in place of the `${VERSION}` in URLS.
These will always be redirected to the current and latest version of the Ontology:

- <http://localhost:8090/current/dpn>
- <http://localhost:8090/latest/dpn>

The `current` version is the one that will also be served up by default if the user doesn't include any version in their request-URL at all.
In the eReefs production deployment of the DPN ontology, the versionless ontology IRI prefix (<http://purl.org/dpn>) will always resolve to
the designated `current` version.

The `latest` version is the the most recent one available (usually the one this server image was built from).

The versions that both of these aliases map to can be configured at runtime using environment variables: see below.
If the `latest` and `current` versions are not the same, then the `latest` version should not be assumed to be stable.

&nbsp;

### Support for IRI-stye URL Paths and Permalinks

One 'feature' of the DPN Ontology is that the two sub-ontologies [dpn-dataset.ttl](../dpn-dataset.ttl) and [dpn-services.ttl](../dpn-services.ttl)
use URI paths that do NOT match their filenames: <http://purl.org/dpn/dataset> and <http://purl.org/dpn/services> respectively.

In addition, all versioned IRIs are structured with the version *following* the resource path: so <http://purl.org/dpn/v9.0> in contrast to the `/v0.9/dpn` path for this server.

For backwards-compatibility reasons, these IRI paths should NOT be changed, so this server has built-in support for transforming IRI-style paths to
actual ontology resource paths.   This allows the `purl.org/dpn` permalink to be directed to the eReefs production deployment of the ontology without any difficulty.

&nbsp;

# Format Conversion

### Runtime Content Negotiation

Even though this repository only includes the ontology files in turtle format, this server can serve the ontology definitions in any of *several* formats via content negotiation.

Two negotiation methods are supported:

- **Option 1** (old school) - include a well known extension as a suffix on your ontology resource URL to ask for the content in a type that can be inferred for that resource.  e.g. `curl -L http://localhost:8090/latest/dpn.rdf` will fetch the DPN ontolgy definition in RDF-xml format.
- **Option 2** (proper content negotiation) - completely omit *any* file-extension in your request-URL, but instead use the HTTP `Accept` header to specify the media type you would like server to respond with: `curl -L -H 'Accept: application/rdf+xml' http://localhost:8090/latest/dpn` will also return a RDF-xml version of the ontology document.

The supported transformations are currently:

| Response Type | Option 1 file extension | Option 2 media type |
|---------------|-------------------------|---------------------|
| Human-readable HTML | `.htm` | `text/html` or `application/xhtml+xml` |
| [Turtle](https://en.wikipedia.org/wiki/Turtle_(syntax)) (exactly the files from this repo) | `.ttl` | `text/turtle` |
| [RDF/XML](https://en.wikipedia.org/wiki/RDF/XML) | `.rdf` | `application/rdf+xml` |
| [JSON-LD](https://en.wikipedia.org/wiki/JSON-LD) | `.json-ld` | `application/ld+json` |
| [N-triples](https://en.wikipedia.org/wiki/N-Triples) | `.nt` | `application/n-triples` |

If you ask for a format that cannot be supported, the server will return a [406 Not Acceptable](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/406) error status code and a list of the actually supported types.

&nbsp;

### TTL -> Linked Data Type Conversion

The server build uses the [RDFLib](https://rdflib.readthedocs.io/en/stable/) python library to
parse and validate the .ttl ontology definitions, and to transform them into other linked data formats.

The server image build process includes a validation step which will transform each .ttl file to RDF-xml,
which will cause a build-time error if the .ttl file contains any syntax errors.

If the pre-converted .rdf files are present in the image at runtime, then they will be served up as-is,
but if they are removed, the same conversion can be performed on-demand.

&nbsp;

### TTL -> HTML rendering

The server handles converting .ttl files to HTML with user-friendly markup,
and uses the [RDFLib/pyLODE](https://github.com/RDFLib/pyLODE) library to do so.

The server image build process includes a validation step which will transform each .ttl file to .htm.
This will cause a build-time error if anything in the ontolgy definition would cause problems for this rendering.

If the pre-converted .htm files are present in the image at runtime, then they will be served up as-is,
or if they are removed, the same conversion can be performed on-demand. This is very useful if you are testing
changes to the ontology in a development environment.

&nbsp;

## Configuration

### Build-time Configuration: Ontology Version Selection and Validation

The DPN Ontology Server image can be tweaked at build-time via the following build arguments:

- `PRIOR_VERSIONS` => Previous versions of the ontology that should also be compiled into the image.
  - This should be set to a space-seperated list of version tag from the [GitHub Releases List](https://github.com/eReefs/dpn-ontology/releases).
  - The default value includes all published versions of the ontology mentioned in a `prior version` IRI.
- `PRIOR_VALIDATE_ARGS` => A space-seperated list of command line arguments used with the [validate.py](./validate.py) script when validating the installed prior versions of the ontology.
  - If you have used a non-default value for `PRIOR_VERSIONS`, you may need to also use a non-default value for this
    argument to remove the `--require_prior` option, which would otherwise fail the build.
  - You can run `python validate.py --help` to see docs for the supported validations.
- `LOCAL_VALIDATE_ARGS` => A space-seperated list of command line arguments used with the [validate.py](./validate.py) script when validating the *local* version of the ontology.
  - If you are testing a development version of the ontology, you should use a custom value for this argument
    that *adds* two extra flags: `--def_rdf --del_htm`.  The build will then delete the .rdf and .htm files it
    created during validation, which means that those will always be regenerated on the fly.

&nbsp;

### Run-time Configuration: Server Behaviour and Appearance

The DPN Ontology Server container can be configured via the following environment variables:

- `CURRENT_VERSION` => The version of the ontology which should be served up if a caller does not request any specific version, or if the `current` version-alias is used in the path.
  - This *also* is the version that will be served for the unversioned DPN Ontology IRI aliases (<http://purl.prg/dpn> -> `https://dpn.ereefs.info/ontology/${CURRENT_VERSION}/dpn`)
  - Defaults to the version from the `dpn.ttl` file that was local at build-time
  - You can also be set to any other version which has been compiled or mounted into the container image.
- `LATEST_VERSION` => The version of the ontology which should be served if the `latest` version-alias is requested.
  - Defaults to the version from the `dpn.ttl` file that was local at build-time
  - Can also be set to any other version which has been compiled or mounted into the container image.
- `CSS_URL` => Absolute URL to an external CSS stylesheet that should be referenced by all HTML documents.
- `FAVICON_URL` => Absolute URL to a custom favicon that you want to be served up in response to any favicon requests.
- `FAVICON_TYPE` => The media type of your custom `FAVICON_URL` (defaults to `image/x-icon`)
- `GTAGID` => Google analytics tag ID that should be used to track requests to HTML versions of your ontology. (Note: does NOT currently track requests for .ttl or other RDF formats)
- `GUNICORN_CMD_ARGS` => Arguments to the GUNicorn webserver that is the entrypoint process for this application.
- `LOG_LEVEL` => Threshold for the level of log messages that should appear in the server log.
  - Defaults to `DEBUG` for the development server target, or `WARN` for the production build target.
- `PATH_PREFIX` => Any custom path that needs to be pre-pended to location headers in redirect-responses.  Defaults to an empty string, but if you are stripping a path-prefix at your reverse-proxy server, you should set this to the value or the stripped prefix.
- `PORT` => The port that the container will listen for HTTP requests on.
- `WEB_CONCURRENCY` => the number of worker processes that the GUNicorn server will start up.
