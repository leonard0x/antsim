from __future__ import division
import Settings as settings
from World import *
from Ant import *
import VispyView as MainView
from Storage import *

import time
import numpy as np
import pyglet
import sys

import copy

import Global as g

import yaml

from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from watchdog.events import FileSystemEventHandler

config = yaml.load(open("config.yml"))


class Simulator(FileSystemEventHandler):
    '''
    This class simulates the behavior of worldobjects over time
    '''

    def __init__(self):
        self.world = World()
        self.avg_fps = np.zeros((200))
        self.avg_fps_index = 0

    def on_modified(self, event):
        if event.src_path == "./config.yml":
            config = yaml.load(open("config.yml"))
            antcount = 0

            self.world.delta_time = config["delta"]

            #update all ants
            for wo in self.world.world_objects:
                if isinstance(wo, Ant):
                    antcount += 1
                    wo.max_speed = config["ant"]["max_speed"]
                    wo.min_speed = config["ant"]["min_speed"]
                    wo.max_turn_angle = config["ant"]["max_turn_angle"]
                    wo.acceleration = config["ant"]["acceleration"]

                    wo.length = config["ant"]["length"]
                    wo.center_radius = config["ant"]["center_radius"]
                    wo.head_radius = config["ant"]["head_radius"]
                    wo.head_angle = config["ant"]["head_angle"]

                    wo.signal_noise = config["ant"]["angle_noise_error"]

                    wo.phero_speed_down_treshold = config["ant"]["phero_speed_down_treshold"]

            print "changed params of " + str(antcount) + " ants."

    def simulate_steps(self, n = 1):
        '''
        this function simulates the behavior of worldobjects for one step and returns a list of objects
        optional param n is the number of steps to simulate
        '''

        t_start = time.clock()

        for x in range(0,n):
            #update the world model
            self.world.tick()

    def record(self, filename, seconds, step = 1, buffer_size = 100):

        # new storage object
        groups = ["ant", "phero"]
        shapes = [(3, len(self.world.world_objects), 2), self.world.phero_map.phero_map.shape]
        dtypes = [np.float, np.float32]
        sto = g.storage = Storage(filename, groups, shapes, dtypes, buffer_size)

        #loop increment for recorded steps
        record_count = 0

        print "#start recording..."

        #number of steps to simulate
        n = int(seconds / self.world.delta_time)
        for x in range(n):
	    start = time.clock()
            self.world.tick()

            if x % step == 0:
                sto.set("ant", record_count, self.world.world_objects_to_numpy())
                sto.set("phero", record_count, self.world.phero_map.phero_map)

                record_count += 1


            fps = int(1 / (time.clock() - start))

            if self.avg_fps[0] == 0:
                self.avg_fps.fill(fps)
            else:
                self.avg_fps[self.avg_fps_index] = fps
                if self.avg_fps_index + 1 > len(self.avg_fps) - 1:
                    self.avg_fps_index = 0
                else:
                    self.avg_fps_index += 1

            self.print_progress("#simulating frames... ", x, n, np.average(self.avg_fps))


        print "#simulated " + str(n) + " frames."
        print "#recorded " + str(record_count) + " frames."

        sto.keyval_set("version", "0.4")
        sto.keyval_set("frame_count", record_count)
        sto.keyval_set("record_step", step)

        sto.keyval_set("world_dimensions", self.world.dimensions)
        sto.keyval_set("world_delta_time", self.world.delta_time)

        sto.keyval_set("phero_resolution", self.world.phero_map.resolution)
        sto.keyval_set("ant_count", self.world.get_ant_count() )

        # write remaining changes to disk
        sto.store()

        print "#all done!"

    def print_progress(self, label, x, max, fps):
        perc = (x / max)
        time_left = (max - x) / (fps * 60)
        print "\r" + label + "{:.1%}".format(perc) + " ~" + "{:.1f}".format(time_left) + "m" + " " + "{:.0f}".format(fps) + "fps",
        sys.stdout.flush()




def create_random_objects(n, dimension):
    '''
    returns a list of n antobjects with random position and direction vectors
    '''

    #returns n objects with position between (10,10) and (390,390)
    return [Ant( np.random.uniform(-1,1, (2)) * dimension, np.random.uniform(-1,1, (2)) ) for a in range(0,n)]

def setup(n = 100):
    '''
    this is the startup function which initializes a Simulator-Object and loads the settings file
    n = number of elements to create
    '''

    #creates a simulator instance
    s = Simulator()

    #add some ants
    s.world.add_objects( create_random_objects(n, s.world.dimensions) )

    return s

if __name__ == "__main__":

    #INPUT DEFAULTS
    live = False
    filename = "record.hdf5"

    view = False
    view_fps = 40

    record = False
    record_time = 5.
    record_step = 10
    ant_count = 20

    buffer_size = 100

    i=1
    while i < len(sys.argv):
        if sys.argv[i] == "-v":
            view = True
        elif sys.argv[i] == "-vfps":
            view_fps = int(sys.argv[i+1])
            i += 1
        elif sys.argv[i] == "-r":
            record = True
        elif sys.argv[i] == "-f":
            filename = sys.argv[i+1]
            i += 1
        elif sys.argv[i] == "-rt":
            record_time = float(sys.argv[i+1])
            i += 1
        elif sys.argv[i] == "-rs":
            record_step = int(sys.argv[i+1])
            i += 1
        elif sys.argv[i] == "-ac":
            ant_count = int(sys.argv[i+1])
            i += 1
        elif sys.argv[i] == "-bs":
            buffer_size = int(sys.argv[i+1])
            i += 1
        elif sys.argv[i] == "-live":
            live = True
            g.live = live
        else:
            print("invalid parameter")

        i += 1

    if record:
        g.simulator = setup(ant_count)

        if not live:
            g.simulator.record(filename, record_time, record_step, buffer_size)

    if view:
        if not live:
            g.storage = Storage(filename, buffer_size=buffer_size)
        if not record and live:
            g.simulator = setup(ant_count)
            event_handler = g.simulator
            observer = Observer()
            observer.schedule(event_handler, path='.', recursive=False)
            observer.start()


        MainView.start_view(view_fps)

        if not record and live:
            print "good bye"
            observer.stop()
            observer.join()
