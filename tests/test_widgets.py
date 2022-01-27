import pytest

from kobo.django.forms import JSONWidget


@pytest.mark.parametrize(("value", "output"), [
    ('{"a": "b"}', '<textarea id="noid" name="test_widget">{&quot;a&quot;: &quot;b&quot;}</textarea>'),
    ({"a": "b"}, '<textarea id="noid" name="test_widget">{&quot;a&quot;: &quot;b&quot;}</textarea>'),
    ("[1, 2, 3]", '<textarea id="noid" name="test_widget">[1, 2, 3]</textarea>'),
    ([1, 2, 3], '<textarea id="noid" name="test_widget">[1, 2, 3]</textarea>'),
])
def test_JSONWidget(value, output):
    w = JSONWidget()
    assert w.render("test_widget", value, attrs={"id": "noid"}) == output
