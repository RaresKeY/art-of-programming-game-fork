from typing import List
from .base_agent import RouteAgent
from ..models import Package, Vehicle, Route, DeliveryMap
from ..core.router import Router
import copy

# TODO: consider package volume, distancea and price better when clustering


def calc_distance(pos1: tuple[float, float], pos2: tuple[float, float]):
    return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2) ** 0.5

class RAgent(RouteAgent):
    def __init__(self, delivery_map: DeliveryMap):
        super().__init__(delivery_map, "Agent R")
        self.description = "custom agent R"
        self._router = Router()

        self._boxes = []
        self._vehicles = []

        self._assigned_boxes = []
        self._assigned_vehicles = []

        self._routes: List[Route] = []

    def plan_routes(self, packages: List[Package], fleet: List[Vehicle]) -> List[Route]:
        if not self.validate_inputs(packages, fleet):
            return []

        self._vehicles = copy.deepcopy(fleet)
        self._boxes = copy.deepcopy(packages)

        self._assigned_boxes = []
        self._assigned_vehicles = []

        self._routes = []

        # cost_per_km_per_m3 = cost_per_km / capacity_m3
        self._vehicles.sort(key=lambda v: v.vehicle_type.cost_per_km / v.vehicle_type.capacity_m3)

        self._clusters_all()

        return self._routes

    def _create_route(self, vehicle: Vehicle, boxes: List[Package]) -> Route:
        route = Route(vehicle=vehicle, 
                      packages=boxes, 
                      stops=[b.destination for b in boxes],
                      delivery_map=self.delivery_map)

        return route

    def greedy_cluster(self, vehicle: Vehicle, cluster: list[Package], depot = (0, 0)):
        route: list[tuple] = []
        boxes: list[Package] = []

        origin = depot
        route.append(depot)

        while cluster:
            cluster.sort(key=lambda x: calc_distance(origin, x.destination), reverse=True)

            box = cluster.pop()
            origin = box.destination

            route.append(origin)
            boxes.append(box)

        route.append(depot)

        final_route = Route(vehicle=vehicle,
                      packages=boxes,
                      stops=route,
                      delivery_map=self.delivery_map)

        return final_route

    def _clusters_all(self):
        while self._boxes:
            clusters: list[Package] = []
            final_clusters: list[Route] = []

            if not self._vehicles:
                break

            veh = self._vehicles.pop()
            self._assigned_vehicles.append(veh)

            # TODO: add memo
            for b in self._boxes:
                if b in self._assigned_boxes:
                    continue
                boxes = sorted(self._boxes, key=lambda x: calc_distance(b.destination, x.destination))
                clusters.append(self._find_cluster(b, boxes, veh))

            for c in clusters:
                final_clusters.append(self.greedy_cluster(veh, c))
                # sort clusters by full distance
                final_clusters.sort(key=lambda x: x.calculate_total_distance(), reverse=True)

            route = final_clusters.pop()

            for b in route.packages:
                self._boxes.remove(b)
                self._assigned_boxes.append(b)

            self._routes.append(route)

    def _find_cluster(self, box: Package, boxes: List[Package], veh: Vehicle):
        cluster = [box]
        cubic = box.volume_m3
        distance = 0.0

        for b in [b for b in boxes if b is not box]:
            cubic += b.volume_m3
            distance += calc_distance(box.destination, b.destination)

            if cubic > veh.vehicle_type.capacity_m3:
                break

            cluster.append(b)

        return cluster

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"
