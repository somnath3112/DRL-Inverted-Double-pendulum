import numpy as np

from python.domain import CarOnTheHillDomain, State
from python.policy import Policy

class Simulation():
    """
        domain: the parametrized car on the hill domain
        policy: the policy used on the domain
        remember_trajectory: if true, it keeps track of the trajectory done by the simulator
        initial_state: initial state on the domain
    """
    def __init__(self, domain: CarOnTheHillDomain, policy: Policy, initial_state: State, remember_trajectory=False, seed=43) -> None:
        self.domain = domain
        self.policy = policy
        self.state = initial_state

        self.trajectory = None 
        if remember_trajectory:
            self.trajectory = list()

        np.random.seed(seed)



    """
        Simulate (steps) steps on the domain, according to the policy
        If remember_trajectory=True, each transition will be remembered
    """
    def simulate(self, steps: int) -> None:
        for _ in range(steps):
            action = self.policy.make_action(self.state)
            previous_state = self.state
            self.state = self.domain.f(self.state, action)
            reward = self.domain.r(self.state, action)
            if self.trajectory is not None:
                self.trajectory.append((previous_state, action, reward, self.state))

    def get_trajectory(self) -> list:
        return self.trajectory


