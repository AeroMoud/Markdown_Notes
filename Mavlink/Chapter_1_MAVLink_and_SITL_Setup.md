# Chapter 1 — MAVLink & ArduPilot SITL: Complete Guide

## Table of Contents

- [What is MAVLink?](#what-is-mavlink)
- [Why it matters in Autonomous Vehicles](#why-it-matters-in-autonomous-vehicles)
- [System Requirements](#system-requirements)
- [Step 1: Install Python and Dependencies](#step-1-install-python-and-dependencies)
- [Step 2: Install pymavlink and MAVProxy](#step-2-install-pymavlink-and-mavproxy)
- [Step 3: Set Up ArduPilot SITL](#step-3-set-up-ardupilot-sitl)
- [Step 4: Build ArduPilot SITL](#step-4-build-ardupilot-sitl)
- [Step 5: Start the Simulated Drone](#step-5-start-the-simulated-drone)
- [Step 6: Connect with APM Planner](#step-6-connect-with-apm-planner)
- [Step 7: Understanding MAVLink Commands](#step-7-understanding-mavlink-commands)
- [Step 8: Python Scripting with MAVLink](#step-8-python-scripting-with-mavlink)
- [Math / Theory — Bitmasks & Enums](#math--theory--bitmasks-and-enums)
- [Code Examples](#code-examples)
- [SITL Network & Ports Reference](#sitl-network--ports-reference)
- [MAVProxy Commands Reference](#mavproxy-commands-reference)
- [Common Mistakes Beginners Make](#common-mistakes-beginners-make)
- [Troubleshooting Guide](#troubleshooting-guide)
- [MAVLink Command Reference](#mavlink-command-reference)
- [Quick Reference Card](#quick-reference-card)
- [Recap — Key Takeaways](#recap--key-takeaways)
- [Check Yourself](#check-yourself)
- [Resources](#resources)

---

## What is MAVLink?

**MAVLink** (Micro Air Vehicle Link) is the communication protocol that drones use to talk to the outside world. Think of it as the postal system of the drone world — every command you send to a drone and every piece of data the drone sends back travels as a MAVLink "packet," a tiny, precise envelope of data with a specific ID number that tells the receiver exactly what's inside.

The simplest analogy: imagine you're controlling a toy car with a remote. The remote sends signals like "go forward," "turn left," and "stop." MAVLink is exactly that — except instead of radio signals, it sends structured binary messages over a network, USB cable, or radio link. The drone autopilot and the ground control software both "speak" MAVLink, so they can understand each other perfectly.

More technically: MAVLink is a **serialization protocol** — it defines how to pack structured data (like GPS coordinates, battery voltage, or arm/disarm commands) into small binary packets, send them over any communication channel (serial, UDP, TCP, Bluetooth), and unpack them on the other side. MAVLink version 2 (the current standard) packets are as small as 11 bytes, making it extremely efficient for low-bandwidth radio links used in real drones.

### What's inside a MAVLink packet?

```
┌────────────────────────────────────────────────────────┐
│  MAVLink v2 Packet Structure                           │
├───────────┬────────────────────────────────────────────┤
│  Magic    │ 0xFD — tells receiver "packet starts here" │
│  Length   │ How many bytes of payload follow           │
│  Flags    │ Incompatibility / compatibility flags      │
│  Seq      │ Sequence number (0–255, then loops)        │
│  Sys ID   │ Which vehicle is this? (e.g., 1 = drone)   │
│  Comp ID  │ Which component? (1 = autopilot)           │
│  Msg ID   │ What type of message? (e.g., 22 = TAKEOFF) │
│  Payload  │ The actual data (GPS coords, voltage, etc) │
│  Checksum │ Error detection                            │
└───────────┴────────────────────────────────────────────┘
```

MAVLink sends short data packets containing specific IDs:
- `ID=22` means Takeoff command
- `ID=24` means GPS Position

Any ground control software that speaks MAVLink can listen to the drone, give it commands, and display telemetry data.

---

## Why it matters in Autonomous Vehicles

MAVLink is not just for flying drones — it's the backbone protocol for a huge portion of **autonomous systems**. ArduPilot (which uses MAVLink) powers not just copters and planes, but also **autonomous ground vehicles (rovers)** and **submarines**. The same protocol, the same Python tools, and the same architecture you learn here transfer directly to the autonomous vehicle industry.

In **autonomous vehicles**, you need exactly what MAVLink provides: a reliable, low-latency, standardized way to send commands to an actuator system (like "turn left 15 degrees") and receive telemetry back (like "current speed: 12 m/s, GPS: 37.7749, -122.4194"). Companies like **Auterion** (which builds enterprise drone software on top of ArduPilot and MAVLink) and projects like **Ardupilot Rover** use this exact protocol for ground vehicle automation.

If MAVLink is implemented incorrectly in an AV system, the consequences are severe: commands arrive out of order and the vehicle executes them in the wrong sequence; a GPS message gets misinterpreted and the vehicle navigates to the wrong location; the heartbeat is not monitored and a disconnected failsafe never triggers. Understanding MAVLink from the ground up means you understand the nervous system of any autonomous vehicle that uses it.

---

## System Requirements

| Requirement | Minimum | Recommended |
|:---|:---|:---|
| Operating System | Ubuntu 18.04+ / Debian 10+ / WSL | Ubuntu 22.04 LTS |
| RAM | 4 GB | 8 GB |
| Disk Space | 10 GB free | 20 GB free |
| Python | 3.6+ | 3.10+ |

> **WSL (Windows Subsystem for Linux)** is fully supported if you are on Windows.

---

## Step 1: Install Python and Dependencies

Open a terminal (`Ctrl + Alt + T`) and run these commands one by one:

### Update your system first

```bash
sudo apt update
sudo apt upgrade -y
```

### Install Python and GUI libraries

```bash
# These packages are required for MAVProxy's GUI features and pymavlink
sudo apt-get install -y \
  python3-dev \        # Python development headers (needed for C extensions)
  python3-opencv \     # Computer vision library (used by some MAVProxy modules)
  python3-wxgtk4.0 \  # wxPython GUI toolkit (MAVProxy uses this for its map)
  python3-pip \        # Python package manager
  python3-matplotlib \ # Plotting library
  python3-lxml \       # XML parser
  python3-pygame       # Game library (used for joystick input in MAVProxy)
```

### Install build tools

```bash
sudo apt-get install -y git build-essential cmake
```

### Install ccache (highly recommended)

```bash
# ccache caches compilation results — makes rebuilds 5–10x faster
sudo apt-get install ccache
```

### Verify Python is working

```bash
python3 --version
# Expected output: Python 3.8.x or higher
```

---

## Step 2: Install pymavlink and MAVProxy

**`pymavlink`** is the Python library that gives you access to all MAVLink message types and lets you write scripts to talk to drones. **`MAVProxy`** is a ground control station that runs entirely in the terminal — it can relay MAVLink streams, accept commands, and act as a proxy between your drone and multiple clients at once.

```bash
# Install pymavlink — the core Python MAVLink library
python3 -m pip install pymavlink --user

# Install MAVProxy and its YAML dependency
python3 -m pip install PyYAML mavproxy --user
```

### Add Python user binaries to your PATH

When you install packages with `--user`, they go into `~/.local/bin/`, which may not be in your PATH by default:

```bash
echo 'export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc
source ~/.bashrc
```

### Verify both are installed

```bash
python3 -c "import pymavlink; print('pymavlink installed successfully!')"
mavproxy.py --version
```

---

## Step 3: Set Up ArduPilot SITL

**SITL** (Software In The Loop) is a full simulation of an ArduPilot autopilot running entirely on your computer. It behaves exactly like a real drone's flight controller — it reads simulated sensor data, runs the real flight code, and outputs motor commands.

### Create a workspace

```bash
mkdir -p ~/workspace
cd ~/workspace
```

### Clone with submodules — this is critical!

ArduPilot depends on many external libraries (called **submodules**) for its hardware abstraction layer (HAL). If you clone without submodules, the build will fail.

```bash
# --recurse-submodules fetches the main repo AND all nested submodules
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
```

| Without Flag | With Flag |
|:---|:---|
| ❌ Only the main repository is cloned | ✅ Main repo + all submodules |
| ❌ Submodule directories exist but are empty | ✅ Complete, buildable codebase |
| ❌ Build will fail immediately | ✅ Ready to compile |

**If you already cloned without the flag:**

```bash
git submodule update --init --recursive
```

### Install ArduPilot's own prerequisites

```bash
cd Tools/environment_install
./install-prereqs-ubuntu.sh -y
cd ../..
```

### Reload environment variables

```bash
source ~/.profile
```

### Add yourself to the dialout group (for real hardware later)

```bash
# This grants permission to access serial/USB ports (needed for real drones)
sudo usermod -a -G dialout $USER
# Note: You must log out and back in for this to take effect
```

---

## Step 4: Build ArduPilot SITL

ArduPilot uses the **`waf`** build system (a Python-based alternative to `make`).

### Configure the build for SITL

```bash
./waf configure --board sitl
```

### Build the ArduCopter vehicle

```bash
# Build only the copter firmware — faster than building all vehicles
./waf copter

# Or build all vehicles:
./waf build
```

### Verify the build succeeded

```bash
ls build/sitl/bin/
# Expected output: arducopter
```

### Clean build (use if something goes wrong)

```bash
./waf clean
./waf copter
```

---

## Step 5: Start the Simulated Drone

You have two ways to launch SITL. Method 2 is strongly recommended for beginners.

### Method 1: Direct Execution (simple, fewer features)

```bash
cd ~/workspace/ardupilot
./build/sitl/bin/arducopter --console --map

# Or specify the vehicle model explicitly
./build/sitl/bin/arducopter --model quad --console --map
```

**Available vehicle models:**

| Flag | Vehicle Type |
|:---|:---|
| `--model quad` | Standard quadcopter (default) |
| `--model hexa` | Hexacopter (6 motors) |
| `--model octa` | Octocopter (8 motors) |
| `--model heli` | Traditional helicopter |

### Method 2: Using `sim_vehicle.py` (recommended)

```bash
cd ~/workspace/ardupilot

# Basic start — console and map window
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map

# With a UDP output stream on port 14550 (needed for external connections)
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map --out=udp:127.0.0.1:14550

# With custom parameters file
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map --param my_params.parm

# With wind simulation (5 m/s from 180 degrees — the south)
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map --wind 5 180

# Run two drones simultaneously (swarm simulation)
./Tools/autotest/sim_vehicle.py -v ArduCopter -I 0 --console --map  # Drone 0
./Tools/autotest/sim_vehicle.py -v ArduCopter -I 1 --console --map  # Drone 1
```

### What you should see after launch

```
┌─────────────────────────────────────────────┐
│  Console Window (Terminal)                  │
│  Scrolling telemetry data in real time      │
│  GPS lock acquired... heartbeat... etc.     │
├─────────────────────────────────────────────┤
│  Map Window (GUI)                           │
│  A helicopter icon on a map                 │
│  Shows drone position and heading           │
└─────────────────────────────────────────────┘
```

> **CRITICAL:** Keep this terminal open for the entire session. Closing it kills the simulated drone.

If the map window doesn't appear, set the display:
```bash
export DISPLAY=:0
# For WSL2:
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
```

---

## Step 6: Connect with APM Planner

**APM Planner 2** is a graphical ground control station — it shows your drone in 3D, displays all telemetry, and lets you interact with your drone through a GUI.

### Download APM Planner

1. Go to: https://github.com/ArduPilot/apm_planner/releases
2. Download: **`APM-Planner_2-2.0.30-x86_64.AppImage`** (~54.5 MB)

### Install and launch

```bash
cd ~/Downloads
chmod +x APM-Planner_2-2.0.30-x86_64.AppImage
./APM-Planner_2-2.0.30-x86_64.AppImage
```

**Optional — move to a permanent location:**
```bash
mkdir -p ~/.local/bin
mv APM-Planner_2-2.0.30-x86_64.AppImage ~/.local/bin/apmplanner
chmod +x ~/.local/bin/apmplanner
apmplanner  # Now you can launch from anywhere
```

### Connect APM Planner to your simulated drone

1. Open APM Planner
2. Click the **"Connect"** button (top right)
3. Set connection type: **TCP**
4. Address: `127.0.0.1`
5. Port: `5760`
6. Click **"Connect"**

**What you will see:**
- A 3D model of your drone
- Artificial horizon
- Battery level, satellite count, altitude
- Live telemetry values updating in real time

---

## Step 7: Understanding MAVLink Commands

This is where most beginners hit a wall. When you see a Python line like:

```python
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0, 1, 0, 0, 0, 0, 0, 0
)
```

...it looks like a wall of numbers. Let's break it down completely.

### Part 1: `master.mav.command_long_send(`

| Part | What it means |
|:---|:---|
| `master` | Your connection object — created with `mavutil.mavlink_connection()` |
| `.mav` | The MAVLink messaging interface inside the connection |
| `.command_long_send` | The function that sends a "long command" (a command with up to 7 parameters) |

There are two command types in MAVLink:

| Function | When to use |
|:---|:---|
| `command_long_send` | Most commands — takes 7 float parameters |
| `command_int` | Commands with precise coordinates (integer lat/lon) |

### Part 2: `mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM`

```python
mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM
#  ^       ^            ^
#  |       |            └─ The constant name (equals integer 400)
#  |       └─ The MAVLink module inside mavutil
#  └─ The Python library installed via pip
```

You could write `400` directly, but the constant is better:
- Self-documenting: you know what 400 means without looking it up
- If the spec ever changes, the library handles it
- Never use magic numbers in production drone code

### Part 3: The 7 parameters (`param1` through `param7`)

Every `command_long_send` always requires exactly **7 command-specific parameters**. If a command only uses 2, you still pass all 7 — the unused ones are set to `0`.

```
┌─────────────────────────────────────────────────────────────┐
│  MAV_CMD_COMPONENT_ARM_DISARM (400)                         │
├──────────┬──────────────────────────────────────────────────┤
│  param1  │  ARM/DISARM — 1 = arm, 0 = disarm               │
│  param2  │  FORCE — 0 = normal, 21196 = bypass safety      │
│  param3  │  unused — must be 0                             │
│  param4  │  unused — must be 0                             │
│  param5  │  unused — must be 0                             │
│  param6  │  unused — must be 0                             │
│  param7  │  unused — must be 0                             │
└──────────┴──────────────────────────────────────────────────┘
```

If you don't fill in all 7 fields, Python will raise a `TypeError`.

### Complete annotated command call

```python
master.mav.command_long_send(
    # TARGET: which drone and which component to send this to
    master.target_system,      # System ID — usually 1 (the autopilot)
    master.target_component,   # Component ID — usually 1 (flight controller)

    # COMMAND: what we want to do
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,  # Command ID 400

    # CONFIRMATION: 0 = send once; 1 = require ACK confirmation
    0,

    # PARAMETERS: always exactly 7
    1,      # param1: ARM (1 = arm, 0 = disarm)
    0,      # param2: FORCE (0 = normal, 21196 = force arm)
    0,      # param3: unused
    0,      # param4: unused
    0,      # param5: unused
    0,      # param6: unused
    0       # param7: unused
)
```

### How parameters are used — visual comparison

```python
# ARM/DISARM — uses param1 and param2
master.mav.command_long_send(..., 1, 0, 0, 0, 0, 0, 0)
#                                  ^  ^  └───┬───┘
#                                  |  |      └─ param3-7 = unused
#                                  |  └─ param2 = Force
#                                  └─ param1 = Arm

# TAKEOFF — uses param7 only (altitude)
master.mav.command_long_send(..., 0, 0, 0, 0, 0, 0, 5)
#                                  └───┬───┘        ^
#                                      |            └─ param7 = altitude
#                                      └─ param1-6 = unused

# SET_MODE — uses param1 (base_mode) and param2 (custom_mode)
master.mav.command_long_send(..., 1, 4, 0, 0, 0, 0, 0)
#                                  ^  ^  └───┬───┘
#                                  |  |      └─ param3-7 = unused
#                                  |  └─ param2 = custom mode (4 = GUIDED)
#                                  └─ param1 = base_mode flag
```

### Parameter usage comparison across commands

| Command | param1 | param2 | param5 | param6 | param7 |
|:---|:---|:---|:---|:---|:---|
| `ARM_DISARM` | Arm (1/0) | Force (0/21196) | 0 | 0 | 0 |
| `NAV_TAKEOFF` | 0 | 0 | 0 | 0 | **altitude** |
| `NAV_WAYPOINT` | Hold time | Radius | **lat** | **lon** | **alt** |
| `NAV_LAND` | 0 | 0 | 0 | 0 | 0 |

### How to find parameters for any command

**Method 1 — Interactive Python shell:**

```python
from pymavlink.dialects.v20 import common as mavlink

# See the integer value of any command constant
print(mavlink.MAV_CMD_NAV_TAKEOFF)           # → 22
print(mavlink.MAV_CMD_COMPONENT_ARM_DISARM)  # → 400
print(mavlink.MAV_CMD_DO_SET_MODE)           # → 176

# Search for commands by keyword
all_cmds = [c for c in dir(mavlink) if 'WAYPOINT' in c]
print(all_cmds)
```

**Method 2 — Official documentation:**

Go to: https://mavlink.io/en/messages/common.html#MAV_CMD

When you open a MAV_CMD page, you will see:
- **Parameter**: the field name (`param1` through `param7`)
- **Label**: a short name describing what it controls
- **Description**: plain-language explanation
- **Values**: allowed values, ranges, or special constants

Reading pattern for `MAV_CMD_COMPONENT_ARM_DISARM`:
1. `param1 = Arm`: 1 means ARM, 0 means DISARM
2. `param2 = Force`: 0 means obey safety checks, 21196 means force the action
3. `param3` through `param7`: unused, set to 0

**Method 3 — Python help:**

```python
from pymavlink.dialects.v20 import common as mavlink
help(mavlink.MAVLink_command_long_message)
```

### Understanding the library structure

- **Dialects**: Different autopilots can add custom commands, grouped by dialect
- **`pymavlink.dialects.v20.common`**: Standard MAVLink 2 commands used by most systems
- **`pymavlink.dialects.v20.ardupilotmega`**: ArduPilot-specific extensions

---

## Step 8: Python Scripting with MAVLink

### Set up your project folder

```bash
mkdir -p ~/workspace/mavlink_tutorial
cd ~/workspace/mavlink_tutorial
```

The scripts below assume your SITL drone is already running in another terminal.

---

## Math / Theory — Bitmasks and Enums

This section explains two fundamental concepts that appear everywhere in MAVLink: **bitmasks** and **enumerated types**. You will encounter them every time you read a `HEARTBEAT` message or interpret flight mode data.

### Enumerated Types (Enums)

An **enumerated type** (enum) is simply a predefined lookup table that maps integers to meaningful names. MAVLink uses enums so that when you read `heartbeat.type = 2`, you don't have to memorize that `2` means "quadrotor" — instead, you look it up in the `MAV_TYPE` enum.

**Key MAVLink enums you will use constantly:**

| Enum Name | What it describes | Example |
|:---|:---|:---|
| `MAV_TYPE` | Type of vehicle | `2` = QUADROTOR |
| `MAV_AUTOPILOT` | Firmware type | `3` = ARDUPILOT |
| `MAV_STATE` | System state | `4` = ACTIVE |
| `MAV_COMPONENT` | Which component | `1` = AUTOPILOT |

```python
# MAV_STATE lookup table — decode heartbeat.system_status
states = {
    0: "UNINIT",            # System not initialized
    1: "BOOT",              # Booting up
    2: "CALIBRATING",       # Calibrating sensors
    3: "STANDBY",           # Ready, waiting for commands
    4: "ACTIVE",            # Flying / mission in progress
    5: "CRITICAL",          # Problem detected — reduced function
    6: "EMERGENCY",         # Immediate landing required
    7: "POWEROFF",          # Shutting down
    8: "FLIGHT_TERMINATION" # Hard stop ordered
}

# MAV_TYPE lookup table — decode heartbeat.type
types = {
    0: "GENERIC",
    1: "FIXED_WING",
    2: "QUADROTOR",
    3: "COAXIAL",
    4: "HELICOPTER",
}
```

### Bitmasks — Packing Many Flags into One Number

A **bitmask** packs multiple yes/no (true/false) flags into a single integer by using each binary bit as an independent flag. This is how MAVLink sends the `base_mode` field in a `HEARTBEAT` — one number that tells you the armed state, guided mode, manual input, and more all at once.

Each bit position represents a power of 2:

```
Bit position:   7    6    5    4    3    2    1    0
Power of 2:   128   64   32   16    8    4    2    1
```

When a flag is **set** (active), its bit is `1`. When **unset** (inactive), its bit is `0`.

#### The `base_mode` bitmask in HEARTBEAT

| Flag Value | Binary | Meaning |
|:---|:---|:---|
| `1` | `0b00000001` | CUSTOM_MODE_ENABLED |
| `2` | `0b00000010` | TEST_MODE_ENABLED |
| `4` | `0b00000100` | AUTO_MODE_ENABLED |
| `8` | `0b00001000` | GUIDED_MODE_ENABLED |
| `16` | `0b00010000` | STABILIZE_MODE_ENABLED |
| `32` | `0b00100000` | HIL_ENABLED (hardware-in-loop) |
| `64` | `0b01000000` | MANUAL_INPUT_ENABLED |
| `128` | `0b10000000` | SAFETY_ARMED |

#### Combining flags

To represent multiple states at once, values are combined with addition (bitwise OR).

Example: Armed + Guided + Stabilize
- `128` (armed) + `8` (guided) + `16` (stabilize) = **152**
- In binary: `0b10011000`

Example: Armed + Guided only
```
Armed:   128  →  0b10000000
Guided:    8  →  0b00001000
                 ----------
Combined: 136  →  0b10001000
```

#### Testing flags with bitwise AND

To test whether a specific flag is set, use the **bitwise AND** operator (`&`):

```python
base_mode = 136  # Armed + Guided

# Is the drone armed?
if base_mode & 128:   # 136 & 128 = 128 (truthy)
    print("Drone is ARMED")

# Is guided mode active?
if base_mode & 8:     # 136 & 8 = 8 (truthy)
    print("GUIDED mode active")

# Is stabilize mode active?
if base_mode & 16:    # 136 & 16 = 0 (falsy)
    print("STABILIZE mode active")  # This won't print
```

#### Decode all flags at once

```python
flags = {
    1:   "CUSTOM_MODE_ENABLED",
    2:   "TEST_MODE_ENABLED",
    4:   "AUTO_MODE_ENABLED",
    8:   "GUIDED_MODE_ENABLED",
    16:  "STABILIZE_MODE_ENABLED",
    32:  "HIL_ENABLED",
    64:  "MANUAL_INPUT_ENABLED",
    128: "SAFETY_ARMED",
}

heartbeat = master.recv_match(type='HEARTBEAT', blocking=True)
base_mode = heartbeat.base_mode

print(f"base_mode raw value: {base_mode}")
print(f"base_mode in binary: {bin(base_mode)}")
print("Active flags:")
for value, name in flags.items():
    if base_mode & value:
        print(f"  ✓ {name}")
```

#### Why bitmasks are used everywhere

| Benefit | Explanation |
|:---|:---|
| **Efficiency** | Send 8 flags in 1 byte instead of 8 separate fields |
| **Speed** | Critical on low-bandwidth radio links (57600 baud serial) |
| **Standardization** | Same representation across all autopilot brands |
| **Extensibility** | Add new flags without breaking existing code |

### The HEARTBEAT Minimal Set

The `HEARTBEAT` message is the only **required** message in MAVLink. Every drone sends one at least once per second to say "I'm alive." If you can receive a heartbeat, the link is working.

```python
# Receive and inspect a heartbeat
heartbeat = master.recv_match(type='HEARTBEAT', blocking=True)
print(f"Drone type: {heartbeat.type}")
print(f"Autopilot: {heartbeat.autopilot}")
print(f"System status: {heartbeat.system_status}")
print(f"Mode flags: {heartbeat.base_mode}")  # This is a bitmask
```

The `SYSTEM_ID` and `COMPONENT_ID` fields in every message identify which vehicle and which component sent it. `wait_heartbeat()` populates `master.target_system` and `master.target_component` automatically.

---

## Code Examples

### Script 1: Basic Connection Test

```python
# test_connection.py
from pymavlink import mavutil
import time

CONNECTION_STRING = 'tcp:127.0.0.1:5760'

print(f"Connecting to drone at {CONNECTION_STRING}...")
master = mavutil.mavlink_connection(CONNECTION_STRING)

# Give the TCP connection a moment to fully establish
time.sleep(1)

print("Waiting for heartbeat signal from drone...")
# wait_heartbeat() blocks until a HEARTBEAT message is received
# This also sets master.target_system and master.target_component
master.wait_heartbeat()

print("Connected to drone!")
print(f"  System ID: {master.target_system}")
print(f"  Component ID: {master.target_component}")
```

---

### Script 2: Reading Telemetry Data

```python
# read_data.py
import time
from pymavlink import mavutil

print("Connecting to SITL drone...")
connection = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
connection.wait_heartbeat()
print("Connected!\n")

print("Reading telemetry for 30 seconds...")
print("-" * 50)

start_time = time.time()
message_count = 0

while time.time() - start_time < 30:
    # recv_match with blocking=False returns None if no message is waiting
    message = connection.recv_match(blocking=False)

    if message:
        message_count += 1
        msg_type = message.get_type()

        if msg_type == "HEARTBEAT":
            print("HEARTBEAT — drone is alive")

        elif msg_type == "GPS_RAW_INT":
            # GPS coordinates are stored as integers (×1e7) to avoid float errors
            lat = message.lat / 1e7
            lon = message.lon / 1e7
            alt = message.alt / 1000  # Convert millimeters to meters
            print(f"GPS — Lat: {lat:.6f}°, Lon: {lon:.6f}°, Alt: {alt:.1f}m")

        elif msg_type == "ATTITUDE":
            # Angles are in radians — convert to degrees for readability
            roll  = message.roll  * (180 / 3.14159)
            pitch = message.pitch * (180 / 3.14159)
            yaw   = message.yaw   * (180 / 3.14159)
            print(f"ATTITUDE — Roll: {roll:.1f}°, Pitch: {pitch:.1f}°, Yaw: {yaw:.1f}°")

    time.sleep(0.5)

print("-" * 50)
print(f"Done. Received {message_count} messages total.")
```

---

### Script 3: Decode a HEARTBEAT Message

```python
# decode_heartbeat.py
from pymavlink import mavutil

master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
master.wait_heartbeat()

# Receive the next heartbeat and decode it
hb = master.recv_match(type='HEARTBEAT', blocking=True)

flags = {
    1:   "CUSTOM_MODE_ENABLED",
    2:   "TEST_MODE_ENABLED",
    4:   "AUTO_MODE_ENABLED",
    8:   "GUIDED_MODE_ENABLED",
    16:  "STABILIZE_MODE_ENABLED",
    32:  "HIL_ENABLED",
    64:  "MANUAL_INPUT_ENABLED",
    128: "SAFETY_ARMED",
}

states = {
    0: "UNINIT", 1: "BOOT", 2: "CALIBRATING", 3: "STANDBY",
    4: "ACTIVE", 5: "CRITICAL", 6: "EMERGENCY", 7: "POWEROFF",
    8: "FLIGHT_TERMINATION"
}

types = {
    0: "GENERIC", 1: "FIXED_WING", 2: "QUADROTOR",
    3: "COAXIAL", 4: "HELICOPTER"
}

print("=== HEARTBEAT DECODED ===")
print(f"Vehicle type:    {types.get(hb.type, 'UNKNOWN')} ({hb.type})")
print(f"System status:   {states.get(hb.system_status, 'UNKNOWN')} ({hb.system_status})")
print(f"base_mode value: {hb.base_mode} (binary: {bin(hb.base_mode)})")
print("\nActive mode flags:")
for value, name in flags.items():
    if hb.base_mode & value:
        print(f"  ✓ {name}")
```

---

### Script 4: Full Drone Control (ARM → TAKEOFF → HOVER → LAND)

```python
# control_drone.py
# Full mission: connect, arm, take off, hover, land, disarm
# SIMULATION ONLY — do not run on a real drone without extra safety code!

import time
from pymavlink import mavutil


def connect_drone(connection_string='tcp:127.0.0.1:5760'):
    """Establish MAVLink connection and wait for heartbeat."""
    print("Connecting to drone...")
    drone = mavutil.mavlink_connection(connection_string)
    time.sleep(1)
    print("Waiting for heartbeat...")
    drone.wait_heartbeat()
    print(f"Connected! System ID: {drone.target_system}\n")
    return drone


def set_mode(drone, base_mode, custom_mode=0):
    """Change flight mode. base_mode=1 with custom_mode=4 is GUIDED."""
    print(f"Setting mode (base_mode={base_mode}, custom_mode={custom_mode})...")
    drone.mav.command_long_send(
        drone.target_system,
        drone.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        base_mode,   # param1: mode flag (1 = custom mode enabled)
        custom_mode, # param2: ArduCopter mode number (4 = GUIDED)
        0, 0, 0, 0, 0
    )
    time.sleep(1)
    print("Mode command sent\n")


def arm_drone(drone, force=False):
    """Arm the drone motors. force=True bypasses safety checks."""
    print("Arming motors...")
    force_value = 21196 if force else 0
    drone.mav.command_long_send(
        drone.target_system,
        drone.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1,            # param1: 1 = ARM
        force_value,  # param2: 0 = normal, 21196 = force
        0, 0, 0, 0, 0
    )
    time.sleep(2)
    print("Motors armed!\n")


def takeoff(drone, altitude_meters=5):
    """Send takeoff command to the specified altitude in meters."""
    print(f"Taking off to {altitude_meters} meters...")
    drone.mav.command_long_send(
        drone.target_system,
        drone.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0, 0, 0, 0, 0, 0,  # params 1–6: unused for basic takeoff
        altitude_meters     # param7: target altitude in meters
    )
    print("Takeoff command sent!\n")


def land(drone):
    """Send land-in-place command."""
    print("Sending land command...")
    drone.mav.command_long_send(
        drone.target_system,
        drone.target_component,
        mavutil.mavlink.MAV_CMD_NAV_LAND,
        0,
        0, 0, 0, 0, 0, 0, 0
    )
    print("Land command sent!\n")


def get_altitude(drone):
    """Get current GPS altitude in meters. Returns None on timeout."""
    msg = drone.recv_match(type='GPS_RAW_INT', blocking=True, timeout=3)
    if msg:
        return msg.alt / 1000  # Convert millimeters to meters
    return None


def main():
    print("MAVLink Drone Control Script")
    print("SIMULATION MODE ONLY")
    print("=" * 50)

    drone = connect_drone()
    set_mode(drone, 1, 4)               # GUIDED mode
    arm_drone(drone, force=False)
    takeoff(drone, altitude_meters=5)

    print("Hovering for 10 seconds...")
    for i in range(10):
        alt = get_altitude(drone)
        if alt is not None:
            print(f"  Altitude: {alt:.1f} meters")
        time.sleep(1)

    land(drone)
    time.sleep(5)

    print("Disarming motors...")
    drone.mav.command_long_send(
        drone.target_system, drone.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        0, 0, 0, 0, 0, 0, 0  # param1=0 means DISARM
    )

    print("\n" + "=" * 50)
    print("Mission complete!")


if __name__ == "__main__":
    main()
```

### Script 5: UDP Test (for debugging connections)

```python
# test_udp.py
from pymavlink import mavutil
import time

# For UDP, use 0.0.0.0 to listen on all interfaces (not a specific server IP)
master = mavutil.mavlink_connection('udp:0.0.0.0:14550')
print("Listening for MAVLink messages on UDP 14550...")

while True:
    msg = master.recv_match(blocking=True, timeout=1)
    if msg:
        print(f"Got: {msg.get_type()}")
```

**How to run the scripts:**

```bash
# Terminal 1 — Start the simulated drone
cd ~/workspace/ardupilot
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map

# Terminal 2 — Run your Python script
cd ~/workspace/mavlink_tutorial
chmod +x control_drone.py
python3 control_drone.py
```

---

## SITL Network & Ports Reference

Understanding which port to connect to is critical. Many beginners connect to the wrong port and wonder why nothing works.

### Default SITL port assignments

| Port | Protocol | Purpose |
|:---|:---|:---|
| **5760** | TCP | Primary SERIAL0 — main GCS link |
| **5762** | TCP | Secondary SERIAL1 — usually free for your script |
| **5763** | TCP | Tertiary SERIAL2 |
| **14550** | UDP | Standard telemetry stream (use for external GCS like QGC) |
| **14551** | UDP | Second UDP broadcast stream |

> **Critical:** When launching with `sim_vehicle.py`, that script internally occupies TCP 5760. Use port 5762 for your Python scripts, or use UDP 14550. See Chapter 4 for the full debugging guide.

### How to find which ports are active

**Method 1 — Read the SITL startup output:**
```
bind port 5760 for SERIAL0
bind port 5762 for SERIAL1
```

**Method 2 — Use MAVProxy `output` command:**
```text
GUIDED> output
3 outputs
0: 172.17.192.1:14550
1: 127.0.0.1:14550
2: 127.0.0.1:14551
```

**Method 3 — Use `netstat`:**
```bash
netstat -uln | grep 14550   # Check UDP ports
netstat -tln | grep 5760    # Check TCP ports
```

### WSL networking

When running SITL in WSL and your Python script in Windows, the networking is more complex:

| IP Address | Meaning |
|:---|:---|
| `127.0.0.1` | Localhost — works when both script and SITL are in the same environment |
| `172.x.x.x` | WSL virtual network — used when crossing the Windows ↔ WSL boundary |

**Find your WSL IP address:**
```bash
# In WSL terminal
hostname -I

# In Windows PowerShell
wsl hostname -I
```

### Connection string decision table

| Scenario | Connection String |
|:---|:---|
| Python in WSL + SITL in WSL | `'tcp:127.0.0.1:5760'` or `'tcp:127.0.0.1:5762'` |
| Python in Windows + SITL in WSL | `'udp:172.x.x.x:14550'` (use WSL IP) |

---

## MAVProxy Commands Reference

MAVProxy is both a standalone GCS and a MAVLink router. Type commands directly into the MAVProxy terminal.

### Essential MAVProxy commands

| Command | What it does |
|:---|:---|
| `output` | List all active MAVLink output connections |
| `output add udp:127.0.0.1:14550` | Add a new UDP output stream |
| `set streamrate 10` | Set telemetry update rate to 10 Hz |
| `status` | Show current vehicle status |
| `heartbeat` | Manually send a heartbeat |
| `module load console` | Load the graphical console module |

### RC control commands (for SITL)

```text
# Set throttle to neutral (1500 µs PWM)
rc 3 1500

# Disable the radio failsafe (prevents arming failure)
param set FS_THR_ENABLE 0

# Arm motors through MAVProxy
arm throttle

# Arm motors bypassing all safety checks
arm throttle force

# Disarm motors
disarm
```

### Common arming error fixes

| Error Message | Cause | Solution |
|:---|:---|:---|
| `Throttle not neutral` | RC channel 3 not at 1500 | `rc 3 1500` |
| `Radio failsafe on` | Failsafe active | `param set FS_THR_ENABLE 0` |
| `Throttle below failsafe` | Throttle value too low | `rc 3 1500` |

---

## Common Mistakes Beginners Make

### Mistake 1: Forgetting `--recurse-submodules` when cloning

**What happens:** Build fails with cryptic errors about missing files.

```bash
# Wrong — will fail to build
git clone https://github.com/ArduPilot/ardupilot.git

# Correct — fetches everything
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git

# Fix if you already cloned wrong
git submodule update --init --recursive
```

### Mistake 2: Connecting before SITL is fully ready

**What happens:** `wait_heartbeat()` blocks forever.

```python
# Wrong — connect immediately and expect heartbeat
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
master.wait_heartbeat()  # May hang if SITL isn't ready yet

# Correct — add a small delay after connection
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
time.sleep(1)
master.wait_heartbeat()
```

### Mistake 3: Wrong number of parameters in `command_long_send`

**What happens:** Python raises `TypeError` about the wrong number of arguments.

```python
# Wrong — only passing 2 params, Python will error
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0, 1, 0  # Missing params 3–7
)

# Correct — all 7 params provided
master.mav.command_long_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0, 1, 0, 0, 0, 0, 0, 0  # params 1–7
)
```

### Mistake 4: Using `==` instead of `&` when testing bitmasks

**What happens:** The condition always evaluates to `True` or `False` incorrectly.

```python
base_mode = 136  # Armed + Guided (binary: 10001000)

# Wrong — using == checks if base_mode IS 128, not if the bit is set
if base_mode == 128:
    print("Armed")       # Will NOT print even though it's armed

# Wrong — comparing & result to True
if (base_mode & 128) == True:  # & returns 128, not True
    print("Armed")              # Will NOT print

# Correct — & returns the bit value; Python treats non-zero as truthy
if base_mode & 128:   # 136 & 128 = 128 (non-zero = truthy)
    print("Armed")    # WILL print correctly
```

### Mistake 5: Using the wrong IP address in WSL

**What happens:** `'tcp:127.0.0.1:5760'` fails when Python is on Windows and SITL is in WSL.

```python
# Wrong — if Python is on Windows and SITL is in WSL
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')  # Won't reach WSL

# Correct — use the WSL virtual IP
master = mavutil.mavlink_connection('udp:172.17.192.1:14550')  # Replace with your WSL IP
# Find your WSL IP with: wsl hostname -I (in PowerShell)
```

### Mistake 6: Forgetting to set GUIDED mode before arming

**What happens:** The arm command is sent, but the drone refuses to arm or arms in the wrong mode.

```python
# Wrong — trying to arm without setting mode first
arm_drone(drone)

# Correct — always set GUIDED mode first
set_mode(drone, 1, 4)   # base_mode=1, custom_mode=4 (GUIDED)
time.sleep(1)
arm_drone(drone)
```

### Mistake 7: Not checking for `None` after `recv_match`

**What happens:** `AttributeError` when accessing fields of a `None` message.

```python
# Wrong — assuming a message always arrives
msg = master.recv_match(type='GPS_RAW_INT', blocking=True, timeout=3)
lat = msg.lat / 1e7  # Crashes if msg is None (timeout)

# Correct — always check first
msg = master.recv_match(type='GPS_RAW_INT', blocking=True, timeout=3)
if msg:
    lat = msg.lat / 1e7
else:
    print("No GPS message received.")
```

---

## Troubleshooting Guide

### "Time moved backwards" warning

**Cause:** Your CPU is overloaded, causing the simulation timing to stutter.

**Fixes:**
1. Reduce simulation speed: `param set SIM_SPEEDUP 1`
2. Close other heavy applications
3. Switch to UDP (lighter than TCP)

### `wait_heartbeat()` hangs forever

| Possible Cause | Solution |
|:---|:---|
| Wrong IP address or port | Verify with `output` command in MAVProxy |
| No telemetry stream on that port | `output add udp:127.0.0.1:14550` |
| Stream rate is 0 | `set streamrate 10` |
| Connection not established yet | Add `time.sleep(1)` before `wait_heartbeat()` |
| TCP 5760 occupied by sim_vehicle.py | Use port 5762 instead |

### UDP connects but `target_system = 0` and no messages arrive

**Diagnosis:**
```text
# In MAVProxy terminal
output        # Verify the UDP stream is listed
status        # Check if any data is flowing at all
```

**Fix:** Add the output stream explicitly:
```text
output add udp:127.0.0.1:14550 -t 1
```

### "Connection refused"

```bash
# Step 1: Make sure SITL is running
# Step 2: Check if something else is using port 5760
sudo netstat -tulpn | grep 5760
# Step 3: Try restarting SITL
# Step 4: Check firewall rules if on a remote machine
```

### GPS not locking / drone won't arm

**Solution:** Wait 10–15 seconds after SITL starts. SITL simulates the GPS lock process. Watch the console for:
```
GPS: lock at ...
```

### "No module named 'pymavlink.dialects'"

```bash
pip uninstall pymavlink
pip install pymavlink --user
```

---

## MAVLink Command Reference

### Most common commands with parameters

| Command | ID | Key Parameters | Description |
|:---|:---|:---|:---|
| `MAV_CMD_NAV_TAKEOFF` | 22 | `param7` = altitude (m) | Take off to altitude |
| `MAV_CMD_NAV_LAND` | 21 | all 0 | Land immediately |
| `MAV_CMD_NAV_RETURN_TO_LAUNCH` | 20 | all 0 | Fly back to home |
| `MAV_CMD_COMPONENT_ARM_DISARM` | 400 | `param1`=1/0, `param2`=0/21196 | Arm / Disarm |
| `MAV_CMD_DO_SET_MODE` | 176 | `param1`=1, `param2`=mode_num | Change flight mode |
| `MAV_CMD_NAV_WAYPOINT` | 16 | `param5`=lat, `param6`=lon, `param7`=alt | Fly to position |
| `MAV_CMD_REQUEST_MESSAGE` | 512 | `param1`=message_id | Request a specific message |
| `MAV_CMD_SET_MESSAGE_INTERVAL` | 511 | `param1`=msg_id, `param2`=interval_us | Set message rate |

### ArduCopter flight mode numbers (for `MAV_CMD_DO_SET_MODE` param2)

| Mode Name | custom_mode value |
|:---|:---|
| STABILIZE | 0 |
| ACRO | 1 |
| ALT_HOLD | 2 |
| AUTO | 3 |
| GUIDED | 4 |
| LOITER | 5 |
| RTL | 6 |
| CIRCLE | 7 |
| LAND | 9 |
| POSHOLD | 16 |
| BRAKE | 17 |

---

## Quick Reference Card

### Starting SITL

```bash
# Basic start
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map

# With UDP output (recommended — avoids TCP 5760 conflict)
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
# TCP port 5762 (avoids sim_vehicle.py occupying 5760)
master = mavutil.mavlink_connection('tcp:127.0.0.1:5762')

# TCP port 5760 (when running arducopter binary directly, not via sim_vehicle.py)
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')

# UDP (multiple clients can connect simultaneously)
master = mavutil.mavlink_connection('udp:0.0.0.0:14550')

# Real drone via USB telemetry radio
master = mavutil.mavlink_connection('/dev/ttyUSB0', baud=57600)

# Windows serial port
master = mavutil.mavlink_connection('COM3', baud=57600)
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
output                            # List connections
output add udp:127.0.0.1:14550   # Add UDP output
set streamrate 10                 # Set telemetry rate
status                            # Show vehicle status
```

### Key Coordinate Conversions

| Raw value | Convert to human units |
|:---|:---|
| `gps.lat` (int) | `gps.lat / 1e7` → degrees |
| `gps.alt` (int, mm) | `gps.alt / 1000` → metres |
| `pos.relative_alt` (int, mm) | `pos.relative_alt / 1000` → metres above home |
| `att.roll` (float, radians) | `att.roll * 180 / math.pi` → degrees |
| `sys.voltage_battery` (int, mV) | `/ 1000` → Volts |

### Recommended Project Structure

```
~/workspace/
├── ardupilot/                      # ArduPilot source code
│   ├── build/sitl/bin/arducopter   # Compiled SITL binary
│   └── Tools/autotest/
│       └── sim_vehicle.py          # SITL launch script
│
└── mavlink_tutorial/               # Your Python scripts
    ├── test_connection.py          # Basic heartbeat test
    ├── read_data.py                # Telemetry reader
    ├── decode_heartbeat.py         # Bitmask / enum decoder
    ├── control_drone.py            # Full ARM → FLY → LAND mission
    └── test_udp.py                 # UDP debugging tool
```

---

## Recap — Key Takeaways

- **MAVLink** is a binary serialization protocol — it packs drone commands and sensor data into tiny packets identified by integer IDs
- **SITL** (Software In The Loop) lets you run a complete ArduPilot simulation on your computer — no hardware needed
- **Always clone ArduPilot with `--recurse-submodules`** — forgetting this is the #1 beginner mistake
- **Port 5762 (TCP)** is the safer choice for Python scripts — port 5760 is often occupied by sim_vehicle.py internally
- **`command_long_send` always takes exactly 7 command-specific parameters** — fill unused ones with `0`
- **Named constants** (`MAV_CMD_COMPONENT_ARM_DISARM`) are always better than magic numbers (`400`)
- **Bitmasks** pack multiple yes/no flags into one number — use `&` (bitwise AND) to test individual flags
- **Enums** are lookup tables that map integer codes to human-readable state names (`MAV_STATE`, `MAV_TYPE`)
- **`HEARTBEAT`** is the foundation of every MAVLink link — it tells you the vehicle type, state, armed status, and active modes
- **In WSL**, know whether your script and SITL are in the same environment — the IP address changes depending on where each runs
- **Set GUIDED mode before arming; arm before takeoff** — the sequence matters
- **Always `time.sleep(1)` after connecting** before calling `wait_heartbeat()`
- **Real drones** work identically — just change the connection string from `tcp:127.0.0.1:5760` to your serial port like `/dev/ttyUSB0`

---

## Check Yourself

**Question 1 (Conceptual):**
A `HEARTBEAT` message arrives with `base_mode = 200`. Which flags are active? Show your working using binary arithmetic.

*(Hint: 200 in binary is `0b11001000`. Check each power-of-2 flag value against the table in the bitmask section.)*

**Question 2 (Applied):**
You want to send a waypoint command to fly your drone to latitude `37.7749`, longitude `-122.4194`, at an altitude of `50 meters`. Write the complete `command_long_send()` call with every parameter correctly filled in and commented.

**Question 3 (Code):**
The following Python snippet is supposed to check whether the drone is armed, but it always prints "Drone is NOT armed" even when you can see on the map that it is armed. Find and fix the bug:

```python
heartbeat = master.recv_match(type='HEARTBEAT', blocking=True)
base_mode = heartbeat.base_mode

if base_mode == 128:
    print("Drone is ARMED")
else:
    print("Drone is NOT armed")
```

**Question 4 (Connection):**
Your Python script uses `'tcp:127.0.0.1:5760'` and hangs on `wait_heartbeat()`. SITL is running. What are the first three things you check and in what order?

---

## Resources

### Official Documentation

| Resource | URL |
|:---|:---|
| MAVLink Developer Guide | https://mavlink.io/en/guide/ |
| MAVLink Command Reference | https://mavlink.io/en/messages/common.html#MAV_CMD |
| pymavlink Python Docs | https://ardupilot.org/dev/docs/mavlink-commands.html |
| ArduPilot SITL Setup | https://ardupilot.org/dev/docs/setting-up-sitl-on-linux.html |
| APM Planner 2 | https://ardupilot.org/planner2/ |
| MAVProxy Documentation | https://ardupilot.org/mavproxy/ |

### Community & Help

| Community | URL |
|:---|:---|
| ArduPilot Discussion Forums | https://discuss.ardupilot.org/ |
| MAVLink GitHub | https://github.com/mavlink/mavlink |
| pymavlink GitHub | https://github.com/ArduPilot/pymavlink |
| ArduPilot Discord | https://discord.gg/ardupilot |
