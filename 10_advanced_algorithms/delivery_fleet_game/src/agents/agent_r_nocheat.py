from typing import List
from .base_agent import RouteAgent
from ..models import Package, Vehicle, Route, DeliveryMap
from ..core.router import Router
import copy


class BoxData:
    def __init__(self):
        self.distances = dict()

    @staticmethod
    def _calc_distance(pos1: tuple[float], pos2: tuple[float]):
        pass
    
    def _get_distances(self, box: Package, boxes: List[Package]) -> List[float]:
        for other_b in boxes:
                if box is not other_b:
                    self.distances[other_b] = box.destination


class RAgent(RouteAgent):
    def __init__(self, delivery_map: DeliveryMap):
        super().__init__(delivery_map, "Agent R")
        self.description = "custom agent R"
        self.router = Router()

    def plan_routes(self, packages: List[Package], fleet: List[Vehicle]) -> List[Route]:
        if not self.validate_inputs(packages, fleet):
            return []

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
    
    def _find_clusters(self, boxes: List[Package]):
        for b in boxes:
            self._get_distances(b, boxes)

    def _get_distances(self, box: Package, boxes: List[Package]) -> List[float]:
        for other_b in boxes:
                if box is not other_b:
                    pass
        return

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"
