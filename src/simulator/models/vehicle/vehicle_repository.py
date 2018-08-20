from .vehicle import Vehicle
from .vehicle_state import VehicleState
import pandas as pd

class VehicleRepository(object):
    vehicles = {}

    @classmethod
    def init(cls):
        cls.vehicles = {}

    @classmethod
    def populate(cls, vehicle_ids, locations):
        for vehicle_id, location in zip(vehicle_ids, locations):
            state = VehicleState(vehicle_id, location)
            cls.vehicles[vehicle_id] = Vehicle(state)

    @classmethod
    def get_all(cls):
        return list(cls.vehicles.values())

    @classmethod
    def get(cls, vehicle_id):
        return cls.vehicles.get(vehicle_id, None)

    @classmethod
    def get_states(cls):
        states = [vehicle.get_state() for vehicle in cls.get_all()]
        cols = VehicleState.__slots__[:]
        df = pd.DataFrame.from_records(states, columns=cols).set_index("id")
        df["earnings"] = [vehicle.earnings for vehicle in cls.get_all()]
        return df