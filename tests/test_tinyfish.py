from services import tinyfish


class FakeResponse:
    ok = True
    status_code = 200
    text = ""

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def test_search_normalizes_tinyfish_results(monkeypatch):
    def fake_get(url, params, headers, timeout):
        assert params["query"] == "Python internship"
        assert headers["X-API-Key"] == "test-key"
        return FakeResponse({"results": [{"title": "Python Intern", "domain": "example.org", "snippet": "A role", "url": "https://example.org/job"}]})

    monkeypatch.setattr(tinyfish.requests, "get", fake_get)
    results = tinyfish.TinyFishClient("test-key").search("Python internship")
    assert results[0]["title"] == "Python Intern"
    assert results[0]["site_name"] == "example.org"


def test_fetch_sends_supported_fields_and_returns_text(monkeypatch):
    def fake_post(url, json, headers, timeout):
        assert json["urls"] == ["https://example.org/job"]
        assert json["format"] == "markdown"
        assert json["image_links"] is False
        assert json["iframe_links"] is False
        assert json["page_metadata"] is False
        return FakeResponse({"results": [{"url": "https://example.org/job", "title": "Python Intern", "text": "Eligibility details"}], "errors": []})

    monkeypatch.setattr(tinyfish.requests, "post", fake_post)
    page = tinyfish.TinyFishClient("test-key").fetch(["https://example.org/job"])[0]
    assert page["text"] == "Eligibility details"


def test_fetch_rejects_non_http_urls():
    try:
        tinyfish.TinyFishClient("test-key").fetch(["file:///etc/passwd"])
    except tinyfish.TinyFishError as exc:
        assert "Invalid source URL" in str(exc)
    else:
        raise AssertionError("Invalid URL should be rejected")
