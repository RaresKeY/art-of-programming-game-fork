from typing import List
from .base_agent import RouteAgent
from ..models import Package, Vehicle, Route, DeliveryMap
from ..core import Router


class CustomAgent(RouteAgent):
    def __init__(self, delivery_map: DeliveryMap):
        super().__init__(delivery_map, "Agent Name")
        self.description = "custom agent"
        self.router = Router()

    def plan_routes(self, packages: List[Package], fleet: List[Vehicle]) -> List[Route]:
        final_routes: List[Route] = []

        return final_routes
    
    def _create_route(self, vehicle: Vehicle, boxes: List[Package]):
        route = Route(vehicle=vehicle, 
                      packages=boxes, 
                      stops=[b.destination for b in boxes],
                      delivery_map=self.delivery_map)
        
        return route

    def __str__(self) -> str:
        return f"{self.name}: {self.description}"
