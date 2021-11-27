import argparse
import bisect
import itertools
import math
import time
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple

from isaac_rng import rng_next, string_to_seed
from isaac_item_pools import ITEM_POOLS
from isaac_items import ITEMS
from isaac_pickups import PICKUP_LIST
from isaac_recipes import find_hardcoded_recipe


QUALITY_RANGES = [
    (0, 0, 1),
    (9, 0, 2),
    (15, 1, 2),
    (19, 2, 3),
    (23, 2, 4),
    (27, 3, 4),
    (31, 3, 4),
    (35, 4, 4),
]


def is_achievement_unlocked(achievement_id):
    return True


def get_result(pickup_array: List[int], seed: int) -> Tuple[int, int]:
    pickup_count = [0] * len(PICKUP_LIST)
    quality_sum = 0
    for pickup_id in pickup_array:
        pickup_count[pickup_id] += 1
        quality_sum += PICKUP_LIST[pickup_id].quality

    hardcoded_recipe = find_hardcoded_recipe(pickup_array)
    if hardcoded_recipe:
        return hardcoded_recipe.item_id, quality_sum

    pool_weights = {
        0: 1.0,
        1: 2.0,
        2: 2.0,
        3: pickup_count[3] * 10.0,
        4: pickup_count[4] * 10.0,
        5: pickup_count[6] * 5.0,
        7: pickup_count[29] * 10.0,
        8: pickup_count[5] * 10.0,
        9: pickup_count[25] * 10.0,
        12: pickup_count[7] * 10.0,
        26: pickup_count[23] * 10.0
        if (
            pickup_count[15] + pickup_count[12] + pickup_count[8] + pickup_count[1] == 0
        )
        else 0.0,
    }

    currentSeed = seed
    for pickup_id in range(len(pickup_count)):
        for _ in range(pickup_count[pickup_id]):
            currentSeed = rng_next(currentSeed, pickup_id)

    collectible_count = 733
    collectible_list = [0.0] * collectible_count
    all_weight = 0.0

    for pool_id, pool_weight in pool_weights.items():
        if pool_weight <= 0.0:
            continue

        item_pool = ITEM_POOLS[pool_id]

        score = quality_sum
        if item_pool.lowered_quality:
            score -= 5

        for min_score, quality_min, quality_max in reversed(QUALITY_RANGES):
            if score >= min_score:
                break

        for quality in range(quality_min, quality_max + 1):
            for item_id, item_weight in item_pool.quality_lists[quality]:
                collectible_list[item_id] += pool_weight * item_weight

    cumulative_weights = list(itertools.accumulate(collectible_list))
    all_weight = sum(collectible_list)

    for _ in range(20):
        currentSeed = rng_next(currentSeed, 6)
        remains = float(currentSeed) * 2.3283062e-10 * all_weight

        if remains >= all_weight:
            break
        
        selected_item_id = bisect.bisect_right(cumulative_weights, remains)

        item_config = ITEMS[selected_item_id]
        if item_config.achievement_id is None or is_achievement_unlocked(
            item_config.achievement_id
        ):
            return selected_item_id, quality_sum

    # return breakfast if above fails
    return 25, quality_sum


def print_progress(current: int, total: int):
    when_to_print = {int(total * 0.1 * (i + 1)): (i + 1) * 10 for i in range(10)}
    if current in when_to_print:
        print(f"{when_to_print[current]}% done")


def find_item_id(seed_string: str, pickup_list: List[int]) -> None:
    seed = string_to_seed(seed_string)
    item_id, quality_sum = get_result(pickup_list, seed)
    item = ITEMS[item_id]
    print(f"SEED: {seed_string}")
    print()
    print(f"[ {PICKUP_LIST[pickup_list[0]].pickup_name}")
    for pickup_id in pickup_list[1:-1]:
        print(f"  {PICKUP_LIST[pickup_id].pickup_name}")

    print(f"  {PICKUP_LIST[pickup_id].pickup_name} ]")
    print(f"(quality {quality_sum}) -> {item.name} (id {item.item_id} {item.quality_str})")


def find_items_for_pickups(seed_string: str, pickup_list: List[int]) -> None:
    seed = string_to_seed(seed_string)
    total_recipe_count = int(math.factorial(len(pickup_list) + 7) / (math.factorial(len(pickup_list) - 1) * math.factorial(8)))
    print(f"Calculating {total_recipe_count} recipes...")

    craftable_set = set()
    with ProcessPoolExecutor() as executor:
        results = executor.map(get_result, itertools.combinations_with_replacement(pickup_list, 8), itertools.repeat(seed), chunksize=32)
        for result in results:
            craftable_set.add(result[0])

    print(f"SEED: {seed_string}")
    print()
    print(f"The following {len(craftable_set)} items are craftable with the given pickup types:")
    print(f"[ {PICKUP_LIST[pickup_list[0]].pickup_name}")
    for pickup_id in pickup_list[1:-1]:
        print(f"  {PICKUP_LIST[pickup_id].pickup_name}")

    print(f"  {PICKUP_LIST[pickup_list[-1]].pickup_name} ] ->")
    for item_id in sorted(craftable_set):
        item = ITEMS[item_id]
        print(f"{item.name} (id {item.item_id} {item.quality_str})")


def find_recipes_for_item(seed_string: str, pickup_list: List[int], item_id: int) -> None:
    seed = string_to_seed(seed_string)
    total_recipe_count = int(math.factorial(len(pickup_list) + 7) / (math.factorial(len(pickup_list) - 1) * math.factorial(8)))
    print(f"Calculating {total_recipe_count} recipes...")
    
    item_recipes = []
    with ProcessPoolExecutor() as executor:
        results = executor.map(get_result, itertools.combinations_with_replacement(pickup_list, 8), itertools.repeat(seed), chunksize=32)
        for result in results:
            if item_id == result[0]:
                item_recipes.append(result)

    item = ITEMS[item_id]
    print(f"SEED: {seed_string}")
    print()
    print(f"The following recipes are viable for {item.name} (id {item.item_id} {item.quality_str}) with the given pickup types:")
    item_recipes.sort(key=lambda tup: tup[1])
    for recipe, quality_sum in item_recipes:
        print(f"[{', '.join([PICKUP_LIST[pid].pickup_name for pid in recipe])}] ({quality_sum})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='Calculate bag of crafting recipes.', epilog="The default behavior is to calculate the item generated by the provided pickups.")
    parser.add_argument("--seed", required=True, help="The seed for your save file (should be 8 characters; remove the space)")
    parser.add_argument('--pickups', required=True, metavar='ID', type=int, nargs="+", help='Use these pickup IDs in calculation. If calculating a single item to create, you must pass 8 IDs. The following are all the valid IDs: ' + ', '.join([f'{pickup.pickup_id} - {pickup.pickup_name}' for pickup in PICKUP_LIST if pickup is not None]))
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--find-pickup-recipes', action="store_true", help="Find all recipes that use these pickup types.")
    group.add_argument('--find-item-recipes', metavar='ITEM_ID', type=int, help="Find all recipes matching this item ID for the given pickup types (sorted by quality).")
    args = parser.parse_args()

    t0 = time.monotonic()
    if args.find_pickup_recipes:
        pickups = list(set(args.pickups))
        find_items_for_pickups(args.seed, pickups)
    elif args.find_item_recipes:
        pickups = list(set(args.pickups))
        find_recipes_for_item(args.seed, pickups, args.find_item_recipes)
    else:
        assert len(args.pickups) == 8, "You must provide 8 pickup IDs when calculating a single result."
        find_item_id(args.seed, args.pickups)
    
    t1 = time.monotonic()
    print()
    print(f"Operation took {(t1 - t0) * 1000:.2f} ms.")