# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Syeam Bin Abdullah

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import time
import typing
import bittensor as bt

# Bittensor Miner Template:
from neurons.miner import Miner
import sturdy
from sturdy.utils.sim_yiop import simulated_yiop_allocation_algorithm


class SimMiner(Miner):
    """
    Your miner neuron class. You should use this class to define your miner's behavior. In particular, you should replace the
    forward function with your own logic. You may also want to override the blacklist and priority functions according to your
    needs.

    This class inherits from the BaseMinerNeuron class, which in turn inherits from BaseNeuron. The BaseNeuron class takes
    care of routine tasks such as setting up wallet, subtensor, metagraph, logging directory, parsing config, etc. You can
    override any of the methods in BaseNeuron if you need to customize the behavior.

    This class provides reasonable default behavior for a miner such as blacklisting unrecognized hotkeys, prioritizing
    requests based on stake, and forwarding requests to the forward function. If you need to define custom
    """

    def __init__(self, config=None):
        super(SimMiner, self).__init__(config=config)

    async def forward(
        self, synapse: sturdy.protocol.AllocateAssets
    ) -> sturdy.protocol.AllocateAssets:
        """
        Processes the incoming 'AllocateAssets' synapse by performing a predefined operation on the input data.
        This method should be replaced with actual logic relevant to the miner's purpose.

        Args:
            synapse (template.protocol.AllocateAssets): The synapse object containing the 'dummy_input' data.

        Returns:
            template.protocol.AllocateAssets: The synapse object with the 'dummy_output' field set to twice the 'dummy_input'
            value.

        The 'forward' function is a placeholder and should be overridden with logic that is appropriate for
        the miner's intended operation. This method demonstrates a basic transformation of input data.
        """
        start_time = time.perf_counter()

        bt.logging.debug("forward()")

        # use default greedy alloaction algorithm to generate allocations
        try:
            synapse.allocations = simulated_yiop_allocation_algorithm(synapse)
        except Exception as e:
            bt.logging.error(f"Error: {e}")

        bt.logging.info(f"sending allocations: {synapse.allocations}")
        end_time = time.perf_counter()
        bt.logging.info(f"Elapsed time ::::::::::::::::::::: {(end_time - start_time) * 1000} milliseconds")
        return synapse


# This is the main function, which runs the miner.
if __name__ == "__main__":
    with SimMiner() as miner:
        while True:
            bt.logging.info("SimMiner running... v1.0.2", time.time())
            time.sleep(5)
