

keys = [f"{i+1}" for i in range(36)]
inventory_dict = dict.fromkeys(keys, None)

keys = [f"craft_{i+1}" for i in range(9)]
Crafting_grid = dict.fromkeys(keys, None)
Crafting_grid["craft_result"] = None
cursor_slot = None


def add_item(items, amt=1, index: int = None):
    avalible_index = index
    if index == None:
        for i in inventory_dict.keys():
            if inventory_dict[i] == None:
                avalible_index = i
                break
            if inventory_dict[i][0] == items:
                inventory_dict[i][1] += amt
                return

    inventory_dict[avalible_index] = [int(items), amt]


def add_item_at(items, amt = 1, index:str = None):
    if index == None:
        add_item(items, amt)
    else:
        inventory_dict[index] = [int(items), amt]


def remove_item(items, amt = 1):

    for i in inventory_dict.keys():
        try:
            if inventory_dict[i][0] == int(items):
                inventory_dict[i][1] -= amt
                if inventory_dict[i][1] <= 0:
                    inventory_dict[i] = None
                return
        except TypeError:
            continue


#inventory order
"""
e = [
    [28, 29, 30, 31, 32, 33, 34, 35, 36]
    [19, 20, 21, 22, 23, 24, 25, 26, 27]
    [10, 11, 12, 13, 14, 15, 16, 17, 18]
    [ 1,  2,  3,  4,  5,  6,  7,  8,  9]
]
"""