"""Small, defensive client for TinyFish Search and Fetch REST APIs."""

from urllib.parse import urlparse

import requests

SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"


class TinyFishError(Exception):
    """Friendly error for TinyFish API failures."""


class TinyFishClient:
    def __init__(self, api_key: str, timeout: int = 150):
        if not api_key or not api_key.strip():
            raise TinyFishError("A TinyFish API key is required.")
        self.api_key = api_key.strip()
        self.timeout = timeout
        self.headers = {"X-API-Key": self.api_key, "Accept": "application/json"}

    @staticmethod
    def _json(response, operation: str):
        if not response.ok:
            detail = (getattr(response, "text", "") or "").replace("\n", " ")[:350]
            if response.status_code == 401:
                raise TinyFishError(f"{operation}: API key rejected (HTTP 401). Check your .env file.")
            if response.status_code == 402:
                raise TinyFishError(f"{operation}: TinyFish allowance or wallet limit reached (HTTP 402).")
            if response.status_code == 429:
                raise TinyFishError(f"{operation}: rate limit reached. Wait a moment and retry.")
            raise TinyFishError(f"{operation} returned HTTP {response.status_code}: {detail}")
        try:
            return response.json()
        except (ValueError, AttributeError) as exc:
            raise TinyFishError(f"{operation} response was not valid JSON.") from exc

    def search(self, query: str, location: str = "IN", language: str = "en", purpose: str = "Find relevant student opportunities"):
        if not query or not query.strip():
            raise TinyFishError("Enter a search query first.")
        params = {"query": query.strip(), "location": location, "language": language}
        if purpose and purpose.strip():
            params["purpose"] = purpose.strip()
        try:
            response = requests.get(SEARCH_URL, params=params, headers=self.headers, timeout=self.timeout)
        except requests.RequestException as exc:
            raise TinyFishError(f"Network error during Search: {exc}") from exc
        payload = self._json(response, "Search")
        results = payload.get("results", []) if isinstance(payload, dict) else []
        if not isinstance(results, list):
            raise TinyFishError("Search response did not contain a results list.")
        clean = []
        for result in results:
            if not isinstance(result, dict):
                continue
            url = str(result.get("url") or "").strip()
            clean.append({
                "title": str(result.get("title") or "Untitled result"),
                "site_name": str(result.get("site_name") or result.get("domain") or ""),
                "snippet": str(result.get("snippet") or ""),
                "url": url,
                "date": str(result.get("date") or ""),
            })
        return clean

    def fetch(self, urls):
        if not urls:
            return []
        valid_urls = []
        for url in urls[:10]:
            parsed = urlparse(str(url))
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise TinyFishError(f"Invalid source URL: {url}")
            valid_urls.append(str(url))
        body = {
            "urls": valid_urls,
            "format": "markdown",
            "links": True,
            "image_links": False,
            "iframe_links": False,
            "page_metadata": False,
        }
        try:
            response = requests.post(
                FETCH_URL,
                json=body,
                headers={**self.headers, "Content-Type": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise TinyFishError(f"Network error during Fetch: {exc}") from exc
        payload = self._json(response, "Fetch")
        results = payload.get("results", []) if isinstance(payload, dict) else []
        errors = payload.get("errors", []) if isinstance(payload, dict) else []
        if not isinstance(results, list):
            raise TinyFishError("Fetch response did not contain a results list.")
        clean = []
        for result in results:
            if isinstance(result, dict):
                clean.append({
                    "url": result.get("url", ""),
                    "final_url": result.get("final_url", ""),
                    "title": result.get("title", ""),
                    "text": result.get("text", "") or "",
                    "format": result.get("format", "markdown"),
                })
        if not clean and errors:
            first = errors[0] if isinstance(errors[0], dict) else {}
            code = first.get("error", "fetch_failed")
            failed_url = first.get("url", "the selected page")
            raise TinyFishError(f"TinyFish could not fetch {failed_url} ({code}). Try opening the source directly.")
        return clean
