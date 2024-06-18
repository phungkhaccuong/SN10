from decimal import Decimal
import math
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
    pool_items = list(pools.items())
    current_allocations = {k: v["borrow_amount"] for k, v in pool_items}
    return current_allocations


from sturdy.utils.misc import supply_rate

def lazy_prob_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    balance = Decimal(max_balance)
    pools = synapse.assets_and_pools["pools"]

    pool_items = list(pools.items())
    max_pool = None
    max_borrow_amount = 0
    rates = []
    for _, pool in pool_items:
        mean_util_rate = pool['borrow_amount'] / pool['reserve_size']
        rate = supply_rate(mean_util_rate, pool)
        rates.append({
            'pool_id': pool['pool_id'],
            'rate': Decimal(rate)
        })

    current_allocations = {k: 0 for k, v in pool_items}
    sorted_rate = sorted(rates, key=lambda x: x['rate'], reverse=False)
    for rate in sorted_rate:
        if balance - rate['rate'] < 0:
            current_allocations[rate['pool_id']] = float(balance) - 0.001
            break
        balance -= rate['rate']
        current_allocations[rate['pool_id']] = float(rate['rate'])

    return current_allocations


from sturdy.utils.misc import format_num_prec, supply_rate
from sturdy.constants import *

def sorted_greedy_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    balance = max_balance
    pools = synapse.assets_and_pools["pools"]

    # how much of our assets we have allocated
    current_allocations = {k: 0.0 for k, _ in pools.items()}

    assert balance >= 0

    # run greedy algorithm to allocate assets to pools
    while balance > 0:
        # TODO: use np.float32 instead of format()??
        current_supply_rates = {
            k: format_num_prec(
                supply_rate(
                    util_rate=v["borrow_amount"]
                    / (current_allocations[k] + pools[k]["reserve_size"]),
                    pool=v,
                )
            )
            for k, v in pools.items()
        }
        # print('current_supply_rates', current_supply_rates)
        default_chunk_size = format_num_prec(CHUNK_RATIO * max_balance)
        to_allocate = 0

        if balance < default_chunk_size:
            to_allocate = balance
        else:
            to_allocate = default_chunk_size

        balance = format_num_prec(balance - to_allocate)
        assert balance >= 0
        max_apy = max(current_supply_rates.values())
        min_apy = min(current_supply_rates.values())
        apy_range = format_num_prec(max_apy - min_apy)

        optimal = {}
        for k, v in current_supply_rates.items():
            optimal[k] = {
                'supply_rate': v,
                'allocation': current_allocations[k]
            }

        alloc_it = optimal.items()
        alloc_it = sorted(alloc_it, key=lambda x: x[1]['supply_rate'], reverse=True)
        alloc_it = {k: v['allocation'] for k, v in alloc_it}
        # print(f'sorted alloc_it: {alloc_it}')
        for pool_id, _ in alloc_it.items():
            delta = format_num_prec(
                to_allocate * ((current_supply_rates[pool_id] - min_apy) / (apy_range)),
            )
            current_allocations[pool_id] = format_num_prec(
                current_allocations[pool_id] + delta
            )
            to_allocate = format_num_prec(to_allocate - delta)

        assert to_allocate == 0  # should allocate everything from current chunk

    return current_allocations


def equity_greedy_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    balance = max_balance
    pools = synapse.assets_and_pools["pools"]

    # how much of our assets we have allocated
    current_allocations = {k: max_balance / len(pools) for k, _ in pools.items()}

    return current_allocations


def equal_greedy_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    balance = max_balance
    pools = synapse.assets_and_pools["pools"]

    # how much of our assets we have allocated
    current_allocations = {k: 0.0 for k, _ in pools.items()}

    assert balance >= 0

    # run greedy algorithm to allocate assets to pools
    while balance > 0:
        # TODO: use np.float32 instead of format()??
        current_supply_rates = {
            k: format_num_prec(
                supply_rate(
                    util_rate=v["borrow_amount"]
                    / (current_allocations[k] + pools[k]["reserve_size"]),
                    pool=v,
                )
            )
            for k, v in pools.items()
        }

        default_chunk_size = format_num_prec(CHUNK_RATIO * max_balance)
        to_allocate = 0

        if balance < default_chunk_size:
            to_allocate = balance
        else:
            to_allocate = default_chunk_size

        balance = format_num_prec(balance - to_allocate)
        assert balance >= 0
        max_apy = max(current_supply_rates.values())
        min_apy = min(current_supply_rates.values())
        apy_range = format_num_prec(max_apy - min_apy)

        alloc_it = current_allocations.items()
        alloc_it = sorted(alloc_it, key=lambda x: current_supply_rates[x[0]])
        # print(f'alloc it: {alloc_it}')
        for pool_id, _ in alloc_it:
            delta = format_num_prec(
                to_allocate * ((current_supply_rates[pool_id] - min_apy) / (apy_range)),
            )
            # print(f'allocating pool {pool_id}: {delta} with supply rate: {current_supply_rates[pool_id]}')
            current_allocations[pool_id] = format_num_prec(
                current_allocations[pool_id] + delta
            )
            to_allocate = format_num_prec(to_allocate - delta)
        # print(f'after allocation: {current_allocations}')

        assert to_allocate == 0  # should allocate everything from current chunk

    return current_allocations



def pick_one_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    pools = synapse.assets_and_pools["pools"]

    simulation = {
        k: supply_rate(1, v)
        for k,v in pools.items()
    }


    # how much of our assets we have allocated
    current_allocations = {k: 0.0 for k, _ in pools.items()}
    alloc_it = current_allocations.items()
    alloc_it = sorted(alloc_it, key=lambda x: simulation[x[0]], reverse=True)
    max_pool_id = alloc_it[0][0]
    current_allocations[max_pool_id] = 1
    return current_allocations

