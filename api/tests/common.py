from typing import Dict

from fastapi import status
from httpx import AsyncClient, Response


async def bad_request(
    method: str,
    url: str,
    client: AsyncClient,
    status_code: int,
    params: Dict = None,
    headers: Dict = None,
) -> str:
    response: Response = await client.request(
        method=method,
        url=url,
        params=params,
        headers=headers,
    )

    response_json = response.json()

    assert response.status_code == status_code
    assert response_json["result"] is False

    return response_json["error_message"]


async def unauthorised(
    method: str,
    url: str,
    client: AsyncClient,
    params: Dict = None,
    headers: Dict = None,
) -> str:
    return await bad_request(
        method=method,
        url=url,
        client=client,
        status_code=status.HTTP_401_UNAUTHORIZED,
        params=params,
        headers=headers,
    )


async def forbidden(
    method: str,
    url: str,
    client: AsyncClient,
    params: Dict = None,
    headers: Dict = None,
) -> str:
    return await bad_request(
        method=method,
        url=url,
        client=client,
        status_code=status.HTTP_403_FORBIDDEN,
        params=params,
        headers=headers,
    )


async def method_not_allowed(
    not_allowed_method: str,
    url: str,
    client: AsyncClient,
    params: Dict = None,
    headers: Dict = None,
) -> str:
    return await bad_request(
        method=not_allowed_method,
        url=url,
        client=client,
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        params=params,
        headers=headers,
    )
