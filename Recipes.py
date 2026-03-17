"""recipes file"""

"""
1 = Grass
2 = Dirt
3 = Stone
4 = oak_log
5 = oak_Leaf
6 = Wood
"""

"""
 1      2       3
 4      5       6
 7      8       9
"""


Wood_recipes = {}


def craft(grid:dict) -> tuple[int, int]:
    layout = []
    for i in range(1, 10):
        item = grid.get(f"craft_{i}")
        layout.append(item[0] if item else 0)

    if layout.count(4) == 1 and layout.count(0) == 8:
        return (6, 4)
    if layout.count(6) == 1 and layout.count(0) == 8:
        return (5, 4)
    if layout.count(1) == 1 and layout.count(0) == 8:
        return (9, 4)
    return (0,0)