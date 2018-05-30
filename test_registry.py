from conformity.fields import Dictionary, UnicodeString, List
import json

instance = Dictionary({
    "title": UnicodeString(),
    "url": UnicodeString(),
    "about_url": UnicodeString(),
    "description": UnicodeString(),
    "tags": List(UnicodeString()),
}, optional_keys=["description", "tags", "about_url"])
instances = List(instance)


def test_registry():
    data = json.load(open('registry.json'))
    assert [] == instances.errors(data)
