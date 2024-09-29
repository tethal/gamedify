from __future__ import annotations

import math
from typing import NamedTuple

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
    tiles: tuple[TileLayout, ...]

    @property
    def view_box(self) -> str:
        board_width = math.ceil(sqrt3 * tile_size * self.rows)
        board_height = math.ceil((1.5 * (self.rows - 1) + 2) * tile_size)
        board_min_x = -board_width / 2
        board_max_y = -tile_size
        return " ".join(str(i) for i in (board_min_x, board_max_y, board_width, board_height))

    @staticmethod
    def from_max_tile_count(max_tile_count: int) -> BoardLayout:
        rows = triangular_inv(max_tile_count)
        tiles = tuple(TileLayout(row, col) for row in range(rows) for col in range(row + 1))
        return BoardLayout(rows, tiles)
