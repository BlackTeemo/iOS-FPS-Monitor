
from ios_device import py_ios_device

channels = py_ios_device.get_channel()
print(channels)


import time

from ios_device import py_ios_device


def callback(rep):
    print(rep)


channel = py_ios_device.start_get_network(callback=callback)
time.sleep(5)
py_ios_device.stop_get_network(channel)
channel.stop()

