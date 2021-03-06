from __future__ import division
from World import *

import numpy as np

import yaml
config = yaml.load(open("config.yml"))


class Ant(WorldObject):
    '''
    class Ant inherits from WorldObject and additionally holds a direction vector ...
    '''

    # speed per second
    max_speed = config["ant"]["max_speed"]
    min_speed = config["ant"]["min_speed"]
    max_turn_angle = config["ant"]["max_turn_angle"]
    acceleration = config["ant"]["acceleration"]

    length = config["ant"]["length"]
    center_radius = config["ant"]["center_radius"]
    head_radius = config["ant"]["head_radius"]
    head_angle = config["ant"]["head_angle"]

    signal_noise = config["ant"]["angle_noise_error"]

    phero_speed_down_treshold = config["ant"]["phero_speed_down_treshold"]

    def __init__(self, position, direction, world_instance = None):
        WorldObject.__init__(self, position, world_instance)
        self.set_type("ant")

        #norm the direction to 1
        self.direction = norm_vector(np.array(direction))
        self.speed = Ant.min_speed

    def to_dict(self):
        d = {}
        d["position"] = self.position
        d["type"] = self.type
        d["direction"] = self.direction
        d["speed"] = self.speed
        return d

    def get_left_antenna_position(self):
        pos_head = self.get_head_position()
        return pos_head + rotate_vector(self.direction * Ant.head_radius, Ant.head_angle / 2)

    def get_right_antenna_position(self):
        pos_head = self.get_head_position()
        return pos_head + rotate_vector(self.direction * Ant.head_radius, 360 - Ant.head_angle / 2)

    def get_head_position(self):
        return self.position + self.direction * (self.length / 2)

    def get_weighted_collision_vector(self, position_list):
        matrix = np.empty((2, len(position_list)), dtype=np.float)

        for i,pos in enumerate(position_list):
            v = ((self.position - pos) / np.linalg.norm(self.position - pos))
            matrix[:,i] = v


        av = np.average(matrix, axis=1)

        return av

    def get_avoiding_vector(self, collision_vector, delta):

        o_turn_angle, turn_angle, orientation = get_oriented_angle(self.direction, self.direction + collision_vector)

        #check if angle exceeds max angle
        if turn_angle > Ant.max_turn_angle * delta:
            o_turn_angle = Ant.max_turn_angle * orientation * delta

        #rotate the vector
        new_direction = rotate_vector(self.direction, o_turn_angle)

        return norm_vector(new_direction)

    def evade_objects(self, delta):
        #this is the main collision method

        pos_in_center_range = self.world.get_positions_in_range_kd(self.position, self.center_radius)
        pos_in_top_range = self.world.get_positions_in_range_and_radius_kd(self.position, self.direction, Ant.head_radius, Ant.head_angle)

        if pos_in_center_range.size == 0 and pos_in_top_range.size == 0:
            return
        elif pos_in_center_range.size > 0 and pos_in_top_range.size == 0:
            pos_in_range = pos_in_center_range
        elif pos_in_center_range.size == 0 and pos_in_top_range.size > 0:
            pos_in_range = pos_in_top_range
        else:
            pos_in_range = np.concatenate((pos_in_center_range, pos_in_top_range), axis=0)

        if len(pos_in_range) > 0:
            collision_vector = self.get_weighted_collision_vector(pos_in_range)
            avoiding_vector = self.get_avoiding_vector(collision_vector, delta)
            self.direction = avoiding_vector

            return True

        return False

    def trail_pheromone(self, delta):
        # turns the ant to the side with higher pheromone concentration

        pos_left = self.get_left_antenna_position()
        pos_right = self.get_right_antenna_position()

        # concentrations
        c_left = self.world.phero_map.get_pheromone_concentration(pos_left, Ant.head_radius)
        c_right = self.world.phero_map.get_pheromone_concentration(pos_right, Ant.head_radius)

        # angle
        # maybe divide by max pheromone concentration

        if c_left + c_right > 0.:

            a = c_left - c_right

            #SIGMOID FUNCTION

            a = 2 / ( 1 + np.exp(-4 * a))  -1

            a += np.random.normal(0, self.signal_noise)

            turn_angle = (self.max_turn_angle * a * delta)

            #print turn_angle

            self.direction = rotate_vector(self.direction, turn_angle)
            return np.absolute(a)
        else:
            self.direction = rotate_vector(self.direction, self.max_turn_angle * np.random.normal(0, self.signal_noise) * delta)
            return 0

    def circuit_world(self):
        shift = self.world.dimensions / 2

        circuited = False
        pos = self.position + shift

        for i in range(pos.shape[0]):
            if pos[i] >= self.world.dimensions[i]:
                pos[i] %= self.world.dimensions[i]
                circuited = True
            elif pos[i] < 0:
                pos[i] = self.world.dimensions[i] - (-pos[i] % self.world.dimensions[i])
                circuited = True

        self.position = pos - shift
        return circuited

    def speed_up(self, delta):
        if self.speed + self.acceleration * delta <= self.max_speed:
            self.speed += self.acceleration * delta
        else:
            self.speed = self.max_speed

    def speed_down(self, delta):
        if self.speed - self.acceleration * delta >= self.min_speed:
            self.speed -= self.acceleration * delta
        else:
            self.speed = self.min_speed

    def tick(self, delta):
        '''
        put here all the movement logic
        '''

        #set pheromone concentration
        self.world.phero_map.add_pheromone_concentration(self.position - (self.direction * self.length / 2), 100. * delta * self.speed)

        evaded = False
        trailed = False

        evaded = self.evade_objects(delta)
        if not evaded:
            trail_change = self.trail_pheromone(delta)

            if trail_change >= self.phero_speed_down_treshold:
                self.speed_down(delta)
            else:
                self.speed_up(delta)
        else:
            self.speed_down(delta)

        self.position = self.position + ( self.direction * self.speed * self.world.delta_time)

        #wrap around the edges of the world
        circuited = self.circuit_world()
