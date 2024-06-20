# Introduction

There are a few miners running different algorithms.

To run the original miner, follow same instruction in [[README.md]]
```
python neurons/miner.py --network finney ...
```

To run the best miner in backtest:
```
python neurons/sim_miner.py --network finney ...
```

Old miner:
```
python neurons/yiop_miner.py --network finney ...
```
or better than best
```
python neurons/precise_yiop_miner.py --network finney ...
```

To run the second best (backup miner) in backtest:
```
python neurons/equal_miner.py --network finney ...
```

# Installation

```
pip install -e .
```

# Running Go Server

```
export CGO_CFLAGS="-I$(python3-config --includes)"
export CGO_LDFLAGS="-L$(python3-config --ldflags)"
```

For MacOS: `arch -arm64 brew install pkg-config`

# Run miner endpoint
```
pm2 start miner_endpoint.py --name miner_endpoint --interpreter python3 -- \
--port 8888
```


# Plarism cheater

To avoid plarism cheater, we disturb the original result a bit. To choose a range of points that are wider or a narrower:
1. Use PlarismCheater to generate list of points
    1. Input: `sphere_points.npy` => best apy, worst penalties
    2. Input: `sphere_points_v1.npy` => mid apy, mid penalties
    3. Input: `sphere_points_v2.npy` => worst apy, almost no penalties