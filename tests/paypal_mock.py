import json
import re
from base64 import b64encode
from time import time

from httpx import Request, Response

from kkp.config import config


class PaypalMockState:
    CAPTURE_RE = re.compile(r".+/v2/checkout/orders/\d+\.\d+/capture")
    GET_PAYOUT_RE = re.compile(r".+/v1/payments/payouts/\d+\.\d+")

    def __init__(
            self, client_id: str = config.paypal_id, client_secret: str = config.paypal_secret, money: int = 1000,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._money = money
        self._orders = {}
        self._payouts = {}
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

    @staticmethod
    def _payout_to_json(payout: dict) -> dict:
        return {
            "batch_header": {
                "payout_batch_id": payout["id"],
                "batch_status": "SUCCESS" if payout["completed"] else "PENDING",
                "sender_batch_header": payout["sender_batch_header"],
            },
            "links": [{
                "href": f"https://api.sandbox.paypal.com/v1/payments/payouts/{payout['id']}",
                "rel": "self",
                "method": "GET",
                "encType": "application/json"
            }]
        }

    def payout_create_callback(self, request: Request) -> Response:
        auth = b64encode(f"{self._client_id}/{self._client_secret}".encode("utf8")).decode("utf8")
        if request.headers.get("authorization") != f"Bearer {auth}":
            return Response(status_code=401, json={
                "error": "invalid_client", "error_description": "Client Authentication failed"
            })

        j_req = json.loads(request.content)
        amount = float(j_req["items"][0]["amount"]["value"])
        if amount > self._money:
            return Response(status_code=200, json={
                "name": "INSUFFICIENT_FUNDS",
                "message": "Sender does not have sufficient funds. Please add funds and retry.",
                "debug_id": str(int(time() * 1000)),
                "information_link": "https://developer.paypal.com/docs/api/payments.payouts-batch/#errors",
                "links": []
            })

        self._money -= amount

        payout_id = str(time() * 1000)
        self._payouts[payout_id] = {
            "id": payout_id,
            "completed": False,
            "sender_batch_header": j_req["sender_batch_header"],
        }

        return Response(status_code=200, json=self._payout_to_json(self._payouts[payout_id]))

    def mark_payout_as_completed(self, payout_id: str) -> None:
        if payout_id not in self._payouts:
            return
        if self._payouts[payout_id]["completed"]:
            return

        self._payouts[payout_id]["completed"] = True

    def payout_get_callback(self, request: Request) -> Response:
        auth = b64encode(f"{self._client_id}/{self._client_secret}".encode("utf8")).decode("utf8")
        if request.headers.get("authorization") != f"Bearer {auth}":
            return Response(status_code=401, json={
                "error": "invalid_client", "error_description": "Client Authentication failed"
            })

        payout_id = request.url.path.split("/payouts/")[1].strip()
        return Response(status_code=200, json=self._payout_to_json(self._payouts[payout_id]))
