# Copyright (c) 2026 Yashraj Sachin Ghemud
# SPDX-License-Identifier: MIT

"""Grid pathfinding utilities."""

from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass
from itertools import count

GridPoint = tuple[int, int]
Passable = Callable[[int, int], bool]


@dataclass(frozen=True, slots=True)
class PathRequest:
    start: GridPoint
    goal: GridPoint
    allow_diagonal: bool = False
    max_nodes: int = 100_000


class AStar:
    """A* implementation with deterministic tie-breaking and bounded work."""

    def __init__(self, passable: Passable) -> None:
        self.passable = passable

    def find(self, request: PathRequest) -> list[GridPoint] | None:
        start, goal = request.start, request.goal
        if not self.passable(*start) or not self.passable(*goal):
            return None
        if start == goal:
            return [start]
        directions: tuple[GridPoint, ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))
        if request.allow_diagonal:
            directions += ((1, 1), (1, -1), (-1, 1), (-1, -1))
        sequence = count()
        frontier: list[tuple[float, int, GridPoint]] = [(0.0, next(sequence), start)]
        came_from: dict[GridPoint, GridPoint] = {}
        cost: dict[GridPoint, float] = {start: 0.0}
        explored = 0
        while frontier and explored < request.max_nodes:
            _, _, current = heapq.heappop(frontier)
            explored += 1
            if current == goal:
                return self._reconstruct(came_from, current)
            for dx, dy in directions:
                candidate = current[0] + dx, current[1] + dy
                if not self.passable(*candidate):
                    continue
                if (
                    dx
                    and dy
                    and (
                        not self.passable(current[0] + dx, current[1])
                        or not self.passable(current[0], current[1] + dy)
                    )
                ):
                    continue
                step_cost = 1.41421356237 if dx and dy else 1.0
                new_cost = cost[current] + step_cost
                if new_cost < cost.get(candidate, float("inf")):
                    cost[candidate] = new_cost
                    priority = new_cost + self._heuristic(candidate, goal, request.allow_diagonal)
                    heapq.heappush(frontier, (priority, next(sequence), candidate))
                    came_from[candidate] = current
        return None

    @staticmethod
    def _heuristic(a: GridPoint, b: GridPoint, diagonal: bool) -> float:
        dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
        return max(dx, dy) if diagonal else dx + dy

    @staticmethod
    def _reconstruct(came_from: dict[GridPoint, GridPoint], current: GridPoint) -> list[GridPoint]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path


class FlowField:
    """Reverse breadth-first field for many agents sharing one destination."""

    def __init__(self, passable: Passable) -> None:
        self.passable = passable
        self.costs: dict[GridPoint, int] = {}
        self.next_step: dict[GridPoint, GridPoint] = {}

    def build(self, goal: GridPoint, *, max_nodes: int = 100_000) -> None:
        self.costs.clear()
        self.next_step.clear()
        queue: list[GridPoint] = [goal]
        self.costs[goal] = 0
        head = 0
        while head < len(queue) and len(self.costs) < max_nodes:
            current = queue[head]
            head += 1
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                candidate = current[0] + dx, current[1] + dy
                if candidate in self.costs or not self.passable(*candidate):
                    continue
                self.costs[candidate] = self.costs[current] + 1
                self.next_step[candidate] = current
                queue.append(candidate)

    def direction_for(self, point: GridPoint) -> GridPoint | None:
        return self.next_step.get(point)
