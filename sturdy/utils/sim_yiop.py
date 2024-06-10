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
    # sim_allocation = {k: v for k, v in zip(pools.keys(), x)}
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



def sim_yiop_algorithm(synapse: AllocateAssets) -> Dict:
    """
    Run a simulation to get the expected value of the borrow_amount
    Assumption: using this expected value as initial pools parameters will bring better yield
    """
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations

    # init_allocation = {
    #     k: max_balance / len(pools) for k, v in pools.items()
    # }
    init_allocation = yiop_allocation_algorithm(synapse)
    # init_allocation = {k: v['borrow_amount'] for k, v in pools.items()}
    # init_allocation = {k: 0.1 for k, v in pools.items()}
    # init_allocation = {k: 0 for k, v in pools.items()}

    simulator = run_simulation(synapse.assets_and_pools, init_allocation)
    borrow_amounts = [{
            pool_id: pool[pool_id]['borrow_amount']
                for pool_id in init_allocation.keys()
            }
        for pool in simulator.pool_history
    ]

    df = pd.DataFrame(borrow_amounts)
    df.mean()
    new_pools = copy.deepcopy(pools)
    for pool in new_pools.values():
        pool['borrow_amount'] = df[pool['pool_id']].mean()

    return yiop_allocation_algorithm(AllocateAssets(assets_and_pools={
        'total_assets': max_balance,
        'pools': new_pools
    }))
    # return yiop_allocation_algorithm(synapse)


def global_yiop_allocation_algorithm(synapse: AllocateAssets, simulator=None) -> Dict:
    bounds = generate_bounds(synapse.assets_and_pools["pools"], synapse.assets_and_pools["total_assets"])

    # pools = synapse.assets_and_pools["pools"]
    # bounds = [[(0, 1) for _ in pools.items()]] # Assuming x[0] and x[1] are bounded between 0 and 1

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

    # bnds = [(0, 1) for _ in pools.items()]  # Assuming x[0] and x[1] are bounded between 0 and 1

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations

    # Define the equality constraint (sum of elements equals max_balance)
    cons = {'type': 'eq', 'fun': lambda x: np.sum(x) - max_balance}

    x0 = np.array([0 for _ in pools.items()])

    # Perform the optimization using the SLSQP method which supports constraints
    res = minimize(simulated_yiop_target_function_2, x0, args=(synapse.assets_and_pools, simulator), method='SLSQP', constraints=cons, bounds=bnds, options={'maxiter': 200, 'disp': False, 'ftol': 1e-20})

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    # negative because we minimize the object instead of maximize
    return -res.fun, {k: v for k, v in zip(pools.keys(), allocation)}


def simulated_yiop_target_function_2(x, assets_and_pools, simulator=None, seed=None):
    """
    _2 => to test with input simulator instead of generate my own
    """
    pools = assets_and_pools['pools']
    allocation = {k: v for k, v in zip(pools.keys(), x)}
    sim_allocation = {k: 0 for k, v in zip(pools.keys(), x)}
    if simulator is None:
        simulator = Simulator(seed=seed)
        simulator.initialize()
        simulator.reset()
        simulator.init_data(copy.deepcopy(assets_and_pools), sim_allocation)
        simulator.update_reserves_with_allocs()
        simulator.run()
        return -calculate_aggregate_apy(allocation, assets_and_pools, simulator.timesteps, simulator.pool_history)
    else:
        return -calculate_aggregate_apy(allocation, assets_and_pools, simulator.timesteps, simulator.pool_history)


def simulated_yiop_allocation_algorithm_2(synapse: AllocateAssets, simulator=None) -> Dict:
    """
    _2 => to test with input simulator instead of generate my own
    """
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
    res = minimize(simulated_yiop_target_function_2, x0, args=(synapse.assets_and_pools, simulator), method='SLSQP', constraints=cons, bounds=bnds)

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    return {k: v for k, v in zip(pools.keys(), allocation)}

