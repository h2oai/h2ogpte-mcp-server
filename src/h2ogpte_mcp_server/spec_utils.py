"""Helpers for normalizing an OpenAPI spec before FastMCP builds tools from it."""


def relax_nullable_enums(node):
    """Recursively add ``None`` to any ``enum`` marked ``nullable: true`` that omits it.

    OpenAPI 3.0 expresses a nullable enum with ``nullable: true`` *plus* the enum
    list, but many strict validators — including the JSON-schema output validation
    FastMCP generates for each tool — check enum membership independently of
    ``nullable``. When the h2oGPTe API returns a real null for such a field (e.g.
    ``Collection.vex_encryption`` is null when the collection follows the server
    default), validation fails with ``None is not one of ['enabled', 'disabled']``.

    Adding null to the enum keeps the value legal for those validators while
    leaving every other field untouched. The ``node`` is mutated in place.
    """
    if isinstance(node, dict):
        enum = node.get("enum")
        if node.get("nullable") is True and isinstance(enum, list) and None not in enum:
            enum.append(None)
        for value in node.values():
            relax_nullable_enums(value)
    elif isinstance(node, list):
        for value in node:
            relax_nullable_enums(value)
