# arm_and_takeoff.py
import time
from pymavlink import mavutil

# 1. Connect
master = mavutil.mavlink_connection('udp:127.0.0.1:14550')
master.wait_heartbeat()
print("Connected.")

# 2. Set mode to GUIDED
# We need to be in GUIDED mode to send direct position commands.
print("Setting mode to GUIDED...")
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_DO_SET_MODE,
    0,
    1,  # activate custom mode param1 set to 1 to be able to set custom mode
    4, 0, 0, 0, 0, 0 # 4 = GUIDED
)

# 3. Arm the drone
# Arming means activating the motors.
print("Arming motors...")
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0,
    1,  # 1 = Arm
    0, 0, 0, 0, 0, 0
)

# Give it a moment to arm
time.sleep(2)
print("Armed. Waiting for stabilization...")

# 4. Takeoff to 5 meters
# We send a TAKEOFF command.
print("Taking off to 5 meters...")
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
    0,
    0,  # Minimum pitch (ignored)
    0, 0, 0, 0,  # Reserved
    5 , 0  # Altitude in meters
)

print("Command sent. Watch the SITL map window!")
print("The script will keep running for 15 seconds.")
time.sleep(15)
print("Script done. You can close the SITL window now.")