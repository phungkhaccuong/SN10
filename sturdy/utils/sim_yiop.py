import sys
import pandas as pd
import numpy as np
import copy
from typing import Dict, List, Tuple
from sturdy.protocol import AllocateAssets
from sturdy.score import run_simulation
from sturdy.utils.gloyiop import generate_bounds
from sturdy.utils.yiop import round_down_to_sum_below, target_function, yiop_allocation_algorithm
from scipy.optimize import minimize

from sturdy.validator.reward import calculate_aggregate_apy
from sturdy.validator.simulator import Simulator
from sturdy.validator.static_simulator import StaticSimulator

def simulated_yiop_target_function(x, assets_and_pools, seed=None):
    pools = assets_and_pools['pools']
    allocation = {k: v for k, v in zip(pools.keys(), x)}
    simulator = StaticSimulator(seed=seed)
    simulator.initialize()
    simulator.reset()
    simulator.init_data(copy.deepcopy(assets_and_pools), allocation)
    simulator.update_reserves_with_allocs()
    simulator.run()

    return -calculate_aggregate_apy(allocation, assets_and_pools, simulator.timesteps, simulator.pool_history)


def simulated_yiop_allocation_algorithm(synapse: AllocateAssets, seed=None) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations


    # Define the bounds for the variables
    bnds = [(0, max_balance) for _ in pools.items()]  # Assuming x[0] and x[1] are bounded between 0 and 1

    # Define the equality constraint (sum of elements equals 1)
    cons = {'type': 'eq', 'fun': lambda x: np.sum(x) - max_balance}

    x0 = np.array([0 for _ in pools.items()])

    # Perform the optimization using the SLSQP method which supports constraints
    res = minimize(simulated_yiop_target_function, x0, args=(synapse.assets_and_pools, seed), method='SLSQP', constraints=cons, bounds=bnds)

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    return {k: v for k, v in zip(pools.keys(), allocation)}


def sim_global_yiop_allocation_algorithm(synapse: AllocateAssets, simulator=None) -> Dict:
    bounds = generate_bounds(synapse.assets_and_pools["pools"], synapse.assets_and_pools["total_assets"])

    best_allocation = None
    current_best = sys.float_info.min
    for bound in bounds:
        result, allocation = yiop_region_allocation_algorithm(synapse, bound, simulator)
        if result > current_best:
            current_best = result
            best_allocation = allocation
    return best_allocation


def yiop_region_allocation_algorithm(synapse: AllocateAssets, bnds: List[Tuple], simulator=None) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations

    # Define the equality constraint (sum of elements equals max_balance)
    cons = {'type': 'eq', 'fun': lambda x: np.sum(x) - max_balance}

    x0 = np.array([0 for _ in pools.items()])

    # Perform the optimization using the SLSQP method which supports constraints
    res = minimize(simulated_yiop_target_function, x0, args=(synapse.assets_and_pools, simulator), method='SLSQP', constraints=cons, bounds=bnds, options={'maxiter': 200, 'disp': False})

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    # negative because we minimize the object instead of maximize
    return -res.fun, {k: v for k, v in zip(pools.keys(), allocation)}

