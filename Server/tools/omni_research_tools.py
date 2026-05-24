"""
Omni Research Tool — web search, page fetching, GPS geocoding.

Pure-Python, key-less sources:
- search: DuckDuckGo HTML endpoint (no API key)
- fetch:  urllib + html-to-text fallback (no BeautifulSoup dep)
- geocode: OpenStreetMap Nominatim (no API key, polite User-Agent required)
"""

import logging
import html
import re
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")

USER_AGENT = "omni-unreal-mcp/0.1 (https://github.com/InventiveHQ/omni-unreal-mcp)"


def _http_get(url: str, accept: str = "*/*", timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _strip_html(text: str) -> str:
    """Quick-and-dirty HTML → text. Good enough for snippets."""
    # Drop script/style blocks
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    # Tags → space
    text = re.sub(r"<[^>]+>", " ", text)
    # Entities
    text = html.unescape(text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def register_omni_research_tools(mcp: FastMCP):
    """Register deep_research."""

    @mcp.tool()
    def deep_research(
        ctx: Context,
        action: str,
        query: str = "",
        url: str = "",
        place: str = "",
        max_results: int = 5,
        max_chars: int = 4000,
    ) -> Dict[str, Any]:
        """Web search, page fetching, and geocoding — no API keys required.

        Actions:
            search:  DuckDuckGo search for `query`, return top `max_results` hits
                     as {title, url, snippet}.
            fetch:   GET `url`, return plain-text excerpt (truncated to max_chars).
            geocode: OpenStreetMap Nominatim lookup for `place`, return list of
                     candidates with {display_name, lat, lon, type}.
        """
        try:
            a = action.lower()
            if a == "search":
                if not query:
                    return {"success": False, "error": "search requires 'query'"}
                # DDG HTML endpoint returns parseable results
                ddg = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                body = _http_get(ddg, accept="text/html")
                results: List[Dict[str, str]] = []
                # Each result block is anchored on class="result__a" link.
                for m in re.finditer(
                    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>'
                    r'.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
                    body, flags=re.S):
                    raw_url, raw_title, raw_snip = m.group(1), m.group(2), m.group(3)
                    # DDG sometimes wraps the real URL in /l/?uddg=
                    parsed = urllib.parse.urlparse(raw_url)
                    if parsed.path == "/l/" and parsed.query:
                        q = urllib.parse.parse_qs(parsed.query)
                        if "uddg" in q:
                            raw_url = urllib.parse.unquote(q["uddg"][0])
                    results.append({
                        "title": _strip_html(raw_title),
                        "url": raw_url,
                        "snippet": _strip_html(raw_snip),
                    })
                    if len(results) >= max_results:
                        break
                return {"success": True, "query": query, "results": results, "count": len(results)}

            if a == "fetch":
                if not url:
                    return {"success": False, "error": "fetch requires 'url'"}
                body = _http_get(url, accept="text/html,*/*")
                text = _strip_html(body)
                truncated = len(text) > max_chars
                return {
                    "success": True, "url": url,
                    "text": text[:max_chars],
                    "char_count": len(text), "truncated": truncated,
                }

            if a == "geocode":
                if not place:
                    return {"success": False, "error": "geocode requires 'place'"}
                nom = ("https://nominatim.openstreetmap.org/search?format=json&"
                       f"q={urllib.parse.quote(place)}&limit={int(max_results)}")
                body = _http_get(nom, accept="application/json")
                import json
                entries = json.loads(body)
                candidates = [
                    {
                        "display_name": e.get("display_name"),
                        "lat": float(e["lat"]) if "lat" in e else None,
                        "lon": float(e["lon"]) if "lon" in e else None,
                        "type": e.get("type"),
                    }
                    for e in entries
                ]
                return {"success": True, "place": place, "candidates": candidates, "count": len(candidates)}

            return {"success": False, "error": f"Unknown action: {action}"}
        except urllib.error.HTTPError as e:
            return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return {"success": False, "error": f"Network error: {e.reason}"}
        except Exception as e:
            logger.error(f"deep_research failed: {e}")
            return {"success": False, "error": str(e)}
