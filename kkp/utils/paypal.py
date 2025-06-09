from time import time

from httpx import AsyncClient
from loguru import logger

from .custom_exception import CustomMessageException
from ..config import config


class PayPal:
    _access_token: str | None = None
    _access_token_expires_at: int = 0

    BASE = "https://api-m.sandbox.paypal.com"
    AUTHORIZE = f"{BASE}/v1/oauth2/token"
    CHECKOUT = f"{BASE}/v2/checkout/orders"
    CAPTURES = f"{BASE}/v2/payments/captures"

    @classmethod
    async def _get_access_token(cls) -> str:
        if cls._access_token is None or cls._access_token_expires_at < time():
            async with AsyncClient() as client:
                resp = await client.post(
                    cls.AUTHORIZE,
                    content="grant_type=client_credentials",
                    auth=(config.paypal_id, config.paypal_secret),
                )

                j = resp.json()
                logger.debug(f"Paypal token response, code={resp.status_code!r}, body={j!r}")

                if "access_token" not in j or "expires_in" not in j:
                    raise CustomMessageException(
                        "Failed to obtain PayPal access token!" if config.is_debug else "An error occurred with PayPal"
                    )

                cls._access_token = j["access_token"]
                cls._access_token_expires_at = time() + j["expires_in"]

        return cls._access_token

    @classmethod
    async def create(cls, price: float, currency: str = "USD") -> str:
        async with AsyncClient() as client:
            resp = await client.post(
                cls.CHECKOUT, headers={"Authorization": f"Bearer {await cls._get_access_token()}"},
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [{
                        "amount": {
                            "currency_code": currency,
                            "value": f"{price:.2f}",
                        },
                    }],
                },
            )

            j_resp = resp.json()
            logger.debug(f"Paypal create order response, code={resp.status_code!r}, body={j_resp!r}")

            if "id" not in j_resp:
                logger.error(
                    f"Failed to create PayPal order, paypal_code={resp.status_code!r}, paypal_resp={j_resp!r}"
                )
                raise CustomMessageException(
                    "Failed to create PayPal order!" if config.is_debug else "An error occurred with PayPal"
                )

            return j_resp["id"]

    @classmethod
    async def capture(cls, order_id: str) -> str | None:
        async with AsyncClient() as client:
            resp = await client.post(
                f"{cls.CHECKOUT}/{order_id}/capture",
                headers={"Authorization": f"Bearer {await cls._get_access_token()}"},
                json={},
            )

            j_resp = resp.json()
            logger.debug(f"Paypal capture response, code={resp.status_code!r}, body={j_resp!r}")

            if resp.status_code >= 400 or j_resp["status"] != "COMPLETED":
                logger.error(
                    f"Failed to capture PayPal, paypal_code={resp.status_code!r}, paypal_resp={j_resp!r}"
                )
                return None

            try:
                return j_resp["purchase_units"][0]["payments"]["captures"][0]["id"]
            except (KeyError, IndexError):  # pragma: no cover
                return None
