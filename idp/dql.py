from utils import J
from replay import ReplayBuffer
from copy import deepcopy
import torch 
import numpy as np
import time
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
import matplotlib.pyplot as plt

print(device)

class DQL():
    def __init__(self, env, critic, file_extension, actions, gamma=0.95, tau=0.999, batch_size=64, replay_buffer_size=int(1e6), episodes=500, steps=1000, nb_simulation=50):
        self.env = env
        self.critic = critic.to(device)
        self.actions = actions
        self.gamma = gamma
        self.tau = tau 
        self.batch_size = batch_size
        self.replay_buffer_size = replay_buffer_size
        self.episodes = episodes
        self.steps = steps 
        self.target_critic = deepcopy(critic).to(device)
        self.epsilon = 1
        self.file_extension = file_extension
        self.nb_simulation = nb_simulation

        # update epsiln
        self.end = 10000
        self.current = 0

        self.critic_optimizer = torch.optim.Adam(self.critic.parameters(), lr=1e-3)

        #These networks must be updated using exponential averaging w.r.t the critic network and the actor policy, not through the gradients
        for param in self.target_critic.parameters():
            param.requires_grad = False 

    def critic_loss(self, batch):
        """
        Computes the loss of the critic network
        """
        with torch.no_grad():
            states, action_index, rewards, new_states, done = batch['states'].to(device), batch['actions'].to(device).long(), batch['rewards'].to(device), batch['new_states'].to(device), batch['done'].to(device)
            #Bellman equation
            target_Q = self.target_critic(new_states).max(axis=1)[0].unsqueeze(1)
            y = torch.where(done == True, rewards, self.gamma*target_Q) 

        # print(action_index)
        Q = torch.gather(self.critic(states), 1, action_index)
        # Q = self.critic(states)[action_index].unsqueeze(1)

        #compute and return the MSE loss 
        return torch.nn.functional.mse_loss(Q, y)

    def update_epsilon(self):
        """
        Epsilon annealed linearly from 1.0 to 0.1 over 10000 frames
        """
        self.epsilon = max((self.end - self.current)/self.end, 0.1)
        self.current += 1

    def choose_action(self, states):
        """
        Chooses an action using the actor network and by applying some noise to explore 
        """
        with torch.no_grad():
            r = np.random.rand()
            if r < self.epsilon:
                action_index = np.random.randint(0, len(self.actions))# .choice(self.actions)

            else:
                action_index = self.compute_optimal_actions(states,values=False)[0]
        return np.array(action_index)

    def compute_optimal_actions(self, states, values=True):
        """
        Choose an action using the actor network
        """
        states = torch.Tensor(np.array(states)).unsqueeze(0)
        with torch.no_grad():
            self.critic.eval()

            y_pred = self.critic(states).detach().to("cpu").numpy()
            best_action_index = np.argmax(y_pred, axis=1)

            self.critic.train()

        if values:
            # print(states)
            # print(self.actions[best_action_index])
            return np.array(torch.Tensor(self.actions[best_action_index]).unsqueeze(1))

        return best_action_index

    def update_networks(self, batch):
        """
        Performs one step of gradient descent for the critic network and the actor network
        """
        #Update critic network using gradient descent
        closs = self.critic_loss(batch)
        self.critic_optimizer.zero_grad()
        closs.backward()
        self.critic_optimizer.step()

        return closs.detach().to("cpu")

    def update_target_networks(self):
        """
        Performs exponential averaging on the parameters of the target networks, with respect to the parameters of the networks
        """
        with torch.no_grad():
            for param, target_param in zip(self.critic.parameters(), self.target_critic.parameters()):
                target_param.data.mul_(self.tau)
                target_param.data.add_(param.data*(1-self.tau))

    def apply(self):
        """
        Train the agent in an online manner
        """
        #Initialize the replay buffer 
        replay_buffer = ReplayBuffer(self.replay_buffer_size)
        self.critic.train()
        self.target_critic.train()

        J_mean = []
        J_std = []

        current_state = self.env.reset()
        # fill the buffer with random actions
        for i in range(1000):
            action_index = np.random.randint(0, len(self.actions))# .choice(self.actions)
            new_state, reward, done, _ = self.env.step([self.actions[action_index]])
            replay_buffer.store((current_state, action_index, reward, new_state, done))
            current_state = self.env.reset() if done else new_state
        #Algorithm
        for i in range(1, self.episodes+1):
            #Initialize a new starting state for the episode
            current_state = self.env.reset()
            
            #Keep track of losses
            critic_losses = []
            actor_losses = []
            
            start = time.process_time()

            self.env.seed(self.nb_simulation + i) # not interfer with the computation of J

            for _ in range(self.steps):
                #make a step in the environment
                action_index = self.choose_action(current_state)
                action = np.array([[self.actions[action_index]]])
                new_state, reward, done, _ = self.env.step(action)

                #store the transition in the replay buffer
                replay_buffer.store((current_state, action_index, reward, new_state, done))

                #update current state
                current_state = self.env.reset() if done else new_state

                #Sample a batch of size batch_size
                batch = replay_buffer.minibatch(self.batch_size)

                #Perform one step of gradient descend for the networks
                closs = self.update_networks(batch)

                #Remember the losses 
                critic_losses.append(closs)

                #Update target networks
                self.update_target_networks()
                self.update_epsilon()

            avg_critic_loss = torch.mean(torch.Tensor(critic_losses))
            j = J(self.env, self, self.gamma, self.nb_simulation, 200)
            J_mean.append(j[0])
            J_std.append(j[1])
            print(time.process_time() - start)
            print("Episode {}: critic: {} | J: {}".format(i, avg_critic_loss, j))

        torch.save(self.critic.state_dict(), "models/critic_{}_{}".format(self.episodes, self.file_extension))

        J_mean = np.array(J_mean)
        J_std = np.array(J_std)
        plt.plot(J_mean, label="Expected return")
        plt.ylabel("Expected return J")
        plt.xlabel("Episode")
        plt.legend()
        plt.fill_between(range(self.episodes),J_mean-J_std,J_mean+J_std,alpha=.1)
        plt.savefig("figures/J_{}.png".format(self.file_extension))

        J_mean.tofile("data/J_mean_{}".format(self.file_extension))
        J_std.tofile("data/J_std_{}".format(self.file_extension))



