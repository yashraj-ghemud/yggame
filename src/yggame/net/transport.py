# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Transport abstractions and deterministic in-memory networking for tests."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Protocol

from .protocol import Packet, SequenceWindow


class Transport(Protocol):
    def send(self, peer: str, packet: Packet) -> None: ...

    def receive(self, peer: str) -> list[Packet]: ...

    def close(self) -> None: ...


@dataclass(slots=True)
class InMemoryTransport:
    """Zero-dependency transport for multiplayer unit tests and local co-op."""

    queues: dict[str, deque[Packet]] = field(default_factory=dict)
    connected: set[str] = field(default_factory=set)
    latency: float = 0.0
    _time: float = 0.0
    _scheduled: list[tuple[float, str, Packet]] = field(default_factory=list)

    def connect(self, peer: str) -> None:
        self.connected.add(peer)
        self.queues.setdefault(peer, deque())

    def disconnect(self, peer: str) -> None:
        self.connected.discard(peer)

    def send(self, peer: str, packet: Packet) -> None:
        if peer not in self.connected:
            raise ConnectionError(f"peer is not connected: {peer}")
        if self.latency <= 0:
            self.queues.setdefault(peer, deque()).append(packet)
        else:
            self._scheduled.append((self._time + self.latency, peer, packet))

    def update(self, delta: float) -> None:
        self._time += max(0.0, delta)
        ready = [item for item in self._scheduled if item[0] <= self._time]
        self._scheduled[:] = [item for item in self._scheduled if item[0] > self._time]
        for _, peer, packet in sorted(ready):
            if peer in self.connected:
                self.queues.setdefault(peer, deque()).append(packet)

    def receive(self, peer: str) -> list[Packet]:
        queue = self.queues.setdefault(peer, deque())
        result = list(queue)
        queue.clear()
        return result

    def close(self) -> None:
        self.connected.clear()
        self.queues.clear()
        self._scheduled.clear()


@dataclass(slots=True)
class ReliableChannel:
    transport: Transport
    peer: str
    resend_after: float = 0.25
    sequence: int = 0
    pending: dict[int, tuple[Packet, float]] = field(default_factory=dict)

    def send(self, kind: str, payload: dict[str, Any], *, reliable: bool = True) -> Packet:
        self.sequence += 1
        packet = Packet(kind, self.sequence, payload, reliable)
        self.transport.send(self.peer, packet)
        if reliable:
            self.pending[packet.sequence] = (packet, 0.0)
        return packet

    def update(self, delta: float) -> None:
        for sequence, (packet, elapsed) in tuple(self.pending.items()):
            elapsed += max(0.0, delta)
            if elapsed >= self.resend_after:
                self.transport.send(self.peer, packet)
                elapsed = 0.0
            self.pending[sequence] = (packet, elapsed)
        for packet in self.transport.receive(self.peer):
            if packet.acknowledged is not None:
                self.pending.pop(packet.acknowledged, None)

    def acknowledge(self, packet: Packet) -> None:
        self.transport.send(self.peer, Packet("ack", self.sequence, {}, False, packet.sequence))


@dataclass(slots=True)
class PeerSession:
    peer_id: str
    channel: ReliableChannel
    receive_window: SequenceWindow = field(default_factory=SequenceWindow)
    connected: bool = True
    last_packet_time: float = 0.0

    def receive(self, packets: list[Packet]) -> list[Packet]:
        accepted: list[Packet] = []
        for packet in packets:
            if self.receive_window.accept(packet.sequence):
                accepted.append(packet)
                self.last_packet_time = 0.0
        return accepted


class SessionManager:
    def __init__(self, transport: Transport, *, timeout: float = 10.0) -> None:
        self.transport = transport
        self.timeout = timeout
        self.sessions: dict[str, PeerSession] = {}
        self._clock = 0.0

    def add(self, peer_id: str) -> PeerSession:
        channel = ReliableChannel(self.transport, peer_id)
        session = PeerSession(peer_id, channel)
        self.sessions[peer_id] = session
        return session

    def remove(self, peer_id: str) -> None:
        session = self.sessions.pop(peer_id, None)
        if session:
            session.connected = False

    def update(self, delta: float) -> dict[str, list[Packet]]:
        self._clock += max(0.0, delta)
        result: dict[str, list[Packet]] = {}
        for peer_id, session in tuple(self.sessions.items()):
            if not session.connected:
                continue
            session.last_packet_time += max(0.0, delta)
            session.channel.update(delta)
            received = self.transport.receive(peer_id)
            accepted = session.receive(received)
            if accepted:
                result[peer_id] = accepted
            if session.last_packet_time >= self.timeout:
                session.connected = False
        return result
