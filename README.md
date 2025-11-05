# Data Provider Node Ontology

- [About the Data Provider Node Ontology](#about-the-data-provider-node-ontology)
- [DPN Ontology Namespaces and Permalinks](#dpn-ontology-namespaces-and-permalinks)
- [DPN Ontology Server](#dpn-ontology-server)

## About the Data Provider Node Ontology

This ontology is being developed by [CSIRO](https://www.csiro.au) for the [eReefs Platform](https://ereefs.org.au).
It is under active development, and will have occasional releases as required to support the evolution of the eReefs platform.

It is used to describe the concepts and properties of Data Provider Nodes (DPNs), the datasets that are published via those nodes, and the web services by which those dataset can be accessed.

It also features a module for describing Datasets. It does not however describe geospatial, temporal, organisational or domain concepts as these are intended to be included from other ontologies via the imports statement.

This version aligns DCAT and DC terms and imports DPN services.

## DPN Ontology Namespaces and Permalinks

The relevant permalinks (Internationalized Resource Identifiers, or IRIs) for the DPN Ontology definitions are:

- [dpn.ttl](./dpn.ttl) => <http://purl.org/dpn>
- [dpn-services.ttl](./dpn-services.ttl) => <http://purl.org/dpn/services>
- [dpn-dataset.ttl](./dpn-dataset.ttl) => <http://purl.org/dpn/dataset>

The hosted version of these resources supports content negotiation via the [HTTP Accept Header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Accept), and you may request the definitions in any of several formats:

- Human-readable HTML => `application/xhtml+xml`
- [Turtle](https://en.wikipedia.org/wiki/Turtle_(syntax)) => `text/turtle`
- [RDF/XML](https://en.wikipedia.org/wiki/RDF/XML) => `application/rdf+xml`
- [JSON-LD](https://en.wikipedia.org/wiki/JSON-LD) => `application/ld+json`
- [N-triples](https://en.wikipedia.org/wiki/N-Triples) => `application/n-triples`

The Data Provider Node Ontology Definitions in this repository and the hosted versions of those definitions accessed via the permalinks listed above are published under the [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/) license (`CC-BY-4.0`).  Please see the [eReefs Attribution Requirements](https://www.ereefs.org.au/legal/copyright-and-licence#attribution-requirements) for details of our preferred attribution.

## DPN Ontology Server

The [server](./server) subdirectory of this repository contains definitions for a web application which is used by the eReefs team to host this ontology in production.

Please refer to the [Server README](./server/README.md) for more information about how it works.

The server software is published under a `BSD 3-Clause` [software license](./server/LICENSE).
