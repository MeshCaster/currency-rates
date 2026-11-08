import httpx


def default_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(10.0, connect=5.0),
        headers={"User-Agent": "myservice/1.0"},
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
