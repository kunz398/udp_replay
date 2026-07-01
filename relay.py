#!/usr/bin/env python3
"""
BattleTankOnline UDP relay server.

Forwards 16-byte game-state packets between two peers in each game session.
Packet format (peer -> relay): [4-byte server_id big-endian][16-byte game data]
Relay strips the header and forwards 16 bytes to the other peer.

Usage:
    python relay.py [port]   (default port: 9000)
"""

from __future__ import annotations

import asyncio
import logging
import signal
import struct
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
ROOM_TTL = 30.0      # seconds before an idle room is pruned
CLEANUP_INTERVAL = 15.0

# server_id -> {"peers": [(ip, port), ...], "last": float}
_rooms: dict[int, dict] = {}


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self.transport = transport
        log.info("UDP relay listening on 0.0.0.0:%d", PORT)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        # Every inbound packet: [4-byte server_id big-endian][16-byte game state]
        if len(data) != 20:
            return
        (server_id,) = struct.unpack_from(">I", data, 0)
        payload = data[4:]

        room = _rooms.setdefault(server_id, {"peers": [], "last": 0.0})
        room["last"] = time.monotonic()
        peers: list[tuple[str, int]] = room["peers"]

        if addr in peers:
            # Known peer — forward payload to the other peer
            for dest in peers:
                if dest != addr:
                    self.transport.sendto(payload, dest)
        elif len(peers) < 2:
            peers.append(addr)
            log.info(
                "server=%d  peer %s registered  (%d/2 peers)",
                server_id, addr, len(peers),
            )

    def error_received(self, exc: Exception) -> None:
        log.warning("socket error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        log.info("relay socket closed")


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL)
        cutoff = time.monotonic() - ROOM_TTL
        stale = [sid for sid, r in list(_rooms.items()) if r["last"] < cutoff]
        for sid in stale:
            _rooms.pop(sid, None)
        if stale:
            log.info("pruned %d idle room(s)", len(stale))


async def main() -> None:
    loop = asyncio.get_running_loop()

    _, _ = await loop.create_datagram_endpoint(
        _Protocol, local_addr=("0.0.0.0", PORT)
    )

    cleanup = asyncio.create_task(_cleanup_loop())

    # Graceful shutdown on SIGINT / SIGTERM
    stop = loop.create_future()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, None)

    log.info("relay ready — waiting for peers")
    await stop

    cleanup.cancel()
    log.info("relay stopped")


if __name__ == "__main__":
    asyncio.run(main())
