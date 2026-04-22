# drone_connect.py
import time
from pymavlink import mavutil

# 1. Start a connection
# We are connecting to the SITL we started in Step 4.
# 'tcp:127.0.0.1:5760' means connect to the same computer (127.0.0.1) on port 5760.
print("Attempting to connect to SITL...")
master = mavutil.mavlink_connection('udp:127.0.0.1:14550')

# 2. Wait for the first heartbeat
# This tells us the drone is ready.
print("Waiting for heartbeat...")
master.wait_heartbeat()
print("Heartbeat received! Connection successful.")

# 3. Print the type of drone we are connected to
# The MAVLink protocol has IDs for vehicle types.
# 2 = Fixed wing, 3 = Quadrotor (Copter)
print(f"Vehicle type: {master.target_system}")

# 4. Keep reading messages for 10 seconds
print("Reading messages for 10 seconds...")
start_time = time.time()
while time.time() - start_time < 10:
    # Try to receive a message
    msg = master.recv_match(blocking=False)
    if msg:
        # Print the name of the message (e.g., SYS_STATUS, ATTITUDE, GPS_RAW_INT)
        print(f"Received: {msg.get_type()}")
    time.sleep(0.1)

print("Script finished.")