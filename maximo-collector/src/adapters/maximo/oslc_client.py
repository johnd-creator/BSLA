"""Read-only OSLC client for Maximo (GET/HEAD/OPTIONS only for business data).

Safety mirrors maximo-knowledge discovery rules:
  * Every /oslc/* request is GET/HEAD/OPTIONS; anything else raises OslcError.
    The ONLY POST in this codebase is the login handshake in auth.py.
  * Site scope (siteid="BSR") applied by default.
  * Rate limiting + response size cap on every request.
  * Session cookies live in memory (requests.Session) — never logged.

Delta sync watermarks: changedate (mxasset/mxwodetail/mxapisr),
statusdate (mxperson/mxitem).
"""

from __future__ import annotations

from contextlib import contextmanager
import logging
import hashlib
import time
from datetime import datetime
from typing import Any, Iterator, Mapping
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlsplit, urlunsplit, urlunparse, unquote

import requests

from src.adapters.maximo.auth import MaximoAuth
from src.config import MaximoConfig

LOG = logging.getLogger(__name__)

READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# These are the only production scopes the collector may use.  The first
# three are site-scoped structures; MXPERSON is an org-level master object on
# this Maximo instance and exposes ``locationorg`` rather than ``siteid``.
_ALLOWED_SCOPE_CLAUSES = frozenset({
    'siteid="BSR"',
    'site="BSR"',
    'worksite="BSR"',
    'locationorg="IP"',
})

OSLC_MEMBER_KEYS = ("_member", "member", "oslc:member", "rdfs:member")

# Detail resources can include large collection references. Keep the response
# below the mandatory 1 MiB cap while retaining every field used by the
# equipment mapper and the verified MXAPIASSET extension allowlist.
ASSET_DETAIL_FIELDS = (
    "assetnum", "assetid", "location", "siteid", "orgid", "status", "status_description",
    "assettype", "plant", "eq11", "parent", "ancestor", "children", "isrunning",
    "installdate", "changedate", "totdowntime", "description", "priority", "failurecode", "issafety",
    "iscalibration", "statusdate", "purchaseprice", "replacecost", "totalcost", "manufacturer",
    "vendor", "ytdcost", "assettype_description", "plant_description", "mainstr",
    "mainstr_description", "hierarchypath", "eq5", "eq9", "eq8", "eq10", "eq11_description",
    "eq23", "newsite", "moved", "pluscismte", "pluscisinhousecal", "tloampartition",
    "removefromactivesp", "mainthierchy", "returnedtovendor", "changepmstatus", "pluscsolution",
    "removefromactiveroutes", "rolltoallchildren", "islinear", "plusgexregistered", "pluscpmextdate",
    "plusciscontam", "disabled", "plusgleaking", "autowogen", "plusgistemp", "plusgispassvalve",
    "moddowntimehist", "totunchargedcost", "unchargedcost", "invcost", "budgetcost", "expectedlife",
)


class OslcError(RuntimeError):
    """Raised for non-read-only requests, transport failures or bad payloads."""


class OslcAuthExpiredError(OslcError):
    """Raised when the session expired mid-request (caller may re-login once)."""


class OslcRequestBudgetExceeded(OslcError):
    """Raised before sending a business request past the configured ceiling."""


class OslcPaginationError(OslcError):
    """Base class for a traversal that cannot be proven complete."""

    def __init__(self, message: str, *, pages: int, next_page_fingerprint: str):
        super().__init__(message)
        self.pages = pages
        self.next_page_fingerprint = next_page_fingerprint


class OslcPaginationLimitError(OslcPaginationError):
    """The safety page cap was reached while another page was advertised."""

    def __init__(self, object_structure: str, *, pages: int, max_pages: int, next_page_fingerprint: str):
        super().__init__(
            f"Maximo pagination for {object_structure} reached max_pages={max_pages} "
            "while another page was available",
            pages=pages,
            next_page_fingerprint=next_page_fingerprint,
        )
        self.max_pages = max_pages


class OslcPaginationLoopError(OslcPaginationError):
    """The source returned a page URL already seen in this traversal."""

    def __init__(self, object_structure: str, *, pages: int, next_page_fingerprint: str):
        super().__init__(
            f"Maximo pagination for {object_structure} repeated a page URL",
            pages=pages,
            next_page_fingerprint=next_page_fingerprint,
        )


def _quote(value: str) -> str:
    return quote(value, safe="")


class OslcClient:
    def __init__(
        self,
        config: MaximoConfig,
        auth: MaximoAuth | None = None,
        session: requests.Session | None = None,
        request_budget: int | None = None,
    ):
        self._config = config
        if config.site_id != "BSR" or config.org_id != "IP":
            raise OslcError("Maximo collector is restricted to site BSR / org IP")
        # Auth and OSLC must share one requests.Session. Otherwise login
        # cookies are stored on one session while business GETs leave through
        # another session and Maximo correctly redirects them to login.jsp.
        if session is None and auth is not None:
            session = auth.session
        self._session = session or requests.Session()
        self._auth = auth or MaximoAuth(config, self._session)
        if self._auth.session is not self._session:
            raise OslcError("Maximo auth and OSLC client must share one HTTP session")
        self._last_request = 0.0
        if request_budget is not None and request_budget < 1:
            raise ValueError("request_budget must be at least 1")
        self._request_budget = request_budget
        self._business_request_count = 0
        self._status_counts: dict[str, int] = {}
        self._detail_request_count = 0
        self._last_iteration_pages = 0
        self._auth_retry_used = False

    @property
    def last_iteration_pages(self) -> int:
        return self._last_iteration_pages

    @property
    def request_telemetry(self) -> dict[str, Any]:
        """Return sanitized request metrics without URLs or response values."""
        return {
            "business_requests": self._business_request_count,
            "status_counts": dict(self._status_counts),
            "detail_requests": self._detail_request_count,
            "budget": self._request_budget,
        }

    @contextmanager
    def bounded_requests(self, limit: int):
        """Limit a traversal including detail reads and authentication retries."""
        if limit < 1:
            raise ValueError("request limit must be positive")
        previous = self._request_budget
        boundary = self._business_request_count + limit
        self._request_budget = min(previous, boundary) if previous is not None else boundary
        try:
            yield
        finally:
            self._request_budget = previous

    # -- low-level request ------------------------------------------------
    def request(self, method: str, path: str) -> requests.Response:
        """GET/HEAD/OPTIONS only. Login POSTs never go through here."""
        method = method.upper()
        if method not in READ_ONLY_METHODS:
            raise OslcError(f"blocked non-read-only method for Maximo: {method}")
        if self._request_budget is not None and self._business_request_count >= self._request_budget:
            raise OslcRequestBudgetExceeded(
                f"Maximo business request budget exhausted at {self._request_budget} requests"
            )
        last_request = max(
            self._last_request,
            getattr(self._auth, "last_request_at", 0.0),
        )
        delay = self._config.rate_limit_seconds - (time.monotonic() - last_request)
        if delay > 0:
            time.sleep(delay)
        base_path = urlsplit(self._config.base_url).path.rstrip("/")
        if path.startswith(("http://", "https://")):
            url = path
        elif base_path and path.startswith(base_path + "/"):
            base = urlsplit(self._config.base_url)
            url = urlunsplit((base.scheme, base.netloc, path, "", ""))
        else:
            url = self._config.base_url + path
        # Maximo can return the web login shell (HTTP 200) when content
        # negotiation is omitted. OSLC calls must explicitly request JSON.
        self._business_request_count += 1
        resp = self._session.request(
            method,
            url,
            headers={"Accept": "application/json"},
            timeout=self._config.timeout_seconds,
            allow_redirects=False,
        )
        status = str(getattr(resp, "status_code", "unknown"))
        self._status_counts[status] = self._status_counts.get(status, 0) + 1
        self._last_request = time.monotonic()
        if len(resp.content) > self._config.max_response_bytes:
            raise OslcError(
                f"Maximo {method} {path} returned oversized body "
                f"({len(resp.content)} > {self._config.max_response_bytes} bytes)"
            )
        return resp

    def get(self, path: str) -> requests.Response:
        return self.request("GET", path)

    # -- OSLC helpers -----------------------------------------------------
    def iterate(self, object_structure: str, **kwargs) -> Iterator[Mapping[str, Any]]:
        for page in self.iterate_pages(object_structure, **kwargs):
            yield from page

    def iterate_pages(
        self,
        object_structure: str,
        *,
        where: str | None = None,
        required_scope: str | None = None,
        select: list[str] | None = None,
        order_by: str | None = None,
        page_size: int | None = None,
        max_pages: int = 1000,
        identity_field: str | None = None,
        strict_members: bool = False,
        allow_resource_links: bool = True,
    ) -> Iterator[list[Mapping[str, Any]]]:
        """Paginate through an OSLC object structure (GET only).

        Logs in lazily on the first request; on session expiry re-logs-in
        once and retries the page.
        """
        required_scope = required_scope or _default_scope_clause(
            object_structure, self._config.site_id, self._config.org_id
        )
        if required_scope not in _ALLOWED_SCOPE_CLAUSES:
            raise OslcError(f"unsupported Maximo scope clause: {required_scope}")
        if page_size is not None and not 1 <= page_size <= self._config.page_size:
            raise OslcError(
                f"Maximo page_size must be between 1 and {self._config.page_size}"
            )
        if max_pages < 1:
            raise OslcError("Maximo max_pages must be at least 1")
        effective_page_size = page_size or self._config.page_size
        if where is None:
            where = required_scope
        elif required_scope not in where:
            raise OslcError(f"every {object_structure} query must include {required_scope}")
        params: list[tuple[str, str]] = [
            ("oslc.paging", "true"),
            ("oslc.pageSize", str(effective_page_size)),
            ("oslc.where", where),
        ]
        if order_by:
            params.append(("oslc.orderBy", order_by))
        if select:
            params.append(("oslc.select", ",".join(select)))

        base = f"{self._config.oslc_root}/{object_structure}"
        url = f"{base}?{urlencode(params, doseq=True)}"
        pages = 0
        retried_auth = False
        seen_page_fingerprints: set[str] = set()
        previous_page_ids: set[str] = set()
        self._last_iteration_pages = 0
        while url:
            page_fingerprint = _page_fingerprint(url)
            if page_fingerprint in seen_page_fingerprints:
                raise OslcPaginationLoopError(
                    object_structure,
                    pages=pages,
                    next_page_fingerprint=page_fingerprint,
                )
            if pages >= max_pages:
                raise OslcPaginationLimitError(
                    object_structure,
                    pages=pages,
                    max_pages=max_pages,
                    next_page_fingerprint=page_fingerprint,
                )
            seen_page_fingerprints.add(page_fingerprint)
            pages += 1
            self._last_iteration_pages = pages
            self._auth.ensure_logged_in()
            resp = self.get(url)
            if MaximoAuth.looks_expired(resp):
                if retried_auth or self._auth_retry_used:
                    raise OslcAuthExpiredError(
                        f"Maximo session still unauthenticated after re-login: HTTP {resp.status_code}"
                    )
                retried_auth = True
                self._auth_retry_used = True
                self._auth.handle_expiry()
                seen_page_fingerprints.remove(page_fingerprint)
                pages -= 1
                continue  # retry exactly this page once; request budget still applies
            if resp.status_code == 403:
                raise OslcError(f"Maximo returned HTTP 403 for {object_structure}; account lacks READ permission")
            resp.raise_for_status()
            payload = resp.json()
            members = _extract_members(payload)
            if strict_members:
                collection = payload if isinstance(payload, list) else next(
                    (payload[k] for k in OSLC_MEMBER_KEYS if k in payload), None
                ) if isinstance(payload, Mapping) else None
                if isinstance(collection, Mapping):
                    collection = [collection]
                if not isinstance(collection, list) or len(collection) != len(members):
                    raise OslcError("invalid OSLC collection shape")
            normalized_page = []
            page_ids: set[str] = set()
            for member in members:
                if _is_resource_link(member):
                    if not allow_resource_links:
                        raise OslcError("resource-only payload refused for exact asset lookup")
                    resource_url = _normalize_next_page_url(
                        str(member["rdf:resource"]), self._config.base_url
                    )
                    if not resource_url:
                        raise OslcError("invalid resource link")
                    if object_structure.lower() == "mxwodetail":
                        _validate_wo_url(resource_url, self._config.base_url, base, detail=True)
                    resource_url = _add_detail_select(resource_url)
                    if object_structure.lower() == "mxwodetail" and select:
                        parsed = urlsplit(resource_url)
                        query = [(k,v) for k,v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() != "oslc.select"]
                        query.append(("oslc.select", ",".join(select)))
                        resource_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
                    self._detail_request_count += 1
                    detail = self.get(resource_url)
                    if MaximoAuth.looks_expired(detail):
                        if retried_auth or self._auth_retry_used:
                            raise OslcAuthExpiredError(
                                "Maximo session expired while reading a resource link"
                            )
                        retried_auth = True
                        self._auth_retry_used = True
                        self._auth.handle_expiry()
                        self._detail_request_count += 1
                        detail = self.get(resource_url)
                    detail.raise_for_status()
                    detail_payload = detail.json()
                    if not isinstance(detail_payload, Mapping):
                        raise OslcError("Maximo resource link did not return a JSON object")
                    normalized = _normalize_member(detail_payload)
                else:
                    normalized = _normalize_member(member)
                if identity_field:
                    identity = str(normalized.get(identity_field) or "").strip()
                    if identity:
                        page_ids.add(identity)
                normalized_page.append(normalized)
            overlap = len(page_ids & previous_page_ids)
            LOG.info(
                "Maximo pagination object=%s page=%d distinct_ids=%d overlap_previous=%d",
                object_structure,
                pages,
                len(page_ids),
                overlap,
            )
            previous_page_ids = page_ids
            next_url = _next_page_url(payload)
            if next_url and next_url.startswith("?"):
                next_url = urljoin(url, next_url)
            url = _normalize_next_page_url(next_url, self._config.base_url) or ""
            if url and object_structure.lower() == "mxwodetail":
                _validate_wo_url(url, self._config.base_url, base, detail=False)
            yield normalized_page


def _validate_wo_url(url, base_url, collection, *, detail):
    path = urlsplit(url).path
    for _ in range(3):
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    if "%" in path or "\\" in path or any(part in {".", ".."} for part in path.split("/")):
        raise OslcError("ambiguous WO resource path")
    path = path.rstrip("/").lower()
    full = urlsplit(base_url.rstrip("/") + collection).path.rstrip("/").lower()
    allowed = {collection.rstrip("/").lower(), full}
    if not any(path.startswith(p + "/") if detail else path == p for p in allowed):
        raise OslcError("WO link left its object scope")


def _extract_members(payload: Any) -> list[Mapping[str, Any]]:
    """Extract member records from an OSLC collection.

    Verified shape (maximo-knowledge): records live under ``_member`` with
    generic OSLC fallbacks.
    """
    if isinstance(payload, list):
        return [m for m in payload if isinstance(m, Mapping)]
    if isinstance(payload, Mapping):
        for key in OSLC_MEMBER_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return [m for m in value if isinstance(m, Mapping)]
            if isinstance(value, Mapping):
                return [value]
    return []


def _default_scope_clause(object_structure: str, site_id: str, org_id: str) -> str:
    """Return the verified BSR/IP scope for an OSLC object structure."""
    if object_structure.lower() == "mxperson":
        return f'locationorg="{org_id}"'
    if object_structure.lower() == "mxitem":
        return f'site="{site_id}"'
    if object_structure.lower() == "mxapilabor":
        return f'worksite="{site_id}"'
    return f'siteid="{site_id}"'


def _is_resource_link(member: Mapping[str, Any]) -> bool:
    """Whether a collection member is an RDF link to a detail resource."""
    return isinstance(member.get("rdf:resource"), str) and not any(
        str(key).startswith("spi:") for key in member
    )


def _normalize_member(member: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize Maximo's ``spi:`` business namespace for the mappers."""
    normalized: dict[str, Any] = {}
    for key, value in member.items():
        name = key[4:] if str(key).startswith("spi:") else key
        normalized[name] = value
    return normalized


def _add_detail_select(resource_url: str) -> str:
    """Limit asset detail responses to the verified scalar field allowlist."""
    parsed = urlsplit(resource_url)
    if "/mxapiasset/" not in parsed.path.lower() and "/mxasset/" not in parsed.path.lower():
        return resource_url
    query = parse_qsl(parsed.query, keep_blank_values=True)
    if any(key.lower() == "oslc.select" for key, _ in query):
        return resource_url
    query.append(("oslc.select", ",".join(ASSET_DETAIL_FIELDS)))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


def _next_page_url(payload: Mapping[str, Any]) -> str | None:
    """Next-page link: nested under oslc:responseInfo (verified) + fallbacks."""
    if not isinstance(payload, Mapping):
        return None
    info = payload.get("oslc:responseInfo")
    info = info if isinstance(info, Mapping) else {}
    next_url = info.get("oslc:nextPage") or payload.get("oslc:nextPage") or payload.get("nextPage")
    if isinstance(next_url, Mapping):
        next_url = (
            next_url.get("rdf:resource")
            or next_url.get("resource")
            or next_url.get("href")
            or next_url.get("@id")
        )
    return str(next_url) if next_url else None


def _page_fingerprint(url: str) -> str:
    """Return a non-sensitive fingerprint for pagination-loop diagnostics."""
    # The URL is needed transiently to make the request, but logs contain only
    # a digest. This prevents query values such as a future session token from
    # appearing in observability output.
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def _normalize_next_page_url(next_url: str | None, base_url: str) -> str | None:
    """Keep Maximo pagination on the configured load-balancer origin.

    Some Maximo deployments emit an internal application-node hostname in
    ``rdf:resource``. Cookies obtained from the public base URL do not match
    that hostname, so following it would lose the authenticated session. Do
    not rewrite or follow that URL: the caller must fix the reverse proxy or
    use an API credential whose origin is explicitly approved.
    """
    if not next_url:
        return None
    base = urlparse(base_url)
    page = urlparse(next_url)
    if page.scheme and page.netloc:
        if page.scheme not in {"http", "https"}:
            raise OslcError("Maximo pagination returned an unsupported URL scheme")
        if page.netloc.lower() != base.netloc.lower():
            raise OslcError(
                "Maximo pagination returned a different origin "
                f"({page.netloc}); refusing to send the authenticated session "
                f"outside configured origin ({base.netloc})"
            )
        return urlunparse((base.scheme, base.netloc, page.path, page.params, page.query, page.fragment))
    if next_url.startswith("/"):
        return next_url
    return urljoin(base_url.rstrip("/") + "/", next_url)


# -- scalar coercion helpers (Maximo booleans are often strings) ----------
def oslc_boolean(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def oslc_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def oslc_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    text = str(value)
    if len(text) >= 19 and text[10] == "T":
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def oslc_pop_text(member: Mapping[str, Any], key: str) -> str | None:
    value = member.get(key)
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("value") or value.get("rdf:label") or value.get("@value")
    value = str(value).strip()
    return value or None


def oslc_pop_bool(member: Mapping[str, Any], key: str) -> bool | None:
    return oslc_boolean(member.get(key))


def oslc_pop_number(member: Mapping[str, Any], key: str) -> float | None:
    return oslc_number(member.get(key))


def oslc_pop_integer(member: Mapping[str, Any], key: str) -> int | None:
    value = oslc_number(member.get(key))
    if value is None or not value.is_integer():
        return None
    return int(value)
