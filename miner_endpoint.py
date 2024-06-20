import argparse
import json
from typing import List
from pydantic import BaseModel

import uvicorn
from fastapi import FastAPI, Request
import time
from datetime import datetime

from sturdy.plarism_cheater import PlarsimCheater
from sturdy.protocol import AllocateAssets
from sturdy.utils.sim_yiop import simulated_yiop_allocation_algorithm
from sturdy.utils.yiop import yiop_allocation_algorithm
import aioredis
import asyncio

import redis
# r = redis.Redis(host='redis.wecom.ai', port=6379, db=0)

plarsim_cheater = PlarsimCheater('sturdy/sphere_points.npy')


class MinerEndpoint:
    def __init__(self):
        self.app = FastAPI()
        self.redis = aioredis.from_url("redis://redis.wecom.ai:6379")
        self.app.add_api_route("/AllocateAssets", self.generate, methods=["POST"])

    async def generate(self, synapse: AllocateAssets, request: Request):
        try:
            start_time = datetime.now()
            allocations = simulated_yiop_allocation_algorithm(synapse)
            synapse.allocations = allocations
            start_time1 = datetime.now()
            allocations_list = plarsim_cheater.generate(allocations)
            end_time1 = datetime.now()
            print(f"processed SearchSynapse11 in {(end_time1 - start_time1).total_seconds()} seconds")
            cache_key = request.headers.get("x-cache-key")

            start_time2 = datetime.now()
            await self.save_redis(allocations_list, cache_key)
            end_time2 = datetime.now()
            print(f"processed SearchSynapse22 in {(end_time2 - start_time2).total_seconds()} seconds")
            end_time = datetime.now()
            print(f"processed SearchSynapse in {(end_time - start_time).total_seconds()} seconds")
            return synapse
        except Exception as e:
            #bt.logging.error("An error occurred while generating proven output",e)
            return synapse

    # async def save_redis(self, allocations_list, raw_key):
    #     # for index, allocations in enumerate(allocations_list, start=1):
    #     #     key = f"{raw_key}-{index}"
    #     #     r.set(key, json.dumps(allocations))
    #     tasks = []
    #     for index, allocations in enumerate(allocations_list, start=1):
    #         start_time2 = datetime.now()
    #         key = f"{raw_key}-{index}"
    #         task = self.redis.set(key, json.dumps(allocations), ex=30)
    #         tasks.append(task)
    #         end_time2 = datetime.now()
    #         print(f"processed SearchSynapse6666 in {(end_time2 - start_time2).total_seconds()} seconds")
    #     await asyncio.gather(*tasks)

    async def save_redis(self, allocations_list, raw_key):
        tasks = []
        for index, allocations in enumerate(allocations_list, start=1):
            start_time2 = datetime.now()
            key = f"{raw_key}-{index}"
            task = self.redis.set(key, json.dumps(allocations), ex=30)
            tasks.append(task)
            end_time2 = datetime.now()
            print(f"processed SearchSynapse6666 in {(end_time2 - start_time2).total_seconds()} seconds")
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
