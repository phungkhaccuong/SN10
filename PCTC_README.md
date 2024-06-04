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