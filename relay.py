#!/usr/bin/env python3
"""
BattleTankOnline UDP relay server.

Forwards 16-byte game-state packets between two peers in each game session.
Packet format (peer -> relay): [4-byte server_id big-endian][16-byte game data]
Relay strips the header and forwards 16 bytes to the other peer.

A minimal HTTP health endpoint is served on TCP (PORT + 1) so the home server
can confirm the process is actually running before advertising VPS relay to clients.

Usage:
    python relay.py [port]   (default port: 9000)
    Health check: GET http://<host>:<port+1>/  -> {"status":"ok"}
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

PORT         = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
HEALTH_PORT  = PORT + 1   # TCP health check endpoint
ROOM_TTL     = 30.0       # seconds before an idle room is pruned
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
        if len(data) != 20:
            return
        (server_id,) = struct.unpack_from(">I", data, 0)
        payload = data[4:]

        room = _rooms.setdefault(server_id, {"peers": [], "last": 0.0})
        room["last"] = time.monotonic()
        peers: list[tuple[str, int]] = room["peers"]

        if addr in peers:
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


async def _health_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    await reader.read(1024)
    body = b'{"status":"ok"}'
    writer.write(
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: application/json\r\n"
        b"Content-Length: " + str(len(body)).encode() + b"\r\n"
        b"Connection: close\r\n"
        b"\r\n" + body
    )
    await writer.drain()
    writer.close()


async def main() -> None:
    loop = asyncio.get_running_loop()

    await loop.create_datagram_endpoint(_Protocol, local_addr=("0.0.0.0", PORT))

    health_server = await asyncio.start_server(_health_handler, "0.0.0.0", HEALTH_PORT)
    log.info("Health endpoint on TCP port %d", HEALTH_PORT)

    cleanup = asyncio.create_task(_cleanup_loop())

    stop = loop.create_future()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, None)

    log.info("relay ready — waiting for peers")
    await stop

    cleanup.cancel()
    health_server.close()
    log.info("relay stopped")


if __name__ == "__main__":
    asyncio.run(main())
