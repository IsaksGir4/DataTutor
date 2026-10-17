import jwt
from fastapi import status
from jwt import PyJWKClient, PyJWKClientError

from app.config.settings import settings
from app.core.errors import DataTutorException

jwks_client = PyJWKClient(settings.keycloak_jwks_url)


def verify_token(token: str) -> dict:
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.KEYCLOAK_AUDIENCE,
            issuer=settings.keycloak_issuer,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        return payload
    except PyJWKClientError:
        raise DataTutorException(
            "auth_provider_error",
            "No se pudo verificar la identidad con el servidor de autenticación.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except jwt.ExpiredSignatureError:
        raise DataTutorException(
            "token_expired",
            "La sesión ha expirado.",
            status.HTTP_401_UNAUTHORIZED,
        )
    except jwt.InvalidAudienceError:
        raise DataTutorException(
            "token_invalid_audience",
            "El token no es válido para esta aplicación.",
            status.HTTP_401_UNAUTHORIZED,
        )
    except jwt.InvalidIssuerError:
        raise DataTutorException(
            "token_invalid_issuer",
            "El emisor del token no es válido.",
            status.HTTP_401_UNAUTHORIZED,
        )
    except jwt.InvalidTokenError:
        raise DataTutorException(
            "token_invalid",
            "Token inválido o corrupto.",
            status.HTTP_401_UNAUTHORIZED,
        )