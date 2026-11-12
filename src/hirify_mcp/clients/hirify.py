"""HTTP API client for Hirify job board using httpx."""

import time
from typing import Any, Dict, List, Optional, Tuple, cast

import httpx

from hirify_mcp.clients.exceptions import (
    HirifyAPIError,
    HirifyError,
    HirifyNetworkError,
    HirifyNotFoundError,
    HirifyRateLimitError,
    HirifyResponseError,
    HirifyTimeoutError,
)
from hirify_mcp.config import logger, settings
from hirify_mcp.models import VacancyDetails, VacancySummary


class TTLCache:
    """Simple in-memory TTL cache with entry expiration."""

    def __init__(self, default_ttl: int = 300, enabled: bool = True):
        self.default_ttl = default_ttl
        self.enabled = enabled
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        if key in self._cache:
            expires_at, value = self._cache[key]
            if time.time() < expires_at:
                return value
            # Expired
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if not self.enabled:
            return
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        self._cache[key] = (time.time() + ttl_seconds, value)

    def clear(self) -> None:
        self._cache.clear()


class HirifyClient:
    """Robust, production-grade HTTP client for the Hirify API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        enable_cache: Optional[bool] = None,
        cache_ttl: Optional[int] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self.base_url = (base_url or settings.API_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.REQUEST_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.MAX_RETRIES
        self.backoff_factor = (
            backoff_factor if backoff_factor is not None else settings.RETRY_BACKOFF
        )

        cache_active = enable_cache if enable_cache is not None else settings.CACHE_ENABLED
        ttl = cache_ttl if cache_ttl is not None else settings.CACHE_TTL
        self.cache = TTLCache(default_ttl=ttl, enabled=cache_active)

        self._headers = {
            "User-Agent": "HirifyMCP/0.2.0 (+https://github.com/VladMontana/hirify_mcp)",
            "Accept": "application/json",
        }
        self._client = http_client or httpx.Client(
            timeout=self.timeout,
            headers=self._headers,
            follow_redirects=True,
        )
        self._own_client = http_client is None

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._own_client and not self._client.is_closed:
            self._client.close()

    def __enter__(self) -> "HirifyClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Execute an HTTP request with retry logic, backoff, and caching."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        cache_key = f"{method}:{url}:{sorted(params.items()) if params else ''}"

        if method.upper() == "GET" and use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data is not None and isinstance(cached_data, dict):
                logger.debug(f"Cache hit for {url}")
                return cast(Dict[str, Any], cached_data)

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                # Polite rate limiting delay between network calls
                if settings.RATE_LIMIT_DELAY > 0:
                    time.sleep(settings.RATE_LIMIT_DELAY)

                logger.debug(f"Request {method} {url} with params {params} (attempt {attempt + 1})")
                response = self._client.request(
                    method=method,
                    url=url,
                    params=params,
                )

                # HTTP 404
                if response.status_code == 404:
                    raise HirifyNotFoundError(
                        message=f"Hirify endpoint or resource not found: {url}",
                        status_code=404,
                        response_body=response.text,
                    )

                # HTTP 429
                if response.status_code == 429:
                    retry_after_str = response.headers.get("Retry-After")
                    retry_after = (
                        float(retry_after_str)
                        if retry_after_str and retry_after_str.isdigit()
                        else (self.backoff_factor * (2**attempt))
                    )
                    logger.warning(f"Hirify rate limit (429) hit. Waiting {retry_after}s...")
                    if attempt < self.max_retries:
                        time.sleep(retry_after)
                        continue
                    raise HirifyRateLimitError(
                        message="Hirify API rate limit exceeded",
                        retry_after=retry_after,
                        status_code=429,
                        response_body=response.text,
                    )

                # HTTP 5xx Server errors - retryable
                if 500 <= response.status_code < 600:
                    if attempt < self.max_retries:
                        sleep_time = self.backoff_factor * (2**attempt)
                        logger.warning(
                            f"Hirify server error {response.status_code} on {url}. Retrying in {sleep_time:.2f}s..."
                        )
                        time.sleep(sleep_time)
                        continue
                    raise HirifyAPIError(
                        message=f"Hirify server error: {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                # Other HTTP 4xx Client errors - NOT retryable
                if 400 <= response.status_code < 500:
                    raise HirifyAPIError(
                        message=f"Hirify client error: {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                # Validate JSON Content-Type and parse
                try:
                    data = response.json()
                except Exception as ex:
                    raise HirifyResponseError(
                        message=f"Failed to parse JSON response from Hirify: {ex}",
                        status_code=response.status_code,
                        response_body=response.text,
                    ) from ex

                if not isinstance(data, (dict, list)):
                    raise HirifyResponseError(
                        message=f"Unexpected response data type: {type(data)}",
                        status_code=response.status_code,
                    )

                # Cache successful GET responses
                if method.upper() == "GET" and use_cache and isinstance(data, dict):
                    self.cache.set(cache_key, data)

                return cast(Dict[str, Any], data)

            except httpx.TimeoutException as ex:
                last_exception = ex
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2**attempt)
                    logger.warning(f"Timeout on {url}. Retrying in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    continue
                raise HirifyTimeoutError(f"Request to Hirify timed out: {url}") from ex

            except httpx.NetworkError as ex:
                last_exception = ex
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2**attempt)
                    logger.warning(
                        f"Network error on {url}: {ex}. Retrying in {sleep_time:.2f}s..."
                    )
                    time.sleep(sleep_time)
                    continue
                raise HirifyNetworkError(f"Network connection failed: {url} ({ex})") from ex

            except (HirifyAPIError, HirifyNotFoundError, HirifyRateLimitError, HirifyResponseError):
                # Re-raise explicit API errors immediately
                raise

            except Exception as ex:
                last_exception = ex
                logger.error(f"Unexpected error during Hirify request: {ex}")
                raise HirifyError(f"Unexpected error: {ex}") from ex

        if last_exception:
            raise HirifyNetworkError(f"Request failed after retries: {last_exception}")
        raise HirifyError("Unknown request failure")

    def search_vacancies(
        self,
        query: Optional[str] = None,
        grade: Optional[str] = None,
        work_format: Optional[str] = None,
        specialization: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        max_page_requests: Optional[int] = None,
        use_cache: bool = True,
    ) -> List[VacancySummary]:
        """Fetch list of vacancies matching parameters across pages.

        Args:
            query: Search keywords passed as 'search' param to Hirify API
            grade: Seniority level (e.g. 'junior', 'middle', 'senior', 'lead')
            work_format: 'remote', 'hybrid', 'onsite'
            specialization: Hirify spec code (e.g. 'backend_dev', 'frontend_dev', 'devops')
            page: Starting page number (1-based)
            limit: Maximum items to return
            max_page_requests: Maximum number of pagination pages to fetch
            use_cache: Whether to use TTL cache

        Returns:
            List of parsed VacancySummary objects.

        Raises:
            HirifyAPIError / HirifyNetworkError if the API request fails.
        """
        vacancies: List[VacancySummary] = []
        seen_ids = set()
        current_page = page
        max_pages = max_page_requests or settings.MAX_PAGE_REQUESTS
        pages_fetched = 0

        while len(vacancies) < limit and pages_fetched < max_pages:
            param_list: List[Tuple[str, str]] = [("page", str(current_page))]
            if query:
                param_list.append(("search", query))
            if grade:
                param_list.append(("grade[]", grade.lower()))
            if work_format:
                param_list.append(("work_format[]", work_format.lower()))
            if specialization:
                param_list.append(("specializations[]", specialization.lower()))

            # Use dict of tuples for httpx params
            params_dict: Dict[str, Any] = {}
            for k, v in param_list:
                if k in params_dict:
                    if isinstance(params_dict[k], list):
                        params_dict[k].append(v)
                    else:
                        params_dict[k] = [params_dict[k], v]
                else:
                    params_dict[k] = v

            raw_data = self._request("GET", "vacancies", params=params_dict, use_cache=use_cache)
            pages_fetched += 1

            raw_items = raw_data.get("data", []) if isinstance(raw_data, dict) else []
            if not raw_items:
                break

            for item in raw_items:
                if not isinstance(item, dict):
                    continue
                try:
                    vac_model = VacancySummary.model_validate(item)
                    if vac_model.is_archived:
                        continue
                    if vac_model.id not in seen_ids:
                        seen_ids.add(vac_model.id)
                        vacancies.append(vac_model)
                        if len(vacancies) >= limit:
                            break
                except Exception as ex:
                    logger.debug(f"Skipping malformed vacancy item {item.get('id')}: {ex}")
                    continue

            # Check pagination boundaries from Laravel response
            last_page = raw_data.get("last_page")
            if last_page is not None and current_page >= int(last_page):
                break

            current_page += 1

        return vacancies[:limit]

    def get_vacancy_details(
        self,
        vacancy_id: int,
        use_cache: bool = True,
    ) -> Optional[VacancyDetails]:
        """Fetch complete vacancy details by ID.

        Returns:
            VacancyDetails object if found, or None if 404.

        Raises:
            HirifyAPIError / HirifyNetworkError on network or server errors.
        """
        try:
            raw_data = self._request("GET", f"vacancies/{vacancy_id}", use_cache=use_cache)
            if not isinstance(raw_data, dict):
                return None
            return VacancyDetails.model_validate(raw_data)
        except HirifyNotFoundError:
            logger.info(f"Vacancy {vacancy_id} not found on Hirify (HTTP 404)")
            return None
        except Exception:
            raise
