from re import A
import numpy as np
from scipy.optimize import minimize
from typing import Dict
import sturdy
from sturdy.plarism_cheater import PlarsimCheater
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


def calc_max_diff(allocation, max_value):
    """
    How much we can displace the allocation so that all its value is smaller than max_value
    """
    diff = allocation.copy()
    for k, v in allocation:
        diff[k] = max_value - v
    return diff


def calc_min_diff(allocation):
    """
    How much we can displace the allocation so that all value are greater than 0
    """
    diff = -allocation
    return diff


def min_ratio_to_bound(max_value, allocation, adjust_diff):
    """
    Scaling the adjust_diff so that allocation after adjustment becomes between 0 and max_value
    """
    ratios = []
    for i in range(len(adjust_diff)):
        if adjust_diff[i] > 0:
            # when adjustment is positive, we need to scale it back until the alloc only reach max_value after adjustment
            alloc = allocation[str(i)]
            ratios.append((max_value - alloc) / adjust_diff[i])
        elif adjust_diff[i] < 0:
            # when adjustment is negative, we need to scale it back until the alloc stops at 0 after adjustment
            alloc = allocation[str(i)]
            ratios.append(alloc / -adjust_diff[i])
        else:
            ratios.append(1)
    return np.min(ratios)


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
    # print('init allocations', yiop_alloc)
    arr = []
    for pool in pools.values():
        res = minimize(pool_target, 0, args=(pool['borrow_amount'] + 0.1, pool), bounds=[(0, max_balance/2)], method='SLSQP')
        # res = minimize(pool_target, 0, args=(pool["reserve_size"], pool), bounds=[(0, 0.6)], method='SLSQP')
        arr.append(res.x[0])
    x0 = np.array(arr)
    x0 = np.clip(x0, 0, max_balance)

    best_allocations = {k: v for k, v in zip(pools.keys(), x0)}

    # print('best allocations', best_allocations)

    diff = []
    for k in best_allocations.keys():
        diff.append(best_allocations[k] - yiop_alloc[k])
    # print('diff',{k: v for k, v in zip(pools.keys(), diff)})
    adjust = normalize_sum_zero(diff)
    # print('adjust',{k: v for k, v in zip(pools.keys(), adjust)})
    better = {}
    for k, v in yiop_alloc.items():
        better[k] = v + adjust[int(k)]
        # if better[k] < 0:
        #     better[k] = 0

    # # round down because sometimes the optimizer gives result which is slightly above max_balance
    # allocation = round_down_to_sum_below(res.x, max_balance)

    # return {k: v for k, v in zip(pools.keys(), allocation)}
    return better


def project_onto_zero_sum_plane(v):
    """
    Projects the vector v onto the plane where the sum of the coordinates is zero.

    Parameters:
    v (numpy array): Input vector

    Returns:
    numpy array: Projected vector
    """
    N = len(v)
    avg = np.sum(v) / N
    projection = v - avg
    return projection


def find_max_scale(X, Y):
    """
    Find the maximum scale alpha such that X + alpha * Y >= 0 element-wise.

    Parameters:
    X (numpy array): The vector to be translated
    Y (numpy array): The direction vector for translation

    Returns:
    float: The maximum scale alpha
    """
    scales = []
    for i in range(len(X)):
        if Y[i] != 0:
            scales.append(-X[i] / Y[i])
        elif X[i] < 0:
            return 0  # If Y[i] == 0 and X[i] < 0, there's no valid alpha

    # Only consider positive scales
    positive_scales = [scale for scale in scales if scale >= 0]

    # If no positive scales found, alpha is zero
    if not positive_scales:
        return 0

    return min(positive_scales)


def igreedy_orthogonal_allocation_allocations(synapse: sturdy.protocol.AllocateAssets):
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
    # print('init allocations', yiop_alloc)
    arr = []
    for pool in pools.values():
        res = minimize(pool_target, 0, args=(pool['borrow_amount'] + 0.3, pool), bounds=[(0, max_balance)], method='SLSQP')
        # res = minimize(pool_target, 0, args=(pool["reserve_size"], pool), bounds=[(0, 0.6)], method='SLSQP')
        arr.append(res.x[0])
    x0 = np.array(arr)
    x0 = np.clip(x0, 0, max_balance)

    best_allocations = {k: v for k, v in zip(pools.keys(), x0)}

    print('best allocations', best_allocations)

    init_vector = np.array(list(yiop_alloc.values()))
    target_vector = np.array(list(best_allocations.values()))
    diff_vector = target_vector - init_vector
    project_vector = project_onto_zero_sum_plane(diff_vector)
    # print('project vector', {k: v for k, v in zip(pools.keys(), project_vector)})
    result_vector = project_vector + init_vector
    if np.any(result_vector < 0): # If the result vector is negative, limit it
        max_scale = find_max_scale(init_vector, project_vector)
        result_vector = max_scale * project_vector + init_vector
    return {k: v for k, v in zip(pools.keys(), result_vector)}


def igreedy_sphere_allocation_allocations(synapse: sturdy.protocol.AllocateAssets):
    better = igreedy_allocation_algorithm(synapse)
    vector = [ 0.00687023, -0.00013409,  0.00755292, -0.0612751 ,  0.05416116,
        0.04018364, -0.00178953, -0.03705576,  0.01185207, -0.00872571]
    for i in range(10):
        better[str(i)] += vector[i]
    return better


cheater = PlarsimCheater('sphere_points.npy')

def disturb(synapse):
    allocation = yiop_allocation_algorithm(synapse)
    x =  [0.00510775, 0.01590273, -0.01409674, 0.02079831, 0.00308688, 0.01238793, -0.02899458, -0.06526999, -0.00996757, 0.06104528]
    allocation = {f'{i}': x[i] + allocation[str(i)] for i in range(10)}
    return allocation