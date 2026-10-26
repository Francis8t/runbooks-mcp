"""M5b — Runbooks server over Streamable HTTP, REQUIRING a valid Cognito JWT.

A custom TokenVerifier validates each bearer token's signature (via Cognito's
JWKS), issuer, expiry, token_use, and scope. Anything missing/invalid is
rejected with 401 BEFORE any tool/resource/prompt code runs.

Env (from the runbooks-cognito stack outputs):
    export ISSUER_URL=...   JWKS_URL=...   REQUIRED_SCOPE=runbooks-mcp/invoke
    export SERVER_URL=http://127.0.0.1:8000/mcp
"""
import os

import jwt
from jwt import PyJWKClient
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings

from runbooks_server import build_server

ISSUER = os.environ["ISSUER_URL"]
JWKS_URL = os.environ["JWKS_URL"]
SCOPE = os.environ.get("REQUIRED_SCOPE", "runbooks-mcp/invoke")
SERVER_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:8000/mcp")

_jwks = PyJWKClient(JWKS_URL)  # lazily fetches + caches Cognito's public keys


class CognitoVerifier(TokenVerifier):
    """Validate a Cognito access token. Return AccessToken on success, else None (→401)."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            signing_key = _jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token, signing_key, algorithms=["RS256"],
                issuer=ISSUER,
                options={"verify_aud": False},  # Cognito M2M tokens carry no 'aud'
            )
        except Exception:
            return None  # bad signature / wrong issuer / expired → reject
        if claims.get("token_use") != "access":
            return None
        scopes = claims.get("scope", "").split()
        if SCOPE not in scopes:
            return None  # valid token, wrong scope
        return AccessToken(
            token=token, client_id=claims.get("client_id", ""),
            scopes=scopes, expires_at=claims.get("exp"),
            subject=claims.get("sub"), claims=claims,
        )


mcp = build_server(
    token_verifier=CognitoVerifier(),
    auth=AuthSettings(
        issuer_url=ISSUER,
        resource_server_url=SERVER_URL,
        required_scopes=[SCOPE],
        validate_token_resource=False,
    ),
)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
