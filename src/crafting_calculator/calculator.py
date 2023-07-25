import bisect
import itertools
import math
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple
from functools import partial, update_wrapper

from .isaac_rng import rng_next, string_to_seed
from .isaac_item_pools import ItemPool
from .isaac_items import ItemListEntry
from .isaac_pickups import PICKUP_LIST
from .isaac_recipes import find_hardcoded_recipe
from .utilities import get_quality_ranges, hardcoded_recipe_requires_unlock


def get_result(
    platform: str, game_version: str, pickup_array: List[int], seed: int
) -> Tuple[List[int], List[int], int]:
    candidates = []
    pickup_count = [0] * len(PICKUP_LIST)
    quality_sum = 0
    for pickup_id in pickup_array:
        pickup_count[pickup_id] += 1
        quality_sum += PICKUP_LIST[pickup_id].quality

    item_pools = ItemPool.load_item_pools(platform, game_version)
    items = ItemListEntry.load_item_list(platform, game_version)

    hardcoded_recipe = find_hardcoded_recipe(platform, game_version, pickup_array)
    if hardcoded_recipe:
        # v1.7.8 requires that hardcoded items are now unlocked. If there's an achievement id, search for more candidates
        if hardcoded_recipe_requires_unlock(platform, game_version):
            candidates.append(hardcoded_recipe.item_id)
        else:
            return pickup_array, [hardcoded_recipe.item_id], quality_sum

    pool_weights = {
        0: 1,
        1: 2,
        2: 2,
        3: pickup_count[3] * 10,
        4: pickup_count[4] * 10,
        5: pickup_count[6] * 5,
        7: pickup_count[29] * 10,
        8: pickup_count[5] * 10,
        9: pickup_count[25] * 10,
        12: pickup_count[7] * 10,
        26: pickup_count[23] * 10
        if (
            pickup_count[15] + pickup_count[12] + pickup_count[8] + pickup_count[1] == 0
        )
        else 0,
    }

    current_seed = seed
    for pickup_id in range(len(pickup_count)):
        for _ in range(pickup_count[pickup_id]):
            current_seed = rng_next(current_seed, pickup_id)

    collectible_count = 733
    collectible_list = [0.0] * collectible_count
    quality_min = 0
    quality_max = 4

    quality_ranges = get_quality_ranges(platform, game_version)

    for pool_id, pool_weight in pool_weights.items():
        if pool_weight <= 0:
            continue

        item_pool = item_pools[pool_id]

        score = quality_sum
        if item_pool.lowered_quality:
            score -= 5

        for min_score, quality_min, quality_max in reversed(quality_ranges):
            if score >= min_score:
                break

        for quality in range(quality_min, quality_max + 1):
            for item_id, item_weight in item_pool.quality_lists[quality]:
                collectible_list[item_id] += pool_weight * item_weight

    cumulative_weights = list(itertools.accumulate(collectible_list))
    all_weight = sum(collectible_list)

    for _ in range(20):
        current_seed = rng_next(current_seed, 6)
        remains = float(current_seed) * 2.3283062e-10 * all_weight

        if remains >= all_weight:
            break

        selected_item_id = bisect.bisect_right(cumulative_weights, remains)

        item_config = items[selected_item_id]
        candidates.append(selected_item_id)
        if item_config.achievement_id is None:
            return pickup_array, candidates, quality_sum

    # return breakfast if above fails
    candidates.append(25)
    return pickup_array, candidates, quality_sum


def print_progress(current: int, total: int):
    when_to_print = {int(total * 0.1 * (i + 1)): (i + 1) * 10 for i in range(10)}
    if current in when_to_print:
        print(f"{when_to_print[current]}% done")


def find_item_id(platform: str, game_version: str, seed_string: str, pickup_list: List[int]) -> None:
    seed = string_to_seed(seed_string)
    _, item_ids, quality_sum = get_result(platform, game_version, pickup_list, seed)
    items = ItemListEntry.load_item_list(platform, game_version)
    print(f"SEED: {seed_string}")
    print()
    print(f"[ {PICKUP_LIST[pickup_list[0]].pickup_name}")
    for pickup_id in pickup_list[1:-1]:
        print(f"  {PICKUP_LIST[pickup_id].pickup_name}")

    print(f"  {PICKUP_LIST[pickup_list[-1]].pickup_name} ]")

    quality_min = 0
    quality_max = 1
    for min_score, quality_min, quality_max in reversed(get_quality_ranges(platform, game_version)):
        if quality_sum >= min_score:
            break

    print(
        f"(total {quality_sum}, {'★' * quality_min + '☆' * (4 - quality_min)}-{'★' * quality_max + '☆' * (4 - quality_max)})"
    )
    print("Candidates:")
    for item_id in item_ids:
        item = items[item_id]
        print(f"{item.name} (id {item.item_id} {item.quality_str})")


def find_items_for_pickups(
    platform: str, game_version: str, seed_string: str, pickup_list: List[int]
) -> None:
    seed = string_to_seed(seed_string)
    total_recipe_count = int(
        math.factorial(len(pickup_list) + 7)
        / (math.factorial(len(pickup_list) - 1) * math.factorial(8))
    )
    print(f"Calculating {total_recipe_count} recipes...")

    get_result_b = update_wrapper(partial(get_result, platform, game_version), get_result)

    craftable_set = set()
    with ProcessPoolExecutor() as executor:
        results = executor.map(
            get_result_b,
            itertools.combinations_with_replacement(pickup_list, 8),
            itertools.repeat(seed),
            chunksize=32,
        )
        for result in results:
            craftable_set.add(result[1][0])

    print(f"SEED: {seed_string}")
    print()
    print(
        f"The following {len(craftable_set)} items are craftable with the given pickup types:"
    )
    print(f"[ {PICKUP_LIST[pickup_list[0]].pickup_name}")
    for pickup_id in pickup_list[1:-1]:
        print(f"  {PICKUP_LIST[pickup_id].pickup_name}")

    print(f"  {PICKUP_LIST[pickup_list[-1]].pickup_name} ] ->")
    items = ItemListEntry.load_item_list(platform, game_version)
    for item_id in sorted(craftable_set):
        item = items[item_id]
        print(f"{item.name} (id {item.item_id} {item.quality_str})")


def find_recipes_for_item(
    platform: str, game_version: str, seed_string: str, pickup_list: List[int], item_id: int
) -> None:
    seed = string_to_seed(seed_string)
    total_recipe_count = int(
        math.factorial(len(pickup_list) + 7)
        / (math.factorial(len(pickup_list) - 1) * math.factorial(8))
    )
    print(f"Calculating {total_recipe_count} recipes...")

    get_result_b = update_wrapper(partial(get_result, platform, game_version), get_result)

    item_recipes = []
    with ProcessPoolExecutor() as executor:
        results = executor.map(
            get_result_b,
            itertools.combinations_with_replacement(pickup_list, 8),
            itertools.repeat(seed),
            chunksize=32,
        )
        for result in results:
            if item_id == result[1][0]:
                item_recipes.append(result)

    items = ItemListEntry.load_item_list(platform, game_version)
    item = items[item_id]
    print(f"SEED: {seed_string}")
    print()
    print(
        f"The following recipes are viable for {item.name} (id {item.item_id} {item.quality_str}) with the given pickup types:"
    )
    item_recipes.sort(key=lambda tup: tup[2])
    for recipe, _, quality_sum in item_recipes:
        print(
            f"[{', '.join([PICKUP_LIST[pid].pickup_name for pid in recipe])}] ({quality_sum})"
        )


def find_uncraftable_items(
    platform: str, game_version: str, seed_string: str, pickup_list: List[int]
) -> None:
    seed = string_to_seed(seed_string)
    total_recipe_count = int(
        math.factorial(len(pickup_list) + 7)
        / (math.factorial(len(pickup_list) - 1) * math.factorial(8))
    )
    print(f"Calculating {total_recipe_count} recipes...")

    items = ItemListEntry.load_item_list(platform, game_version)
    uncraftable_set = set(items)
    with ProcessPoolExecutor() as executor:
        results = executor.map(
            get_result,
            itertools.combinations_with_replacement(pickup_list, 8),
            itertools.repeat(seed),
            chunksize=32,
        )
        for result in results:
            uncraftable_set.discard(result[1][0])

    print(f"SEED: {seed_string}")
    print()
    print(
        f"The following {len(uncraftable_set)} items are uncraftable with the given pickup types:"
    )
    print(f"[ {PICKUP_LIST[pickup_list[0]].pickup_name}")
    for pickup_id in pickup_list[1:-1]:
        print(f"  {PICKUP_LIST[pickup_id].pickup_name}")

    print(f"  {PICKUP_LIST[pickup_list[-1]].pickup_name} ] -X->")
    for item_id in sorted(uncraftable_set):
        item = items[item_id]
        print(f"{item.name} (id {item.item_id} {item.quality_str})")
