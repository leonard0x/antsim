# antsim

antsim is a multi agent simulation, which tries to emulate the trailfinding behavior of ants, which interact via scent and tactile sensors.

## Usage

Python Simulator.py
 - r (record)
 - rt (time in seconds to record)
 - rs (record every nth step)
 - f (filename)
 - ac (ant count)
 - bs (buffer size) the number of simulated frames which will be in ram at a time

 - v (view)
 - live (shows the data right away)

## Example
	Python Simulator.py -r -v -rt 60 -rs 5 -f test.hdf5

	Simulates for 60 seconds, saves every 5th step to file test.hdf5 and shows it afterwards

## Example 2	
	Python Simulator.py -live -v -ac 100
	
	You can also simulate live with the command. this wont save to a file, but display the simulated data right away. 
