import numpy as np


import numpy as np

def adjust_vector(X):
    # Prevent negative
    X = np.array(X)
    negative_indices = X < 0
    total_negative_sum = X[negative_indices].sum()

    # Initialize Y with zeros
    Y = np.zeros_like(X)

    # Calculate the total sum of non-negative elements in X
    non_negative_indices = X >= 0
    total_non_negative_sum = X[non_negative_indices].sum()

    # Distribute the negative sum proportionally across non-negative elements
    Y[non_negative_indices] = -total_negative_sum * (X[non_negative_indices] / total_non_negative_sum)

    # Adjust negative values to zero
    Y[negative_indices] = -X[negative_indices]

    return Y

# Example usage:
X = [3, -2, 5, -1, 4]
Y = adjust_vector(X)
print("Original X:", X)
print("Adjustment Y:", Y)
print("Adjusted X + Y:", np.array(X) + Y)


def generate_points_with_min_distance(N, dim=3, min_distance=0.1, radius_step=1e-5, epsilon=1e-10):
    """
    Generate N points in dim dimensions such that each new point is at least min_distance away from all others.
    """
    points = []
    for i in range(1, 50):
        radius = radius_step * i
        print(f'search in radius: {radius}')
        iteration = 1000_000
        while len(points) < N and iteration > 0:
            new_point = np.random.randn(dim)
            new_point -= np.mean(new_point) + epsilon
            new_point = new_point / np.linalg.norm(new_point) * (min_distance + epsilon)
            # Check if new_point has at least min_distance distance from all existing points
            if all(np.linalg.norm(new_point - existing_point) >= min_distance and np.linalg.norm(new_point - existing_point) <= min_distance + radius for existing_point in points):
                points.append(new_point)
                vec_str = [str(x) for x in new_point]
                vec_str = ', '.join(vec_str)
                print(f'Total: {len(points)}. New point added: {vec_str}')
            iteration -= 1

    return np.array(points)

def main():
    # Parameters
    N = 256  # Number of points to generate
    dim = 10 # Dimension of each point
    min_distance = 0.1  # Minimum distance between points

    # Generate points with minimum distance constraint
    points = generate_points_with_min_distance(N, dim=dim, min_distance=min_distance, epsilon=1e-10, radius_step=1e-2)

    # Print the generated points
    print(f"Generated points with at least 0.1 distance from each other: {len(points)}")

    # Verify sum and L2 norm of each vector
    sums = np.sum(points, axis=1)
    norms = np.linalg.norm(points, axis=1)
    print("Sum of elements of each vector:")
    print(sums)
    print("L2 norm of each vector:")
    print(norms)

    # Check distances between all pairs of points
    distances = np.linalg.norm(points[:, np.newaxis] - points[np.newaxis, :], axis=-1)
    count_smaller_than_one = np.sum((distances < min_distance) & (distances > 0))
    print(f"Number of distances smaller than {min_distance}: {count_smaller_than_one}")

    np.save('points.npy', points)

if __name__ == "__main__":
    main()