from ctypes import util
import sys
import copy
from decimal import Decimal

from numpy import sort
from sturdy.pools import generate_assets_and_pools
from sturdy.protocol import AllocateAssets
from sturdy.utils.misc import greedy_allocation_algorithm
from sturdy.utils.lazy import pick_one_allocation_algorithm, sorted_greedy_allocation_algorithm, equal_greedy_allocation_algorithm
from sturdy.validator.reward import calculate_aggregate_apy
from sturdy.validator.simulator import Simulator
from sturdy.utils.misc import supply_rate


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