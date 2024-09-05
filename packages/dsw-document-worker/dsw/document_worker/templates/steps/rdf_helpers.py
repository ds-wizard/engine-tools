from rdflib import URIRef, Literal


def build_term(g, uri):
    if uri is not None:
        # URI: ':title'
        if uri.startswith(":"):
            return URIRef(g.namespace_manager.store.namespace('') + uri[1:])

        # URI: 'rda:title'
        splitted = uri.split(":")
        if len(splitted) == 2 and splitted[1][0] != "/":
            return URIRef(g.namespace_manager.store.namespace(splitted[0]) + splitted[1])

        # URI: 'http://schema.org/person#title'
        if "://" in uri:
            return URIRef(uri)

        # Literal
        return Literal(uri)


def shorten_uri(g, uri):
    return uri


def get_subjects_by(g, predicate, object):
    return g.subjects(build_term(g, predicate), build_term(g, object))


def get_objects_by(g, subject, predicate):
    return g.objects(build_term(g, subject), build_term(g, predicate))


def get_sparql(g, query, init_bindings):
    return list(g.query(query, initBindings=init_bindings))


def get_subject_by(g, predicate, object):
    return next(get_subjects_by(g, predicate, object), None)


def get_object_by(g, subject, predicate):
    return next(get_objects_by(g, subject, predicate), None)


def get_sparql_one(g, query):
    return list(g.query(query))[0]
