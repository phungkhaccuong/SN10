from typing import Dict
from unittest import result
import numpy as np
import sturdy
from sturdy.utils.yiop import yiop_allocation_algorithm

def negative_avoidance(X):
    X = np.array(X)
    Y = np.zeros_like(X)

    # Identify indices with negative and non-negative values in X
    negative_indices = np.where(X < 0)[0]
    positive_indices = np.where(X >= 0)[0]

    # Calculate the total negative sum
    total_negative_sum = -np.sum(X[negative_indices])

    # Calculate the proportionate redistribution of the negative sum
    positive_sum = np.sum(X[positive_indices])
    if positive_sum > 0:
        redistribution_factors = X[positive_indices] / positive_sum
        redistributed_values = total_negative_sum * redistribution_factors

        # Set Y values to offset negative values in X
        Y[negative_indices] = -X[negative_indices]
        Y[positive_indices] = -redistributed_values
    else:
        # If there are no positive values, we cannot redistribute; return an error
        raise ValueError("All values in X are negative or zero, cannot make X + Y non-negative.")

    return Y


class PlarsimCheater():

    def __init__(self, sphere_filename, index):
        self._sphere_points = np.load(sphere_filename)
        self._index = index

    def plarism_allocation(self, synapse: sturdy.protocol.AllocateAssets) -> Dict:
        allocation = yiop_allocation_algorithm(synapse)
        X = np.array(list(allocation.values()))
        # adjust_vec = self._sphere_points[self._index]
        adjust_vec = self._sphere_points[np.random.randint(0, len(self._sphere_points))]
        result_vec = X + adjust_vec
        if np.any(result_vec < 0):
            # adjust the result to avoid having negative allocation
            y = negative_avoidance(result_vec)
            result_vec += y
        return {k: v for k, v in zip(allocation.keys(), result_vec)}
