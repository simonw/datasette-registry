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

def test_registry_sort_order():
    data = json.load(open('registry.json'))
    try:
        assert data == sorted(data, key=lambda x: x['title'].lower())
    except AssertionError:
        print("Sort with `jq -c 'sort_by(.title| ascii_downcase)' registry.json | jq '.' > temp.json && mv temp.json registry.json`")
        raise
