import httpx


async def call_agent(client: httpx.AsyncClient, endpoint_name: str, params: dict) -> dict:
    """Call an Agentfield agent endpoint. Returns the JSON response."""
    url = f"/reasoners/{endpoint_name}"
    response = await client.post(url, json=params)
    response.raise_for_status()
    return response.json()
