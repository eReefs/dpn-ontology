# DPN Ontology Server

The files in this repository can be used to build a Docker image that
can serve up the latest *and* significant past DPN Ontology 
definitions in ttl, rdf or html formats, not just their native .ttl formats.

## TTL -> RDF conversion

The server build uses the [RDF2RDF](https://sourceforge.net/projects/rdf2rdf/) java 
library to compile the native .ttl files to RDF:  this will throw an error at build 
time if the .ttl file has any syntax errors.

The java library is quite old, and was downloaded from <https://sourceforge.net/projects/rdf2rdf/>. It's binary is included in this repository as a workaround for SourceForge's interactive download workflow. It is licensed with the GNU General Public License version 2.0 (GPLv2).

The library's docs include a broken link to a now-defunct openRDF.org Sesame project. That
project evolved into[RDF4J]<https://github.com/eclipse-rdf4j/rdf4j>, so future versions of this server may migrate
to that.

## TTL -> HTML conversion

The server handles converting .ttl files to HTML with user-friendly markup at *runtime*, 
and requires a working Live Owl Document Environment (LODE) server to do so.   This allows
the generated HTML to be rendered with deployment-specific customisations, like a visual identity.

The LODE server is a Java Servlet web application, and we recommend the version
of the source code from <https://github.com/sharon-tickell/LODE/tree/refactor>

## Runtime Configuration

The DPN Ontology Server container can be convifired via the following environment variables:

- `CONTACT_EMAIL` => Email address for the server administrator, displayed on error pages.  Defaults to `"admin@example.com`
- `CURRENT_VERSION` => The version of the ontology which should be served up by default, or if the `current` version is selected.  Defaults to `latest`, but can also be set to any other version which has been compiled into the container image.
- `ENABLE_ACCESS_LOGGING` => Whether the server container should generate access logs. Defaults to `true`
- `ENDPOINT` => Any custom path that needs to be pre-pended to location headers in redirect-responses.  Defaults to an empty string, but if you are stripping a path-prefix at your reverse-proxy server, you should set this to the value or the stripped prefix.
- `FAVICON_URL` => Absolute URL to a custom favicon that you want to be served up in response to any favicon requests. Defaults to `/favicon.ico`, which will return a 404.
- `LODE_BASEURL` => The absolute base URL of the LODE server that should be used to render HTML versions of the ontology.  Defaults to an empty string, which means no on-the-fly rendering.
- `LOG_LEVEL` => The level of detail at which error messages should be logged. Defaults to `warn`.
