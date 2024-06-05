import bittensor as bt
import time
from neurons.miner import Miner


class RegisterMiner(Miner):

    def __init__(self, config=None):
        self.wandb = None
        super(RegisterMiner, self).__init__(config=config)

    def run(self):
        """
        Identical to the original mienr, however only start to register then exit
        """

        # Check that miner is registered on the network.
        self.sync()

        # Serve passes the axon information to the network + netuid we are hosting on.
        # This will auto-update if the axon port of external ip have changed.
        bt.logging.info(
            f"Serving miner axon {self.axon} on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}"
        )
        # self.axon.serve(netuid=self.config.netuid, subtensor=self.subtensor)
        self.axon.start()

        bt.logging.info(f"Miner registered and starting at block: {self.block}, exiting now")

    def check_registered(self):
        pass

    def stop_run_thread(self):
        """
        Stops the miner's operations that are running in the background thread.
        """
        if self.is_running:
            bt.logging.debug("Stopping miner in background thread.")
            self.should_exit = True
            self.thread.join(120) # longer wait time for registration
            self.is_running = False
            bt.logging.debug("Stopped")

if __name__ == "__main__":
    with RegisterMiner() as miner:
        bt.logging.info("Miner running v1.0.1...", time.time())