from typing import Dict
import sturdy


def lazy_and_humble_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    balance = max_balance
    pools = synapse.assets_and_pools["pools"]

    # must allocate borrow amount as a minimum to ALL pools
    balance -= sum([v["borrow_amount"] for k, v in pools.items()])
    current_allocations = {k: v["borrow_amount"] for k, v in pools.items()}
    sum_allocations = sum(current_allocations.values())
    remaining_delta = sum_allocations / len(pools)
    humble_allocations = {k: v + remaining_delta * 0.2 for k, v in current_allocations.items()}
    return humble_allocations


def lazy_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    balance = max_balance
    pools = synapse.assets_and_pools["pools"]

    # must allocate borrow amount as a minimum to ALL pools
    balance -= sum([v["borrow_amount"] for k, v in pools.items()])
    current_allocations = {k: v["borrow_amount"] for k, v in pools.items()}
    return current_allocations
