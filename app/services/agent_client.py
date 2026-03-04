import httpx
from fastapi import HTTPException


async def call_agent(client: httpx.AsyncClient, endpoint_name: str, params: dict) -> dict:
    """Call an Agentfield agent endpoint. Returns the JSON response."""
    url = f"/reasoners/{endpoint_name}"
    try:
        response = await client.post(url, json=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:500] if e.response else str(e)
        raise HTTPException(status_code=e.response.status_code, detail=detail)
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Engine service unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Engine request timed out")
