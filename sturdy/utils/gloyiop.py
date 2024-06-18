"""
Using regions to seek for optimal allocation of assets

Since each pool represents a dimension divided by a kink, we split each pool into 2 regions,
for 10 pools there will be 2^10 = 1024 regions to search.
"""
import itertools
import sys
from scipy.optimize import minimize
import numpy as np
from sturdy.utils.misc import supply_rate
from sturdy.utils.yiop import target_function
from sturdy.utils.yiop import round_down_to_4_digits
from sturdy.utils.yiop import round_down_to_sum_below
import sturdy
from typing import Dict, List, Tuple


def generate_bounds(pools, max_balance):
    """
    Sample pools
    {
        '0': {'pool_id': '0', 'base_rate': 0.03, 'base_slope': 0.019, 'kink_slope': 0.663, 'optimal_util_rate': 0.9, 'borrow_amount': 0.7, 'reserve_size': 1.0},
        '1': {'pool_id': '1', 'base_rate': 0.02, 'base_slope': 0.064, 'kink_slope': 0.806, 'optimal_util_rate': 0.7, 'borrow_amount': 0.9, 'reserve_size': 1.0
    }
    """
    pool_items = list(pools.items())
    iterables = []
    for _, pool in pool_items:
        kink = pool["borrow_amount"] / pool['optimal_util_rate'] - pool['reserve_size']
        if kink <= 0:
            iterables.append([(0, max_balance)])
        else:
            iterables.append([(0, kink), (kink, max_balance)])

    results = list(itertools.product(*iterables))
    return [list(item) for item in results]


def global_yiop_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    bounds = generate_bounds(synapse.assets_and_pools["pools"], synapse.assets_and_pools["total_assets"])

    # pools = synapse.assets_and_pools["pools"]
    # bounds = [[(0, 1) for _ in pools.items()]] # Assuming x[0] and x[1] are bounded between 0 and 1

    best_allocation = None
    current_best = sys.float_info.min
    for bound in bounds:
        result, allocation = yiop_region_allocation_algorithm(synapse, bound)
        if result > current_best:
            current_best = result
            best_allocation = allocation
    return best_allocation


def yiop_region_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets, bnds: List[Tuple]) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    # bnds = [(0, 1) for _ in pools.items()]  # Assuming x[0] and x[1] are bounded between 0 and 1

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations

    # Define the equality constraint (sum of elements equals max_balance)
    cons = {'type': 'eq', 'fun': lambda x: np.sum(x) - max_balance}

    x0 = np.array([0 for _ in pools.items()])

    # Perform the optimization using the SLSQP method which supports constraints
    res = minimize(target_function, x0, args=(pools), method='SLSQP', constraints=cons, bounds=bnds, options={'maxiter': 200, 'disp': False, 'ftol': 1e-20})

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    # negative because we minimize the object instead of maximize
    return -res.fun, {k: v for k, v in zip(pools.keys(), allocation)}
