"""Free web search providers and a page fetcher. Standard library plus optional `ddgs` package."""

import html
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser

USER_AGENT = "consearch/0.1 (conversational research assistant; contact: you@example.com)"


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


def _strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.load(resp)


class DuckDuckGoSearch:
    """No API key. Uses the `ddgs` package. It is an unofficial client, so it can be rate limited under heavy use."""

    def search(self, query: str, count: int = 5) -> list[SearchResult]:
        from ddgs import DDGS  # pip install ddgs

        rows = DDGS().text(query, max_results=count) or []
        return [
            SearchResult(title=r.get("title", ""), url=r["href"], snippet=r.get("body", ""))
            for r in rows if r.get("href")
        ]


class WikipediaSearch:
    """No API key. Official MediaWiki API. Strong for encyclopedic facts, weak for news."""

    ENDPOINT = "https://en.wikipedia.org/w/api.php"

    def search(self, query: str, count: int = 5) -> list[SearchResult]:
        params = urllib.parse.urlencode({
            "action": "query", "list": "search", "srsearch": query,
            "srlimit": count, "format": "json", "utf8": 1,
        })
        data = _get_json(f"{self.ENDPOINT}?{params}")
        results = []
        for item in data.get("query", {}).get("search", []):
            slug = urllib.parse.quote(item["title"].replace(" ", "_"))
            results.append(SearchResult(
                title=item["title"],
                url=f"https://en.wikipedia.org/wiki/{slug}",
                snippet=_strip_tags(item.get("snippet", "")),
            ))
        return results


class SearxngSearch:
    """Free and self-hosted. Run SearXNG with JSON output enabled in settings.yml (search.formats: [html, json])."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def search(self, query: str, count: int = 5) -> list[SearchResult]:
        params = urllib.parse.urlencode({"q": query, "format": "json"})
        data = _get_json(f"{self.base_url}/search?{params}")
        return [
            SearchResult(title=r.get("title", ""), url=r["url"], snippet=_strip_tags(r.get("content", "")))
            for r in data.get("results", [])[:count]
        ]


def make_search(provider: str, searxng_url: str | None = None):
    if provider == "duckduckgo":
        return DuckDuckGoSearch()
    if provider == "wikipedia":
        return WikipediaSearch()
    if provider == "searxng":
        if not searxng_url:
            raise ValueError("SEARXNG_URL must be set when SEARCH_PROVIDER=searxng")
        return SearxngSearch(searxng_url)
    raise ValueError(f"Unknown search provider: {provider}")


class _TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "nav", "footer", "svg", "form"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.title = ""
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip and data.strip():
            self.parts.append(data.strip())


def fetch_page(url: str, max_chars: int = 50_000) -> tuple[str, str]:
    """Download a page and return (title, plain text)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        content_type = resp.headers.get_content_type()
        charset = resp.headers.get_content_charset() or "utf-8"
        raw = resp.read(max_chars * 4)
    body = raw.decode(charset, errors="replace")
    if content_type != "text/html":
        return url, body[:max_chars]

    parser = _TextExtractor()
    parser.feed(body)
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    return parser.title.strip() or url, text[:max_chars]
