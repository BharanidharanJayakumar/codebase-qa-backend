import httpx

AGENT_ENDPOINT = "/api/v1/execute/codebase-qa-agent"


async def call_agent(client: httpx.AsyncClient, endpoint_name: str, params: dict) -> dict:
    """Call an Agentfield agent endpoint. Returns the JSON response."""
    url = f"{AGENT_ENDPOINT}.{endpoint_name}"
    response = await client.post(url, json={"input": params})
    response.raise_for_status()
    return response.json()
