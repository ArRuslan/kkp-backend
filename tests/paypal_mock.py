import re
from base64 import b64encode
from time import time

from httpx import Request, Response

from kkp.config import config


class PaypalMockState:
    CAPTURE_RE = re.compile(r".+/v2/checkout/orders/\d+\.\d+/capture")

    def __init__(self, client_id: str = config.paypal_id, client_secret: str = config.paypal_secret) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._orders = {}
        self._captures = {}

    def auth_callback(self, request: Request) -> Response:
        auth = b64encode(f"{self._client_id}:{self._client_secret}".encode("utf8")).decode("utf8")
        if request.headers.get("authorization") != f"Basic {auth}":
            return Response(status_code=401, json={
                "error": "invalid_client", "error_description": "Client Authentication failed"
            })
        if request.content != b"grant_type=client_credentials":
            return Response(status_code=400, json={
                "error": "unsupported_grant_type", "error_description": "Grant Type is NULL"
            })

        return Response(status_code=200, json={
            "access_token": b64encode(f"{self._client_id}/{self._client_secret}".encode("utf8")).decode("utf8"),
            "expires_in": 32400,
        })

    def order_callback(self, request: Request) -> Response:
        auth = b64encode(f"{self._client_id}/{self._client_secret}".encode("utf8")).decode("utf8")
        if request.headers.get("authorization") != f"Bearer {auth}":
            return Response(status_code=401, json={
                "error": "invalid_client", "error_description": "Client Authentication failed"
            })

        order_id = str(time() * 1000)
        self._orders[order_id] = {
            "payed": False,
            "refunded": False,
            "capture_id": None,
        }

        return Response(status_code=200, json={
            "id": order_id,
        })

    def capture_callback(self, request: Request) -> Response:
        auth = b64encode(f"{self._client_id}/{self._client_secret}".encode("utf8")).decode("utf8")
        if request.headers.get("authorization") != f"Bearer {auth}":
            return Response(status_code=401, json={
                "error": "invalid_client", "error_description": "Client Authentication failed"
            })

        order_id = request.url.path.split("/")[-2]
        if order_id not in self._orders:
            return Response(status_code=404, json={
                "error": "invalid_order", "error_description": "",
            })

        if not self._orders[order_id]["payed"]:
            return Response(status_code=200, json={
                "status": "NOT_COMPLETED",
            })

        if self._orders[order_id]["refunded"]:
            return Response(status_code=200, json={
                "status": "REFUNDED",
            })

        return Response(status_code=200, json={
            "status": "COMPLETED",
            "purchase_units": [{
                "payments": {
                    "captures": [{
                        "id": self._orders[order_id]["capture_id"]
                    }]
                }
            }]
        })

    def refund_callback(self, request: Request) -> Response:
        auth = b64encode(f"{self._client_id}/{self._client_secret}".encode("utf8")).decode("utf8")
        if request.headers.get("authorization") != f"Bearer {auth}":
            return Response(status_code=401, json={
                "error": "invalid_client", "error_description": "Client Authentication failed"
            })

        capture_id = request.url.path.split("/")[-2]
        if capture_id not in self._captures:
            return Response(status_code=404, json={
                "error": "invalid_order", "error_description": "",
            })

        if not self._captures[capture_id]["payed"]:
            return Response(status_code=200, json={
                "status": "NOT_COMPLETED",
            })

        if self._captures[capture_id]["refunded"]:
            return Response(status_code=200, json={
                "status": "REFUNDED",
            })

        self._captures[capture_id]["refunded"] = True

        return Response(status_code=200, json={
            "status": "COMPLETED",
        })

    def mark_as_payed(self, order_id: str) -> None:
        if order_id not in self._orders:
            return
        if self._orders[order_id]["payed"]:
            return

        self._orders[order_id]["payed"] = True
        self._orders[order_id]["capture_id"] = str(time() * 1000)
        self._captures[self._orders[order_id]["capture_id"]] = self._orders[order_id]