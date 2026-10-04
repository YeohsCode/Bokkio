from bokkio.model import BokkioError, RefResolver, stable_hash


def test_ref_resolver_returns_matching_node_and_rejects_stale_ref():
    node = {"ref": stable_hash("same"), "children": []}
    resolver = RefResolver([node])
    assert resolver.get(node["ref"]) is node
    try:
        resolver.get("missing")
    except BokkioError as error:
        assert "new snapshot" in str(error)
    else:
        raise AssertionError("missing ref must fail")
