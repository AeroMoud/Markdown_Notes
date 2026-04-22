# drone_connect.py
import time
from pymavlink import mavutil

# Use the WSL IP address that MAVProxy shows
# In your case: 172.17.192.1
master = mavutil.mavlink_connection('udp:127.0.0.1:14550')

print("Waiting for heartbeat...")
master.wait_heartbeat()
print("Heartbeat received! Connection successful.")