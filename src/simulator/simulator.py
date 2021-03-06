import numpy as np
from .models.vehicle.vehicle_repository import VehicleRepository
from .models.customer.customer_repository import CustomerRepository
from .services.demand_generation_service import DemandGenerator
from .services.routing_service import RoutingEngine
from common.time_utils import get_local_datetime
from config.settings import OFF_DURATION, PICKUP_DURATION
from logger import sim_logger
from logging import getLogger

class Simulator(object):

    def __init__(self, start_time, timestep):
        self.reset(start_time, timestep)
        sim_logger.setup_logging(self)
        self.logger = getLogger(__name__)
        self.demand_generator = DemandGenerator()
        self.routing_engine = RoutingEngine.create_engine()
        self.route_cache = {}

    def reset(self, start_time=None, timestep=None):
        if start_time is not None:
            self.__t = start_time
        if timestep is not None:
            self.__dt = timestep
        VehicleRepository.init()
        CustomerRepository.init()


    def populate_vehicle(self, vehicle_id, location):
        VehicleRepository.populate(vehicle_id, location)


    def step(self):
        for customer in CustomerRepository.get_all():
            customer.step(self.__dt)
            if customer.is_arrived() or customer.is_disappeared():
                CustomerRepository.delete(customer.get_id())

        for vehicle in VehicleRepository.get_all():
            vehicle.step(self.__dt)
            if vehicle.exit_market():
                score = ','.join(map(str, [self.get_current_time(), vehicle.get_id()] + vehicle.get_score()))
                sim_logger.log_score(score)
                VehicleRepository.delete(vehicle.get_id())

        self.__populate_new_customers()
        self.__update_time()
        if self.__t % 3600 == 0:
            self.logger.info("Elapsed : {}".format(get_local_datetime(self.__t)))

    def match_vehicles(self, commands):
        for command in commands:
            vehicle = VehicleRepository.get(command["vehicle_id"])
            if vehicle is None:
                self.logger.warning("Invalid Vehicle id")
                continue
            customer = CustomerRepository.get(command["customer_id"])
            if customer is None:
                self.logger.warning("Invalid Customer id")
                continue

            triptime = command["duration"]
            vehicle.head_for_customer(customer.get_origin(), triptime, customer.get_id())
            customer.wait_for_vehicle(triptime)


    def dispatch_vehicles(self, commands):
        od_pairs = []
        vehicles = []
        for command in commands:
            vehicle = VehicleRepository.get(command["vehicle_id"])
            if vehicle is None:
                self.logger.warning("Invalid Vehicle id")
                continue

            if "offduty" in command:
                off_duration = self.sample_off_duration()
                vehicle.take_rest(off_duration)
            elif "cache_key" in command:
                l, a = command["cache_key"]
                route, triptime = self.routing_engine.get_route_cache(l, a)
                vehicle.cruise(route, triptime)
            else:
                vehicles.append(vehicle)
                od_pairs.append((vehicle.get_location(), command["destination"]))
        routes = self.routing_engine.route(od_pairs)

        for vehicle, (route, triptime) in zip(vehicles, routes):
            if triptime == 0:
                continue
            vehicle.cruise(route, triptime)

    def __update_time(self):
        self.__t += self.__dt

    def __populate_new_customers(self):
        new_customers = self.demand_generator.generate(self.__t, self.__dt)
        CustomerRepository.update_customers(new_customers)

    def sample_off_duration(self):
        return np.random.randint(OFF_DURATION / 2, OFF_DURATION * 3 / 2)

    def sample_pickup_duration(self):
        return np.random.exponential(PICKUP_DURATION)

    def get_current_time(self):
        t = self.__t
        return t

    def get_new_requests(self):
        return CustomerRepository.get_new_requests()

    def get_vehicles_state(self):
        return VehicleRepository.get_states()


    # def log_score(self):
    #     for vehicle in VehicleRepository.get_all():
    #         score = ','.join(map(str, [self.get_current_time(), vehicle.get_id()] + vehicle.get_score()))
    #         sim_logger.log_score(score)
