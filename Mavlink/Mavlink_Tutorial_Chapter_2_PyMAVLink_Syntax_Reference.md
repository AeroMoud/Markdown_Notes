# 🚁 PyMAVLink Syntax & Patterns — Complete Reference Tutorial

## 📋 Table of Contents

- [What is PyMAVLink?](#-what-is-pymavlink)
- [Why it matters in autonomous vehicles](#-why-it-matters-in-autonomous-vehicles)
- [Installation](#-installation)
- [Pattern 1 — Creating Connections](#-pattern-1--creating-connections)
- [Pattern 2 — Heartbeat & Handshake](#-pattern-2--heartbeat--handshake)
- [Pattern 3 — Sending Commands](#-pattern-3--sending-commands)
- [Pattern 4 — Receiving Messages](#-pattern-4--receiving-messages)
- [Pattern 5 — Accessing Message Fields](#-pattern-5--accessing-message-fields)
- [Pattern 6 — MAVLink Constants](#-pattern-6--mavlink-constants)
- [Pattern 7 — Setting Flight Mode](#-pattern-7--setting-flight-mode)
- [Pattern 8 — Arming and Disarming](#-pattern-8--arming-and-disarming)
- [Pattern 9 — Takeoff and Landing](#-pattern-9--takeoff-and-landing)
- [Pattern 10 — Mission Upload Handshake](#-pattern-10--mission-upload-handshake)
- [Pattern 11 — Reading Telemetry Streams](#-pattern-11--reading-telemetry-streams)
- [Pattern 12 — Parameter Read and Write](#-pattern-12--parameter-read-and-write)
- [Pattern 13 — Requesting Specific Message Streams](#-pattern-13--requesting-specific-message-streams)
- [Pattern 14 — Position Commands (SET_POSITION_TARGET)](#-pattern-14--position-commands)
- [Pattern 15 — Geofence Configuration](#-pattern-15--geofence-configuration)
- [Pattern 16 — Error Handling and Timeouts](#-pattern-16--error-handling-and-timeouts)
- [Quick Reference Tables](#-quick-reference-tables)
- [Common Mistakes Beginners Make](#-common-mistakes-beginners-make)
- [Recap — Key Takeaways](#-recap--key-takeaways)
- [Check Yourself](#-check-yourself)

---

## 🧠 What is PyMAVLink?

**PyMAVLink** is the official Python library that lets you communicate with drones using the **MAVLink protocol**. Think of it as Python's translator for the drone's language — it converts your Python function calls into the exact binary packets the drone understands, and parses incoming packets back into readable Python objects.

Without PyMAVLink, you would need to manually construct binary packets, calculate checksums, and handle the low-level communication yourself. PyMAVLink abstracts all of that away so you can focus on *what* you want the drone to do.

The library is used in ground control stations, companion computers, autonomous mission scripts, and testing tools. It is the same underlying protocol used by tools like MAVProxy, Mission Planner, and QGroundControl under the hood.

---

## 🚗 Why it matters in autonomous vehicles

In real-world autonomous drone systems — like delivery drones, inspection UAVs, or aerial mapping platforms — the flight computer (running ArduPilot or PX4) needs to receive commands and send back sensor data. PyMAVLink is what the *companion computer* (a Raspberry Pi, Jetson Nano, or laptop) uses to talk to the flight controller.

Companies like **Skydio**, **Zipline**, and **AgEagle** use MAVLink-based communication in their architectures. Autoware and ROS-based drone stacks also interface with flight controllers through MAVLink bridges.

If you get the syntax wrong, the drone might not receive your command, arm when it shouldn't, fail to upload the mission, or fly to the wrong coordinates. Understanding the exact calling patterns is therefore safety-critical knowledge, not just a coding detail.

---

## 📦 Installation

```bash
# Install the core library
pip install pymavlink --user

# Also install MAVProxy if you want a ground control terminal
pip install mavproxy --user

# Verify installation
python3 -c "from pymavlink import mavutil; print('pymavlink OK')"
```

---

## 🔌 Pattern 1 — Creating Connections

This is always the **first line** in any PyMAVLink script. You create a `master` connection object that represents your link to the drone.

### Connection string format

```
<protocol>:<address>:<port>
```

### All common connection strings

```python
from pymavlink import mavutil

# ─────────────────────────────────────────────────────────────
# TCP — most reliable for SITL simulation
# ─────────────────────────────────────────────────────────────
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')

# ─────────────────────────────────────────────────────────────
# UDP — used for real telemetry radios and MAVProxy outputs
# ─────────────────────────────────────────────────────────────
master = mavutil.mavlink_connection('udp:127.0.0.1:14550')

# For WSL: use the WSL network IP instead of localhost
master = mavutil.mavlink_connection('udp:172.17.192.1:14550')

# ─────────────────────────────────────────────────────────────
# Serial — for real drones connected via USB or UART
# ─────────────────────────────────────────────────────────────
master = mavutil.mavlink_connection('/dev/ttyUSB0', baud=57600)  # USB telemetry radio
master = mavutil.mavlink_connection('/dev/ttyACM0', baud=115200) # USB direct to FC
master = mavutil.mavlink_connection('/dev/ttyS0', baud=57600)    # UART on companion computer

# ─────────────────────────────────────────────────────────────
# Windows serial port
# ─────────────────────────────────────────────────────────────
master = mavutil.mavlink_connection('COM3', baud=57600)
```

### Connection options table

| Scenario | Protocol | Address | Port |
|---|---|---|---|
| Python + SITL, same machine | `tcp` | `127.0.0.1` | `5760` |
| Python in Windows, SITL in WSL | `udp` | WSL IP (172.x.x.x) | `14550` |
| Real drone via telemetry radio | Serial | `/dev/ttyUSB0` | N/A |
| Real drone via USB | Serial | `/dev/ttyACM0` | N/A |
| MAVProxy UDP output | `udp` | `127.0.0.1` | `14550` |

---

## 💓 Pattern 2 — Heartbeat & Handshake

After creating the connection, you **must** wait for the first heartbeat before sending any commands. This confirms the link is alive and gives you the drone's system and component IDs.

```python
import time
from pymavlink import mavutil

# Create connection
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')

# Always give the connection a moment to establish before requesting heartbeat
time.sleep(1)

# Block until a heartbeat message arrives — timeout after 10 seconds
print("Waiting for heartbeat...")
master.wait_heartbeat()
print("Heartbeat received!")

# After wait_heartbeat(), these are now populated:
print(f"System ID    : {master.target_system}")    # Usually 1
print(f"Component ID : {master.target_component}") # Usually 1
```

### Manually inspecting a heartbeat

```python
# recv_match blocks until a HEARTBEAT arrives
hb = master.recv_match(type='HEARTBEAT', blocking=True, timeout=5)

if hb:
    # MAV_TYPE: what kind of vehicle (2 = quadrotor, 1 = fixed wing, etc.)
    print(f"Vehicle type     : {hb.type}")

    # MAV_AUTOPILOT: which firmware (3 = ArduPilot, 12 = PX4, etc.)
    print(f"Autopilot type   : {hb.autopilot}")

    # MAV_STATE: current system state (3 = STANDBY, 4 = ACTIVE, etc.)
    print(f"System state     : {hb.system_status}")

    # base_mode is a bitmask — bit 7 (value 128) = SAFETY_ARMED
    is_armed = bool(hb.base_mode & 128)
    print(f"Armed            : {is_armed}")
else:
    print("No heartbeat received within timeout!")
```

---

## 📤 Pattern 3 — Sending Commands

This is the core pattern for sending flight commands to the drone. Almost all commands go through `command_long_send()`.

### The full signature

```python
master.mav.command_long_send(
    target_system,    # int: which drone (master.target_system)
    target_component, # int: which part of drone (master.target_component)
    command,          # int: the MAV_CMD constant (e.g., 400 for ARM)
    confirmation,     # int: 0 = first send, 1+ = retries
    param1,           # float: command-specific parameter 1
    param2,           # float: command-specific parameter 2
    param3,           # float: command-specific parameter 3
    param4,           # float: command-specific parameter 4
    param5,           # float: command-specific parameter 5
    param6,           # float: command-specific parameter 6
    param7            # float: command-specific parameter 7
)
```

### The 7 parameters rule

Every `command_long_send` **always** takes exactly 7 command-specific parameters. Unused ones must be `0`. This is non-negotiable — missing a parameter causes a Python error.

```
┌──────────────────────────────────────────────────┐
│  command_long_send(sys, comp, cmd, conf,          │
│                    p1, p2, p3, p4, p5, p6, p7)   │
│                    ↑──────────── 7 params ──────↑ │
└──────────────────────────────────────────────────┘
```

### Checking if a command was accepted

After sending a command, you should listen for a `COMMAND_ACK` message to confirm the drone accepted it.

```python
# Send any command
master.mav.command_long_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0,          # confirmation: 0 = first attempt
    1,          # param1: 1 = ARM
    0, 0, 0, 0, 0, 0  # params 2-7: unused
)

# Wait for ACK — the drone replies with COMMAND_ACK to confirm
ack = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)

if ack:
    if ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
        print("✅ Command accepted!")
    else:
        # Result codes:
        # 0 = ACCEPTED
        # 1 = TEMPORARILY_REJECTED
        # 2 = DENIED
        # 3 = UNSUPPORTED
        # 4 = FAILED
        # 5 = IN_PROGRESS
        print(f"❌ Command rejected. Result code: {ack.result}")
else:
    print("⚠️ No ACK received within timeout.")
```

---

## 📥 Pattern 4 — Receiving Messages

This is how you **listen** for messages from the drone. You use `recv_match()` to wait for specific message types.

### `recv_match()` full signature

```python
msg = master.recv_match(
    type=None,        # str or list: message type(s) to filter for
    blocking=True,    # bool: True = wait; False = return immediately
    timeout=None      # float: seconds to wait (only matters when blocking=True)
)
```

### Receiving a single message type

```python
# Block and wait up to 5 seconds for a GPS message
gps = master.recv_match(type='GPS_RAW_INT', blocking=True, timeout=5)

if gps:
    # Coordinates are stored as integers (multiply by 1e-7 to get degrees)
    lat = gps.lat / 1e7
    lon = gps.lon / 1e7
    alt = gps.alt / 1000  # Altitude is in millimetres → convert to metres
    print(f"Position: {lat:.6f}, {lon:.6f} at {alt:.1f}m")
else:
    print("No GPS message received.")
```

### Receiving any one of multiple message types

```python
# Wait for whichever of these arrives first
msg = master.recv_match(
    type=['MISSION_REQUEST_INT', 'MISSION_REQUEST', 'MISSION_ACK'],
    blocking=True,
    timeout=5
)

if msg:
    msg_type = msg.get_type()  # Find out which one arrived
    print(f"Received: {msg_type}")
else:
    print("Timeout — no message received.")
```

### Non-blocking receive (polling)

```python
import time

# Continuously poll for messages without blocking
start = time.time()
while time.time() - start < 10:  # Run for 10 seconds

    msg = master.recv_match(blocking=False)  # Returns None immediately if no message

    if msg is None:
        time.sleep(0.01)  # Small sleep to avoid 100% CPU usage
        continue

    msg_type = msg.get_type()

    if msg_type == 'HEARTBEAT':
        print("💓 Heartbeat")
    elif msg_type == 'ATTITUDE':
        print(f"Roll: {msg.roll:.2f} rad, Pitch: {msg.pitch:.2f} rad")
    elif msg_type == 'GPS_RAW_INT':
        print(f"GPS fix type: {msg.fix_type}")
```

### Blocking vs non-blocking comparison

| | `blocking=True` | `blocking=False` |
|---|---|---|
| **Behaviour** | Waits until message arrives | Returns immediately |
| **Return if no message** | Returns `None` after timeout | Returns `None` right away |
| **Use case** | Waiting for a specific event | Continuous polling loop |
| **CPU usage** | Low (thread sleeps) | High (need manual `time.sleep`) |

---

## 🔍 Pattern 5 — Accessing Message Fields

Once you have a message object, you access its data as **attributes** (like `msg.lat` not `msg['lat']`).

### Common messages and their fields

```python
# ─── HEARTBEAT ───────────────────────────────────────────────
hb = master.recv_match(type='HEARTBEAT', blocking=True)
hb.type             # MAV_TYPE: vehicle type number
hb.autopilot        # MAV_AUTOPILOT: firmware type number
hb.base_mode        # Bitmask of mode flags
hb.custom_mode      # ArduPilot-specific mode number
hb.system_status    # MAV_STATE: current health of system

# ─── GPS_RAW_INT ─────────────────────────────────────────────
gps = master.recv_match(type='GPS_RAW_INT', blocking=True)
gps.lat             # Latitude  × 1e7 (divide by 1e7 to get degrees)
gps.lon             # Longitude × 1e7
gps.alt             # Altitude in millimetres above MSL
gps.fix_type        # 0=no fix, 2=2D, 3=3D
gps.satellites_visible  # Number of satellites

# ─── ATTITUDE ────────────────────────────────────────────────
att = master.recv_match(type='ATTITUDE', blocking=True)
att.roll            # Radians (multiply by 180/pi for degrees)
att.pitch           # Radians
att.yaw             # Radians
att.rollspeed       # Radians per second
att.pitchspeed      # Radians per second
att.yawspeed        # Radians per second

# ─── GLOBAL_POSITION_INT ─────────────────────────────────────
# This is EKF-fused data — more accurate than GPS_RAW_INT
pos = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
pos.lat             # Latitude  × 1e7
pos.lon             # Longitude × 1e7
pos.alt             # Altitude in mm above MSL
pos.relative_alt    # Altitude in mm above home (takeoff point)
pos.vx              # X velocity in cm/s
pos.vy              # Y velocity in cm/s
pos.vz              # Z velocity in cm/s (positive = down)
pos.hdg             # Heading in centidegrees (divide by 100 for degrees)

# ─── SYS_STATUS ──────────────────────────────────────────────
sys = master.recv_match(type='SYS_STATUS', blocking=True)
sys.voltage_battery     # Battery voltage in millivolts
sys.current_battery     # Current in 10s of milliamps (-1 if not measured)
sys.battery_remaining   # Remaining battery % (0-100, -1 if unknown)
sys.load                # CPU load as % * 10 (e.g., 250 = 25.0%)

# ─── VFR_HUD ─────────────────────────────────────────────────
hud = master.recv_match(type='VFR_HUD', blocking=True)
hud.airspeed        # m/s
hud.groundspeed     # m/s
hud.heading         # 0-359 degrees
hud.throttle        # 0-100 percent
hud.alt             # metres above MSL (float)
hud.climb           # m/s (positive = climbing)

# ─── COMMAND_ACK ─────────────────────────────────────────────
ack = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
ack.command         # Which command this ACK is for (e.g., 400 = ARM)
ack.result          # MAV_RESULT: 0 = accepted, 1-5 = various failures

# ─── MISSION_CURRENT ─────────────────────────────────────────
mc = master.recv_match(type='MISSION_CURRENT', blocking=True)
mc.seq              # Index of the currently active waypoint

# ─── STATUSTEXT ──────────────────────────────────────────────
# Human-readable status messages from the drone
st = master.recv_match(type='STATUSTEXT', blocking=True)
st.severity         # 0=EMERGENCY, 4=WARNING, 6=INFO
st.text             # String message from autopilot
```

### get_type() — identify which message you received

```python
# When you receive any message without filtering, use get_type()
msg = master.recv_match(blocking=True, timeout=1)

if msg:
    msg_type = msg.get_type()  # Returns a string like 'HEARTBEAT', 'GPS_RAW_INT', etc.

    if msg_type == 'HEARTBEAT':
        print("Got heartbeat")
    elif msg_type == 'ATTITUDE':
        print(f"Yaw = {msg.yaw * 180 / 3.14159:.1f}°")
```

---

## 📚 Pattern 6 — MAVLink Constants

Constants are named values that represent numbers. Using them makes code readable and avoids magic numbers.

### How to access constants

```python
from pymavlink import mavutil

# All constants are accessed through:
mavutil.mavlink.<CONSTANT_NAME>

# Examples:
mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM   # = 400
mavutil.mavlink.MAV_CMD_NAV_TAKEOFF            # = 22
mavutil.mavlink.MAV_CMD_NAV_LAND               # = 21
mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH   # = 20
mavutil.mavlink.MAV_CMD_NAV_WAYPOINT           # = 16
mavutil.mavlink.MAV_CMD_DO_SET_MODE            # = 176
mavutil.mavlink.MAV_RESULT_ACCEPTED            # = 0
mavutil.mavlink.MAV_MISSION_ACCEPTED           # = 0
mavutil.mavlink.MAV_FRAME_GLOBAL               # = 0
mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT  # = 3
mavutil.mavlink.MAV_MISSION_TYPE_MISSION       # = 0
```

### Look up a constant's numeric value

```python
# You can always print a constant to see the number it represents
print(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF)  # Output: 22
print(mavutil.mavlink.MAV_RESULT_ACCEPTED)  # Output: 0
```

### Search for constants interactively

```python
# In a Python shell — find all constants related to MISSION
from pymavlink.dialects.v20 import ardupilotmega as mavlink
mission_consts = [attr for attr in dir(mavlink) if 'MISSION' in attr]
print(mission_consts)
```

### MAV_CMD reference table

| Constant | Value | Description |
|---|---|---|
| `MAV_CMD_NAV_WAYPOINT` | 16 | Fly to a GPS waypoint |
| `MAV_CMD_NAV_RETURN_TO_LAUNCH` | 20 | Go back to launch point |
| `MAV_CMD_NAV_LAND` | 21 | Land at current location |
| `MAV_CMD_NAV_TAKEOFF` | 22 | Takeoff to altitude |
| `MAV_CMD_DO_SET_MODE` | 176 | Change flight mode |
| `MAV_CMD_COMPONENT_ARM_DISARM` | 400 | Arm or disarm motors |
| `MAV_CMD_REQUEST_MESSAGE` | 512 | Request a specific message |
| `MAV_CMD_SET_MESSAGE_INTERVAL` | 511 | Set message stream rate |
| `MAV_CMD_DO_FENCE_ENABLE` | 207 | Enable/disable geofence |

---

## ✈️ Pattern 7 — Setting Flight Mode

You must set the flight mode to **GUIDED** before arming and executing autonomous commands. Without GUIDED mode, commands like takeoff are ignored.

### Method 1: Using MAV_CMD_DO_SET_MODE (recommended)

```python
import time
from pymavlink import mavutil

master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
master.wait_heartbeat()

# Set GUIDED mode
# base_mode = 1 means GUIDED in ArduPilot's flag system
# custom_mode = 4 is ArduPilot's internal number for GUIDED
master.mav.command_long_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_CMD_DO_SET_MODE,
    0,
    1,   # param1: base_mode = 1 (MAV_MODE_FLAG_CUSTOM_MODE_ENABLED)
    4,   # param2: custom_mode = 4 (ArduCopter GUIDED = 4)
    0, 0, 0, 0, 0  # params 3-7: unused
)
time.sleep(1)
print("GUIDED mode set")
```

### Method 2: Using set_mode() helper

```python
# PyMAVLink has a built-in helper for setting modes by name
master.set_mode('GUIDED')

# Other valid mode names for ArduCopter:
# 'STABILIZE', 'ALT_HOLD', 'LOITER', 'AUTO', 'RTL', 'LAND', 'GUIDED'
```

### ArduCopter mode numbers (custom_mode values)

| Mode Name | custom_mode value |
|---|---|
| STABILIZE | 0 |
| ACRO | 1 |
| ALT_HOLD | 2 |
| AUTO | 3 |
| GUIDED | 4 |
| LOITER | 5 |
| RTL | 6 |
| CIRCLE | 7 |
| LAND | 9 |
| DRIFT | 11 |
| POSHOLD | 16 |
| BRAKE | 17 |
| THROW | 18 |

---

## ⚙️ Pattern 8 — Arming and Disarming

Motors must be armed before the drone can fly. Always set GUIDED mode first.

### Arm

```python
def arm_drone(master, force=False):
    """
    Arm the drone's motors.
    force=True bypasses safety checks (simulation use only — dangerous on real drone).
    """
    force_value = 21196 if force else 0  # 21196 is ArduPilot's force-arm magic number

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1,            # param1: 1 = ARM (0 = DISARM)
        force_value,  # param2: 0 = normal, 21196 = force bypass safety checks
        0, 0, 0, 0, 0 # params 3-7: unused
    )

    # Wait for confirmation
    ack = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
    if ack and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
        print("✅ Armed!")
        return True
    else:
        print(f"❌ Arm failed. Result: {ack.result if ack else 'no ACK'}")
        return False
```

### Disarm

```python
def disarm_drone(master):
    """Disarm the drone's motors."""
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        0,            # param1: 0 = DISARM
        0, 0, 0, 0, 0, 0
    )
    print("Disarm command sent.")
```

### Wait for arming to complete by watching heartbeat

```python
import time

def wait_for_arm(master, timeout=15):
    """
    Block until the drone's heartbeat shows it is armed.
    Returns True if armed within timeout, False otherwise.
    """
    start = time.time()
    while time.time() - start < timeout:
        hb = master.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
        if hb:
            # Bit 7 of base_mode (value 128) = SAFETY_ARMED flag
            if hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
                print("✅ Drone is armed (confirmed via heartbeat)")
                return True
    print("❌ Arm confirmation timed out")
    return False
```

---

## 🚀 Pattern 9 — Takeoff and Landing

### Takeoff

```python
def takeoff(master, altitude_m):
    """
    Command the drone to take off to a specific altitude in metres.
    Drone must be ARMED and in GUIDED mode first.
    altitude_m goes in param7 — all other params are 0.
    """
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0, 0, 0, 0,   # params 1-4: unused (minimum pitch, empty, empty, yaw)
        0, 0,         # params 5-6: lat/lon (0 = use current position)
        altitude_m    # param7: target altitude in metres
    )
    print(f"Takeoff command sent — target altitude: {altitude_m}m")
```

### Wait until target altitude is reached

```python
def wait_altitude(master, target_alt_m, tolerance=0.5):
    """
    Block until the drone reaches target_alt_m (±tolerance metres).
    Uses GLOBAL_POSITION_INT which provides EKF-fused altitude.
    """
    print(f"Climbing to {target_alt_m}m...")
    while True:
        pos = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=2)
        if pos:
            current_alt = pos.relative_alt / 1000  # mm → m
            print(f"  Altitude: {current_alt:.1f}m")
            if abs(current_alt - target_alt_m) <= tolerance:
                print(f"✅ Target altitude reached: {current_alt:.1f}m")
                break
```

### Land

```python
def land(master):
    """Command the drone to land at its current position."""
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0,
        0, 0, 0, 0, 0, 0, 0  # All params unused for basic land
    )
    print("Land command sent.")
```

### Return to Launch (RTL)

```python
def return_to_launch(master):
    """Command the drone to fly back to its takeoff location and land."""
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
        0,
        0, 0, 0, 0, 0, 0, 0  # No parameters needed
    )
    print("RTL command sent.")
```

---

## 📋 Pattern 10 — Mission Upload Handshake

Uploading a mission (a sequence of waypoints) requires a strict back-and-forth protocol between you and the drone.

### The handshake sequence

```
Your script                     Drone
     │                            │
     │──── MISSION_COUNT ────────>│  "I'm sending N items"
     │                            │
     │<─── MISSION_REQUEST_INT ───│  "Send me item 0"
     │──── MISSION_ITEM_INT ─────>│  "Here is item 0"
     │                            │
     │<─── MISSION_REQUEST_INT ───│  "Send me item 1"
     │──── MISSION_ITEM_INT ─────>│  "Here is item 1"
     │                            │
     │         ... repeat ...     │
     │                            │
     │<─── MISSION_ACK ───────────│  "Mission received OK"
```

### Complete mission upload function

```python
import time
from pymavlink import mavutil

def upload_mission(master, waypoints):
    """
    Upload a list of waypoints to the drone.

    waypoints: list of dicts, each with keys:
        lat   (float degrees)
        lon   (float degrees)
        alt   (float metres, relative to home)
        cmd   (MAV_CMD constant, default = MAV_CMD_NAV_WAYPOINT)
    """

    # ── Step 1: Tell the drone how many mission items are coming ──────────────
    total_items = len(waypoints)
    master.mav.mission_count_send(
        master.target_system,
        master.target_component,
        total_items,
        mavutil.mavlink.MAV_MISSION_TYPE_MISSION  # 0 = normal mission
    )
    print(f"Told drone to expect {total_items} mission items")

    # ── Step 2: Wait for each MISSION_REQUEST_INT, then send the item ─────────
    items_sent = 0

    while items_sent < total_items:
        # Drone requests items one at a time in sequence
        msg = master.recv_match(
            type=['MISSION_REQUEST_INT', 'MISSION_REQUEST', 'MISSION_ACK'],
            blocking=True,
            timeout=5
        )

        if msg is None:
            print("❌ Timeout waiting for MISSION_REQUEST")
            return False

        msg_type = msg.get_type()

        if msg_type == 'MISSION_ACK':
            # Drone might send MISSION_ACK early if something went wrong
            if msg.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                print("✅ Mission upload accepted early!")
                return True
            else:
                print(f"❌ Mission ACK with error: {msg.type}")
                return False

        # Get the sequence number the drone is asking for
        seq = msg.seq
        wp = waypoints[seq]

        # Send the requested mission item
        master.mav.mission_item_int_send(
            master.target_system,
            master.target_component,
            seq,                                          # Sequence number (0-based)
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,  # Altitude relative to home
            wp.get('cmd', mavutil.mavlink.MAV_CMD_NAV_WAYPOINT),
            1 if seq == 0 else 0,   # current: 1 = this is the first waypoint
            1,                       # autocontinue: 1 = proceed to next waypoint
            0,                       # param1: hold time (seconds)
            2.0,                     # param2: acceptance radius (metres)
            0,                       # param3: pass-through radius
            float('nan'),            # param4: yaw (nan = don't change yaw)
            int(wp['lat'] * 1e7),    # x: latitude as integer (degrees × 1e7)
            int(wp['lon'] * 1e7),    # y: longitude as integer (degrees × 1e7)
            wp['alt'],               # z: altitude in metres
            mavutil.mavlink.MAV_MISSION_TYPE_MISSION
        )
        items_sent += 1
        print(f"  Sent item {seq}: lat={wp['lat']}, lon={wp['lon']}, alt={wp['alt']}m")

    # ── Step 3: Wait for final MISSION_ACK ────────────────────────────────────
    ack = master.recv_match(type='MISSION_ACK', blocking=True, timeout=5)

    if ack and ack.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
        print("✅ Mission uploaded successfully!")
        return True
    else:
        print(f"❌ Mission upload failed. ACK type: {ack.type if ack else 'timeout'}")
        return False


# Example usage:
waypoints = [
    {'lat': -35.363261, 'lon': 149.165230, 'alt': 10},  # Waypoint 0
    {'lat': -35.362261, 'lon': 149.165230, 'alt': 15},  # Waypoint 1
    {'lat': -35.362261, 'lon': 149.166230, 'alt': 15},  # Waypoint 2
]
upload_mission(master, waypoints)
```

---

## 📡 Pattern 11 — Reading Telemetry Streams

The drone continuously broadcasts many different message types. This pattern shows how to read them in a continuous monitoring loop.

```python
import time
import math
from pymavlink import mavutil

def monitor_telemetry(master, duration_seconds=30):
    """
    Read and display telemetry for a given number of seconds.
    """
    print(f"Monitoring telemetry for {duration_seconds} seconds...\n")
    start = time.time()

    while time.time() - start < duration_seconds:
        msg = master.recv_match(blocking=True, timeout=1)

        if msg is None:
            continue

        msg_type = msg.get_type()

        # ── GPS position ──────────────────────────────────────────────────
        if msg_type == 'GLOBAL_POSITION_INT':
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            alt = msg.relative_alt / 1000  # mm → m
            print(f"📍 Position: {lat:.6f}, {lon:.6f} | Alt: {alt:.1f}m")

        # ── Attitude (orientation) ────────────────────────────────────────
        elif msg_type == 'ATTITUDE':
            roll  = math.degrees(msg.roll)
            pitch = math.degrees(msg.pitch)
            yaw   = math.degrees(msg.yaw)
            print(f"🔄 Roll: {roll:.1f}° | Pitch: {pitch:.1f}° | Yaw: {yaw:.1f}°")

        # ── Battery ───────────────────────────────────────────────────────
        elif msg_type == 'SYS_STATUS':
            voltage = msg.voltage_battery / 1000  # mV → V
            remaining = msg.battery_remaining      # percent
            print(f"🔋 Battery: {voltage:.2f}V | {remaining}%")

        # ── HUD data ──────────────────────────────────────────────────────
        elif msg_type == 'VFR_HUD':
            print(f"🌀 Speed: {msg.groundspeed:.1f}m/s | Climb: {msg.climb:.2f}m/s | Throttle: {msg.throttle}%")

        # ── Text messages from autopilot ──────────────────────────────────
        elif msg_type == 'STATUSTEXT':
            severity_names = {0:'EMERGENCY', 1:'ALERT', 2:'CRITICAL',
                              3:'ERROR', 4:'WARNING', 5:'NOTICE', 6:'INFO', 7:'DEBUG'}
            sev = severity_names.get(msg.severity, '?')
            print(f"📢 [{sev}] {msg.text}")

        # ── Active waypoint ───────────────────────────────────────────────
        elif msg_type == 'MISSION_CURRENT':
            print(f"🎯 Active waypoint: #{msg.seq}")

        # ── Waypoint reached ──────────────────────────────────────────────
        elif msg_type == 'MISSION_ITEM_REACHED':
            print(f"✅ Reached waypoint #{msg.seq}")
```

---

## 🎛️ Pattern 12 — Parameter Read and Write

ArduPilot has hundreds of tunable parameters (like `WPNAV_SPEED`, `FENCE_ENABLE`, etc.). You can read and write them from Python.

### Read a parameter

```python
def get_parameter(master, param_name, timeout=5):
    """
    Request and return the value of a named parameter.
    Returns None if the parameter doesn't exist or times out.
    """
    # Request the parameter by name
    master.mav.param_request_read_send(
        master.target_system,
        master.target_component,
        param_name.encode('utf-8'),  # Must be bytes, max 16 characters
        -1  # -1 = request by name (not by index)
    )

    # Wait for the PARAM_VALUE response
    msg = master.recv_match(type='PARAM_VALUE', blocking=True, timeout=timeout)

    if msg and msg.param_id.strip('\x00') == param_name:
        print(f"Parameter {param_name} = {msg.param_value}")
        return msg.param_value
    else:
        print(f"❌ Could not read parameter: {param_name}")
        return None

# Usage:
get_parameter(master, 'WPNAV_SPEED')    # Waypoint navigation speed
get_parameter(master, 'FENCE_ENABLE')   # Whether geofence is enabled
get_parameter(master, 'RTL_ALT')        # Return-to-launch altitude
```

### Write a parameter

```python
def set_parameter(master, param_name, param_value, param_type=None):
    """
    Write a new value to a named parameter.
    param_type: use mavutil.mavlink.MAV_PARAM_TYPE_REAL32 for floats (default)
    """
    if param_type is None:
        # REAL32 works for most ArduPilot parameters
        param_type = mavutil.mavlink.MAV_PARAM_TYPE_REAL32

    master.mav.param_set_send(
        master.target_system,
        master.target_component,
        param_name.encode('utf-8'),  # Parameter name as bytes (max 16 chars)
        float(param_value),          # New value as float
        param_type
    )

    # Drone echoes back a PARAM_VALUE to confirm the write
    msg = master.recv_match(type='PARAM_VALUE', blocking=True, timeout=5)
    if msg and msg.param_id.strip('\x00') == param_name:
        print(f"✅ Set {param_name} = {msg.param_value}")
        return True
    else:
        print(f"❌ Failed to confirm write for {param_name}")
        return False

# Usage examples:
set_parameter(master, 'WPNAV_SPEED', 500)    # 500 cm/s = 5 m/s
set_parameter(master, 'FENCE_ENABLE', 1)     # Enable geofence
set_parameter(master, 'RTL_ALT', 3000)       # RTL altitude = 30m (in cm)
set_parameter(master, 'ARMING_CHECK', 0)     # Disable all arming checks (SITL only!)
```

### Read all parameters

```python
def get_all_parameters(master):
    """Request all parameters from the drone and return them as a dict."""
    # Request the full parameter list
    master.mav.param_request_list_send(
        master.target_system,
        master.target_component
    )

    params = {}
    total = None

    while True:
        msg = master.recv_match(type='PARAM_VALUE', blocking=True, timeout=3)
        if msg is None:
            break
        name = msg.param_id.strip('\x00')
        params[name] = msg.param_value
        total = msg.param_count  # Total number of parameters available
        if len(params) >= total:
            break

    print(f"Retrieved {len(params)} of {total} parameters")
    return params
```

---

## 📶 Pattern 13 — Requesting Specific Message Streams

By default SITL sends many messages, but on a real drone you may need to explicitly request the message types you need, or set their rates.

### Request a specific message once

```python
def request_message(master, message_id):
    """
    Request the drone to send a specific message right now.
    message_id: the MAVLink message ID number (e.g., 33 for GLOBAL_POSITION_INT)
    """
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE,
        0,
        message_id,   # param1: the message ID you want
        0, 0, 0, 0, 0, 0
    )

# Common message IDs:
# 0   = HEARTBEAT
# 24  = GPS_RAW_INT
# 30  = ATTITUDE
# 33  = GLOBAL_POSITION_INT
# 74  = VFR_HUD
# 1   = SYS_STATUS
# 253 = STATUSTEXT

request_message(master, 33)  # Request a GLOBAL_POSITION_INT right now
```

### Set a message stream rate

```python
def set_message_rate(master, message_id, rate_hz):
    """
    Set the rate at which the drone broadcasts a specific message.
    rate_hz: messages per second (0 = disable)
    """
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
        0,
        message_id,               # param1: message ID
        1e6 / rate_hz if rate_hz > 0 else -1,  # param2: interval in microseconds
        0, 0, 0, 0, 0
    )
    print(f"Set message {message_id} to {rate_hz} Hz")

# Examples:
set_message_rate(master, 30, 10)  # ATTITUDE at 10 Hz
set_message_rate(master, 33, 5)   # GLOBAL_POSITION_INT at 5 Hz
set_message_rate(master, 24, 2)   # GPS_RAW_INT at 2 Hz
set_message_rate(master, 24, 0)   # Disable GPS_RAW_INT stream
```

### Request a data stream group (legacy method)

```python
def request_data_stream(master, stream_id, rate_hz):
    """
    Request a group of related messages at a given rate.
    This is the older MAV_DATA_STREAM method — still works on ArduPilot.
    """
    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        stream_id,   # MAV_DATA_STREAM group ID
        rate_hz,     # Messages per second
        1            # 1 = start streaming, 0 = stop
    )

# Stream IDs (MAV_DATA_STREAM):
# 0 = ALL          - All streams
# 1 = RAW_SENSORS  - IMU, GPS raw data
# 2 = EXTENDED_STATUS - SYS_STATUS, MEMINFO
# 3 = RC_CHANNELS  - RC input/output
# 4 = RAW_CONTROLLER - attitude controller output
# 6 = POSITION     - GLOBAL_POSITION_INT, ATTITUDE
# 10 = EXTRA1      - ATTITUDE, SIMSTATE
# 11 = EXTRA2      - VFR_HUD
# 12 = EXTRA3      - AHRS, HWSTATUS

request_data_stream(master, mavutil.mavlink.MAV_DATA_STREAM_ALL, 10)  # All at 10 Hz
request_data_stream(master, 6, 5)   # Position data at 5 Hz
```

---

## 🧭 Pattern 14 — Position Commands

To fly the drone to a specific GPS position while in GUIDED mode, use `SET_POSITION_TARGET_GLOBAL_INT`.

```python
def fly_to_position(master, lat, lon, alt):
    """
    Command the drone to fly to a specific GPS coordinate.
    Drone must be in GUIDED mode and airborne.

    lat, lon: float degrees
    alt: float metres (relative to home)
    """
    # type_mask tells the drone which fields to use.
    # We want to control position only (not velocity/acceleration).
    # Set bits for fields you want IGNORED:
    # bits: vx, vy, vz, ax, ay, az, force, yaw_rate, yaw
    # 0b0000111111111000 = ignore velocity + acceleration + yaw
    type_mask = 0b0000111111111000  # = 0x0FF8 = 4088

    master.mav.set_position_target_global_int_send(
        0,                          # time_boot_ms (0 = not used)
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,  # altitude relative to home
        type_mask,
        int(lat * 1e7),            # lat as integer (degrees × 1e7)
        int(lon * 1e7),            # lon as integer (degrees × 1e7)
        alt,                       # altitude in metres
        0, 0, 0,                   # vx, vy, vz (ignored by type_mask)
        0, 0, 0,                   # ax, ay, az (ignored)
        0,                         # yaw in radians (ignored)
        0                          # yaw_rate (ignored)
    )
    print(f"Flying to: {lat:.6f}, {lon:.6f} at {alt}m")
```

---

## 🚧 Pattern 15 — Geofence Configuration

A geofence limits where the drone can fly. When violated, the drone can RTL, land, or hold position.

```python
def enable_geofence(master):
    """Enable the geofence using parameter write."""
    set_parameter(master, 'FENCE_ENABLE', 1)   # 1 = enabled
    set_parameter(master, 'FENCE_TYPE', 7)     # 7 = all fence types active
    # FENCE_TYPE bitmask:
    # 1 = Max altitude fence
    # 2 = Circle fence (radius around home)
    # 4 = Polygon fence
    # 7 = All of the above

def disable_geofence(master):
    """Disable the geofence."""
    set_parameter(master, 'FENCE_ENABLE', 0)

def set_geofence_radius(master, radius_metres):
    """Set the circular geofence radius around home."""
    set_parameter(master, 'FENCE_RADIUS', radius_metres)

def set_geofence_max_altitude(master, alt_metres):
    """Set the maximum altitude fence (in metres)."""
    set_parameter(master, 'FENCE_ALT_MAX', alt_metres)

def set_geofence_action(master, action):
    """
    Set what happens when the fence is breached.
    action: 0 = Report only, 1 = RTL, 2 = Land, 3 = SmartRTL, 4 = Brake
    """
    set_parameter(master, 'FENCE_ACTION', action)

# Enable geofence via command (alternative)
def toggle_geofence_via_command(master, enable=True):
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_DO_FENCE_ENABLE,
        0,
        1 if enable else 0,  # param1: 1 = enable, 0 = disable
        0, 0, 0, 0, 0, 0
    )
```

---

## 🛡️ Pattern 16 — Error Handling and Timeouts

Real-world drone scripts must handle timeouts, lost connections, and rejected commands gracefully.

```python
import time
from pymavlink import mavutil

def send_command_with_retry(master, command, params, retries=3, timeout=5):
    """
    Send a command_long and retry up to `retries` times if no ACK is received.
    params: list of exactly 7 floats [p1, p2, p3, p4, p5, p6, p7]
    Returns True if accepted, False if all retries fail.
    """
    for attempt in range(retries):
        print(f"  Sending command (attempt {attempt + 1}/{retries})...")

        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            command,
            attempt,    # confirmation: increment on retries
            *params     # Unpack the 7 parameters
        )

        ack = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=timeout)

        if ack is None:
            print(f"  ⚠️ No ACK received (attempt {attempt + 1})")
            continue

        if ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            print(f"  ✅ Command accepted!")
            return True
        elif ack.result == mavutil.mavlink.MAV_RESULT_IN_PROGRESS:
            print(f"  ⏳ Command in progress...")
            time.sleep(1)
            return True  # Treat in-progress as success
        else:
            result_names = {
                0: 'ACCEPTED', 1: 'TEMPORARILY_REJECTED',
                2: 'DENIED', 3: 'UNSUPPORTED', 4: 'FAILED'
            }
            result_str = result_names.get(ack.result, f'UNKNOWN({ack.result})')
            print(f"  ❌ Command rejected: {result_str}")
            return False

    print("❌ All retry attempts exhausted.")
    return False


def safe_connect(connection_string, timeout=30):
    """
    Connect to drone with a timeout. Returns master object or None.
    """
    print(f"Connecting to {connection_string}...")
    try:
        master = mavutil.mavlink_connection(connection_string)
        master.wait_heartbeat(timeout=timeout)
        print(f"✅ Connected — System {master.target_system}")
        return master
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None


# Usage:
master = safe_connect('tcp:127.0.0.1:5760')

if master:
    send_command_with_retry(
        master,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        [1, 0, 0, 0, 0, 0, 0]   # ARM with normal safety checks
    )
```

---

## 📊 Quick Reference Tables

### Full function signature summary

| Function | Purpose | Key Parameters |
|---|---|---|
| `mavutil.mavlink_connection(str)` | Create connection | Connection string |
| `master.wait_heartbeat()` | Wait for first heartbeat | — |
| `master.mav.command_long_send(...)` | Send flight command | sys, comp, cmd, conf, p1-p7 |
| `master.recv_match(type=..., blocking=..., timeout=...)` | Receive message | type, blocking, timeout |
| `msg.get_type()` | Get message type string | — |
| `master.mav.mission_count_send(...)` | Start mission upload | sys, comp, count, type |
| `master.mav.mission_item_int_send(...)` | Send one waypoint | seq, frame, cmd, lat, lon, alt |
| `master.mav.param_request_read_send(...)` | Read a parameter | sys, comp, name, index |
| `master.mav.param_set_send(...)` | Write a parameter | sys, comp, name, value, type |
| `master.mav.request_data_stream_send(...)` | Request stream group | sys, comp, stream_id, rate |
| `master.set_mode(name)` | Set flight mode by name | Mode string |

### MAV_RESULT codes

| Value | Constant | Meaning |
|---|---|---|
| 0 | `MAV_RESULT_ACCEPTED` | Command accepted and executing |
| 1 | `MAV_RESULT_TEMPORARILY_REJECTED` | Try again later |
| 2 | `MAV_RESULT_DENIED` | Not allowed (mode, safety check) |
| 3 | `MAV_RESULT_UNSUPPORTED` | Command not known |
| 4 | `MAV_RESULT_FAILED` | Command failed during execution |
| 5 | `MAV_RESULT_IN_PROGRESS` | Long command, still running |

### Key coordinate conversions

| Raw value | Convert to human units | Example |
|---|---|---|
| `gps.lat` (int) | `gps.lat / 1e7` → degrees | `355363261 / 1e7 = 35.5363°` |
| `gps.lon` (int) | `gps.lon / 1e7` → degrees | — |
| `gps.alt` (int, mm) | `gps.alt / 1000` → metres | `10000 / 1000 = 10m` |
| `pos.relative_alt` (int, mm) | `pos.relative_alt / 1000` → metres | — |
| `att.roll` (float, radians) | `att.roll * 180 / math.pi` → degrees | — |
| `sys.voltage_battery` (int, mV) | `/ 1000` → Volts | `12600 / 1000 = 12.6V` |

---

## ⚠️ Common Mistakes Beginners Make

### ❌ Mistake 1: Forgetting `time.sleep(1)` after connecting

**What happens:** `wait_heartbeat()` times out or `target_system` stays at 0.

```python
# ❌ Wrong — connecting and immediately requesting heartbeat
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
master.wait_heartbeat()  # May fail or get wrong IDs

# ✅ Correct — give the TCP session a moment to fully establish
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
time.sleep(1)
master.wait_heartbeat()
```

---

### ❌ Mistake 2: Sending fewer than 7 parameters to `command_long_send`

**What happens:** Python raises a `TypeError` about wrong number of arguments.

```python
# ❌ Wrong — only 5 parameters instead of 7
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
    0,
    0, 0, 0, 0, 5  # Only 5 params!
)

# ✅ Correct — always exactly 7 parameters
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
    0,
    0, 0, 0, 0, 0, 0, 5  # 7 params — altitude is param7
)
```

---

### ❌ Mistake 3: Forgetting to encode parameter names as bytes

**What happens:** `param_request_read_send` raises a `TypeError`.

```python
# ❌ Wrong — passing a Python string directly
master.mav.param_request_read_send(
    master.target_system, master.target_component,
    'FENCE_ENABLE',  # String won't work!
    -1
)

# ✅ Correct — encode to bytes first
master.mav.param_request_read_send(
    master.target_system, master.target_component,
    b'FENCE_ENABLE',  # Bytes literal
    -1
)
# Or:
param_name = 'FENCE_ENABLE'
master.mav.param_request_read_send(
    master.target_system, master.target_component,
    param_name.encode('utf-8'),
    -1
)
```

---

### ❌ Mistake 4: Not checking for `None` after `recv_match`

**What happens:** `AttributeError` when accessing fields of a `None` message.

```python
# ❌ Wrong — assuming a message always arrives
msg = master.recv_match(type='GPS_RAW_INT', blocking=True, timeout=3)
lat = msg.lat / 1e7  # Crashes if msg is None (timeout)

# ✅ Correct — always check first
msg = master.recv_match(type='GPS_RAW_INT', blocking=True, timeout=3)
if msg:
    lat = msg.lat / 1e7
    print(f"Latitude: {lat:.6f}")
else:
    print("No GPS message received — check stream rate.")
```

---

### ❌ Mistake 5: Using raw GPS altitude instead of relative altitude

**What happens:** Your altitude readout shows hundreds of metres instead of your actual height above ground.

```python
# ❌ Wrong — GPS_RAW_INT.alt is in mm above sea level
gps = master.recv_match(type='GPS_RAW_INT', blocking=True)
alt = gps.alt / 1000  # Could be 500m if you're at high elevation!

# ✅ Correct — GLOBAL_POSITION_INT.relative_alt is above home (takeoff point)
pos = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
alt = pos.relative_alt / 1000  # Metres above where you launched — what you usually want
```

---

### ❌ Mistake 6: Arming without setting GUIDED mode first

**What happens:** ARM command is rejected with `DENIED` or `TEMPORARILY_REJECTED`.

```python
# ❌ Wrong — trying to arm without being in GUIDED mode
master.mav.command_long_send(..., MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, ...)

# ✅ Correct — set GUIDED first, then arm
master.set_mode('GUIDED')
time.sleep(1)
master.mav.command_long_send(..., MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, ...)
```

---

### ❌ Mistake 7: Using `GPS_RAW_INT` lat/lon directly without dividing by 1e7

**What happens:** Your waypoints end up thousands of kilometres away from the intended location.

```python
# ❌ Wrong — using the raw integer directly as degrees
lat = gps.lat   # This is 355363261, NOT 35.5363261°

# ✅ Correct — divide by 1e7
lat = gps.lat / 1e7  # = 35.5363261°
```

---

## 🔁 Recap — Key Takeaways

- **`mavutil.mavlink_connection(str)`** is always first — it creates your link to the drone.
- **Always call `time.sleep(1)` then `wait_heartbeat()`** before sending any commands.
- **`master.mav.XXX_send()`** is for **sending**; **`master.recv_match()`** is for **receiving**.
- **`command_long_send` always requires exactly 7 command parameters** — fill unused ones with `0`.
- **Always check `if msg is not None`** before accessing any message fields.
- **Coordinates are stored as integers (× 1e7)** — always divide by `1e7` to get degrees.
- **`relative_alt` (in mm) is height above home** — divide by `1000` to get metres.
- **Set GUIDED mode before arming; arm before takeoff** — the sequence matters.
- **Mission upload is a handshake** — you must respond to each `MISSION_REQUEST_INT` individually.
- **Parameter names must be `bytes`** — use `.encode('utf-8')` when passing names.

---

## ✅ Check Yourself

**Question 1 — Conceptual:**
What is the difference between `blocking=True` and `blocking=False` in `recv_match()`? When would you choose each one?

**Question 2 — Applied:**
You want to fly a drone to the GPS coordinate (37.7749°N, -122.4194°W) at 20 metres above the launch point. Write the `set_position_target_global_int_send` call that does this. Which frame would you use and why?

**Question 3 — Code:**
The following code crashes. Identify the two bugs and write the corrected version:

```python
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
master.wait_heartbeat()

master.mav.param_request_read_send(
    master.target_system,
    master.target_component,
    'WPNAV_SPEED',
    -1
)

msg = master.recv_match(type='PARAM_VALUE', blocking=True, timeout=3)
print(f"Speed = {msg.param_value}")
```

---

*Tutorial covers PyMAVLink patterns for ArduPilot SITL and real drone connections. All examples tested with ArduCopter 4.x and pymavlink 2.x.*
