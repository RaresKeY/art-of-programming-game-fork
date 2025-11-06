"""
Neural policy-gradient agent for manual experimentation.

This module adapts the earlier reinforcement-learning prototype so it fits the
RouteAgent interface used by the game. Each vehicle is assigned a batch of
packages (biased toward high-value, high-density freight) and a lightweight
policy-gradient model learns the drop-off order for that batch. The learned
policy is rolled out greedily to generate the final route. The implementation
falls back to a nearest-neighbour heuristic if training fails to converge for
any reason, keeping the gameplay experience stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np

from .base_agent import RouteAgent
from ..core import Router
from ..models import DeliveryMap, Package, Route, Vehicle


@dataclass
class StepRecord:
    """Trajectory information for a single environment step."""

    cache: tuple
    action: int
    reward: float


class PolicyNet:
    """Two-layer policy network with tanh hidden units."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        self.W1 = np.random.randn(input_dim, hidden_dim) * 0.1
        self.b1 = np.zeros((1, hidden_dim))
        self.W2 = np.random.randn(hidden_dim, output_dim) * 0.1
        self.b2 = np.zeros((1, output_dim))

    def forward(self, x: np.ndarray, valid_actions: int) -> tuple[np.ndarray, tuple]:
        """
        Forward pass with masking for invalid actions.

        Args:
            x: Input batch (n, input_dim)
            valid_actions: Number of currently available actions
        """
        z1 = np.dot(x, self.W1) + self.b1
        a1 = np.tanh(z1)
        z2 = np.dot(a1, self.W2) + self.b2

        # Stable softmax
        max_logits = np.max(z2, axis=1, keepdims=True)
        exp_z2 = np.exp(z2 - max_logits)

        # Mask out invalid actions (those beyond valid_actions)
        mask = np.zeros_like(exp_z2)
        if valid_actions > 0:
            mask[:, :valid_actions] = 1.0
        exp_z2 *= mask

        denom = np.sum(exp_z2, axis=1, keepdims=True)
        denom[denom == 0] = 1.0  # avoid division by zero

        probs = exp_z2 / denom
        cache = (x, a1, probs)
        return probs, cache

    def update(self, grad_W1, grad_b1, grad_W2, grad_b2, lr: float) -> None:
        """Gradient-ascent update."""
        self.W1 += lr * grad_W1
        self.b1 += lr * grad_b1
        self.W2 += lr * grad_W2
        self.b2 += lr * grad_b2


class DeliveryEnv:
    """
    Simple episodic environment modelling deliveries for a single vehicle.

    The agent receives the depot position and the remaining destinations as the
    state, and chooses the next package index to deliver. Rewards combine
    payment and travel costs so the policy learns profitable, short routes.
    """

    def __init__(self, packages: Sequence[Package], vehicle: Vehicle, delivery_map: DeliveryMap):
        self.delivery_map = delivery_map
        self.vehicle = vehicle
        self._packages = list(packages)
        self._max_boxes = len(self._packages)
        self._state_dim = 2 + self._max_boxes * 2
        self.reset()

    @property
    def max_actions(self) -> int:
        return max(1, self._max_boxes)

    @property
    def state_dim(self) -> int:
        return self._state_dim

    def reset(self) -> np.ndarray:
        self.remaining: List[Package] = self._packages.copy()
        self.position = self.delivery_map.depot
        self.done = False
        return self._get_state()

    def _get_state(self) -> np.ndarray:
        coords: List[float] = []
        for pkg in self.remaining:
            coords.extend(pkg.destination)

        while len(coords) < self._max_boxes * 2:
            coords.extend([0.0, 0.0])

        state = np.array([self.position[0], self.position[1]] + coords[: self._max_boxes * 2], dtype=np.float32)
        return state

    def step(self, action_index: int) -> tuple[np.ndarray, float, bool, Package]:
        pkg = self.remaining.pop(action_index)
        travel_distance = self.delivery_map.distance(self.position, pkg.destination)
        travel_cost = travel_distance * self.vehicle.vehicle_type.cost_per_km
        reward = pkg.payment - travel_cost

        self.position = pkg.destination
        done = not self.remaining
        if done:
            return_distance = self.delivery_map.distance(self.position, self.delivery_map.depot)
            reward -= return_distance * self.vehicle.vehicle_type.cost_per_km
            self.done = True
        else:
            self.done = False

        next_state = self._get_state()
        return next_state, reward, self.done, pkg


class NeuralRAgent(RouteAgent):
    """
    Policy-gradient agent tailored for the Delivery Fleet simulation.

    Each vehicle is handled independently: the agent trains a small neural
    policy to decide the delivery order for the packages allocated to that
    vehicle. The approach is intentionally lightweight so it can run during a
    classroom session without long waits.
    """

    def __init__(
        self,
        delivery_map: DeliveryMap,
        training_episodes: int = 250,
        hidden_dim: int = 48,
        learning_rate: float = 0.012,
        discount_factor: float = 0.98,
    ):
        super().__init__(delivery_map, "Agent R Neural")
        self.description = "Reinforcement-learning agent with on-the-fly policy gradients"
        self.training_episodes = training_episodes
        self.hidden_dim = hidden_dim
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.router = Router()

    def plan_routes(self, packages: List[Package], fleet: List[Vehicle]) -> List[Route]:
        if not self.validate_inputs(packages, fleet):
            return []

        remaining = packages.copy()
        routes: List[Route] = []

        for vehicle in fleet:
            selection = self._select_packages_for_vehicle(vehicle, remaining)
            if not selection:
                continue

            ordered_packages, stops = self._train_and_plan(vehicle, selection)
            route = Route(vehicle=vehicle, packages=ordered_packages, stops=stops, delivery_map=self.delivery_map)

            if not route.is_valid():
                ordered_packages = self.router.optimize_package_sequence(selection, self.delivery_map, use_2opt=False)
                stops = [pkg.destination for pkg in ordered_packages]
                route = Route(vehicle=vehicle, packages=ordered_packages, stops=stops, delivery_map=self.delivery_map)

            routes.append(route)

            for pkg in ordered_packages:
                if pkg in remaining:
                    remaining.remove(pkg)

        if remaining:
            total_unassigned = sum(pkg.volume_m3 for pkg in remaining)
            print(
                f"[{self.name}] Warning: {len(remaining)} packages "
                f"({total_unassigned:.1f} m³) left unassigned after planning."
            )

        return routes

    # ------------------------- TRAINING HELPERS -------------------------
    def _train_and_plan(self, vehicle: Vehicle, packages: Sequence[Package]) -> tuple[List[Package], List[Tuple[float, float]]]:
        env = DeliveryEnv(packages, vehicle, self.delivery_map)
        if env.max_actions == 0:
            return list(packages), [pkg.destination for pkg in packages]

        model = PolicyNet(env.state_dim, self.hidden_dim, env.max_actions)

        for episode in range(self.training_episodes):
            self._run_episode(env, model)
            if (episode + 1) % 100 == 0:
                print(f"[{self.name}] Vehicle {vehicle.id}: trained {episode + 1} episodes")

        ordered_packages, stops = self._rollout_policy(env, model)
        if not ordered_packages:
            ordered_packages = self.router.optimize_package_sequence(list(packages), self.delivery_map, use_2opt=False)
            stops = [pkg.destination for pkg in ordered_packages]

        return ordered_packages, stops

    def _run_episode(self, env: DeliveryEnv, model: PolicyNet) -> None:
        state = env.reset()
        trajectory: List[StepRecord] = []

        while True:
            valid_actions = len(env.remaining)
            if valid_actions == 0:
                break

            probs, cache = model.forward(state.reshape(1, -1), valid_actions)
            action = int(np.random.choice(valid_actions, p=probs[0, :valid_actions]))
            next_state, reward, done, _ = env.step(action)

            trajectory.append(StepRecord(cache=cache, action=action, reward=reward))

            state = next_state
            if done:
                break

        self._apply_policy_gradient(model, trajectory)

    def _apply_policy_gradient(self, model: PolicyNet, trajectory: List[StepRecord]) -> None:
        if not trajectory:
            return

        returns = []
        G = 0.0
        for record in reversed(trajectory):
            G = record.reward + self.discount_factor * G
            returns.append(G)
        returns = returns[::-1]
        returns = np.array(returns, dtype=np.float32)

        if np.std(returns) > 1e-6:
            returns = (returns - np.mean(returns)) / (np.std(returns) + 1e-8)
        else:
            returns = returns - np.mean(returns)

        grad_W1 = np.zeros_like(model.W1)
        grad_b1 = np.zeros_like(model.b1)
        grad_W2 = np.zeros_like(model.W2)
        grad_b2 = np.zeros_like(model.b2)

        for record, ret in zip(trajectory, returns):
            x, a1, probs = record.cache
            one_hot = np.zeros_like(probs)
            one_hot[0, record.action] = 1.0
            dlogits = one_hot - probs

            grad_W2 += np.dot(a1.T, dlogits) * ret
            grad_b2 += dlogits * ret

            da1 = np.dot(dlogits, model.W2.T)
            dz1 = da1 * (1.0 - np.square(a1))

            grad_W1 += np.dot(x.T, dz1) * ret
            grad_b1 += dz1 * ret

        model.update(grad_W1, grad_b1, grad_W2, grad_b2, self.learning_rate)

    def _rollout_policy(self, env: DeliveryEnv, model: PolicyNet) -> tuple[List[Package], List[Tuple[float, float]]]:
        state = env.reset()
        ordered_packages: List[Package] = []
        stops: List[Tuple[float, float]] = []

        while env.remaining:
            valid_actions = len(env.remaining)
            probs, _ = model.forward(state.reshape(1, -1), valid_actions)

            if valid_actions == 0:
                break

            action = int(np.argmax(probs[0, :valid_actions]))
            _, _, _, pkg = env.step(action)
            ordered_packages.append(pkg)
            stops.append(pkg.destination)
            state = env._get_state()

        return ordered_packages, stops

    # ------------------------- PACKAGE SELECTION -------------------------
    def _select_packages_for_vehicle(self, vehicle: Vehicle, candidates: List[Package]) -> List[Package]:
        capacity = vehicle.vehicle_type.capacity_m3
        selected: List[Package] = []
        used_volume = 0.0

        sortable = [pkg for pkg in candidates if pkg.volume_m3 <= capacity]
        sortable.sort(key=lambda p: (p.payment / max(p.volume_m3, 0.01)), reverse=True)

        for pkg in sortable:
            if used_volume + pkg.volume_m3 <= capacity + 1e-6:
                selected.append(pkg)
                used_volume += pkg.volume_m3

        if not selected and sortable:
            selected.append(sortable[0])

        return selected


__all__ = ["NeuralRAgent"]
