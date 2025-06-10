from functools import wraps
from time import time
from typing import ParamSpec, TypeVar, Callable, Awaitable, Concatenate

from httpx import AsyncClient
from loguru import logger

from .custom_exception import CustomMessageException
from ..config import config


P = ParamSpec("P")
T = TypeVar("T")


def with_httpx(func: Callable[Concatenate[AsyncClient, P], Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    @wraps(func)
    async def httpx_wrapper(*args: P.args, **kwargs: P.kwargs):
        async with AsyncClient() as client:
            return await func(*args, client=client, **kwargs)

    return httpx_wrapper


class PayPal:
    _access_token: str | None = None
    _access_token_expires_at: int = 0

    BASE = "https://api-m.sandbox.paypal.com"
    AUTHORIZE = f"{BASE}/v1/oauth2/token"
    CHECKOUT = f"{BASE}/v2/checkout/orders"
    CAPTURES = f"{BASE}/v2/payments/captures"
    PAYOUTS = f"{BASE}/v1/payments/payouts"

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
    @with_httpx
    async def create(cls, price: float, currency: str = "USD", *, client: AsyncClient) -> str:
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
    @with_httpx
    async def capture(cls, order_id: str, *, client: AsyncClient) -> str | None:
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

    @classmethod
    @with_httpx
    async def create_payout(cls, treatment_id: int, email: str, amount: float, *, client: AsyncClient) -> str | None:
        resp = await client.post(
            cls.PAYOUTS, headers={"Authorization": f"Bearer {await cls._get_access_token()}"},
            json={
                "sender_batch_header": {
                    "sender_batch_id": f"treatment-{treatment_id}",
                    "email_subject": "Treatment payout",
                    "email_message": "Treatment payout",
                },
                "items": [{
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value":  f"{amount:.2f}",
                        "currency": "USD",
                    },
                    "note": f"Thanks for helping animals!",
                    "receiver": email,
                }],
            },
        )

        j_resp = resp.json()
        logger.debug(f"Paypal create payout response, code={resp.status_code!r}, body={j_resp!r}")

        if resp.status_code >= 400 or not j_resp.get("batch_header", {}).get("payout_batch_id"):
            message = j_resp.get("message", "Unknown error")
            raise CustomMessageException(f"Failed to create PayPal payout: {message}")

        return j_resp["batch_header"]["payout_batch_id"]

    @classmethod
    @with_httpx
    async def check_payout(cls, payout_id: str, *, client: AsyncClient) -> bool:
        resp = await client.get(
            f"{cls.PAYOUTS}/{payout_id}",
            headers={"Authorization": f"Bearer {await cls._get_access_token()}"},
        )

        j_resp = resp.json()
        logger.debug(f"Paypal get payout response, code={resp.status_code!r}, body={j_resp!r}")

        if resp.status_code >= 400 or not j_resp.get("batch_header", {}).get("payout_batch_id"):
            message = j_resp.get("message", "Unknown error")
            raise CustomMessageException(f"Failed to get PayPal payout: {message}")

        return j_resp["batch_header"]["batch_status"] == "SUCCESS"
