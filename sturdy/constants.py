NUM_POOLS = 10  # number of pools to generate per query per epoch - for scoring miners
MIN_BASE_RATE = 0.01
MAX_BASE_RATE = 0.05  # keep the base rate the same for every pool for now - 0
BASE_RATE_STEP = 0.01
MIN_SLOPE = 0.01
MAX_SLOPE = 0.1
MIN_KINK_SLOPE = 0.15
MAX_KINK_SLOPE = 1
SLOPE_STEP = 0.001
MIN_OPTIMAL_RATE = 0.65
MAX_OPTIMAL_RATE = 0.95
OPTIMAL_UTIL_STEP = 0.05
MIN_UTIL_RATE = 0.55
MAX_UTIL_RATE = 0.95
UTIL_RATE_STEP = 0.05
MIN_TOTAL_ASSETS = 0.5
MAX_TOTAL_ASSETS = 3.5
TOTAL_ASSETS_STEP = 0.1
CHUNK_RATIO = 0.01  # chunk size as a percentage of total assets allocated during each iteration of greedy allocation algorithm
GREEDY_SIG_FIGS = 8  # significant figures to round to for greedy algorithm allocations

REVERSION_SPEED = 0.1  # reversion speed to median borrow rate of pools
MIN_TIMESTEPS = 50
MAX_TIMESTEPS = 200
TIMESTEPS_STEP = 5
# some randomness to sprinkle into the simulation
MIN_STOCHASTICITY = 0.02  # min stochasticity
MAX_STOCHASTICITY = 0.05  # max stochasticity
STOCHASTICITY_STEP = 0.005
POOL_RESERVE_SIZE = 1.0

QUERY_RATE = 2  # how often synthetic validator queries miners (blocks)
QUERY_TIMEOUT = 10  # timeout (seconds)
SIMILARITY_THRESHOLD = 0.1  # similarity threshold for plagiarism checking
