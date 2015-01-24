from __future__ import division
import numpy as np
import Diffusion as df
### helper functions ###

def get_distance(v1, v2):
	'''Returns the distance between to 2d vectors'''

	diff = v1 - v2
	return np.linalg.norm(diff)

def norm_vector(v1):
	return v1 / np.linalg.norm(v1)

def get_angle(v1, v2):
	return np.degrees( np.arccos( np.dot(v1,v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)) ) )

def get_oriented_angle(v1, v2):
	angle = get_angle(v1,v2)
	oriented_angle = angle
	orientation = 0

	#create 2x2 matrix from v1,v2
	a = np.concatenate((v1, v2), axis=0).reshape((2,2))

	det = np.linalg.det(a)

	if det > 0:
		orientation = 1
	elif det < 0:
		orientation = -1
		oriented_angle = oriented_angle * -1 

	elif det == 0:
		orientation = 0
		
	return oriented_angle, angle, orientation

def rotate_vector(v, r):
	'''counter clock wise rotation'''
	theta = np.radians(r)
	rotMatrix = np.array([[np.cos(theta), -np.sin(theta)], 
                         [np.sin(theta),  np.cos(theta)]])

	return np.dot(rotMatrix, v)


class World():
	'''
	class World holds a set of objects which must have a positionvector [x,y]
	It can give back distances between objects or return a set of objects in a given range
	'''
	def __init__(self, dimensions = [400,400]):
		'''
		2d array - dimensions of the world
		'''

		self.dimensions = dimensions

		#first we use a list to hold objects
		self.world_objects = []

		self.phero_map = np.zeros(tuple(dimensions))

		#time which passes between two ticks
		self.delta_time = 1 / 40
		

	def get_objects_in_range(self, pos, radius):
		'''returns a list of objects in a given range
		needs a position vector and a radius
		'''

		in_range = []

		for o in self.world_objects:
			if get_distance(o.position, pos) <= radius:
				in_range.append(o)

		return in_range

	def get_objects_in_range_and_radius(self, pos, dir, radius, check_angle):
		'''returns a list of objects in a given range, direction and angle'''

		in_range = self.get_objects_in_range(pos, radius)
		in_angle = [];

		for o in in_range:
			o_direction = o.position - pos
			angle = get_angle(dir, o_direction)

			if 0 <= angle <= (check_angle / 2):
				in_angle.append(o)

		return in_angle

	def any_objects_in_range(self, pos, radius):
		for o in self.world_objects:
			distance = get_distance(o.position, pos)

			#if distance == 0, its the object itself!
			if distance <= radius * 2 and distance != 0.:
				return True

		return False

	def get_objects(self, type = "all"):
		'''returns all objects

		type: optional parameter to filter by object type
		'''

		return self.world_objects

	def add_object(self, object):
		#set world_instance to self
		object.world = self

		self.world_objects.append(object)


	def set_objects(self, object_list):
		self.world_objects = object_list

	def add_objects(self, object_list):
		for o in object_list:
			self.add_object(o)

	def remove_all_objects(self):
		self.world_objects = []


	#update objects
	def update(self):
		self.update_objects()

		#update pheromap
		#self.phero_map = df.diffuse(self.phero_map)

	def update_objects(self):
		'''
		iterates through all objects and calls the tick-method
		'''
		for o in self.world_objects:
			o.tick(self.delta_time)


class WorldObject():
	'''
	class WorldObject has a position-vector and a type
	'''

	#this list defines the different object-types which can be later used as labels or for type-filtering
	object_types = ["ant", "pheromone"]

	def __init__(self, position, world_instance = None):
		self.position = np.array(position, dtype=float)
		self.type = ""
		self.world = world_instance

	def is_type(self, typestring):
		if self.type == typestring:
			return True
		return False

	def tick(self, delta):
		'''
		this will be overwritten by child classes
		'''
		pass

	def get_distance(self, object):
		'''returns the distance between this and another object
		
		'''
		pass






class Ant(WorldObject):
	'''
	class Ant inherits from WorldObject and additionally holds a direction vector ...
	'''

	def __init__(self, position, direction, world_instance = None):
		WorldObject.__init__(self, position, world_instance)

		#NOTE: All elements are relative to one second!

		#norm the direction to 1
		self.direction = norm_vector(np.array(direction))
		self.type = "ant"
		self.speed = 100
		self.max_speed = 200
		self.min_speed = 5
		self.length = 10
		self.center_radius = 5 * 15
		self.head_radius = 4
		self.head_angle = 100

		self.max_turn_angle = 20

	def get_weighted_collision_vector(self, object_list):

		v_sum = np.array([0,0], dtype=float)
		for o in object_list:
			try:
				#if the position is the same:
				if np.array_equal(self.position, o.position):
					v = np.array([0,0])
				else:
					v = ((self.position - o.position) / np.linalg.norm(self.position - o.position))
			except Exception, e:
				print e
				v = np.array([0,0])
			finally:
				v_sum = v_sum + v
		
		return v_sum / len(object_list)

	def get_avoiding_vector(self, collision_vector, delta):
		o_turn_angle, turn_angle, orientation = get_oriented_angle(self.direction, self.direction + collision_vector)

		#check if angle exceeds max angle
		if turn_angle > self.max_turn_angle * delta:
			print "angle is more than max!!"
			o_turn_angle = self.max_turn_angle * orientation * delta

		#rotate the vector
		new_direction = rotate_vector(self.direction, o_turn_angle)

		return norm_vector(new_direction)

	def evade(self, delta):
		#this is the main collision method

		o_in_center_range = self.world.get_objects_in_range(self.position, self.center_radius)
		o_in_top_range = self.world.get_objects_in_range_and_radius(self.position, self.direction, self.head_radius, self.head_angle)

		#if just itself is in the list
		if len(o_in_center_range + o_in_top_range) < 2:
			return;

		
		collision_vector = self.get_weighted_collision_vector(o_in_top_range + o_in_center_range)

		avoiding_vector = self.get_avoiding_vector(collision_vector, delta) 

		#print "avoiding" , avoiding_vector

		self.direction = avoiding_vector

	def tick(self, delta):
		'''
		put here all the movement logic
		'''
		self.evade(delta)
		self.position = self.position + ( self.direction * self.min_speed * delta)







class Pheromone(WorldObject):
	'''
	class Pheromone inherits from WorldObject and has strength and decay
	'''

	def __init__(self, position):
		WorldObject.__init__(self, position, world_instance = None)
		self.strength = 1
		self.decay = 0.01
		self.type = "phero"

	def tick(self, delta):
                print "strength", self.strength
                if self.strength - self.decay > 0:
                        self.strength = self.strength - self.decay
                else:
                        self.strength = 0
