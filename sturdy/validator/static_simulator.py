import numpy as np
from sturdy.utils.misc import borrow_rate
from sturdy.validator.simulator import Simulator


class StaticSimulator(Simulator):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # initialize pools
    # Function to update borrow amounts and other pool params based on reversion rate and stochasticity
    def generate_new_pool_data(self):
        latest_pool_data = self.pool_history[-1]
        curr_borrow_rates = np.array(
            [pool["borrow_rate"] for _, pool in latest_pool_data.items()]
        )
        curr_borrow_amounts = np.array(
            [pool["borrow_amount"] for _, pool in latest_pool_data.items()]
        )
        curr_reserve_sizes = np.array(
            [pool["reserve_size"] for _, pool in latest_pool_data.items()]
        )

        median_rate = np.median(curr_borrow_rates)  # Calculate the median borrow rate
        noise = [0] * len(curr_borrow_rates)  # disable noise for faster calculation
        rate_changes = (
            -self.reversion_speed * (curr_borrow_rates - median_rate) + noise
        )  # Mean reversion principle
        new_borrow_amounts = (
            curr_borrow_amounts + rate_changes * curr_borrow_amounts
        )  # Update the borrow amounts
        amounts = np.clip(
            new_borrow_amounts, 0, curr_reserve_sizes
        )  # Ensure borrow amounts do not exceed reserves
        pool_uids = list(latest_pool_data.keys())

        new_pool_data = {
            pool_uids[i]: {
                "noise": noise[i],
                "curr_borrow_rate": curr_borrow_rates[i],
                "rate_change": rate_changes[i],
                "borrow_amount": amounts[i],
                "reserve_size": curr_reserve_sizes[i],
                "borrow_rate": borrow_rate(
                    amounts[i] / curr_reserve_sizes[i],
                    self.assets_and_pools["pools"][pool_uids[i]],
                ),
            }
            for i in range(len(amounts))
        }

        return new_pool_data