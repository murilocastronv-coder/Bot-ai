"""Ordens reais de SOL-PERP na Jupiter Perpetuals para o robô SAM SOL (conta real).

Construído a partir do IDL público do programa (createIncreasePositionMarketRequest /
createDecreasePositionMarketRequest). A Jupiter usa pedidos: enviamos o pedido e um keeper
da Jupiter executa-o segundos depois; confirmamos lendo a conta Position on-chain.

Segurança:
- cada transação é SIMULADA antes; se a simulação falha nada é enviado;
- a garantia é USDC (o programa troca USDC -> SOL nas compras, com saída mínima protegida);
- a chave privada vem cifrada do banco (sam_wallet.py) e nunca é registada em logs.
Funções síncronas (requests): chame-as com asyncio.to_thread.
"""
from __future__ import annotations

import base64
import hashlib
import os
import random
import struct
import time

import requests
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

PROGRAM_ID = Pubkey.from_string("PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu")
POOL = Pubkey.from_string("5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq")
EVENT_AUTHORITY = Pubkey.from_string("37hJBDnntwqhGbK7L6M1bLyvccj4u55CCUiLPdYkiqBN")
SOL_CUSTODY = Pubkey.from_string("7xS2gz2bTp3fwCC7knJvUWTEU9Tycczu6VhJYKgi1wdz")
USDC_CUSTODY = Pubkey.from_string("G18jKKXQwBbrHeiK3C9MRXhkHsLHf7XgCSisykV46EZa")
USDC_MINT = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ATA_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
PERPETUALS = Pubkey.find_program_address([b"perpetuals"], PROGRAM_ID)[0]
SIDE = {"long": 1, "short": 2}
SLIPPAGE = 0.01
CONFIRM_TIMEOUT = 90


class PerpsError(RuntimeError):
    pass


def rpc(method, params):
    url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    r = requests.post(url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("error"):
        raise PerpsError("RPC recusou " + method + ": " + str(data["error"])[:200])
    return data.get("result")


# ------------------------------------------------------------------ codificação
def _disc(name):
    snake = "".join("_" + c.lower() if c.isupper() else c for c in name)
    return hashlib.sha256(("global:" + snake).encode()).digest()[:8]


def _u64(v):
    return struct.pack("<Q", int(v))


def _opt_u64(v):
    return b"\x00" if v is None else b"\x01" + _u64(v)


def _opt_bool(v):
    return b"\x00" if v is None else b"\x01" + (b"\x01" if v else b"\x00")


def ata(owner, mint):
    return Pubkey.find_program_address([bytes(owner), bytes(TOKEN_PROGRAM), bytes(mint)], ATA_PROGRAM)[0]


def collateral_custody(side):
    return SOL_CUSTODY if side == "long" else USDC_CUSTODY


def position_pda(owner, side):
    return Pubkey.find_program_address(
        [b"position", bytes(owner), bytes(POOL), bytes(SOL_CUSTODY), bytes(collateral_custody(side)),
         bytes([SIDE[side]])], PROGRAM_ID)[0]


def request_pda(position, counter, increase):
    return Pubkey.find_program_address(
        [b"position_request", bytes(position), _u64(counter), bytes([1 if increase else 2])], PROGRAM_ID)[0]


def _meta(pubkey, writable=False, signer=False):
    return AccountMeta(pubkey, is_signer=signer, is_writable=writable)


def _tail():
    return [_meta(PROGRAM_ID), _meta(TOKEN_PROGRAM), _meta(ATA_PROGRAM), _meta(SYSTEM_PROGRAM),
            _meta(EVENT_AUTHORITY), _meta(PROGRAM_ID)]


def increase_ix(owner, side, collateral_raw, size_raw, price_limit_raw, jupiter_min_out, counter):
    position = position_pda(owner, side)
    request = request_pda(position, counter, True)
    data = (_disc("createIncreasePositionMarketRequest") + _u64(size_raw) + _u64(collateral_raw) +
            bytes([SIDE[side]]) + _u64(price_limit_raw) + _opt_u64(jupiter_min_out) + _u64(counter))
    accounts = [_meta(owner, True, True), _meta(ata(owner, USDC_MINT), True), _meta(PERPETUALS), _meta(POOL),
                _meta(position, True), _meta(request, True), _meta(ata(request, USDC_MINT), True),
                _meta(SOL_CUSTODY), _meta(collateral_custody(side)), _meta(USDC_MINT)] + _tail()
    return Instruction(PROGRAM_ID, data, accounts)


def decrease_ix(owner, side, price_limit_raw, counter):
    position = position_pda(owner, side)
    request = request_pda(position, counter, False)
    data = (_disc("createDecreasePositionMarketRequest") + _u64(0) + _u64(0) + _u64(price_limit_raw) +
            _opt_u64(None) + _opt_bool(True) + _u64(counter))
    accounts = [_meta(owner, True, True), _meta(ata(owner, USDC_MINT), True), _meta(PERPETUALS), _meta(POOL),
                _meta(position), _meta(request, True), _meta(ata(request, USDC_MINT), True),
                _meta(SOL_CUSTODY), _meta(collateral_custody(side)), _meta(USDC_MINT)] + _tail()
    return Instruction(PROGRAM_ID, data, accounts)


# ------------------------------------------------------------------ leituras on-chain
def read_position(owner, side):
    info = rpc("getAccountInfo", [str(position_pda(owner, side)), {"encoding": "base64", "commitment": "confirmed"}])
    value = (info or {}).get("value")
    if not value:
        return None
    raw = base64.b64decode(value["data"][0])
    off = 8 + 32 * 4 + 16
    side_byte = raw[off]
    off += 1
    price, size, collateral = struct.unpack_from("<QQQ", raw, off)
    return {"side": {1: "long", 2: "short"}.get(side_byte, "none"), "price": price / 1e6, "size_usd": size / 1e6,
            "collateral_usd": collateral / 1e6}


def usdc_balance(owner):
    result = rpc("getTokenAccountsByOwner", [str(owner), {"mint": str(USDC_MINT)}, {"encoding": "jsonParsed"}])
    return sum(int(a["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"])
               for a in (result or {}).get("value", [])) / 1e6


def sol_balance(owner):
    return int((rpc("getBalance", [str(owner), {"commitment": "confirmed"}]) or {}).get("value", 0)) / 1e9


# ------------------------------------------------------------------ envio
def _send(kp, instructions):
    ixs = [set_compute_unit_limit(400_000), set_compute_unit_price(100_000)] + instructions
    blockhash = Hash.from_string(rpc("getLatestBlockhash", [{"commitment": "finalized"}])["value"]["blockhash"])
    tx = VersionedTransaction(MessageV0.try_compile(kp.pubkey(), ixs, [], blockhash), [kp])
    encoded = base64.b64encode(bytes(tx)).decode()
    sim = rpc("simulateTransaction", [encoded, {"encoding": "base64", "sigVerify": False, "replaceRecentBlockhash": True}])
    err = (sim or {}).get("value", {}).get("err")
    if err is not None:
        logs = [l for l in (sim["value"].get("logs") or []) if "rror" in l][-2:]
        raise PerpsError("Simulação recusou a ordem (nada foi enviado): " + str(err) + " " + " | ".join(logs)[:300])
    return rpc("sendTransaction", [encoded, {"encoding": "base64", "skipPreflight": True, "maxRetries": 3}])


def _wait(owner, side, opened, min_size=0.0):
    deadline = time.monotonic() + CONFIRM_TIMEOUT
    while time.monotonic() < deadline:
        pos = read_position(owner, side)
        size = (pos or {}).get("size_usd", 0)
        if opened and size > min_size + 0.01:
            return pos
        if not opened and size == 0:
            return pos or {"size_usd": 0}
        time.sleep(3)
    raise PerpsError("A Jupiter não executou o pedido em " + str(CONFIRM_TIMEOUT) + " s (o pedido expira e o "
                     "dinheiro volta para a carteira)")


def open_position(kp, side, collateral_usd, leverage, price):
    """Abre (ou aumenta) a posição SOL com garantia em USDC. Devolve a posição on-chain."""
    owner = kp.pubkey()
    if usdc_balance(owner) < collateral_usd:
        raise PerpsError("USDC insuficiente na carteira para a garantia de $" + format(collateral_usd, ".2f"))
    current = read_position(owner, side) or {}
    counter = random.getrandbits(63)
    collateral_raw = int(collateral_usd * 1e6)
    size_raw = int(collateral_usd * leverage * 1e6)
    limit = price * (1 + SLIPPAGE if side == "long" else 1 - SLIPPAGE)
    # compra: o programa troca USDC -> SOL; saída mínima = valor ao preço atual menos a derrapagem
    min_out = int(collateral_usd / price * 1e9 * (1 - 2 * SLIPPAGE)) if side == "long" else None
    sig = _send(kp, [increase_ix(owner, side, collateral_raw, size_raw, int(limit * 1e6), min_out, counter)])
    pos = _wait(owner, side, opened=True, min_size=current.get("size_usd", 0))
    pos["signature"] = sig
    return pos


def close_position(kp, side, price):
    """Fecha a posição inteira (volta para USDC)."""
    owner = kp.pubkey()
    current = read_position(owner, side)
    if not current or current["size_usd"] == 0:
        return {"size_usd": 0, "already_closed": True}
    counter = random.getrandbits(63)
    limit = price * (1 - SLIPPAGE if side == "long" else 1 + SLIPPAGE)
    sig = _send(kp, [decrease_ix(owner, side, int(limit * 1e6), counter)])
    pos = _wait(owner, side, opened=False)
    pos["signature"] = sig
    return pos
