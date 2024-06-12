import argparse
from typing import List
from pydantic import BaseModel

import bittensor as bt
import uvicorn
from fastapi import FastAPI

from sturdy.protocol import AllocateAssets
from sturdy.utils.sim_yiop import simulated_yiop_allocation_algorithm
from sturdy.utils.yiop import yiop_allocation_algorithm


class MinerEndpoint:
    def __init__(self):
        self.app = FastAPI()
        self.app.add_api_route("/AllocateAssets", self.generate,
                               methods=["POST"])

    async def generate(self, synapse: AllocateAssets):
        try:
            synapse.allocations = simulated_yiop_allocation_algorithm(synapse)
            return synapse
        except Exception as e:
            bt.logging.error("An error occurred while generating proven output",
                             e)
            return synapse


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
