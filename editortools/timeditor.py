from albow.controls import RotatableImage, Label
import pygame
import os
from albow.widget import Widget
from albow.layout import Column, Row
from albow.fields import TimeField, IntField
import math

class TimeEditor(Widget):
    # Do Not Change These Fields (unless necessary)
    ticksPerDay = 24000
    ticksPerHour = ticksPerDay / 24
    ticksPerMinute = ticksPerDay / (24 * 60)
    maxRotation = 360.04
    rotationToTick = 66.66
    
    
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
        return ((delta * 30) * (1 / 66.66))
    
    def degreesToTicks(self, deg):
        return (deg * 66.66)
    
    def ticksToDegrees(self, ticks):
        return (ticks * (1 / 66.66))
    
    def __init__(self, current_tick_time=0, **kwds):
        super(TimeEditor, self).__init__(**kwds)
        self.final = 0
        self._current_tick_time = current_tick_time
        self.original_value = current_tick_time
        self._current_tick_time += (self.ticksPerHour * 30)
        d, h, m, t = self.fromTicks(self._current_tick_time)
        self.last_pos = (None, None)
        
        self.day_input = IntField(value=d, min=1)
        
        self.rot_image = RotatableImage(image=pygame.image.load(os.path.join("toolicons", "day_night_cycle.png")))
        self.rot_image.set_angle(self.ticksToDegrees(self._current_tick_time))
        self.rot_image.mouse_drag = self.mouse_drag
        self.rot_image.mouse_up = self.mouse_up
        
        self.time_field = TimeField(value=(h, m))
        self.time_label = Label("Time of day:")
        #self._debug_ticks = Label("")
        self.add(Column((
                         Row((Label("Day: "), self.day_input)), 
                         self.rot_image, 
                         Row((self.time_label, self.time_field))
                         ))
                 )
        self.shrink_wrap()
        
    def mouse_drag(self, event):
        if self.last_pos == (None, None):
            self.last_pos = event.pos
        delta = (event.pos[0] - self.last_pos[0]) / 10
        #if self.degreesToTicks(self.rot_image.get_angle()) == self.original_value:
        #    print "Setting" 
        #    self.rot_image.set_angle(self.deltaToDegrees(delta * -1))
        #else:
        #    print "Adding"
        self.rot_image.add_angle(self.deltaToDegrees(delta))
        
        self._current_tick_time = self.degreesToTicks(self.rot_image.get_angle() * -1)
        d, h, m, t = self.fromTicks(self._current_tick_time + (self.ticksPerHour * 30))
        self.time_field.set_value((h,m))
        
        
    def mouse_up(self, event):
        self.last_pos = (None, None)