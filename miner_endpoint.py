import argparse
import asyncio
import json
from datetime import datetime

import aioredis
import bittensor as bt
import uvicorn
from bittensor import TerminalInfo
from fastapi import FastAPI, Request

from sturdy.plarism_cheater import PlarsimCheater
from sturdy.protocol import AllocateAssets
from sturdy.utils.sim_yiop import simulated_yiop_allocation_algorithm
from sturdy.utils.yiop import yiop_allocation_algorithm

plarsim_cheater = PlarsimCheater('sturdy/sphere_points_v2.npy')


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

            await self.save_redis(synapse, allocations_list, cache_key)
            end_time = datetime.now()
            print(f"processed SearchSynapse in {(end_time - start_time).total_seconds()} seconds")
            return synapse
        except Exception as e:
            bt.logging.error("An error occurred while generating proven output", e)
            return synapse

    async def save_redis(self, synapse, allocations_list, raw_key):
        try:
            tasks = []
            print(f"data:{synapse.__dict__}")
            for index, allocations in enumerate(allocations_list, start=1):
                key = f"{raw_key}-{index}"
                synapse.allocations = allocations
                dict = synapse.dict()
                del dict['axon']
                del dict['dendrite']

                task = self.redis.set(key, json.dumps(dict), ex=30)

                # print(f"DUMP:{json.dumps(self.to_dict(synapse))}")
                # task = self.redis.set(key, json.dumps(self.to_dict(synapse)), ex=30)
                tasks.append(task)
            await asyncio.gather(*tasks)
        except Exception as e:
            print("save_redis error")
            pass

    def to_dict(self, synapse):
        terminalInfo = TerminalInfo(status_code=None, status_message=None, process_time=None, ip=None, port=None,
                                    version=None, nonce=None, uuid=None, hotkey=None, signature=None)
        return {
            "assets_and_pools": synapse.assets_and_pools,
            "allocations": synapse.allocations,
            "name": synapse.name,
            "timeout": synapse.timeout,
            "total_size": synapse.total_size,
            "header_size": synapse.header_size,
            "dendrite": self.to_dict_terminal_info(terminalInfo),
            "axon": self.to_dict_terminal_info(terminalInfo),
            "computed_body_hash": synapse.computed_body_hash,
            "required_hash_fields": synapse.required_hash_fields
        }

    def to_dict_terminal_info(self, terminalInfo):
        return {
            "status_code": terminalInfo.status_code,
            "status_message": terminalInfo.status_message,
            "process_time": terminalInfo.process_time,
            "ip": terminalInfo.ip,
            "port": terminalInfo.port,
            "version": terminalInfo.version,
            "nonce": terminalInfo.nonce,
            "uuid": terminalInfo.uuid,
            "hotkey": terminalInfo.hotkey,
            "signature": terminalInfo.signature
        }


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
