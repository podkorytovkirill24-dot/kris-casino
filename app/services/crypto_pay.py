from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp


class CryptoPayError(RuntimeError):
    pass


@dataclass(frozen=True)
class CryptoPayInvoice:
    invoice_id: int
    bot_invoice_url: str | None
    web_app_invoice_url: str | None
    mini_app_invoice_url: str | None
    pay_url: str | None
    status: str | None


class CryptoPayClient:
    def __init__(self, api_token: str, base_url: str) -> None:
        self.api_token = api_token
        self.base_url = base_url.rstrip("/")

    async def _request(self, method: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}/{method}"
        headers = {"Crypto-Pay-API-Token": self.api_token}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, json=payload or {}) as response:
                data = await response.json()
                if not data.get("ok"):
                    raise CryptoPayError(str(data.get("error", "Crypto Pay error")))
                return data.get("result")

    async def create_invoice(
        self,
        asset: str,
        amount: str,
        description: str,
        payload: str,
        allow_comments: bool,
        allow_anonymous: bool,
    ) -> CryptoPayInvoice:
        params = {
            "asset": asset,
            "amount": amount,
            "description": description,
            "payload": payload,
            "allow_comments": allow_comments,
            "allow_anonymous": allow_anonymous,
        }
        result = await self._request("createInvoice", params)
        return CryptoPayInvoice(
            invoice_id=int(result.get("invoice_id")),
            bot_invoice_url=result.get("bot_invoice_url"),
            web_app_invoice_url=result.get("web_app_invoice_url"),
            mini_app_invoice_url=result.get("mini_app_invoice_url"),
            pay_url=result.get("pay_url"),
            status=result.get("status"),
        )

    async def get_invoices(self, invoice_ids: list[int]) -> list[dict[str, Any]]:
        params = {"invoice_ids": ",".join(str(item) for item in invoice_ids)}
        result = await self._request("getInvoices", params)
        if isinstance(result, dict) and "items" in result:
            return list(result.get("items") or [])
        if isinstance(result, list):
            return result
        return []
