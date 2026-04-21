# 🚁 Complete ArduPilot SITL & MAVLink Tutorial - Beginner's Guide

## 📚 Table of Contents
1. [Introduction](#introduction)
2. [What is MAVLink?](#what-is-mavlink)
3. [System Requirements](#system-requirements)
4. [Step 1: Install Python and Dependencies](#step-1-install-python-and-dependencies)
5. [Step 2: Install pymavlink and MAVProxy](#step-2-install-pymavlink-and-mavproxy)
6. [Step 3: Set Up ArduPilot SITL](#step-3-set-up-ardupilot-sitl)
7. [Step 4: Build ArduPilot SITL](#step-4-build-ardupilot-sitl)
8. [Step 5: Start the Simulated Drone](#step-5-start-the-simulated-drone)
9. [Step 6: Connect with APM Planner (Linux)](#step-6-connect-with-apm-planner-linux)
10. [Step 7: Understanding MAVLink Commands](#step-7-understanding-mavlink-commands)
11. [Step 8: Python Scripting with MAVLink](#step-8-python-scripting-with-mavlink)
12. [Understanding SITL Network & Ports](#understanding-sitl-network--ports)
13. [MAVProxy Commands Reference](#mavproxy-commands-reference)
14. [Complete Python Examples](#complete-python-examples)
15. [Troubleshooting Guide](#troubleshooting-guide)
16. [MAVLink Command Reference](#mavlink-command-reference)
17. [Resources](#resources)

---

## Introduction

This tutorial will teach you how to work with **MAVLink** (drone communication protocol) using **ArduPilot SITL** (Software-In-the-Loop simulation). You don't need any physical drone hardware - everything runs on your computer!

**What you'll learn:**
- What MAVLink is and how it works
- How to set up a virtual drone on your computer
- How to understand SITL network ports and connections
- How to connect ground control software to your virtual drone
- How to find and use MAVLink command codes
- How to write Python scripts to control the drone
- How to troubleshoot common issues

---

## What is MAVLink?

Think of MAVLink as the **language that drones use to communicate**.

- **MAV** = Micro Air Vehicle (a drone)
- **Link** = The connection

MAVLink sends short data packets containing specific IDs. For example:
- `ID=22` might mean "Takeoff command"
- `ID=24` might mean "GPS Position"

Any ground control software that speaks MAVLink can listen to the drone, give it commands, and display telemetry data.

---

## System Requirements

**Operating System:** 
- Ubuntu 18.04+, 20.04+, 22.04+
- Debian 10+
- Linux Mint 19+
- Other Debian-based distributions
- **WSL (Windows Subsystem for Linux)** - fully supported!

**Minimum Requirements:**
- 4GB RAM (8GB recommended)
- 10GB free disk space
- Python 3.6 or higher

---

## Step 1: Install Python and Dependencies

Open a terminal (`Ctrl + Alt + T`) and run these commands:

### Update System Packages:
```bash
sudo apt update
sudo apt upgrade -y
```

### Install Python and Required Packages:
```bash
sudo apt-get install -y python3-dev python3-opencv python3-wxgtk4.0 python3-pip python3-matplotlib python3-lxml python3-pygame
```

### Install Additional Build Tools:
```bash
sudo apt-get install -y git build-essential cmake
```

### Install ccache for Faster Builds (Recommended):
```bash
sudo apt-get install ccache
```
**Effect:** Makes subsequent builds 5-10x faster! ⚡

### Verify Python Installation:
```bash
python3 --version
# Should show Python 3.8 or higher
```

---

## Step 2: Install pymavlink and MAVProxy

### Install pymavlink (Python MAVLink library):
```bash
python3 -m pip install pymavlink --user
```

### Install MAVProxy (Ground Control Station in terminal):
```bash
python3 -m pip install PyYAML mavproxy --user
```

### Add Python User Binaries to PATH:
```bash
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc
source ~/.bashrc
```

### Verify Installation:
```bash
# Check pymavlink
python3 -c "import pymavlink; print('pymavlink installed successfully!')"

# Check MAVProxy
mavproxy.py --version
```

---

## Step 3: Set Up ArduPilot SITL

### Create Workspace Directory:
```bash
mkdir -p ~/workspace
cd ~/workspace
```

### ⚠️ IMPORTANT: Clone with Submodules

**Always use the `--recurse-submodules` flag!** ArduPilot relies heavily on submodules for HAL drivers and libraries.

```bash
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
```

| Without Flag | With Flag |
|:---|:---|
| ❌ Only main repository cloned | ✅ Main repo + all submodules |
| ❌ Empty submodule directories | ✅ Complete codebase ready |
| ❌ Will fail to build | ✅ Ready to compile |

**If you forgot the flag:**
```bash
git submodule update --init --recursive
```

### Install ArduPilot Prerequisites:
```bash
cd Tools/environment_install
./install-prereqs-ubuntu.sh -y
cd ../..
```

### Reload Environment Variables:
```bash
source ~/.profile
```

### Add User to Dialout Group (for USB/serial access later):
```bash
sudo usermod -a -G dialout $USER
# Logout required for changes to take effect
```

---

## Step 4: Build ArduPilot SITL

### Configure Build for SITL:
```bash
./waf configure --board sitl
```

### Build Only Copter (Recommended for beginners):
```bash
./waf copter
```

### Or Build All Vehicles:
```bash
./waf build
```

### Verify Build Success:
```bash
# After building only copter
ls build/sitl/bin/
# You should see: arducopter
```

### Clean Build (if needed):
```bash
./waf clean
./waf copter
```

---

## Step 5: Start the Simulated Drone

You have **two methods** to start SITL:

### Method 1: Direct Execution (Simple)

```bash
cd ~/workspace/ardupilot
./build/sitl/bin/arducopter --console --map
```

**With specific vehicle model:**
```bash
./build/sitl/bin/arducopter --model quad --console --map
```

**Available models:**
- `--model quad` - Standard quadcopter (default)
- `--model hexa` - Hexacopter
- `--model octa` - Octocopter
- `--model heli` - Helicopter

### Method 2: Using sim_vehicle.py (Recommended)

This script provides more features and easier configuration:

```bash
cd ~/workspace/ardupilot
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map
```

**With UDP output (for external connections):**
```bash
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map --out=udp:127.0.0.1:14550
```

**Common sim_vehicle.py options:**
```bash
# Without map (faster startup)
./Tools/autotest/sim_vehicle.py -v ArduCopter --console

# With custom parameters
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map --param my_params.parm

# With wind simulation
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map --wind 5 180

# Multiple vehicles (swarm)
./Tools/autotest/sim_vehicle.py -v ArduCopter -I 0 --console --map
./Tools/autotest/sim_vehicle.py -v ArduCopter -I 1 --console --map
```

### Setting Display (if map doesn't show):
```bash
export DISPLAY=:0
```

**What you should see:**
- A console window with scrolling telemetry data
- A map window showing your drone as a helicopter icon
- The drone starts on the ground at a simulated location

> **⚠️ IMPORTANT:** Keep this terminal window open! This is your virtual drone.

---

## Step 6: Connect with APM Planner (Linux)

APM Planner is a graphical ground control station that communicates with your drone using MAVLink.

### Download APM Planner for Linux:

1. Go to: https://github.com/ArduPilot/apm_planner/releases

2. Download the AppImage file:
   **`APM-Planner_2-2.0.30-x86_64.AppImage`** (54.5 MB)

### Install and Run APM Planner:

```bash
cd ~/Downloads
chmod +x APM-Planner_2-2.0.30-x86_64.AppImage
./APM-Planner_2-2.0.30-x86_64.AppImage
```

**Optional - Move to applications folder:**
```bash
mkdir -p ~/.local/bin
mv APM-Planner_2-2.0.30-x86_64.AppImage ~/.local/bin/apmplanner
chmod +x ~/.local/bin/apmplanner
```

### Connect APM Planner to SITL:

1. Open APM Planner
2. Click the **"Connect"** button
3. Select connection type:
   - **Type:** TCP
   - **Address:** `127.0.0.1`
   - **Port:** `5760`
4. Click **"Connect"**

**What you should see:**
- A 3D model of your drone
- Artificial horizon display
- Battery voltage, satellite count, altitude
- Real-time telemetry data

---

## Step 7: Understanding MAVLink Commands

Excellent question! You've identified exactly what confuses most beginners when they first see MAVLink code. Let me break down each of these three parts.

### 1. `master.mav.command_long_send(`

This is the function call that sends a MAVLink command to the drone.

Let's break it down piece by piece:

| Part | What it means |
|------|---------------|
| `master` | Your connection object (created with `mavutil.mavlink_connection()`) |
| `.mav` | The MAVLink messaging interface |
| `.command_long_send` | The function to send a "long command" (a command with up to 7 parameters) |

### Why "command_long"?
There are actually two ways to send commands in MAVLink:
- **`command_long`**: Used for most commands (takes 7 parameters)
- **`command_int`**: Used for commands that need precise coordinates or integers (like latitude/longitude)

### 2. `mavutil.`

This is referencing the `mavutil` library. A complete constant looks like:

```python
mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM
```

Let's break this down:

| Part | What it means |
|------|---------------|
| `mavutil` | The Python library installed with `pip install pymavlink` |
| `.mavlink` | The MAVLink module inside `mavutil` |
| `.MAV_CMD_COMPONENT_ARM_DISARM` | The constant that equals the number `400` (the command ID) |

### Why not just write `400`?
You could, but the constant is better because:
- It is self-documenting
- It is easier to read later
- It avoids magic numbers

Both of these do the same thing:

```python
# Recommended
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    # ...
)

# Works, but harder to understand
master.mav.command_long_send(
    master.target_system, master.target_component,
    400,
    # ...
)
```

### 3. The 5 Remaining Parameters: `0, 0, 0, 0, 0`

This is the most confusing part for beginners.

### Why are there 5 zeros?
Every `command_long_send` always expects exactly **7 command-specific parameters** (`param1` through `param7`).

| Parameter Number | Purpose | In ARM/DISARM command |
|-----------------|---------|----------------------|
| param1 | Used for the "Arm" action | 1 = ARM, 0 = DISARM |
| param2 | Used for the "Force" action | 0 = normal, 21196 = force |
| param3 | Not used by this command | Must be 0 |
| param4 | Not used by this command | Must be 0 |
| param5 | Not used by this command | Must be 0 |
| param6 | Not used by this command | Must be 0 |
| param7 | Not used by this command | Must be 0 |

Some commands use all 7 parameters. For example, `MAV_CMD_NAV_WAYPOINT` uses latitude, longitude, and altitude:

```python
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
    0,
    0,          # param1: Hold time
    0,          # param2: Acceptance radius
    0,          # param3: Pass radius
    0,          # param4: Yaw
    37.7749,    # param5: Latitude
    -122.4194,  # param6: Longitude
    20          # param7: Altitude
)
```

### Visual Representation

Think of it like a form with 7 fields:

```text
┌─────────────────────────────────────────────────────────────┐
│ MAV_CMD_COMPONENT_ARM_DISARM (400)                          │
├─────────────────────────────────────────────────────────────┤
│ param1: [1]    ← ARM/Disarm                                 │
│ param2: [0]    ← Force                                      │
│ param3: [0]    ← (unused)                                   │
│ param4: [0]    ← (unused)                                   │
│ param5: [0]    ← (unused)                                   │
│ param6: [0]    ← (unused)                                   │
│ param7: [0]    ← (unused)                                   │
└─────────────────────────────────────────────────────────────┘
```

If you don't fill in all 7 fields, Python will give you an error because the function expects exactly 7 arguments.

## Complete Example with Explanations

```python
master.mav.command_long_send(
    # TARGET (2 parameters)
    master.target_system,    # System ID (which drone, usually 1)
    master.target_component, # Component ID (which part of drone, 1 = autopilot)
    
    # COMMAND (1 parameter)
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,  # Command ID 400
    
    # CONFIRMATION (1 parameter)
    0,  # 0 = send once, no need for confirmation; 1 = require confirmation
    
    # COMMAND-SPECIFIC PARAMETERS (7 parameters)
    1,      # param1: ARM (1 = arm, 0 = disarm)
    0,      # param2: FORCE (0 = normal, 21196 = force)
    0,      # param3: UNUSED (must be 0)
    0,      # param4: UNUSED (must be 0)
    0,      # param5: UNUSED (must be 0)
    0,      # param6: UNUSED (must be 0)
    0       # param7: UNUSED (must be 0)
)
```

---

## How to Know Which Parameters Are Used?

You need to check the MAVLink documentation for each command.

### ARM/DISARM - Uses param1 and param2

```python
master.mav.command_long_send(..., 1, 0, 0, 0, 0, 0, 0)
#                                  ^  ^  └───┬───┘
#                                  |  |      └─ param3-7 = unused
#                                  |  └─ param2 = Force
#                                  └─ param1 = Arm
```

### TAKEOFF - Uses param7 only (altitude)

```python
master.mav.command_long_send(..., 0, 0, 0, 0, 0, 0, 5)
#                                  └───┬───┘        ^
#                                      |            └─ param7 = altitude
#                                      └─ param1-6 = unused
```

### SET_MODE - Uses param1 and param2

```python
master.mav.command_long_send(..., 1, 0, 0, 0, 0, 0, 0)
#                                  ^  ^  └───┬───┘
#                                  |  |      └─ param3-7 = unused
#                                  |  └─ param2 = custom mode (0 for GUIDED)
#                                  └─ param1 = base mode (1 = GUIDED)
```

---

## Quick Summary

| Your Question | Answer |
|---------------|--------|
| **What is `master.mav.command_long_send`?** | The function that sends a MAVLink command to the drone |
| **What is `mavutil.`?** | The Python library containing MAVLink command constants |
| **Why 5 zeros?** | Every command takes 7 parameters total. If a command only uses 2 parameters, the remaining 5 must be set to 0 |

---

### 🔍 Method 1: The Most Practical Way - Use the Python Library Itself

The `pymavlink` library contains all the command definitions. You can access them directly in your Python code or explore them in an interactive shell.

#### Interactive Exploration (Recommended)

Open a terminal and start a Python shell:

```bash
python
```

Then run:

```python
from pymavlink.dialects.v20 import common as mavlink

# See all available command constants by typing this and pressing TAB twice
mavlink.MAV_CMD_[PRESS TAB TWICE]

# Explore specific commands
print(mavlink.MAV_CMD_NAV_TAKEOFF)           # Output: 22
print(mavlink.MAV_CMD_COMPONENT_ARM_DISARM)  # Output: 400
print(mavlink.MAV_CMD_DO_SET_MODE)           # Output: 176
```

This is the most direct way to find the integer code for any command. The naming convention is clear: `MAV_CMD_` followed by the category and action.

#### Access in Your Scripts

You can also import command constants directly for cleaner code:

```python
from pymavlink.dialects.v20 import common as mavlink

arm_command = mavlink.MAV_CMD_COMPONENT_ARM_DISARM  # 400
takeoff_command = mavlink.MAV_CMD_NAV_TAKEOFF       # 22
```

### 🌐 Method 2: The Official MAVLink Documentation

For a complete, authoritative list of commands and parameters, use the official docs:

1. Go to: https://mavlink.io/en/messages/common.html#MAV_CMD
2. Search the page for the command name, like `MAV_CMD_NAV_TAKEOFF`.
3. Read the command description and parameter definitions.

The documentation explains:
- The purpose of the command
- The 7 parameters (`param1` ... `param7`)
- Which message type to use (`COMMAND_LONG` vs. `COMMAND_INT`)

### 📘 How to Read a MAVLink Command Table

When you open a `MAV_CMD` page, you will usually see a table with these columns:

- **Parameter**: The field name, usually `param1` through `param7`.
- **Label**: A short name that describes what the parameter controls.
- **Description**: A plain-language explanation of what the value means and how the command uses it.
- **Values**: The allowed values, ranges, or special constants.

Example reading pattern:

1. Find the command row, such as `MAV_CMD_COMPONENT_ARM_DISARM`.
2. Read the description for each parameter:
   - `param1` often says `Arm`: this means 1 = arm, 0 = disarm.
   - `param2` often says `Force`: this means 0 = normal, 21196 = force.
3. If a parameter says `MAV_BOOL`, use `0` or `1` only.
4. If a parameter says `inc: 21196`, it usually means there are only two valid values: `0` and `21196`.
5. If a parameter is unused for that command, set it to `0`.

A simple interpretation for `MAV_CMD_COMPONENT_ARM_DISARM`:

- `param1 = Arm`: 1 means ARM, 0 means DISARM.
- `param2 = Force`: 0 means obey safety checks, 21196 means force the action.
- `param3` through `param7`: unused, set to 0.

This is the key skill: read the parameter labels and descriptions, then map them to the `command_long_send()` call.

### 📚 How to Understand the Library Structure

- **Dialects**: Different autopilots can add custom commands. These are grouped by dialect.
- **`pymavlink.dialects.v20.common`**: Standard MAVLink 2 commands used by most systems.
- **`pymavlink.dialects.v20.ardupilotmega`**: ArduPilot-specific extensions.

### ✍️ Example: Finding and Using the "Set Mode" Command

```python
from pymavlink.dialects.v20 import common as mavlink
print(mavlink.MAV_CMD_DO_SET_MODE)  # Output: 176
```

Then use it in your script:

```python
master.mav.command_long_send(
    master.target_system,
    master.target_component,
    mavlink.MAV_CMD_DO_SET_MODE,
    0,
    1,  # param1: set mode to GUIDED
    0, 0, 0, 0, 0, 0
)
```

---

## Step 8: Python Scripting with MAVLink

### Create Your Project Folder:
```bash
mkdir -p ~/workspace/mavlink_tutorial
cd ~/workspace/mavlink_tutorial
```

### Script 1: Reading Drone Data

Create `read_data.py`:

```bash
nano read_data.py
```

```python
#!/usr/bin/env python3
"""
MAVLink Tutorial - Script 1: Reading Drone Data
"""

import time
from pymavlink import mavutil

print("🔌 MAVLink Data Reader")
print("=" * 50)

# Establish connection to SITL
print("Connecting to SITL drone...")
connection = mavutil.mavlink_connection('tcp:127.0.0.1:5760')

# Wait for heartbeat
print("Waiting for heartbeat...")
connection.wait_heartbeat()
print("✅ Heartbeat received! Drone is connected.\n")

# Display drone info
print(f"📡 Target System ID: {connection.target_system}")
print(f"🎛️ Target Component ID: {connection.target_component}\n")

# Read and display messages
print("📊 Reading telemetry data (30 seconds)...")
print("-" * 50)

start_time = time.time()
message_count = 0

while time.time() - start_time < 30:
    message = connection.recv_match(blocking=False)
    
    if message:
        message_count += 1
        msg_type = message.get_type()
        
        if msg_type == "HEARTBEAT":
            print(f"❤️ Heartbeat - Drone is alive")
            
        elif msg_type == "GPS_RAW_INT":
            lat = message.lat / 1e7
            lon = message.lon / 1e7
            alt = message.alt / 1000
            print(f"📍 GPS - Lat: {lat:.6f}, Lon: {lon:.6f}, Alt: {alt:.1f}m")
            
        elif msg_type == "ATTITUDE":
            roll = message.roll * 180 / 3.14159
            pitch = message.pitch * 180 / 3.14159
            yaw = message.yaw * 180 / 3.14159
            print(f"🔄 Attitude - Roll: {roll:.1f}°, Pitch: {pitch:.1f}°, Yaw: {yaw:.1f}°")
    
    time.sleep(0.5)

print("-" * 50)
print(f"✅ Finished! Received {message_count} messages.")
```

Save and exit (`Ctrl+X`, then `Y`, then `Enter`)

```bash
chmod +x read_data.py
```

### Script 2: Complete Drone Control

Create `control_drone.py`:

```bash
nano control_drone.py
```

```python
#!/usr/bin/env python3
"""
MAVLink Tutorial - Script 2: Complete Drone Control
⚠️ SIMULATION ONLY!
"""

import time
from pymavlink import mavutil

def connect_drone():
    """Establish connection to the drone"""
    print("🔌 Connecting to drone...")
    drone = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
    time.sleep(1)  # Give connection time to establish
    print("💓 Waiting for heartbeat...")
    drone.wait_heartbeat()
    print("✅ Drone connected!\n")
    return drone

def set_mode(drone, mode_id):
    """Set flight mode (1 = GUIDED, 0 = AUTO, etc.)"""
    print(f"🔄 Setting mode to {mode_id}...")
    drone.mav.command_long_send(
        drone.target_system,
        drone.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        mode_id,  # Base mode
        0, 0, 0, 0, 0, 0
    )
    time.sleep(1)
    print(f"✅ Mode set\n")

def arm_drone(drone, force=False):
    """Arm the drone"""
    print("⚙️ Arming motors...")
    force_value = 21196 if force else 0
    drone.mav.command_long_send(
        drone.target_system,
        drone.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1,           # 1 = Arm
        force_value, # 0 = normal, 21196 = force
        0, 0, 0, 0, 0
    )
    time.sleep(2)
    print("✅ Motors armed!\n")

def takeoff(drone, altitude_meters=5):
    """Take off to specified altitude"""
    print(f"✈️ Taking off to {altitude_meters} meters...")
    drone.mav.command_long_send(
        drone.target_system,
        drone.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0, 0, 0, 0, 0, 0,
        altitude_meters
    )
    print("✅ Takeoff command sent!\n")

def land(drone):
    """Land the drone"""
    print("🛬 Landing...")
    drone.mav.command_long_send(
        drone.target_system,
        drone.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0,
        0, 0, 0, 0, 0, 0, 0
    )
    print("✅ Land command sent!\n")

def get_altitude(drone):
    """Get current altitude"""
    msg = drone.recv_match(type='GPS_RAW_INT', blocking=True, timeout=3)
    if msg:
        return msg.alt / 1000
    return None

def main():
    print("🚁 MAVLink Drone Control Script")
    print("⚠️ SIMULATION MODE")
    print("=" * 50)
    
    # Connect
    drone = connect_drone()
    
    # Set GUIDED mode
    set_mode(drone, 1)  # 1 = GUIDED
    
    # Arm
    arm_drone(drone, force=False)
    
    # Takeoff
    takeoff(drone, altitude_meters=5)
    
    # Hover
    print("📊 Hovering for 10 seconds...")
    for i in range(10):
        altitude = get_altitude(drone)
        if altitude:
            print(f"📈 Altitude: {altitude:.1f} meters")
        time.sleep(1)
    
    # Land
    land(drone)
    time.sleep(5)
    
    # Disarm
    print("⚙️ Disarming motors...")
    drone.mav.command_long_send(
        drone.target_system,
        drone.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        0, 0, 0, 0, 0, 0, 0
    )
    
    print("\n" + "=" * 50)
    print("🎉 Mission complete!")

if __name__ == "__main__":
    main()
```

```bash
chmod +x control_drone.py
```

### Run the Scripts:

**Terminal 1 (Drone):**
```bash
cd ~/workspace/ardupilot
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map
```

**Terminal 2 (Python):**
```bash
cd ~/workspace/mavlink_tutorial
python3 control_drone.py
```

---

## Understanding SITL Network & Ports

### 📡 Default SITL Ports

| Port | Protocol | Purpose |
|:---|:---|:---|
| **5760** | TCP | Primary SERIAL0 (main GCS link) |
| **5762** | TCP | Secondary SERIAL1 |
| **5763** | TCP | Tertiary SERIAL2 |
| **14550** | UDP | Common telemetry stream |

### 🔍 How to Find Active Ports

**Method 1: Read SITL Startup Output**
```
bind port 5760 for SERIAL0
SERIAL0 on TCP port 5760
bind port 5762 for SERIAL1
SERIAL1 on TCP port 5762
```

**Method 2: MAVProxy `output` Command**
```
STABILIZE> output
3 outputs
0: 172.17.192.1:14550
1: 127.0.0.1:14550
2: 127.0.0.1:14551
```

**Method 3: `netstat` Command**
```bash
# Check UDP ports
netstat -uln | grep 14550

# Check TCP ports
netstat -tln | grep 5760
```

### 🌐 WSL-Specific Networking

| IP Address | Purpose |
|:---|:---|
| `127.0.0.1` | Localhost (within same environment) |
| `172.x.x.x` | WSL virtual network (WSL ↔ Windows communication) |

**🔑 Key Insight:** When Python runs in Windows and SITL in WSL, use the WSL IP address!

**Find your WSL IP:**
```bash
# In WSL terminal
ip addr show | grep -E "172\.|eth0"
```
```powershell
# In Windows PowerShell
wsl hostname -I
```

### ✅ Working Connection Strings

| Scenario | Connection String |
|:---|:---|
| Python in WSL → SITL in WSL | `'tcp:127.0.0.1:5760'` ✅ |
| Python in Windows → SITL in WSL | `'udp:172.x.x.x:14550'` (use WSL IP) |
| Python in Windows → SITL in WSL | `'tcp:127.0.0.1:5760'` ✅ |

---

## MAVProxy Commands Reference

### Essential Commands

| Command | Purpose |
|:---|:---|
| `output` | List all active connections |
| `output add udp:127.0.0.1:14550` | Add UDP output |
| `set streamrate 10` | Set telemetry rate to 10Hz |
| `status` | Show vehicle status |
| `heartbeat` | Manually send heartbeat |
| `module load console` | Load console module |

### 🎮 RC Control in SITL

```text
# Set throttle to neutral (1500 PWM)
rc 3 1500

# Disable radio failsafe
param set FS_THR_ENABLE 0

# Force arm (bypass checks)
arm throttle force
```

### Common Arming Errors

| Error | Cause | Fix |
|:---|:---|:---|
| `Throttle not neutral` | RC3 not at 1500 | `rc 3 1500` |
| `Radio failsafe on` | Failsafe active | `param set FS_THR_ENABLE 0` |
| `Throttle below failsafe` | Low throttle value | `rc 3 1500` |

---

## Complete Python Examples

### Basic Connection Test

```python
# test_connection.py
from pymavlink import mavutil
import time

# Choose your connection
CONNECTION_STRING = 'tcp:127.0.0.1:5760'  # Recommended

print(f"Connecting to {CONNECTION_STRING}...")
master = mavutil.mavlink_connection(CONNECTION_STRING)

# Important: Give connection time to establish
time.sleep(1)

print("Waiting for heartbeat...")
master.wait_heartbeat()
print("✅ Connected!")

print(f"Target system: {master.target_system}")
print(f"Target component: {master.target_component}")
```

---

## MAVLink Minimal Set: HEARTBEAT, Enums, and Bitmasks

This is one of the most important pages for MAVLink fundamentals. The minimal set contains the definitions every MAVLink system must support. Think of it as the communication alphabet.

### 1. HEARTBEAT is the foundation
The `HEARTBEAT` message is the only required message in the minimal set. Every drone sends one at least once per second to say "I'm alive." If you can receive a heartbeat, the link is working.

```python
# How to receive and inspect a heartbeat in Python
heartbeat = master.recv_match(type='HEARTBEAT', blocking=True)
print(f"Drone type: {heartbeat.type}")
print(f"Autopilot: {heartbeat.autopilot}")
print(f"System status: {heartbeat.system_status}")
print(f"Mode flags: {heartbeat.base_mode}")  # This is a bitmask
```

### 2. Enumerated types are lookup tables
The minimal set also defines number dictionaries that tell you what each numeric value means.
- `MAV_TYPE`: vehicle type (quadcopter, plane, rover, etc.)
- `MAV_AUTOPILOT`: autopilot firmware (ArduPilot, PX4, etc.)
- `MAV_STATE`: system status state (standby, active, emergency)
- `MAV_COMPONENT`: specific component IDs (autopilot, camera, GPS)

### 3. What is a bitmask?
A bitmask packs many yes/no flags into a single number using binary bits. Each power-of-two value sets one bit:
- `1` = `0b00000001`
- `2` = `0b00000010`
- `4` = `0b00000100`
- `8` = `0b00001000`
- `16` = `0b00010000`
- `32` = `0b00100000`
- `64` = `0b01000000`
- `128` = `0b10000000`

The `base_mode` field in `HEARTBEAT` is a bitmask. It lets MAVLink send multiple mode flags in one byte.

| Flag Value | Binary | Meaning |
|---|---|---|
| `1` | `0b00000001` | CUSTOM_MODE_ENABLED |
| `2` | `0b00000010` | TEST_MODE_ENABLED |
| `4` | `0b00000100` | AUTO_MODE_ENABLED |
| `8` | `0b00001000` | GUIDED_MODE_ENABLED |
| `16` | `0b00010000` | STABILIZE_MODE_ENABLED |
| `32` | `0b00100000` | HIL_ENABLED |
| `64` | `0b01000000` | MANUAL_INPUT_ENABLED |
| `128` | `0b10000000` | SAFETY_ARMED |

### 4. Combining flags
To represent multiple states at once, the values are combined with addition (bitwise OR).

Example: Armed + Guided + Stabilize
- `128` (armed)
- `8` (guided)
- `16` (stabilize)

Total: `128 + 8 + 16 = 152`

In binary: `0b10011000`

### 5. Decode `base_mode` in Python
```python
flags = {
    1: "CUSTOM_MODE_ENABLED",
    2: "TEST_MODE_ENABLED",
    4: "AUTO_MODE_ENABLED",
    8: "GUIDED_MODE_ENABLED",
    16: "STABILIZE_MODE_ENABLED",
    32: "HIL_ENABLED",
    64: "MANUAL_INPUT_ENABLED",
    128: "SAFETY_ARMED",
}

heartbeat = master.recv_match(type='HEARTBEAT', blocking=True)
base_mode = heartbeat.base_mode
print(f"base_mode: {base_mode} (binary: {bin(base_mode)})")
for value, name in flags.items():
    if base_mode & value:
        print(f"✓ {name}")
```

### 6. Decode `MAV_STATE` and `MAV_TYPE`
```python
states = {
    0: "UNINIT",
    1: "BOOT",
    2: "CALIBRATING",
    3: "STANDBY",
    4: "ACTIVE",
    5: "CRITICAL",
    6: "EMERGENCY",
    7: "POWEROFF",
    8: "FLIGHT_TERMINATION",
}

types = {
    0: "GENERIC",
    1: "FIXED_WING",
    2: "QUADROTOR",
    3: "COAXIAL",
    4: "HELICOPTER",
    # ... more types
}

print(f"System status: {states.get(heartbeat.system_status, 'UNKNOWN')}")
print(f"Vehicle type: {types.get(heartbeat.type, 'UNKNOWN')}")
```

### Why bitmasks are used
| Benefit | Explanation |
|---|---|
| Efficiency | Send many flags in one byte instead of many separate numbers |
| Speed | Less data on low-bandwidth radio links |
| Standardization | Same representation across systems |
| Extensibility | Add new flags without breaking old messages |

---

### Practical note
The `HEARTBEAT` message is the minimal set page brought to life: it tells you the vehicle type, autopilot type, system status, and the current mode flags. Keep this page in mind whenever you're debugging a MAVLink link.

### Practical example: setting mode flags
To send GUIDED mode, use `base_mode = 8`.
To send GUIDED + ARMED, use `base_mode = 8 + 128 = 136`.

```python
master.mav.command_long_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_CMD_DO_SET_MODE,
    0,
    8,  # base_mode = GUIDED only
    0, 0, 0, 0, 0, 0
)
```

---

### Summary of the minimal set
1. `HEARTBEAT` is the foundation - check it first.
2. Bitmasks pack multiple flags into one number; use `&` to test them.
3. Enum values are readable names for numeric states.
4. `SYSTEM_ID` and `COMPONENT_ID` identify the drone and its parts.

Now you get both the conceptual minimal-set story and the practical Python code without losing the existing examples.

### UDP Test Script (for debugging)

```python
# test_udp.py
from pymavlink import mavutil
import time

# Try different UDP addresses
# master = mavutil.mavlink_connection('udp:127.0.0.1:14550')
# master = mavutil.mavlink_connection('udp:172.17.192.1:14550')  # WSL IP

master = mavutil.mavlink_connection('udp:127.0.0.1:14550')
print("Listening for MAVLink messages...")

while True:
    msg = master.recv_match(blocking=True, timeout=1)
    if msg:
        print(f"Got: {msg.get_type()}")
```

---

## Troubleshooting Guide

### ❌ "Time moved backwards" Warning

**Cause:** CPU overload causing simulation timing issues

**Solutions:**
1. Reduce simulation speed:
   ```text
   param set SIM_SPEEDUP 1
   ```
2. Use UDP instead of TCP for lighter communication

### ❌ Python Script Hangs on `wait_heartbeat()`

| Possible Cause | Solution |
|:---|:---|
| Wrong IP/port | Check with `output` command |
| No telemetry stream | `output add udp:127.0.0.1:14550` |
| Stream rate too low | `set streamrate 10` |
| Need connection delay | Add `time.sleep(1)` before heartbeat |

### ❌ UDP Not Receiving Messages

**Symptoms:**
- `wait_heartbeat()` succeeds
- `target_system = 0`
- No messages received

**Diagnosis:**
```text
# In MAVProxy
output        # Check active outputs
status        # Check if data is flowing
```

**Fix:** Add explicit output stream:
```text
output add udp:127.0.0.1:14550 -t 1
```

### ❌ "Connection refused"

**Solution:** 
1. Make sure SITL is running
2. Check if port is in use:
   ```bash
   sudo netstat -tulpn | grep 5760
   ```
3. Try restarting SITL

### ❌ GPS not locking (drone won't arm)

**Solution:** Wait 10-15 seconds after SITL starts
- SITL simulates GPS lock automatically
- Check if you see "GPS: lock" in console

### ❌ "No module named 'pymavlink.dialects'"

**Solution:** Reinstall pymavlink
```bash
pip uninstall pymavlink
pip install pymavlink --user
```

### ❌ WSL Display Issues

**Solution:** Set display environment variable
```bash
export DISPLAY=:0
# For WSL2:
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
```

---

## MAVLink Command Reference

### Common Commands and Their Parameters

| Command | ID | Key Parameters | Description |
|---------|-----|----------------|-------------|
| `MAV_CMD_NAV_TAKEOFF` | 22 | param7 = altitude (m) | Take off to altitude |
| `MAV_CMD_NAV_LAND` | 21 | none (all 0) | Land immediately |
| `MAV_CMD_NAV_RETURN_TO_LAUNCH` | 20 | none (all 0) | Return home |
| `MAV_CMD_COMPONENT_ARM_DISARM` | 400 | param1 = 1/0, param2 = 0/21196 | Arm/disarm motors |
| `MAV_CMD_DO_SET_MODE` | 176 | param1 = mode (1=GUIDED) | Change flight mode |
| `MAV_CMD_NAV_WAYPOINT` | 16 | param5 = lat, param6 = lon, param7 = alt | Go to position |

### Flight Mode Values (for MAV_CMD_DO_SET_MODE)

| Value | Mode | Description |
|-------|------|-------------|
| 0 | AUTO | Autonomous mission |
| 1 | GUIDED | Controlled by GCS |
| 2 | LOITER | Hover in place |
| 3 | STABILIZE | Stabilized manual |
| 4 | ACRO | Acrobatic mode |
| 5 | ALT_HOLD | Hold altitude |
| 6 | RTL | Return to Launch |
| 7 | LAND | Landing |

### How to Research Any Command

1. **Interactive Python:**
```python
from pymavlink.dialects.v20 import common as mavlink
help(mavlink.MAV_CMD_NAV_WAYPOINT)
```

2. **Official Docs:** https://mavlink.io/en/messages/common.html#MAV_CMD

3. **Search in Python:**
```python
# Find all commands containing "WAYPOINT"
commands = [c for c in dir(mavlink) if 'WAYPOINT' in c]
print(commands)
```

---

## Quick Reference Card

### Starting SITL
```bash
# Basic start
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map

# With UDP output
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map --out=udp:127.0.0.1:14550
```

### Build Commands
```bash
./waf configure --board sitl
./waf copter
./waf clean
```

### Python Connection Strings
```python
# TCP (most reliable)
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')

# UDP localhost
master = mavutil.mavlink_connection('udp:127.0.0.1:14550')

# UDP with WSL IP (Python on Windows)
master = mavutil.mavlink_connection('udp:172.17.192.1:14550')
```

### Arm/Disarm Sequence in MAVProxy
```text
rc 3 1500                    # Neutral throttle
param set FS_THR_ENABLE 0    # Disable failsafe
arm throttle                 # Arm
disarm                       # Disarm
```

### Useful MAVProxy Commands
```text
output                       # List connections
output add udp:127.0.0.1:14550  # Add UDP output
set streamrate 10            # Set telemetry rate
status                       # Show vehicle status
```

---

## Resources

### Official Documentation
- **MAVLink Guide:** https://mavlink.io/en/guide/
- **MAVLink Commands:** https://mavlink.io/en/messages/common.html#MAV_CMD
- **pymavlink Documentation:** https://ardupilot.org/dev/docs/mavlink-commands.html
- **ArduPilot SITL:** https://ardupilot.org/dev/docs/setting-up-sitl-on-linux.html
- **APM Planner:** https://ardupilot.org/planner2/
- **MAVProxy Documentation:** https://ardupilot.org/mavproxy/

### Community & Help
- **ArduPilot Discussion Forums:** https://discuss.ardupilot.org/
- **MAVLink GitHub:** https://github.com/mavlink/mavlink
- **pymavlink GitHub:** https://github.com/ArduPilot/pymavlink
- **ArduPilot Discord:** https://discord.gg/ardupilot

### Project Structure
```
~/workspace/
├── ardupilot/              # ArduPilot source code
│   ├── build/sitl/bin/arducopter
│   └── Tools/autotest/sim_vehicle.py
└── mavlink_tutorial/       # Your Python scripts
    ├── read_data.py
    ├── control_drone.py
    ├── test_connection.py
    └── test_udp.py
```

---

## Key Takeaways

1. **Always use `--recurse-submodules`** when cloning ArduPilot
2. **Check SITL startup output** to know your active ports
3. **Use TCP (port 5760)** for most reliable Python connections
4. **In WSL, know your IP address** - `127.0.0.1` vs `172.x.x.x`
5. **The `output` command** is your best friend for debugging
6. **Add `time.sleep(1)`** after connection before heartbeat
7. **You don't need to memorize command codes** - you can always look them up

---

**🎉 Congratulations! You've completed the MAVLink and ArduPilot SITL tutorial!**

Remember: All the skills you learned here work with REAL drones too. The only difference is changing the connection string from `tcp:127.0.0.1:5760` to your telemetry radio's serial port (like `/dev/ttyUSB0` or `/dev/ttyACM0`).

Happy flying! 🚁