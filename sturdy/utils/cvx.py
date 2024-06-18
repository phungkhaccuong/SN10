import cvxopt
from cvxopt import matrix, solvers
from sturdy.utils.misc import supply_rate

# def target_function(x, pools):
#     pool_items = [pool for idx, pool in pools.items()]
#     total_yield = 0
#     for idx, pool in enumerate(pool_items):
#         alloc = x[idx]
#         util_rate = pool["borrow_amount"] / (pool["reserve_size"] + alloc)
#         pool_yield = alloc * supply_rate(util_rate, pool)
#         total_yield += pool_yield
#     return -total_yield


def target_function_cvxopt(pools):
    # Extract necessary pool information
    pool_items = [pool for idx, pool in pools.items()]
    num_pools = len(pool_items)

    # Define the P matrix for quadratic terms (since we have a linear objective, P is a zero matrix)
    P = matrix(0.0, (num_pools, num_pools))

    # Define the q vector for linear terms (we need to maximize total yield, hence minimizing -total_yield)
    q = matrix(0.0, (num_pools, 1))

    for idx, pool in enumerate(pool_items):
        util_rate = pool["borrow_amount"] / pool["reserve_size"]
        q[idx] = -supply_rate(util_rate, pool)  # Negative because cvxopt minimizes

    # Define the constraints Gx <= h (G is identity matrix and h is zero vector if we have no other constraints)
    G = matrix(0.0, (num_pools, num_pools))
    h = matrix(0.0, (num_pools, 1))

    for i in range(num_pools):
        G[i, i] = -1.0  # Ensuring allocations are non-negative

    # Define any additional constraints on allocation sums if needed
    # For example, if you want the sum of allocations to be less than or equal to a total available amount

    # Example total allocation constraint:
    A = matrix(1.0, (1, num_pools))
    b = matrix(total_allocation)  # total_allocation should be defined as the sum of available allocations

    # Solve the quadratic programming problem
    sol = solvers.qp(P, q, G, h, A, b)

    return sol['x']