import numpy as np
from typing import List, Tuple
import random


# ----------------- UTILITIES -----------------
def calc_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5


# ----------------- DATA STRUCTURES -----------------
class Box:
    def __init__(self, destination: Tuple[float, float], price: float):
        self.destination = destination
        self.price = price


# ----------------- ENVIRONMENT -----------------
class DeliveryEnv:
    """
    Simple RL environment:
    - State: current position + remaining box coords
    - Action: index of next box
    - Reward: income minus travel cost
    """
    def __init__(self, boxes: List[Box], depot=(0.0, 0.0), cost_per_km=1.0):
        self.boxes_init = boxes
        self.depot = depot
        self.cost_per_km = cost_per_km
        self.reset()

    def reset(self):
        self.boxes = self.boxes_init.copy()
        self.position = self.depot
        self.done = False
        self.total_income = 0.0
        return self._get_state()

    def _get_state(self):
        # Flatten remaining destinations into a vector
        coords = []
        for b in self.boxes:
            coords.extend(b.destination)
        # Pad so the state size stays constant
        while len(coords) < 10 * 2:
            coords.extend([0.0, 0.0])
        state = np.array([self.position[0], self.position[1]] + coords[:20])
        return state

    def step(self, action_index: int):
        box = self.boxes.pop(action_index)
        dist = calc_distance(self.position, box.destination)
        reward = box.price - self.cost_per_km * dist
        self.total_income += reward
        self.position = box.destination
        self.done = len(self.boxes) == 0
        return self._get_state(), reward, self.done


# ----------------- POLICY NETWORK -----------------
class PolicyNet:
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        self.W1 = np.random.randn(input_dim, hidden_dim) * 0.1
        self.b1 = np.zeros((1, hidden_dim))
        self.W2 = np.random.randn(hidden_dim, output_dim) * 0.1
        self.b2 = np.zeros((1, output_dim))

    def forward(self, x: np.ndarray):
        z1 = np.dot(x, self.W1) + self.b1
        a1 = np.tanh(z1)
        z2 = np.dot(a1, self.W2) + self.b2
        exp_z2 = np.exp(z2 - np.max(z2))
        probs = exp_z2 / np.sum(exp_z2)
        return probs, (x, a1)

    def update(self, grad_W1, grad_b1, grad_W2, grad_b2, lr=0.01):
        self.W1 += lr * grad_W1
        self.b1 += lr * grad_b1
        self.W2 += lr * grad_W2
        self.b2 += lr * grad_b2


# ----------------- TRAINING LOOP -----------------
def train(env: DeliveryEnv, model: PolicyNet, episodes=2000, lr=0.01, gamma=0.99):
    for ep in range(episodes):
        state = env.reset()
        states, actions, rewards, caches = [], [], [], []
        total_reward = 0.0

        while not env.done:
            probs, cache = model.forward(state.reshape(1, -1))
            action = np.random.choice(len(env.boxes), p=probs[0, :len(env.boxes)])
            next_state, reward, done = env.step(action)

            states.append(state)
            actions.append(action)
            rewards.append(reward)
            caches.append(cache)
            total_reward += reward

            state = next_state

        # Compute discounted returns
        returns = np.zeros_like(rewards)
        G = 0
        for t in reversed(range(len(rewards))):
            G = rewards[t] + gamma * G
            returns[t] = G
        returns = (returns - np.mean(returns)) / (np.std(returns) + 1e-8)

        # Backpropagate (REINFORCE algorithm)
        grad_W1 = np.zeros_like(model.W1)
        grad_b1 = np.zeros_like(model.b1)
        grad_W2 = np.zeros_like(model.W2)
        grad_b2 = np.zeros_like(model.b2)

        for t in range(len(rewards)):
            state_t = states[t].reshape(1, -1)
            probs, (x, a1) = caches[t]
            dlog = np.zeros_like(probs)
            dlog[0, actions[t]] = 1 - probs[0, actions[t]]
            grad_W2 += np.dot(a1.T, dlog) * returns[t]
            grad_b2 += dlog * returns[t]
            da1 = np.dot(dlog, model.W2.T)
            dz1 = da1 * (1 - a1 ** 2)
            grad_W1 += np.dot(x.T, dz1) * returns[t]
            grad_b1 += dz1 * returns[t]

        model.update(grad_W1, grad_b1, grad_W2, grad_b2, lr)

        if (ep + 1) % 100 == 0:
            print(f"Episode {ep+1}, Total Reward: {total_reward:.2f}")


# ----------------- DEMO -----------------
if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)

    # Create random boxes
    boxes = [Box((random.uniform(-10, 10), random.uniform(-10, 10)),
                 price=random.uniform(5, 20)) for _ in range(5)]

    env = DeliveryEnv(boxes, depot=(0, 0), cost_per_km=0.5)
    input_dim = 22  # 2 (pos) + 5*2 (dest) + padding
    model = PolicyNet(input_dim=input_dim, hidden_dim=32, output_dim=5)

    train(env, model, episodes=1000, lr=0.01)
