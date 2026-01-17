import logging
import os
import re
import sys

from bs4 import BeautifulSoup as Soup
import falcon
from pylode.profiles.ontpub import OntPub
from rdflib import Graph
import validators
from wsgiref.simple_server import make_server

# Remove any handlers that might have been added to the root logger
# by some library someplace...
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Configure logging before anything else
if __name__ == '__main__':
    # Log configuration should up to this application
    logging.basicConfig(
        format=f'%(asctime)s.%(msecs)03d %(levelname)s [pid=%(process)d %(threadName)s %(name)s:%(lineno)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=os.getenv('LOG_LEVEL', 'INFO').upper(),
        stream=sys.stdout
    )
elif 'gunicorn.error' in logging.Logger.manager.loggerDict:
    # This application is running under GUnicorn, which has already initialised logging.
    # Ensure pylode server logs are directed to the GUnicorn error log,
    # any that the configured log-level is respected.
    logging.root.setLevel(os.getenv('LOG_LEVEL', 'INFO').upper())
    gunicorn_logger = logging.getLogger('gunicorn.error')
    for gunicorn_handler in gunicorn_logger.handlers:
        logging.root.addHandler(gunicorn_handler)

_logger = logging.getLogger(__name__)

CSS_URL = os.getenv('CSS_URL')
FAVICON_TYPE = os.getenv('FAVICON_TYPE', 'image/x-icon')
FAVICON_URL = os.getenv('FAVICON_URL')
GTAGID = os.getenv('GTAGID')
PATH_PREFIX = os.getenv('PATH_PREFIX', '')
MEDIA_DEFAULT = 'application/rdf+xml'
MEDIA_EXTENSIONS = {
    'text/html': '.htm',
    'text/turtle': '.ttl',
    'application/rdf+xml': '.rdf',
    'application/ld+json': '.json-ld',
    'application/n-triples' : '.nt',
    'application/xhtml+xml': '.htm'
}
ONTOLOGY_BASE = os.getenv('ONTOLOGY_BASE', os.path.join(os.getcwd()))
with open(f"{ONTOLOGY_BASE}/.local.version", 'r') as f:
    LOCAL_VERSION = f.read().strip()
LATEST_VERSION = os.getenv('LATEST_VERSION') or LOCAL_VERSION
CURRENT_VERSION = os.getenv('CURRENT_VERSION') or LOCAL_VERSION

def media_type_from_extension(filename: str) -> str | None:
    """Determines the most likely MIME type based on a file extension.

    :param filename:
        The filename you want to know the most likely content type of.
    :return:
        The MIME type that best matches the file extension (if any) of `filename`
        or None if there is no file extension we recognise
    """
    for k, v in MEDIA_EXTENSIONS.items():
        if filename.endswith(v):
            return k
    return None


def extension_from_media_type(media_type: str) -> str | None:
    """Identifies the most appropriate RDF file extension for a specific content type.

    :param media_type:
        The MIME type for the content you need a file extension for.
    :return:
        An appropriate file extension, including a leading period
        OR None if the content type was not understood
    """
    return MEDIA_EXTENSIONS.get(media_type, None)

def safejoin(head: str, *tail) -> str:
    """Sanitise and join parts of a path.

    Ensures that the result is always *below* the head,
    and that the result contains no invalid path characters.

    Inspired by:
    - https://gist.github.com/gfranxman/289669e70871d807637ff1034715695a
    - https://stackoverflow.com/a/24510379
    """
    for t in tail:
        if t == '..' or t.startswith('../') or os.path.isabs(t):
            _logger.warning(f"Security risk in path join: segment '{t}' includes an absolute or parent path")
            raise falcon.HTTPNotFound()
    abshead = os.path.abspath(head)
    result = os.path.normpath(os.path.join(abshead, *tail))
    if not result.startswith(f'{abshead}{os.path.sep}'):
        _logger.warning(f"Security risk in path join: result '{result}' has escaped the root ('{abshead}').")
        raise falcon.HTTPNotFound()
    return result

class HtmlCustomiser:
    """Falcon middleware for modifying HTML response documents."""

    def process_response(self, req: falcon.Request, resp: falcon.Response, resource: object, req_succeeded: bool) -> None:
        """Post-processing of a Falcon app response (after routing)."""

        content_type = resp.get_header('content-type', None)
        if content_type == 'text/html':
            # Determine whether any customisation has been required
            if CSS_URL or FAVICON_URL or GTAGID:
                # Customisations *have* been configured
                # Modify whatever HTML is currently in the response object
                soup = Soup(resp.text, features='html.parser')
                head = soup.find('head')
                if CSS_URL:
                    _logger.debug('Injecting custom css link')
                    css_tag = soup.new_tag('link')
                    css_tag['rel'] = 'stylesheet'
                    css_tag['href'] = CSS_URL
                    head.append(css_tag)

                if FAVICON_URL:
                    _logger.debug('Injecting custom favicon link')
                    for old_icon in soup.find_all('link', rel='icon'):
                        old_icon.decompose()
                    favicon_tag = soup.new_tag('link')
                    favicon_tag['rel'] = 'icon'
                    favicon_tag['type'] = FAVICON_TYPE
                    favicon_tag['href'] = FAVICON_URL
                    head.append(favicon_tag)

                if GTAGID:
                    _logger.debug('Injecting custom google analytics tag')
                    async_tag = soup.new_tag('script')
                    async_tag['async src'] = f'https://www.googletagmanager.com/gtag/js?id={GTAGID}'
                    gtag = soup.new_tag('script')
                    gtag.string = f"""window.dataLayer = window.dataLayer || [];
                        function gtag(){{dataLayer.push(arguments);}}
                        gtag('js', new Date());
                        gtag('config', '{GTAGID}');"""
                    head.append(async_tag)
                    async_tag.insert_after(gtag)
                resp.text = soup.prettify(formatter='html')
                if content_type is None:
                    resp.content_type = 'text/html'
            else:
                _logger.debug('No HTML cutomisations have been configured')
        else:
            _logger.debug(f'Skipping HTML customisations for {content_type} response')


class OntologyResource:
    """Falcon Request Handler that deals with local DPN ontology resources."""

    def on_get(self, req: falcon.Request, resp: falcon.Response, version: str, resource: str) -> None:
        """Handle requests for local ontology resource files, with content negotiation and aliases."""
        _logger.debug(f"Handling  request for ontology version '{version}' resource '{resource}'")

        # Validate that the `version` path parameter exactly matches an installed ontology version.
        if not version:
            _logger.info(f"Missing ontology version in request path '{req.path}'")
            raise falcon.HTTPRouteNotFound(description=f"Missing ontology version")

        version_path = safejoin(ONTOLOGY_BASE, version)
        if not os.path.isdir(version_path):
            _logger.info(f"Ontology version directory '{version_path}' for '{req.path}' not found")
            raise falcon.HTTPRouteNotFound(description=f"Unknown ontology version '{version}'")

        # Identify the ontology resource the request is for, and the format it is wanted in.
        basename, extension = os.path.splitext(resource)
        if not basename:
            # No ontology resource has actually been requested at all!
            _logger.info(f"Missing ontology resource in request path '{req.path}'")
            raise falcon.HTTPRouteNotFound(description='Missing ontology resource')

        if extension:
            # The caller has asked for a response of a type identified by this extension
            target_type = media_type_from_extension(extension.lower())
        elif req.accept == '*/*':
            # The caller has not indicated a preference for any particular content type
            # Default to rdf+xml for backward-compatibility with the old ontology server.
            target_type = MEDIA_DEFAULT
        else:
            # The caller is attempting content-type negotiation
            target_type = req.client_prefers(MEDIA_EXTENSIONS.keys())
        if not target_type:
            # We don't know how to generate responses of any acceptable type
            _logger.info(f"Unable to identify a supported an acceptable media type from extension='{extension}' or Accept='{req.accept}'")
            raise falcon.HTTPNotAcceptable(description=f'Supported media types are: {MEDIA_EXTENSIONS.keys()}')

        # Does an ontology resource of this type exist as a local file already?
        exact_path = safejoin(version_path, resource)
        if not extension:
            exact_path = f'{exact_path}{extension_from_media_type(target_type)}'
        if os.path.isfile(exact_path):
            # Yes!  We can serve up the requested resource as-is.
            _logger.info(f"Serving existing resource '{exact_path}' as an exact match for '{req.path}' of type '{target_type}'")
            with open(exact_path, "rb") as file:
                resp.text = file.read()
            resp.set_header("content-type", media_type_from_extension(exact_path))
            resp.status = falcon.HTTP_200
        else:
            # No: there is no exactly-matching local resource, but we may be able to convert something
            _logger.debug(f"Exact resource path '{exact_path}' does not exist or is not an accessible file")
            source_candidates = [
                safejoin(version_path, f'{basename}.ttl'),
                safejoin(version_path, f'{basename}.rdf')
            ]
            conversion_source = None
            for s in source_candidates:
                if s != exact_path and os.path.isfile(s):
                    conversion_source = s
                    break
            if conversion_source and target_type in ['text/html', 'application/xhtml+xml']:
                # Use pyLODE to convert the ontology resource to human-readable HTML.
                _logger.info(f"Using pyLODE to convert '{conversion_source}' to HTML for '{req.path}' of type '{target_type}'")
                sort_subjects = req.get_param_as_bool('sort', required=False, blank_as_true=False, default=False)
                ontology_doc = OntPub(conversion_source, sort_subjects=sort_subjects)
                resp.text = ontology_doc.make_html(include_css=True)
                resp.set_header("content-type", target_type)
                resp.status = falcon.HTTP_200
            elif conversion_source and target_type:
                # Use RDFLib to convert the ontology resource to a different RDF format
                _logger.info(f"Using RDFLib to convert '{conversion_source}' for '{req.path}' of type '{target_type}'")
                graph = Graph()
                graph.parse(conversion_source, format=media_type_from_extension(conversion_source))
                resp.text = graph.serialize(format=target_type)
                resp.set_header("content-type", target_type)
                resp.status = falcon.HTTP_200
            else:
                # Conversion will not be possible, as we don't have anything to convert
                _logger.info(f"Unable to identify an RDF conversion source for '{req.path}' and type '{target_type}'")
                raise falcon.HTTPNotFound(description=f"Unknown ontology resource '{req.path}'")


class OntologyResourceAlias:
    """Falcon Request Handler that deals with ontology resource aliases."""

    def __init__(self, version: str,  resource: str, required_prefix: str = 'dpn'):
        """Set per-handler-instance defaults for missing local resource path parts."""
        self._default_version = version
        self._default_resource = resource
        self._required_prefix = required_prefix

    def on_get(self, req: falcon.Request, resp: falcon.Response, version: str = '', resource: str = '', extension: str = '', **kwargs) -> None:
        """Handle requests for resource aliases directing them to the appropriate local resource."""
        use_version = version if version else self._default_version
        use_resource = f'{resource}{extension}' if resource else f'{self._default_resource}{extension}'
        effective_path = f'/{use_version}/{use_resource}' if use_version else f'/{use_resource}'
        if req.path == effective_path:
            _logger.warning(f"Requested path '{req.path}' is not actually an alias - check your routing rules!")
            OntologyResource().on_get(req=req, resp=resp, version=use_version, resource=use_resource)
        elif not use_resource.startswith(self._required_prefix):
            _logger.info(f"Requested path '{req.path}' is not a valid ontology resource alias")
            raise falcon.HTTPNotFound(description=f"Invalid ontology resource '{req.path}'")
        else:
            _logger.info(f"Requested path '{req.path}' is an alias for '{effective_path}'. Redirecting.")
            raise falcon.HTTPSeeOther(location=f'{PATH_PREFIX}{effective_path}')

class RemoteResource:
    """Falcon Request Handler that deals with redirects to remote resources of any type."""

    def __init__(self, remote_target: str | None = None):
        """Set per-handler-instance defaults for missing local resource path parts."""
        self._remote_target = remote_target
        if not validators.url(self._remote_target):
            raise ValueError(f"'{self._remote_target}' is not a valid remote resource URL")

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle requests for remote resource aliases."""
        raise falcon.HTTPMovedPermanently(location=self._remote_target)


app = falcon.App(middleware=[HtmlCustomiser()])
app.req_options.strip_url_path_trailing_slash=True

# Route requests for a default favicon to any custom favicon
if FAVICON_URL:
    app.add_route("/favicon.ico", RemoteResource(remote_target=FAVICON_URL))

# Set up redirect-routing for Ontology resource aliases where the version *follows* a resource ID alias
# (like in versions DPN Ontology IRIs) or where the resource name needs a hyphen instead of a path
# Matching requests will be redirected
dpn_dataset_alias = OntologyResourceAlias(version=CURRENT_VERSION, resource='dpn-dataset')
app.add_route('/{version}/dpn/dataset{extension}', dpn_dataset_alias)
app.add_route('/{version}/dpn/dataset', dpn_dataset_alias)
app.add_route('/dpn/dataset/{version}', dpn_dataset_alias)
app.add_route('/dpn/dataset', dpn_dataset_alias)
app.add_route('/dataset/{version}', dpn_dataset_alias)
app.add_route('/dataset', dpn_dataset_alias)

dpn_services_alias = OntologyResourceAlias(version=CURRENT_VERSION, resource='dpn-services')
app.add_route('/{version}/dpn/services{extension}', dpn_services_alias)
app.add_route('/{version}/dpn/services', dpn_services_alias)
app.add_route('/dpn/services/{version}', dpn_services_alias)
app.add_route('/dpn/services', dpn_services_alias)
app.add_route('/services/{version}', dpn_services_alias)
app.add_route('/services', dpn_services_alias)

dpn_default_alias = OntologyResourceAlias(version=CURRENT_VERSION, resource='dpn')
app.add_route('/dpn/{version}', dpn_default_alias)
app.add_route('/dpn', dpn_default_alias)
app.add_route('/', dpn_default_alias)

# Redirect-routing for static version aliases
# (These will be redirected to the appropriate real version)
if CURRENT_VERSION:
    app.add_route('/current/{resource:path}', dpn_default_alias)
    app.add_route('/current', dpn_default_alias)
if LATEST_VERSION:
    dpn_latest_alias = OntologyResourceAlias(version=LATEST_VERSION, resource='dpn')
    app.add_route('/latest/{resource:path}', dpn_latest_alias)
    app.add_route('/latest', dpn_latest_alias)

# Direct routing for any resources with a definite version/resource structure
# (This is the one that actually does the work of service up content)
app.add_route('/{version}/{resource:path}', OntologyResource())

# And lastly, a catch-all redirect-route for any *other* path,
# assuming that any content in the path is EITHER only a real version OR only a resource.
app.add_sink(dpn_default_alias.on_get, prefix=r'/(?P<version>v\d+(\.\d+)*)$')
app.add_sink(dpn_default_alias.on_get, prefix=r'/(?P<resource>.*)$')


if __name__ == '__main__':
    # Launch a standalone HTTP server
    listen_port = int(os.getenv('PORT', 8000))
    with make_server('', listen_port, api) as httpd:
        # Serve until process is killed
        httpd.serve_forever()
