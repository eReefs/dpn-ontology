#!/usr/local/bin/python
import argparse
import functools
import glob
import logging
import os
import re
import shutil
import sys

from pylode.profiles.ontpub import OntPub
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS

_logger = logging.getLogger(__name__)

ONTOLOGY_BASE = os.getenv('ONTOLOGY_BASE', os.path.join(os.getcwd()))

def installation_directory(version: str) -> str | None:
    """Retrieve the absolute installation directory of an ontology version.

    :returns:
        The installation path (OR SYMLINK PATH) if that version can be found,
        Or None if there is no valid match.
    """
    expected = os.path.join(ONTOLOGY_BASE, version)
    return expected if os.path.isdir(expected) else None


def identify_version(value: str, fix_semver: bool = False) -> str | None:
    """Extract and return an ontology version from a string that should contain one."""
    match = re.search(r'v\d+(\.\d+)*', value)
    version = match.group(0) if match else None
    if version and fix_semver:
        version_parts = version.split('.')
        if len(version_parts) > 3:
            # Some early releases had 4-part semver tags where the last part was a build-id.
            # Those were NOT used in the ontology IRIs, so don't consider them part of the version.
            version_parts = version_parts[:-1]
        if len(version_parts) > 2 and version_parts[-1] == "0":
            # Releases *always* included a patch version in the tag, even if there hadn't been any patches.
            # Those were ALSO not used in the IRI: omit them.
            version_parts = version_parts[:-1]
    return version


class ValidationResults:
    """Collect categorised feedback about a validation step."""

    def __init__(self, target: str) -> None:
        self.target = target
        self.feedback = []
        self.warnings = []
        self.errors = []

    def __str__(self) -> str:
        feedback_lines = "\n".join(
            [ f"\t\t- {f}" for f in self.feedback ]
        )
        warning_lines = "\n".join(
            [ f"\t\t- {w}" for w in self.warnings ]
        )
        error_lines = "\n".join(
            [ f"\t\t- {e}" for e in self.errors ]
        )
        return ''.join([
            f"Validation results for '{self.target}':",
            f"\n\tFEEDBACK:\n{feedback_lines}" if feedback_lines else '',
            f"\n\tWARNINGS:\n{warning_lines}" if warning_lines else '',
            f"\n\tERRORS:\n{error_lines}" if error_lines else ''
        ])

    @property
    def passed(self) -> bool:
        return True if len(self.errors) == 0 else False

    @property
    def log_level(self):
        if len(self.errors) > 0:
            return logging.ERROR
        elif len(self.warnings):
            return logging.WARNING
        else:
            return logging.INFO

def process_ttl_file(
    ttl: str,
    expect_version: str,
    fix_version: bool = False,
    require_prior: bool = False,
    fix_missing_title: bool = False,
    make_rdf: bool = False, del_rdf: bool = False,
    make_htm: bool = False, del_htm: bool = False,
    **kwargs
) -> bool:
    """Validate a single ontology .ttl file.

    :returns:
        a boolean which indicates whether the file passed validation or not.
    """
    results = ValidationResults(ttl)

    try:
        # Load and parse the ttl file, and identify the ontology subject
        graph = Graph()
        graph.parse(ttl, format='text/turtle')
        ontology = next(graph.subjects(predicate=RDF.type, object=OWL.Ontology))

        # Check we have a version IRI containing the expected version
        version_iri = graph.value(subject=ontology, predicate=OWL.versionIRI, object=None, default=None, any=False)
        if version_iri:
            results.feedback.append(f"Ontology version IRI '{version_iri}' configured")
            version = identify_version(version_iri)

        if version_iri and version and expect_version.startswith(version):
            results.feedback.append(f"Ontology version '{version}' matches expected version '{expect_version}'")
        elif fix_version:
            try:
                resource = os.path.basename(ttl).replace('-', '/')
                corrected_iri = f'http://purl.org/{resource}/{expect_version}'
                graph.set((ontology, OWL.versionIRI,  URIRef(corrected_iri)))
                graph.serialize(destination=ttl, format='text/turtle')
                results.warnings.append(f"Ontology version IRI '{version_iri}' corrected to '{corrected_iri}")
            except Exception as e:
                results.errors.append(f"Failed to correct mismatched or missing version IRI: {e}")
        elif version_iri and version:
                results.errors.append(f"Ontology version '{version}' does not match expected version '{expect_version}'")
        elif version_iri:
            results.errors.append(f"Ontology version IRI '{version_iri}' does not include an identifiable version")
        else:
            results.errors.append('Ontology versionIRI not configured')

        # Ontology priorVersion: optionally present, valid if present, optionally installed
        prior_version_iri = graph.value(subject=ontology, predicate=OWL.priorVersion, object=None, default=None, any=False)
        if prior_version_iri:
            results.feedback.append(f"Ontology prior version IRI '{prior_version_iri}' is configured")
            prior_version = identify_version(prior_version_iri)
            if prior_version:
                prior_dir = installation_directory(prior_version)
                if prior_dir:
                    results.feedback.append(f"Ontology prior version '{prior_version}' is installed at {prior_dir}'")
                elif require_prior:
                    results.errors.append(f"Ontology prior version '{prior_version}' is not installed")
                else:
                    results.warnings.append(f"Ontology prior version '{prior_version}' is not installed")
            else:
                results.errors.append(f"Ontology prior version IRI '{prior_version_iri}' does not include an identifiable version")
        else:
            results.warnings.append('Ontology prior version IRI is not configured')

        # Ontology title: should be present, or else pyLODE can't cope
        title = graph.value(subject=ontology, predicate=DCTERMS.title, object=None, default=None, any=False)
        if not title:
            title = graph.value(subject=ontology, predicate=RDFS.label, object=None, default=None, any=False)
        if title:
            results.feedback.append(f"Ontology title '{title}' is configured")
        elif fix_missing_title:
            try:
                title = 'Data Provider Node ontology'
                if 'dpn-dataset' in ttl:
                    title = 'Data Provider Node Dataset ontology'
                elif 'dpn-services' in ttl:
                    title = 'Data Provider Node Services ontology'
                graph.add((ontology, DCTERMS.title,  Literal(title)))
                graph.serialize(destination=ttl, format='text/turtle')
                results.warnings.append(f"Missing ontology title '{title}' added")
            except Exception as e:
                results.errors.append(f"Failed to fixing missing ontology title: {e}")
        else:
            results.warnings.append(f"Ontology title is not configured")

        # Derived .rdf file
        base, ext = os.path.splitext(ttl)
        rdf = f'{base}.rdf'
        rdf_exists = os.path.isfile(rdf)
        if make_rdf:
            if rdf_exists:
                results.warnings.append(f"Replacing existing .rdf file '{rdf}'")
            else:
                results.feedback.append(f"Making .rdf '{rdf}'")
            try:
                graph.serialize(destination=rdf, format='application/rdf+xml')
                rdf_exists = os.path.isfile(rdf)
            except Exception as e:
                results.errors.append(f"Failed making .rdf '{rdf}' from '{ttl}': {e}")
        if rdf_exists and del_rdf:
            results.warnings.append(f"Removing .rdf file '{rdf}'")
            os.remove(rdf)
        elif rdf_exists:
            results.feedback.append(f"Retaining .rdf file '{rdf}'")
        else:
            results.warnings.append(f"No .rdf file exists")

        # Derived .htm file
        htm = f'{base}.htm'
        htm_exists = os.path.isfile(htm)
        if make_htm:
            if htm_exists:
                results.warnings.append(f"Replacing existing .htm file '{htm}'")
            else:
                results.feedback.append(f"Making .htm file '{htm}'")
            try:
                doc = OntPub(ttl, sort_subjects=False)
                doc.make_html(destination=htm, include_css=True)
                htm_exists = os.path.isfile(htm)
            except Exception as e:
                results.errors.append(f"Failed making .htm '{htm}' from '{ttl}': {e}")
        if htm_exists and del_htm:
            results.warnings.append(f"Removing .htm file '{htm}'")
            os.remove(htm)
        elif htm_exists:
            results.feedback.append(f"Retaining .htm file '{htm}'")
        else:
            results.warnings.append('No .htm file exists')
    except Exception as e:
        results.errors.append(f"Unexpected exception processing '{ttl}': {e}")

    _logger.log(level=results.log_level, msg=str(results))
    return results.passed


def process_version(version, del_lode_subdir: bool = True, **kwargs) -> bool:
    """Validate all .ttl files for an Ontology version.

    :returns:
        a boolean which indicates whether the version passed validation or not.
    """
    results = ValidationResults(version)
    try:
        dir = installation_directory(version)
        if dir:
            results.feedback.append(f"Ontology version '{version}' is installed at '{dir}'")

            ttl_files = sorted(glob.glob(f'{dir}/*.ttl'))
            if len(ttl_files) > 0:
                expect_version = identify_version(version, fix_semver=True)
                for ttl in ttl_files:
                    passed = process_ttl_file(ttl, expect_version=expect_version, **kwargs)
                    if passed:
                        results.feedback.append(f".ttl file '{ttl}' is valid")
                    else:
                        results.errors.append(f".ttl file '{ttl}' failed validation")
            else:
                results.errors.append(f"There are no .ttl files present in '{dir}'")

        lode_subdir = f'{dir}/lode'
        if os.path.isdir(lode_subdir):
            if del_lode_subdir:
                results.warnings.append(f"Deleting legacy lode subdirectory at '{lode_subdir}'")
                shutil.rmtree(lode_subdir)
            else:
                results.feedback.append(f"Retaining legacy lode subdirectory at '{lode_subdir}'")
        else:
            results.feedback.append(f"legacy lode subdirectory does not exist at '{lode_subdir}")
    except Exception as e:
        results.errors.append(f"Unexpected exception processing '{version}': {e}")

    _logger.log(level=results.log_level, msg=str(results))
    return results.passed

if __name__ == '__main__':
    try:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(
            format=f'%(levelname)s [%(name)s:%(lineno)s] %(message)s',
            level=os.getenv('LOG_LEVEL', 'INFO').upper(),
            stream=sys.stdout
        )

        parser = argparse.ArgumentParser()
        parser.add_argument('--target', help='.ttl file path OR ontology version ID. Omit to process all installed versions')
        parser.add_argument('--fix_version', action='store_true', help='Whether a mismatch between the versionIRI and installation-version should be corrected')
        parser.add_argument('--require_prior', action='store_true', help='Whether any prior version must also be installed')
        parser.add_argument('--fix_missing_title', action='store_true', help='Whether a missing ontology title should be corrected')
        parser.add_argument('--make_rdf', action='store_true', help='Whether a new or replacement .rdf file should be generated from each .ttl file')
        parser.add_argument('--del_rdf', action='store_true', help='Whether an existing .rdf file should be removed (even if it was just generated)')
        parser.add_argument('--make_htm', action='store_true', help='Whether a new or replacement .htm file should be generated from each .ttl file')
        parser.add_argument('--del_htm', action='store_true', help='Whether an existing .htm file should be removed (even if it was just generated)')
        parser.add_argument('--del_lode_subdir', action='store_true', help='Whether any legacy lode resources subdirectory should be removed')

        args = parser.parse_args()
        kwargs = vars(args)
        target = kwargs.pop('target', None)
        if target and target.endswith('.ttl'):
            # Process a single .ttl file
            expect_version = identify_version(target, fix_semver=True)
            all_passed = process_ttl_file(ttl=target, expect_version=expect_version, **kwargs)
        elif target:
            # Process all .ttl files in the target version
            all_passed = process_version(version=target, **kwargs)
        else:
            # Process all installed ontology versions
            # (but only real directories, not symlinks to directories!)
            results = ValidationResults('All installed versions')
            installed_versions = sorted([
                os.path.basename(d) for d in glob.glob(f'{ONTOLOGY_BASE}/*')
                if os.path.isdir(d) and not os.path.islink(d) and not d.startswith('.')
            ])
            for v in installed_versions:
                passed = process_version(version=v, **kwargs)
                if passed:
                    results.feedback.append(f"Version '{v}' is valid")
                else:
                    results.errors.append(f"Version '{v}' failed validation")
            _logger.log(level=results.log_level, msg=str(results))
            all_passed = results.passed

        if all_passed:
            _logger.info('Validation succeeded')
            sys.exit(0)
        else:
            sys.exit('Validation failed - see log for details')
    except Exception as e:
        _logger.exception('Unexpected error performing validation')
        sys.exit(str(e))
