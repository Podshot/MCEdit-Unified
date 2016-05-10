from albow.controls import RotatableImage, Label
import pygame
import os
from albow.widget import Widget
from albow.layout import Column, Row
from albow.fields import TimeField, IntField
import math
import types

class ModifiedTimeField(TimeField):
    
    _callback = None
    
    def __init__(self, callback=None, **kwds):
        super(ModifiedTimeField, self).__init__(**kwds)
        self._callback = callback
        
    def __setattr__(self, *args, **kwargs):
        if  self._callback and args[0] == "value":
            self._callback(args[1])
        return TimeField.__setattr__(self, *args, **kwargs)

class TimeEditor(Widget):
    # Do Not Change These Fields (unless necessary)
    ticksPerDay = 24000
    ticksPerHour = ticksPerDay / 24
    ticksPerMinute = ticksPerDay / (24 * 60)
    _maxRotation = 360.04
    _tickToDegree = 66.66
    _distance = 600.0
    _time_adjustment = (ticksPerHour * 30)
    
    
    # -- Conversion Methods -- #
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
    
    def degreesToTicks(self, deg):
        return (deg * self._tickToDegree)
    
    def ticksToDegrees(self, ticks):
        return (ticks * (1 / self._tickToDegree))
    
    def doTimeAdjustment(self, ticks):
        return (ticks + self._time_adjustment)
    
    def undoTimeAdjustment(self, ticks):
        return (ticks - self._time_adjustment)
    
    # -- Special Callback -- #
    def _timeFieldCallback(self, (h, m)):
        ticks = self.undoTimeAdjustment(self.toTicks((1, h, m, 0)))
        deg = 0
        if ticks > 0:
            deg = self.ticksToDegrees(self.undoTimeAdjustment(self.toTicks((1, h, m, 0))))
        else:
            deg = self.ticksToDegrees(24000 + ticks)
        self.rot_image.set_angle(0)
        self.rot_image.add_angle(deg)
        
        self._current_tick_time = max(min(self.degreesToTicks(self.rot_image.get_angle() * -1), 24000.0), 0)
        self._current_time = self.fromTicks(self.doTimeAdjustment(self._current_tick_time))
    
    def __init__(self, current_tick_time=0, **kwds):
        super(TimeEditor, self).__init__(**kwds)
        
        self._current_tick_time = current_tick_time
        self._current_time = self.fromTicks(self.doTimeAdjustment(self._current_tick_time))
        
        self.__original_value = current_tick_time
        self.__original_time = self._current_time
        
        self.last_pos = (None, None)
        
        self.day_input = IntField(value=self.__original_time[0], min=1)
        
        __deg = self.ticksToDegrees(current_tick_time)
        
        self.rot_image = RotatableImage(
                                        image=pygame.image.load(os.path.join("toolicons", "day_night_cycle.png")),
                                        min_angle=-self._maxRotation,
                                        max_angle=0,
                                        angle=__deg
                                        )
        self.rot_image.mouse_drag = self.mouse_drag
        self.rot_image.mouse_up = self.mouse_up
        self.rot_image.tooltipText = "Left-Click and drag to the left or the right"
        
        self.time_field = ModifiedTimeField(
                                            value=(self.__original_time[1], self.__original_time[2]),
                                            callback=self._timeFieldCallback
                                            )
        __time_field_old_value = self.time_field.value
        self.add(Column((
                         Row((Label("Day: "), self.day_input)), 
                         self.rot_image, 
                         Row((Label("Time of day:"), self.time_field))
                         ))
                 )
        self.shrink_wrap()
        
    
    def get_time_value(self):     
        if self.time_field.editing:
            self._timeFieldCallback(self.time_field.value)
        rot_ticks = max(min(self.degreesToTicks(self.rot_image.get_angle() * -1), 24000.0), 0)
        return (((self.day_input.value * self.ticksPerDay) + rot_ticks) - self.ticksPerDay)
    
    def get_daytime_value(self):
        if self.time_field.editing:
            self._timeFieldCallback(self.time_field.value)
        ticks = max(min(self.degreesToTicks(self.rot_image.get_angle() * -1), 24000), 0)
        return ticks
    
    def mouse_down(self, event):
        if "tooltipText" in self.rot_image.__dict__:
            del self.rot_image.tooltipText
        
    def mouse_drag(self, event):
        if self.last_pos == (None, None):
            self.last_pos = event.pos
        delta = (event.pos[0] - self.last_pos[0])
        
        self.rot_image.add_angle(self.deltaToDegrees(delta))
        
        self._current_tick_time = max(min(self.degreesToTicks(self.rot_image.get_angle() * -1), 24000.0), 0)
        self._current_time = self.fromTicks(self.doTimeAdjustment(self._current_tick_time))
        self.time_field.set_value((self._current_time[1], self._current_time[2]))
        self.last_pos = event.pos      
        
    def mouse_up(self, event):
        self.last_pos = (None, None)