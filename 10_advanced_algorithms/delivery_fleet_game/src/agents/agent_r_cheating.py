from typing import List
from .base_agent import RouteAgent
from ..models import Package, Vehicle, Route, DeliveryMap
from ..core.router import Router
import copy


class RAgent(RouteAgent):
    def __init__(self, delivery_map: DeliveryMap):
        super().__init__(delivery_map, "Agent R")
        self.description = "custom agent R"
        self.router = Router()

    def plan_routes(self, packages: List[Package], fleet: List[Vehicle]) -> List[Route]:
        veh = copy.deepcopy(fleet)
        boxes = copy.deepcopy(packages)

        assigned_b = []
        final_routes = []

        for b in boxes:
            for v in veh:
                assigned_b.append(b)
            final_routes.append(self._create_route(v, assigned_b))
            assigned_b = []

        return final_routes

    def _create_route(self, vehicle: Vehicle, boxes: List[Package]) -> Route:
        route = Route(vehicle=vehicle, 
                      packages=boxes, 
                      stops=[b.destination for b in boxes],
                      delivery_map=self.delivery_map)
        
        return route

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"
