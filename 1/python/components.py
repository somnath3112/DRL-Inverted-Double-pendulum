from random import uniform
import numpy as np
from pprint import pprint

class Action:
    def __init__(self, action:tuple) -> None:
        self.i = action[1]
        self.j = action[0]

    def __repr__(self):
        return "(" + str(self.i) + "," + str(self.j) + ")"

class State:
    """ State space """
    def __init__(self, x, y) -> None:
        self.x = x
        self.y = y

    def __repr__(self):
        return "(" + str(self.x) + "," + str(self.y) + ")"

class StochasticDomain():
    # Action space
    LEFT = Action((0, -1))
    RIGHT = Action((0, 1))
    UP = Action((-1, 0))
    DOWN = Action((1, 0))

    def __init__(self, g, w) -> None:
        self.g = g
        self.w = w
        self.m, self.n = g.shape

    def interact(self, state: State, action: Action):
        """Interacts with the domain, returns a (state, reward) pair"""
        noise = uniform(0, 1)
        new_state = self.f(state, action, noise)
        reward = self.R(new_state)
        return (new_state, reward)

    def f(self, state: State, action: Action, noise: float):
        """ Dynamics functions """
        new_state = None
        if noise < self.w:
            new_state = self.F(state, action)
        else:
            new_state = self.state = State(0, 0)
        return new_state

    def r(self, state: State, action: Action, noise: float):
        """ Reward signal """
        new_state = self.f(state, action, noise)
        return self.R(new_state)

    def possibleTransitions(self, state: State, action: Action):
        """
        Returns a list of (new_state, reward, probability) tuples 
        for each possible transitions of this action in the current state.
        """
        first_state = self.f(state, action, 0.0)
        first_reward = self.r(state, action, 0.0)

        second_state = self.f(state, action, self.w)
        second_reward = self.r(state, action, self.w)

        return [(first_state, first_reward, self.w), (second_state, second_reward, 1-self.w)]

    def F(self, state: State, action: Action):
        """ Update the state deterministically """
        new_x = min(max(state.x + action.i, 0), self.n - 1)
        new_y = min(max(state.y + action.j, 0), self.m - 1)

        new_state = State(new_x, new_y)
        return new_state

    def R(self, state: State):
        return self.g[state.y][state.x]

    def print_domain(self, state):
        """ Clean print of the domain """
        tab = self.g
        res = [list(map(str, sub)) for sub in tab]
        res[state.y][state.x] =  ">" + res[state.y][state.x] + "<"
        pprint(res)

class DeterministicDomain(StochasticDomain):
    def __init__(self, g) -> None:
        super().__init__(g, 1.0)


