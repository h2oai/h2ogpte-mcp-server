from h2ogpte_mcp_server.spec_utils import relax_nullable_enums


def test_adds_null_to_nullable_enum():
    # Regression: Collection.vex_encryption is nullable but the enum omitted null,
    # so a real null tripped output validation ("None is not one of [...]").
    spec = {
        "components": {
            "schemas": {
                "Collection": {
                    "properties": {
                        "vex_encryption": {
                            "type": "string",
                            "enum": ["enabled", "disabled"],
                            "nullable": True,
                        }
                    }
                }
            }
        }
    }
    relax_nullable_enums(spec)
    assert spec["components"]["schemas"]["Collection"]["properties"]["vex_encryption"][
        "enum"
    ] == ["enabled", "disabled", None]


def test_leaves_non_nullable_enum_untouched():
    spec = {"field": {"type": "string", "enum": ["a", "b"]}}
    relax_nullable_enums(spec)
    assert spec["field"]["enum"] == ["a", "b"]


def test_idempotent_when_null_already_present():
    spec = {"field": {"enum": ["a", None], "nullable": True}}
    relax_nullable_enums(spec)
    assert spec["field"]["enum"] == ["a", None]


def test_walks_nested_lists_and_dicts():
    spec = {"oneOf": [{"enum": ["x"], "nullable": True}, {"no": "enum"}]}
    relax_nullable_enums(spec)
    assert spec["oneOf"][0]["enum"] == ["x", None]
