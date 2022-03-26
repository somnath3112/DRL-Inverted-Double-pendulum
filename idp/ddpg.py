from replay import ReplayBuffer
from copy import deepcopy
import torch 
import numpy as np 
import gym 
import random

class DDPG():
    def __init__(self, env, critic, actor, gamma=0.99, tau=0.995, batch_size=32, replay_buffer_size=100, episodes=100, steps=500):
        self.env = env 
        self.critic = critic 
        self.actor = actor
        self.gamma = gamma
        self.tau = tau 
        self.batch_size = batch_size
        self.replay_buffer_size = replay_buffer_size
        self.episodes = episodes
        self.steps = steps 
        self.target_critic = deepcopy(critic)
        self.target_actor = deepcopy(actor)

        self.critic_optimizer = torch.optim.Adam(self.critic.parameters())
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters())

        #These networks must be updated using exponential averaging w.r.t the critic network and the actor policy, not through the gradients
        for param in self.target_critic.parameters():
            param.requires_grad = False 
        for param in self.target_actor.parameters():
            param.requires_grad = False 

    """
    Computes the loss of the critic network
    """
    def critic_loss(self, batch):
        states, actions, rewards, new_states, done = batch['states'], batch['actions'], batch['rewards'], batch['new_states'], batch['done']
        with torch.no_grad():
            #Select current believe of which action maximises the cumulative reward
            actor_actions = self.target_actor(new_states).unsqeeze(1)
            new_states = new_states.unsqueeze(1)
            #Input of the target critic network
            x = torch.cat((new_states, actor_actions), 1)
            #Bellman equation
            y = rewards + (1-done)*self.gamma*self.target_critic(x)
            #Input of the critic network
            states = states.unsqueeze(1)
            actions = states.unsqueeze(1)
            x = torch.cat((states, actions), 1)

        #compute and return the MSE loss 
        return ((y-self.critic(x))**2).mean()

    """
    Computes the loss of the actor network
    """
    def actor_loss(self, batch):
        states = batch['states']
        actor_actions = self.target_actor(states).unsqueeze(1)
        with torch.no_grad():
            states = states.unsqueeze(1)
            #Input of the critic network
            x = torch.cat((states, actor_actions))

        #Compute and return the loss 
        return -self.critic(x).mean()

    """
    Chooses an action using the actor network and by applying some noise to explore 
    """
    def choose_action(self, state):
        action = self.actor(state) + random.uniform(-0.01, 0.01)
        return np.clip(action, -1.0, 1.0)

    """
    Performs one step of gradient descent for the critic network and the actor network
    """
    def update_networks(self, batch):
        #Update critic network using gradient descent
        self.critic_optimizer.zero_grad()
        critic_loss = critic_loss(batch)
        critic_loss.backward()
        self.critic_optimizer.step()

        #Compute the loss for the actor
        self.actor_optimizer.zero_grad()
        actor_loss = actor_loss(batch)
        actor_loss.backward()
        self.actor_optimizer.step()

    """
    Performs exponential averaging on the parameters of the target networks, with respect to the parameters of the networks
    """
    def update_target_networks(self):
        with torch.no_grad():
            for param, target_param in zip(self.critic.parameters(), self.target_critic.parameters()):
                target_param.data.mul_(self.tau)
                target_param.add_(param.data*(1-self.tau))
            for param, target_param in zip(self.actor.parameters(), self.target_actor.parameters()):
                target_param.data.mul_(self.tau)
                target_param.add_(param.data*(1-self.tau))

    def apply(self):
        #Initialize the replay buffer 
        replay_buffer = ReplayBuffer(self.replay_buffer_size)
        #Algorithm
        for _ in range(self.episodes):
            #Initialize a new starting state for the episode
            current_state = self.env.reset()
            for _ in range(self.steps):
                #make a step in the environment
                action = self.choose_action(current_state)
                reward, new_state, done, _ = self.env.step(action)

                #store the transition in the replay buffer
                replay_buffer.store((current_state, action, reward, new_state, done))

                #update current state
                current_state = self.env.reset() if done else new_state
                
                #Sample a batch of size batch_size
                batch = replay_buffer.minibatch(self.batch_size)

                #Perform one step of gradient descend for the networks
                self.update_networks(batch)

                #Update target networks
                self.update_target_networks()





