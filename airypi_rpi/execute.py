import RPi.GPIO as GPIO

import serial, smbus, spidev
import sys
import json

object_map = {}

def cleanup():
    object_map = {}
    GPIO.cleanup()

def json_unpack(value):
    if isinstance(value, dict):
        if value['type'] == 'bytearray':
            return bytearray(value['data'])
    return value

def json_pack(data):
    if data.__class__ == bytearray:
        return {'type':'bytes', 'data': str(data)}
    return data

def call(module, m):
    obj = None

    if 'object' in m and m['object'] in object_map:
        obj = object_map[m['object']]
    elif 'class' in m:
        obj = getattr(module, m['class'])
    else:
        obj = module

    if 'property' in m:
        return getattr(obj, m['property'])
    elif 'setter' in m:
        return setattr(obj, m['setter'], m['value'])
    else:
        args = m['args']
        kwargs = m['kwargs']

        args = [json_unpack(arg) for arg in args]
        kwargs = {key:json_unpack(kwargs[key]) for (key, value) in kwargs.items()}


        if m['func'] == '__init__':
            cls = getattr(module, m['class'])
            object_map[m['object']] = cls(*args, **kwargs)
            return None

        if m['func'] == '__del__':
            del object_map[m['object']]
            return None

        func = getattr(obj, m['func'])
        return func(*args, **kwargs)


def gpio_exec(login, m):    
    module = GPIO
    retval = None

    if 'func' in m and 'extra' in m:
        if m['func'] == 'add_event_detect' or m['func'] == 'add_event_callback':
            key = m['extra']

            def gpio_callback():
                login.s.post(login.app_url + '/run/event', data = json.dumps({'type': 'gpio_callback', 'key': key}))
            m['kwargs']['callback'] = gpio_callback
        
    retval = call(module, m)
            
    return json_pack(retval)

def serial_exec(login, m):
    module = serial
    return json_pack(call(module, m))

def smbus_exec(login, m):
    module = smbus
    return json_pack(call(module, m))

def spidev_exec(login, m):
    module = spidev
    return json_pack(call(module, m))

def permitted_modules():
    return {'RPi.GPIO' : gpio_exec, 'serial' : serial_exec, 'smbus': smbus_exec, 'spidev': spidev_exec}