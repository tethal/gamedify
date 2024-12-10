from __future__ import annotations

import math
from typing import Generator, NamedTuple

from app import model

sqrt3 = math.sqrt(3)
tile_size = 11
tile_width = sqrt3 * tile_size
tile_height = 2 * tile_size


def triangular(n: int):
    return n * (n + 1) // 2


def triangular_inv(n: int):
    return math.floor((math.sqrt(1 + 8 * n + 1) - 1) // 2)


class TileLayout(NamedTuple):
    row: int
    col: int

    @property
    def id(self):
        return triangular(self.row) + self.col

    @property
    def q(self):
        return -self.row + self.col

    @property
    def r(self):
        return self.row

    @property
    def x(self):
        return tile_size * (sqrt3 * self.q + (sqrt3 * self.r) / 2)

    @property
    def y(self):
        return tile_size * 1.5 * self.r


class BoardLayout(NamedTuple):
    rows: int

    @property
    def view_box(self) -> str:
        board_width = math.ceil(sqrt3 * tile_size * self.rows)
        board_height = math.ceil((1.5 * (self.rows - 1) + 2) * tile_size)
        board_min_x = -board_width / 2
        board_max_y = -tile_size
        return " ".join(str(i) for i in (board_min_x, board_max_y, board_width, board_height))

    @property
    def tiles(self) -> tuple[TileLayout, ...]:
        return tuple(TileLayout(row, col) for row in range(self.rows) for col in range(row + 1))

    @staticmethod
    def from_max_tile_count(max_tile_count: int) -> BoardLayout:
        rows = triangular_inv(max_tile_count)
        return BoardLayout(rows)


DIRS = (
    (-1, -1),  # top left
    (-1, 0),  # top right
    (0, -1),  # left
    (0, 1),  # right
    (1, 0),  # bottom left
    (1, 1),  # bottom right
)


def is_winner_move(game: model.Game, start_tile: model.Tile) -> bool:
    visited = set()
    tiles = {(t.row, t.col): t for t in game.tiles}

    def neighbours(r, c) -> Generator[tuple[int, int], None, None]:
        return ((r + dr, c + dc) for dr, dc in DIRS)

    def visit(r, c):
        tile = tiles.get((r, c), None)
        if not tile or tile.state != start_tile.state or (r, c) in visited:
            return
        visited.add((r, c))
        for nr, nc in neighbours(r, c):
            visit(nr, nc)

    visit(start_tile.row, start_tile.col)
    left_edge = any(col == 0 for (_, col) in visited)
    right_edge = any(col == row for row, col in visited)
    bottom_edge = any(row == game.rows - 1 for row, _ in visited)
    return left_edge and right_edge and bottom_edge
