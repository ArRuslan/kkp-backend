from httpx import AsyncClient

from kkp.utils.jwt import JWT

# The URL that provides public certificates for verifying ID tokens issued
# by Google's OAuth 2.0 authorization server.
GOOGLE_OAUTH2_CERTS_URL = "https://www.googleapis.com/oauth2/v1/certs"
GOOGLE_ISSUERS = ["accounts.google.com", "https://accounts.google.com"]
_GOOGLE_CERTS = None


async def _fetch_certs() -> dict[str, str]:
    global _GOOGLE_CERTS

    if _GOOGLE_CERTS is not None:
        return _GOOGLE_CERTS

    async with AsyncClient(follow_redirects=True) as cl:
        resp = await cl.get(GOOGLE_OAUTH2_CERTS_URL)
        if resp.status_code >= 400:
            return {}
        _GOOGLE_CERTS = resp.json()

    return _GOOGLE_CERTS


async def verify_token(id_token: str) -> dict[str, ...]:
    """Verifies an ID token and returns the decoded token.

    Args:
        id_token (Union[str, bytes]): The encoded token.

    Returns:
        Mapping[str, Any]: The decoded token.
    """
    certs = await _fetch_certs()

    return JWT.decode(
        id_token,
        secret=certs,
    )


async def verify_oauth2_token(id_token: str, audience: str):
    """Verifies an ID Token issued by Google's OAuth 2.0 authorization server.

    Args:
        id_token (Union[str, bytes]): The encoded token.
        audience (str): The audience that this token is intended for. This is
            typically your application's OAuth 2.0 client ID. If None then the
            audience is not verified.

    Returns:
        Mapping[str, Any]: The decoded token.

    Raises:
        ValueError: If token verification fails or the issuer is invalid.
    """
    idinfo = await verify_token(id_token)
    if idinfo is None:
        raise ValueError(f"Failed to verify token")

    if idinfo["iss"] not in GOOGLE_ISSUERS:
        raise ValueError(f"Wrong issuer. 'iss' should be one of the following: {GOOGLE_ISSUERS}")
    if idinfo["aud"] != audience:
        raise ValueError(f"Wrong audience. 'aud' should be: {audience}")

    return idinfo
