from albow.controls import RotatableImage, Label
import pygame
import os
from albow.widget import Widget
from albow.layout import Column, Row
from albow.fields import TimeField, IntField
import math
import types

class TimeEditor(Widget):
    # Do Not Change These Fields (unless necessary)
    ticksPerDay = 24000
    ticksPerHour = ticksPerDay / 24
    ticksPerMinute = ticksPerDay / (24 * 60)
    _maxRotation = 360.04
    _tickToDegree = 66.66
    _distance = 600.0
    
    
    @classmethod
    def fromTicks(cls, time):
        day = time / cls.ticksPerDay
        tick = time % cls.ticksPerDay
        hour = tick / cls.ticksPerHour
        tick %= cls.ticksPerHour
        minute = tick / cls.ticksPerMinute
        tick %= cls.ticksPerMinute

        return day, hour, minute, tick
    
    @classmethod
    def toTicks(cls, (day, hour, minute, ticks)):
        time = (day * cls.ticksPerDay) + (hour * cls.ticksPerHour) + (minute * cls.ticksPerMinute) + ticks
        return time
    
    def deltaToDegrees(self, delta):
        return ((delta * (24000 / self._distance)) * (1 / self._tickToDegree))
        #return ((delta * (24000.0 / 16000.0)) * (1.0 / 66.66))
    
    def degreesToTicks(self, deg):
        return (deg * self._tickToDegree)
    
    def ticksToDegrees(self, ticks):
        return (ticks * (1 / self._tickToDegree))
    
    def __init__(self, current_tick_time=0, **kwds):
        super(TimeEditor, self).__init__(**kwds)
        self._current_tick_time = current_tick_time
        self.original_value = current_tick_time
        self._current_tick_time += (self.ticksPerHour * 30)
        d, h, m, t = self.fromTicks(self._current_tick_time)
        self.last_pos = (None, None)
        
        self.day_input = IntField(value=d, min=1)
        
        self.rot_image = RotatableImage(
                                        image=pygame.image.load(os.path.join("toolicons", "day_night_cycle.png")),
                                        min_angle=-self._maxRotation,
                                        max_angle=0
                                        )
        #self.rot_image.set_angle(self.ticksToDegrees(self._current_tick_time))
        self.rot_image.mouse_drag = self.mouse_drag
        self.rot_image.mouse_up = self.mouse_up
        
        self.time_field = TimeField(value=(h, m))
        self._time_field_old_value = self.time_field.value
        #self._debug_ticks = Label("")
        self.add(Column((
                         Row((Label("Day: "), self.day_input)), 
                         self.rot_image, 
                         Row((Label("Time of day:"), self.time_field))
                         ))
                 )
        self.shrink_wrap()
    
    '''    
    def draw(self, surface):
        if not self.time_field.editing:
            if self._time_field_old_value != self.time_field.value:
                h, m = self.time_field.value
                ticks = self.toTicks((self.day_input.value, h, m, 0))
                self.rot_image.set_angle(self.ticksToDegrees(ticks) * -1)
                self._time_field_old_value = self.time_field.value
        #Widget.draw(self, surface)
    '''
        
    def mouse_drag(self, event):
        #METHOD #1
        if self.last_pos == (None, None):
            self.last_pos = event.pos
        delta = (event.pos[0] - self.last_pos[0])
        #print "Delta: {}".format(delta)
        #print "Degrees: {}".format(self.deltaToDegrees(delta))
        #print ""
        #if self.degreesToTicks(self.rot_image.get_angle()) == self.original_value:
        #    print "Setting" 
        #    self.rot_image.set_angle(self.deltaToDegrees(delta * -1))
        #else:
        #    print "Adding"
        self.rot_image.add_angle(self.deltaToDegrees(delta))
        
        self._current_tick_time = self.degreesToTicks(self.rot_image.get_angle() * -1)
        d, h, m, t = self.fromTicks(self._current_tick_time + (self.ticksPerHour * 30))
        self.time_field.set_value((h,m))
        self.last_pos = event.pos
        '''
        #METHOD #2
        if self.last_pos == (None, None):
            self.last_pos = event.pos
        delta = (event.pos[0] - self.last_pos[0]) / 600.0
        if delta >= 0.0:
            new_delta = max(min(delta, 0.5), 0.0)
        else:
            new_delta = max(min(delta, 0.0), -0.5)
        print "Distance: {}".format((event.pos[0] - self.last_pos[0]))
        print "Delta: {}".format(delta)
        print "New Delta: {}".format(new_delta)
        print "Ticks: {}".format(new_delta * 24000)
        print "Degrees: {}".format(new_delta * 360)
        print ""
        self.rot_image.add_angle(new_delta * 360)
        
        self._current_tick_time = new_delta * 24000
        d, h, m, t = self.fromTicks(self._current_tick_time + (self.ticksPerHour * 30))
        self.time_field.set_value((h,m))
        '''
        
        
    def mouse_up(self, event):
        self.last_pos = (None, None)
        
    def get_value(self):
        return None