# Introduction

There are a few miners running different algorithms.

To run the original miner, follow same instruction in [[README.md]]
```
python neurons/miner.py --network finney ...
```

To run the best miner in backtest:

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