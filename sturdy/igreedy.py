import numpy as np
from scipy.optimize import minimize
from typing import Dict
import sturdy
from sturdy.utils.misc import supply_rate
from sturdy.utils.yiop import round_down_to_sum_below, yiop_allocation_algorithm
from sturdy.utils.misc import format_num_prec


def target_function(x, pools):
    pool_items = [pool for idx, pool in pools.items()]
    total_yield = 0
    for idx, pool in enumerate(pool_items):
        alloc = x[idx]
        util_rate = pool["borrow_amount"] / (pool["reserve_size"] + alloc)
        pool_yield = alloc * supply_rate(util_rate, pool)
        total_yield += pool_yield
    return -total_yield


def borrow_rate(util_rate: float, pool: Dict) -> float:
    # interest_rate = (
    #     pool["base_rate"] + (util_rate / pool["optimal_util_rate"]) * pool["base_slope"]
    #     if util_rate < pool["optimal_util_rate"]
    #     else pool["base_rate"]
    #     + pool["base_slope"]
    #     + ((util_rate - pool["optimal_util_rate"]) / (1 - pool["optimal_util_rate"]))
    #     * pool["kink_slope"]
    # )
    interest_rate = (
        pool["base_rate"]
        + pool["base_slope"]
        + ((util_rate - pool["optimal_util_rate"]) / (1 - pool["optimal_util_rate"]))
        * pool["kink_slope"]
    )

    # interest_rate = (
    #     pool["base_rate"] + (util_rate / pool["optimal_util_rate"]) * pool["base_slope"]
    # )
    return interest_rate


def supply_rate(util_rate: float, pool: Dict) -> float:
    return util_rate * borrow_rate(util_rate, pool)

def pool_target(alloc, borrow_amount, pool):
    util_rate = borrow_amount / (pool["reserve_size"] + alloc)
    pool_yield = alloc * supply_rate(util_rate, pool)
    return -pool_yield


def igreedy_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations


    def normalize_sum_zero(input_arr):
        """
        This function normalizes an array to have a sum of 0.
        """
        arr = np.array(input_arr)
        ratio = arr[arr > 0].sum() /  -arr[arr < 0].sum()
        for idx, v in enumerate(arr):
            if arr[idx] < 0:
                arr[idx] *= ratio
        return arr

    yiop_alloc = yiop_allocation_algorithm(synapse)
    arr = []
    for pool in pools.values():
        res = minimize(pool_target, 0, args=(pool['borrow_amount'] + 0.1, pool), bounds=[(0, 0.6)], method='SLSQP')
        # res = minimize(pool_target, 0, args=(pool["reserve_size"], pool), bounds=[(0, 0.6)], method='SLSQP')
        arr.append(res.x[0])
    x0 = np.array(arr)

    best_allocations = {k: v for k, v in zip(pools.keys(), x0)}

    diff = []
    for k in best_allocations.keys():
        diff.append(best_allocations[k] - yiop_alloc[k])

    adjust = normalize_sum_zero(diff)

    better = {}
    for k, v in yiop_alloc.items():
        better[k] = v + adjust[int(k)]

    # # round down because sometimes the optimizer gives result which is slightly above max_balance
    # allocation = round_down_to_sum_below(res.x, max_balance)

    # return {k: v for k, v in zip(pools.keys(), allocation)}
    return better
