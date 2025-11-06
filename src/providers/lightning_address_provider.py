from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import requests


@dataclass(frozen=True)
class LightningAddressError(Exception):
    address: str
    message: str


@dataclass(frozen=True)
class KeysendResponse:
    pubkey: str
    custom_data: List[Dict[str, str]]


@dataclass(frozen=True)
class LnurlpResponse:
    invoice: str


@dataclass(frozen=True)
class LightningAddressProvider:

    requester: Callable = requests.request
    timeout: int = 10

    def resolve_keysend(self, lightning_address: str) -> Optional[KeysendResponse]:
        if "@" not in lightning_address:
            return None

        username, domain = lightning_address.split("@", 1)
        url = f"https://{domain}/.well-known/keysend/{username}"

        try:
            response = self.requester("GET", url, timeout=self.timeout)
        except requests.exceptions.RequestException:
            return None

        # Check if response has content before trying to parse JSON
        if not response.text or not response.text.strip():
            return None

        try:
            data = response.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            return None

        if data.get("status") != "OK" or data.get("tag") != "keysend":
            return None

        return KeysendResponse(
            pubkey=data.get("pubkey"),
            custom_data=data.get("customData", [])
        )

    def resolve_lnurlp(self, lightning_address: str, amount_msats: int, sender_name: str, message: str) -> Optional[LnurlpResponse]:
        if "@" not in lightning_address:
            return None

        username, domain = lightning_address.split("@", 1)
        lnurl_url = f"https://{domain}/.well-known/lnurlp/{username}"

        # Get LNURLp well-known info
        try:
            lnurl_response = self.requester("GET", lnurl_url, timeout=self.timeout)
        except requests.exceptions.RequestException:
            return None

        # Check if response has content before trying to parse JSON
        if not lnurl_response.text or not lnurl_response.text.strip():
            return None

        try:
            lnurl_data = lnurl_response.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            return None

        if lnurl_data.get("tag") != "payRequest":
            return None

        callback_url = lnurl_data.get("callback")
        if not callback_url:
            return None

        min_sendable = lnurl_data.get("minSendable", 0)
        max_sendable = lnurl_data.get("maxSendable", float('inf'))

        if amount_msats < min_sendable or amount_msats > max_sendable:
            return None

        # Build parameters for the callback URL
        params = {"amount": amount_msats}

        payer_data = lnurl_data.get("payerData", {})
        if sender_name and "name" in payer_data:
            params["name"] = sender_name

        max_comment_length = payer_data.get("commentAllowed", 0)
        if message and max_comment_length > 0:
            params["comment"] = message[:max_comment_length]

        # Request invoice from callback URL
        try:
            callback_response = self.requester(
                "GET",
                callback_url,
                params=params,
                timeout=self.timeout
            )
        except requests.exceptions.RequestException:
            return None

        # Check if callback response has content before trying to parse JSON
        if not callback_response.text or not callback_response.text.strip():
            return None

        try:
            callback_data = callback_response.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            return None

        invoice = callback_data.get("pr")
        if not invoice:
            return None

        return LnurlpResponse(
            invoice=invoice
        )
