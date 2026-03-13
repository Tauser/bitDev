import time
from typing import Iterable, Optional

import requests


DEFAULT_TIMEOUT = 3.0
DEFAULT_RETRIES = 2
DEFAULT_BACKOFF = 0.25
DEFAULT_RETRY_STATUS = (429, 500, 502, 503, 504)
DEFAULT_RETRY_METHODS = {"GET", "HEAD"}


class HttpClient:
    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        backoff: float = DEFAULT_BACKOFF,
        user_agent: str = "CryptoMonitor/1.0 (+local-rpi)",
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json, text/plain, */*",
            }
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
        backoff: Optional[float] = None,
        retry_on_status: Optional[Iterable[int]] = None,
        retry_methods: Optional[Iterable[str]] = None,
        headers: Optional[dict] = None,
        **kwargs,
    ):
        effective_timeout = self.timeout if timeout is None else timeout
        max_retries = self.retries if retries is None else retries
        backoff_factor = self.backoff if backoff is None else backoff
        status_to_retry = tuple(DEFAULT_RETRY_STATUS if retry_on_status is None else retry_on_status)
        allowed_methods = {
            m.upper() for m in (DEFAULT_RETRY_METHODS if retry_methods is None else retry_methods)
        }

        method_u = method.upper()
        last_exc = None

        for attempt in range(max_retries + 1):
            try:
                response = self.session.request(
                    method=method_u,
                    url=url,
                    timeout=effective_timeout,
                    headers=headers,
                    **kwargs,
                )

                should_retry_status = (
                    method_u in allowed_methods
                    and response.status_code in status_to_retry
                    and attempt < max_retries
                )
                if should_retry_status:
                    self._sleep(backoff_factor, attempt)
                    continue

                return response
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                last_exc = exc
                if attempt >= max_retries:
                    raise
                self._sleep(backoff_factor, attempt)

        if last_exc is not None:
            raise last_exc

        raise RuntimeError("HTTP request failed unexpectedly")

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    @staticmethod
    def _sleep(backoff_factor: float, attempt: int) -> None:
        if backoff_factor <= 0:
            return
        delay = backoff_factor * (2 ** attempt)
        time.sleep(delay)


_http_client_singleton = HttpClient()


def get_http_client() -> HttpClient:
    return _http_client_singleton