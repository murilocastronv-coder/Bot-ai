"""Carteira Solana da conta real do robô SAM SOL, guardada CIFRADA no banco (tabela settings).

O plano free do Render não tem disco persistente, por isso a chave fica no PostgreSQL,
cifrada com SAM_WALLET_PASSPHRASE (variável do Render, 24+ caracteres). Sem essa variável
nada é criado. A chave privada nunca é mostrada no Telegram nem registada em logs.
"""
from __future__ import annotations

import base64
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from solders.keypair import Keypair

import services as sv

KEY = "sam_sol_wallet"


class WalletError(RuntimeError):
    pass


def _passphrase() -> str:
    p = os.getenv("SAM_WALLET_PASSPHRASE", "")
    if len(p) < 24:
        raise WalletError("Configure SAM_WALLET_PASSPHRASE (24+ caracteres) no Render → Environment")
    return p


def _fernet(salt: bytes, passphrase: str) -> Fernet:
    key = Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1).derive(passphrase.encode())
    return Fernet(base64.urlsafe_b64encode(key))


async def address(s) -> str | None:
    data = await sv.get_setting(s, KEY)
    return data.get("address") if isinstance(data, dict) else None


async def create_or_get(s) -> tuple[str, bool]:
    data = await sv.get_setting(s, KEY)
    if isinstance(data, dict) and data.get("address"):
        return data["address"], False
    passphrase = _passphrase()
    salt = os.urandom(16)
    kp = Keypair()
    payload = {"version": 1, "address": str(kp.pubkey()), "salt": base64.b64encode(salt).decode(),
               "ciphertext": _fernet(salt, passphrase).encrypt(bytes(kp)).decode()}
    await sv.set_setting(s, KEY, payload)
    await s.commit()
    return payload["address"], True


async def keypair(s) -> Keypair:
    data = await sv.get_setting(s, KEY)
    if not isinstance(data, dict) or not data.get("address"):
        raise WalletError("Carteira real ainda não criada")
    try:
        secret = _fernet(base64.b64decode(data["salt"]), _passphrase()).decrypt(data["ciphertext"].encode())
    except InvalidToken as ex:
        raise WalletError("SAM_WALLET_PASSPHRASE não confere com a carteira guardada") from ex
    kp = Keypair.from_bytes(secret)
    if str(kp.pubkey()) != data["address"]:
        raise WalletError("Endereço da carteira não confere")
    return kp
