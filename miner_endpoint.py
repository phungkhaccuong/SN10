import argparse
from typing import List
from pydantic import BaseModel

import bittensor as bt
import uvicorn
from fastapi import FastAPI
import time
from datetime import datetime

from sturdy.plarism_cheater import PlarsimCheater
from sturdy.protocol import AllocateAssets
from sturdy.utils.sim_yiop import simulated_yiop_allocation_algorithm
from sturdy.utils.yiop import yiop_allocation_algorithm
import redis
r = redis.Redis(host='redis.wecom.ai', port=6379, db=0)


class MinerEndpoint:
    def __init__(self):
        self.app = FastAPI()
        self.app.add_api_route("/AllocateAssets", self.generate, methods=["POST"])

    async def generate(self, synapse: AllocateAssets):
        try:
            start_time = datetime.now()
            allocations = simulated_yiop_allocation_algorithm(synapse)
            synapse.allocations = allocations
            bt.logging.info(f"synapse::{synapse.__str__()}")
            allocations_list = PlarsimCheater.generate(allocations)
            self.save_redis(allocations_list, synapse.redis_key)
            end_time = datetime.now()
            elapsed_time = (end_time - start_time).total_seconds()
            bt.logging.info(f"processed SearchSynapse in {elapsed_time} seconds")
            return synapse
        except Exception as e:
            bt.logging.error("An error occurred while generating proven output",e)
            return synapse

    def save_redis(self, allocations_list, raw_key):
        for index, allocations in enumerate(allocations_list, start=1):
            key = f"{raw_key}-{index}"
            r.set(key, allocations)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args()

    app = MinerEndpoint()
    uvicorn.run(
        app.app,
        host="0.0.0.0",
        port=args.port,
    )
