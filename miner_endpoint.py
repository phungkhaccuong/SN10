import argparse
import asyncio
import json
from datetime import datetime

import aioredis
import bittensor as bt
import uvicorn
from fastapi import FastAPI, Request

from sturdy.plarism_cheater import PlarsimCheater
from sturdy.protocol import AllocateAssets
from sturdy.utils.sim_yiop import simulated_yiop_allocation_algorithm
from sturdy.utils.yiop import yiop_allocation_algorithm

plarsim_cheater = PlarsimCheater('sturdy/sphere_points.npy')


class MinerEndpoint:
    def __init__(self):
        self.app = FastAPI()
        self.redis = aioredis.from_url("redis://redis.wecom.ai:6379")
        self.app.add_api_route("/AllocateAssets", self.generate, methods=["POST"])

    async def generate(self, synapse: AllocateAssets, request: Request):
        try:
            start_time = datetime.now()
            allocations = yiop_allocation_algorithm(synapse)
            synapse.allocations = allocations
            allocations_list = plarsim_cheater.generate(allocations)
            cache_key = request.headers.get("x-cache-key")

            await self.save_redis(allocations_list, cache_key)
            end_time = datetime.now()
            print(f"processed SearchSynapse in {(end_time - start_time).total_seconds()} seconds")
            return synapse
        except Exception as e:
            bt.logging.error("An error occurred while generating proven output",e)
            return synapse

    async def save_redis(self, allocations_list, raw_key):
        tasks = []
        for index, allocations in enumerate(allocations_list, start=1):
            key = f"{raw_key}-{index}"
            task = self.redis.set(key, json.dumps(allocations), ex=30)
            tasks.append(task)
        await asyncio.gather(*tasks)


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
