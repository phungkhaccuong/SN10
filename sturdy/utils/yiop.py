import copy
from decimal import Decimal
from typing import Dict, List
from scipy.optimize import minimize
from scipy.optimize import basinhopping
import numpy as np
from sturdy.utils.misc import supply_rate
import sturdy
from sturdy.validator.reward import calculate_aggregate_apy
from sturdy.validator.simulator import Simulator

import bittensor as bt

from redis import StrictRedis
from redis_cache import RedisCache

def target_function(x, pools):
    pool_items = [pool for idx, pool in pools.items()]
    total_yield = 0
    for idx, pool in enumerate(pool_items):
        alloc = x[idx]
        util_rate = pool["borrow_amount"] / (pool["reserve_size"] + alloc)
        pool_yield = alloc * supply_rate(util_rate, pool)
        total_yield += pool_yield
    return -total_yield


def round_down_to_4_digits(arr: List[float]) -> np.array:
    return np.array([Decimal(str(x)).quantize(Decimal('0.0000'), rounding='ROUND_DOWN') for x in arr])


def round_down_to_sum_below(arr: List[float], max_value, epsilon=Decimal('0.000001')):
    # using Decimal to prevent cheater punishment
    max_value = Decimal(max_value)
    # Convert the input array to a list of Decimals
    arr = round_down_to_4_digits(arr)

    # Continue decrementing elements until the sum is below 1
    while sum(arr) >= max_value:
        # Decrement each element by epsilon
        arr -= epsilon
        # Ensure no element becomes negative
        arr = np.maximum(arr, Decimal('0'))

    return [float(i) for i in arr]


def yiop3_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations


    # Define the bounds for the variables
    bnds = [(0, 1) for _ in pools.items()]  # Assuming x[0] and x[1] are bounded between 0 and 1

    # Define the equality constraint (sum of elements equals 1)
    cons = {'type': 'eq', 'fun': lambda x: np.sum(x) - max_balance}

    x0 = np.array([0 for _ in pools.items()])

    # Perform the optimization using the SLSQP method which supports constraints
    res = minimize(target_function, x0, args=(pools), method='COBYLA', constraints=cons, bounds=bnds)

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    return {k: v for k, v in zip(pools.keys(), allocation)}


def yiop2_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations


    # Define the bounds for the variables
    bnds = [(0, 1) for _ in pools.items()]  # Assuming x[0] and x[1] are bounded between 0 and 1

    # Define the equality constraint (sum of elements equals 1)
    cons = {'type': 'eq', 'fun': lambda x: np.sum(x) - max_balance}

    x0 = np.array([0 for _ in pools.items()])

    # Perform the optimization using the SLSQP method which supports constraints
    res = minimize(target_function, x0, args=(pools), method='dogleg', constraints=cons, bounds=bnds)

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    return {k: v for k, v in zip(pools.keys(), allocation)}


def fine_yiop_target_function(x, assets_and_pools, timesteps, pool_history):
    pools = assets_and_pools['pools']
    allocation = {k: v for k, v in zip(pools.keys(), x)}
    return calculate_aggregate_apy(allocation, assets_and_pools, timesteps, pool_history)


def simulated_yiop_target_function(x, assets_and_pools):
    pools = assets_and_pools['pools']
    allocation = {k: v for k, v in zip(pools.keys(), x)}
    simulator = Simulator()
    simulator.initialize()
    simulator.reset()
    simulator.init_data(copy.deepcopy(assets_and_pools), allocation)
    simulator.update_reserves_with_allocs()
    simulator.run()

    return calculate_aggregate_apy(allocation, assets_and_pools, simulator.timesteps, simulator.pool_history)


def fine_yiop_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations


    # Define the bounds for the variables
    bnds = [(0, 1) for _ in pools.items()]  # Assuming x[0] and x[1] are bounded between 0 and 1

    # Define the equality constraint (sum of elements equals 1)
    cons = {'type': 'eq', 'fun': lambda x: np.sum(x) - max_balance}

    x0 = np.array([0 for _ in pools.items()])

    # Perform the optimization using the SLSQP method which supports constraints
    res = minimize(target_function, x0, args=(pools), method='SLSQP', constraints=cons, bounds=bnds)

    # first round
    init_allocation = {k: v for k, v in zip(pools.keys(), res.x)}

    # second round - testing with Simulator
    simulator = Simulator()
    simulator.initialize()
    simulator.reset()
    simulator.init_data(copy.deepcopy(synapse.assets_and_pools), init_allocation)
    simulator.update_reserves_with_allocs()
    simulator.run()

    x0 = res.x
    res = minimize(fine_yiop_target_function, x0, args=(synapse.assets_and_pools, simulator.timesteps, simulator.pool_history), method='SLSQP', constraints=cons, bounds=bnds)

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    return {k: v for k, v in zip(pools.keys(), allocation)}


def simulated_yiop_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations


    # Define the bounds for the variables
    bnds = [(0, 1) for _ in pools.items()]  # Assuming x[0] and x[1] are bounded between 0 and 1

    # Define the equality constraint (sum of elements equals 1)
    cons = {'type': 'eq', 'fun': lambda x: np.sum(x) - max_balance}

    x0 = np.array([0 for _ in pools.items()])

    # Perform the optimization using the SLSQP method which supports constraints
    res = minimize(simulated_yiop_target_function, x0, args=(synapse.assets_and_pools), method='SLSQP', constraints=cons, bounds=bnds)

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    return {k: v for k, v in zip(pools.keys(), allocation)}


def precise_yiop_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations


    # Define the bounds for the variables
    bnds = [(0, max_balance) for _ in pools.items()]  # Assuming x[0] and x[1] are bounded between 0 and max_balance

    # Define the equality constraint (sum of elements equals max_balance)
    cons = {'type': 'eq', 'fun': lambda x: np.sum(x) - max_balance}

    x0 = np.array([0 for _ in pools.items()])

    # Perform the optimization using the SLSQP method which supports constraints
    res = minimize(target_function, x0, args=(pools), method='SLSQP', constraints=cons, bounds=bnds, options={'flol': 1e-10})

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    return {k: v for k, v in zip(pools.keys(), allocation)}


def yiop_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    if 'reserve_size' not in pools['0']:
        # For out of date validator
        allocations = {k: v["borrow_amount"] for k, v in pools.items()}
        return allocations


    # Define the bounds for the variables
    bnds = [(0, max_balance) for _ in pools.items()]  # Assuming x[0] and x[1] are bounded between 0 and max_balance

    # Define the equality constraint (sum of elements equals max_balance)
    cons = {'type': 'eq', 'fun': lambda x: np.sum(x) - max_balance}

    x0 = np.array([0 for _ in pools.items()])

    # Perform the optimization using the SLSQP method which supports constraints
    res = minimize(target_function, x0, args=(pools), method='SLSQP', constraints=cons, bounds=bnds)

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    return {k: v for k, v in zip(pools.keys(), allocation)}


def gloyiop_allocation_algorithm(synapse: sturdy.protocol.AllocateAssets) -> Dict:
    max_balance = synapse.assets_and_pools["total_assets"]
    pools = synapse.assets_and_pools["pools"]

    # Define the bounds for the variables
    bounds = [(0, 1) for _ in pools.items()]  # Assuming x[0] and x[1] are bounded between 0 and 1

    # Define the equality constraint (sum of elements equals 1)
    constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - max_balance}

    x0 = np.array([0 for _ in pools.items()])

    minimizer_kwargs = {"method": "SLSQP", "bounds": bounds, "constraints": constraints, "args": (pools)}
    # Perform the optimization using the SLSQP method via Basinhopping
    res = basinhopping(target_function, x0, minimizer_kwargs=minimizer_kwargs)

    # round down because sometimes the optimizer gives result which is slightly above max_balance
    allocation = round_down_to_sum_below(res.x, max_balance)

    return {k: v for k, v in zip(pools.keys(), allocation)}


if __name__ == "__main__":
    """
    This main function tests the allocation manually with a input pools
    """
    # 2 pools
    # pools ={'0': {'pool_id': '0', 'base_rate': 0.02, 'base_slope': 0.067, 'kink_slope': 0.19, 'optimal_util_rate': 0.85, 'borrow_amount': 0.65, 'reserve_size': 1.0}, '1': {'pool_id': '1', 'base_rate': 0.01, 'base_slope': 0.037, 'kink_slope': 0.956, 'optimal_util_rate': 0.75, 'borrow_amount': 0.55, 'reserve_size': 1.0}}

    # full pools
    pools = {'0': {'pool_id': '0', 'base_rate': 0.03, 'base_slope': 0.087, 'kink_slope': 0.687, 'optimal_util_rate': 0.65, 'borrow_amount': 0.8, 'reserve_size': 1.0}, '1': {'pool_id': '1', 'base_rate': 0.04, 'base_slope': 0.059, 'kink_slope': 0.595, 'optimal_util_rate': 0.65, 'borrow_amount': 0.6, 'reserve_size': 1.0}, '2': {'pool_id': '2', 'base_rate': 0.01, 'base_slope': 0.073, 'kink_slope': 0.53, 'optimal_util_rate': 0.7, 'borrow_amount': 0.85, 'reserve_size': 1.0}, '3': {'pool_id': '3', 'base_rate': 0.01, 'base_slope': 0.011, 'kink_slope': 0.699, 'optimal_util_rate': 0.7, 'borrow_amount': 0.9, 'reserve_size': 1.0}, '4': {'pool_id': '4', 'base_rate': 0.05, 'base_slope': 0.028, 'kink_slope': 0.404, 'optimal_util_rate': 0.7, 'borrow_amount': 0.8, 'reserve_size': 1.0}, '5': {'pool_id': '5', 'base_rate': 0.03, 'base_slope': 0.026, 'kink_slope': 0.539, 'optimal_util_rate': 0.65, 'borrow_amount': 0.6, 'reserve_size': 1.0}, '6': {'pool_id': '6', 'base_rate': 0.05, 'base_slope': 0.059, 'kink_slope': 0.95, 'optimal_util_rate': 0.7, 'borrow_amount': 0.6, 'reserve_size': 1.0}, '7': {'pool_id': '7', 'base_rate': 0.01, 'base_slope': 0.042, 'kink_slope': 0.492, 'optimal_util_rate': 0.7, 'borrow_amount': 0.55, 'reserve_size': 1.0}, '8': {'pool_id': '8', 'base_rate': 0.02, 'base_slope': 0.077, 'kink_slope': 0.466, 'optimal_util_rate': 0.7, 'borrow_amount': 0.65, 'reserve_size': 1.0}, '9': {'pool_id': '9', 'base_rate': 0.05, 'base_slope': 0.094, 'kink_slope': 0.769, 'optimal_util_rate': 0.85, 'borrow_amount': 0.8, 'reserve_size': 1.0}}

    # Define the bounds for the variables
    bnds = [(0, 1) for _ in pools.items()]  # Assuming x[0] and x[1] are bounded between 0 and 1
    # Define the equality constraint (sum of elements equals 1)
    cons = {'type': 'eq', 'fun': lambda x: np.sum(x) - 0.999999999}

    x0 = np.array([0 for _ in pools.items()])

    # Perform the optimization using the SLSQP method which supports constraints
    res = minimize(target_function, x0, args=(pools), method='SLSQP', constraints=cons, bounds=bnds)

    # Print the results
    print('Maximum array', np.array2string(res.x, separator=', '))
    print("Maximum point:", res.x)
    print("Maximum value:", -res.fun)  # Since we minimized the negative function

    print("Target: ", target_function(res.x, pools))
    # print("Manual best", target_function([0.87, 0.13], pools))

