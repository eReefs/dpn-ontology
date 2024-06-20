# DPN Ontology Server

The files in this repository can be used to build a Docker image that
can serve up the latest *and* significant past DPN Ontology 
definitions in ttl, rdf or html formats, not just their native .ttl formats.

- [TTL -\> RDF compilation](#ttl---rdf-compilation)
- [TTL -\> HTML rendering](#ttl---html-rendering)
- [Build-time Configuration](#build-time-configuration)
- [Run-time Configuration](#run-time-configuration)


## TTL -> RDF compilation

The server build uses the [RDF2RDF](https://sourceforge.net/projects/rdf2rdf/) java 
library to compile the native .ttl files to RDF:  this will throw an error at build 
time if the .ttl file has any syntax errors.

The java library is quite old, and was downloaded from <https://sourceforge.net/projects/rdf2rdf/>. It's binary is included in this repository as a workaround for SourceForge's interactive download workflow. It is licensed with the GNU General Public License version 2.0 (GPLv2).

The library's docs include a broken link to a now-defunct openRDF.org Sesame project. That
project evolved into[RDF4J]<https://github.com/eclipse-rdf4j/rdf4j>, so future versions of this server may migrate
to that.

## TTL -> HTML rendering

The server handles converting .ttl files to HTML with user-friendly markup at *runtime*, 
and requires a working Live Owl Document Environment (LODE) server to do so.   This allows
the generated HTML to be rendered with deployment-specific customisations, like a visual identity.

The LODE server is a Java Servlet web application, and we recommend the version
of the source code from <https://github.com/sharon-tickell/LODE/tree/refactor>

## Build-time Configuration

The DPN Ontology Server image can be tweaked at build-time via the following build arguments:

- `ONTOLOGY_VERSION` => The version of the ontology that is being built. Defaults to `latest` for development builds, but should be set to a proper semantic version matching a tag on the repository for release builds.
- `OLD_VERSIONS` => Previous versions of the ontology that should also be served up: this should be set to a space-seperated list of a version tag that matches the semver of any 'previous version' property in the `dpn.ttl` file (i.e. all significant releases). These versions should have official GitHub releases with an associated `dpn_ontology_${VERSION}.tar.gz` artifact available for download.

## Run-time Configuration

The DPN Ontology Server container can be configured via the following environment variables:

- `ACCESS_LOG_PATH` => The path that the web server should write access logs to. Defaults to `/proc/self/fd/1`, which is the container's STDOUT. Set this to `/dev/null` to suppress access logging.
- `ERROR_LOG_LEVEL` => The level of detail at which error messages should be logged. Defaults to `warn`.
- `CONTACT_EMAIL` => Email address for the server administrator, displayed on error pages.  Defaults to `"admin@example.com`
- `FAVICON_URL` => Absolute URL to a custom favicon that you want to be served up in response to any favicon requests. Defaults to `/favicon.ico`, which will return a 404.
- `CURRENT_VERSION` => The version of the ontology which should be served up by default, or if the `current` version is requested.  Defaults to the `ONTOLOGY_VERSION` that was built, but can also be set to any other version which has been compiled into the container image.
- `LATEST_VERSION` => The version of the ontology which should be served up by default, or if the `latest` version is requested.  Defaults to `ONTOLOGY_VERSION` that was built, but can also be set to any other version which has been compiled into the container image.
- `LODE_BASEURL` => The absolute base URL of the LODE server that should be used to render HTML versions of the ontology.  Defaults to an empty string, which means no on-the-fly rendering.
  - NOTE that for lode rendering to work, the LODE server must be to be able to call back to this DPN-ontology server to request the RDF to render. It usually requires that your DPN Ontology server be set up with a proper DNS-supported hostname rather than `localhost`.
- `LODE_PROXY` => Set this to `true` (the default) to reverse-proxy any render requests to the LODE server, or `false` to redirect instead. (Redirects may be easier to debug if this is not behaving as expected).
- `PATH_PREFIX` => Any custom path that needs to be pre-pended to location headers in redirect-responses.  Defaults to an empty string, but if you are stripping a path-prefix at your reverse-proxy server, you should set this to the value or the stripped prefix.
