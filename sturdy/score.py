from ctypes import util
import sys
import copy
from decimal import Decimal

from numpy import sort
from sturdy.pools import generate_assets_and_pools
from sturdy.protocol import AllocateAssets
from sturdy.utils.misc import greedy_allocation_algorithm
from sturdy.utils.lazy import pick_one_allocation_algorithm, sorted_greedy_allocation_algorithm, equal_greedy_allocation_algorithm
from sturdy.validator.reward import calc_list_agg_py, calculate_aggregate_apy
from sturdy.validator.simulator import Simulator
from sturdy.utils.misc import supply_rate


def get_list_agg_apy(assets_and_pools, allocations):
    simulator = Simulator()
    simulator.initialize()
    simulator.init_data(copy.deepcopy(assets_and_pools), allocations)
    simulator.reset()
    simulator.init_data(copy.deepcopy(assets_and_pools), allocations)
    simulator.update_reserves_with_allocs()
    simulator.run()
    return calc_list_agg_py(
        allocations,
        assets_and_pools,
        simulator.timesteps,
        simulator.pool_history,
    )



def get_agg_apy(assets_and_pools, allocations):
    simulator = Simulator()
    simulator.initialize()
    allocations = {
        k: 0 for k, v in allocations.items()
    }
    simulator.init_data(copy.deepcopy(assets_and_pools), allocations)
    simulator.reset()
    simulator.init_data(copy.deepcopy(assets_and_pools), allocations)
    simulator.update_reserves_with_allocs()
    simulator.run()
    return calculate_aggregate_apy(
        allocations,
        assets_and_pools,
        simulator.timesteps,
        simulator.pool_history,
    )


def run_simulation(assets_and_pools, allocations):
    simulator = Simulator()
    simulator.initialize()
    simulator.init_data(copy.deepcopy(assets_and_pools), allocations)
    simulator.reset()
    simulator.init_data(copy.deepcopy(assets_and_pools), allocations)
    simulator.update_reserves_with_allocs()
    simulator.run()
    return simulator


def calculate_apy(simulator: Simulator, assets_and_pools, allocations):
    # reset simulator for next run
    simulator.reset()

    if allocations is None:
        return sys.float_info.min

    simulator.init_data(copy.deepcopy(assets_and_pools), allocations)

    # update reserves given allocations
    # simulator.allocations = allocations
    simulator.update_reserves_with_allocs()
    # TODO: use this or just run reset()?
    updated_assets_pools = copy.deepcopy(simulator.assets_and_pools)

    initial_balance = updated_assets_pools["total_assets"]
    total_allocated = Decimal(0)
    cheating = False

    for _, allocation in allocations.items():
        total_allocated += Decimal(
            str(allocation)
        )  # This should fix precision issues with python floats

        # score response very low if miner is cheating somehow
        if total_allocated > initial_balance:
            cheating = True
            break

    # punish if miner they're cheating
    # TODO: create a more forgiving penalty system?
    if cheating:
        print(
            f"CHEATER DETECTED - PUNISHING 👊😠"
        )
        print(
            f"Allocations: {allocations} {np.sum(np.array(list(allocations.values())))}, total: {updated_assets_pools['total_assets']}"
        )
        return sys.float_info.min

    # run simulation
    simulator.run()
    # calculate aggregate yield
    pct_yield = 0
    for pools in simulator.pool_history:
        curr_yield = 0
        for uid, pool_data in pools.items():
            # print(f'uid: {uid}, pool_data: {pool_data}')
            util_rate = pool_data["borrow_amount"] / pool_data["reserve_size"]
            # util_rate = allocations[uid] / (pool_data['reserve_size'] + allocations[uid])
            pool_yield = allocations[uid] * supply_rate(
                util_rate, simulator.assets_and_pools["pools"][uid]
            )
            # print(f'uid {uid}, reserve: {pool_data["reserve_size"]} allocation: {allocations[uid]} util_rate: {util_rate} yield {pool_yield}')
            curr_yield += pool_yield
        pct_yield += curr_yield
        # print(f'curr_yield: {curr_yield} pct_yield: {pct_yield}')

    pct_yield /= initial_balance
    # print(f'pct_yield after balance: {pct_yield}, steps: {simulator.timesteps} apy: {pct_yield / simulator.timesteps * 365}')
    return(
        pct_yield / simulator.timesteps
    ) * 365  # for simplicity each timestep is a day in the simulator


def calc_strategy_apy(allocations, assets_and_pools, simulator=None, seed=None):
    simulator = Simulator(seed=seed)
    simulator.initialize()
    simulator.init_data(copy.deepcopy(assets_and_pools), allocations)

    return calculate_apy(simulator, assets_and_pools, allocations)

def strategies_apy(strategies):
    init_assets_and_pools = generate_assets_and_pools()

    result_apy = {}
    synapse = AllocateAssets(assets_and_pools=copy.deepcopy(init_assets_and_pools))
    for k, v in strategies.items():
        allocation = strategies[k](synapse=synapse)
        result_apy[k] = calc_strategy_apy(allocation, init_assets_and_pools)
    return result_apy