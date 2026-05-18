# MAVLink Chapter 3 — Mission Planning & Autonomous Flight

## Table of Contents

- [How Missions Work in MAVLink](#how-missions-work-in-mavlink)
- [The Mission Upload Handshake](#the-mission-upload-handshake)
- [Script 1: mission_upload.py — Build and upload a mission](#script-1-mission_uploadpy)
- [Key Concepts in mission_upload.py](#key-concepts-in-mission_uploadpy)
- [Common Pitfalls and Their Fixes](#common-pitfalls-and-their-fixes)
- [Script 2: telemetry_monitor.py — Live sensor dashboard](#script-2-telemetry_monitorpy)
- [Understanding the Key Telemetry Messages](#understanding-the-key-telemetry-messages)
- [Running Everything Together](#running-everything-together)
- [Requesting Data Streams](#requesting-data-streams)
- [Recap — Key Takeaways](#recap--key-takeaways)
- [Check Yourself](#check-yourself)

---

## How Missions Work in MAVLink

A "mission" is a list of **mission items** stored on the drone. Each item is one command with coordinates and parameters — go to this waypoint, hover here, land there. Your Python script builds that list, uploads it to the drone, then starts it. The drone handles the rest.

Key rules:
- **Sequence 0 is always the home placeholder.** ArduCopter stores it but never executes it. Execution always begins from item 1. If you put a real command at seq 0, the drone silently skips it.
- **Takeoff must happen in GUIDED mode**, not as a mission item. AUTO-mode takeoff requires an RC throttle input above a minimum threshold. In SITL with no RC controller, the drone will sit on the ground and never take off. GUIDED-mode takeoff uses the MAVLink command directly and does not depend on RC at all.
- **GUIDED mode requires `custom_mode=4`**, not 0. The mode change command takes two parameters: `param1=1` (the base_mode flag) and `param2=4` (ArduCopter's number for GUIDED). Sending `param2=0` makes the mode change silently fail.

The complete flight flow for SITL:

```
Old (broken) flow:  arm → switch AUTO → item 0 (TAKEOFF in mission) → waypoints
Correct flow:       switch GUIDED → arm → takeoff_guided() → switch AUTO → item 1+
```

---

## The Mission Upload Handshake

Uploading a mission requires a strict back-and-forth protocol:

```
Your script                     Drone
     |                            |
     |---- MISSION_COUNT -------->|   "I have N items"
     |<--- MISSION_REQUEST_INT ---|   "Send me item 0"
     |---- MISSION_ITEM_INT ----->|   "Here is item 0"
     |<--- MISSION_REQUEST_INT ---|   "Send me item 1"
     |---- MISSION_ITEM_INT ----->|   "Here is item 1"
     |         ... repeat ...     |
     |<--- MISSION_ACK -----------|   "All received, mission accepted"
```

You cannot just blast all items at once. If `MISSION_ACK.type != MAV_MISSION_ACCEPTED`, the upload failed and the error code tells you why (invalid sequence, unsupported frame, etc.).

---

## Script 1: mission_upload.py

This script builds a multi-waypoint mission, uploads it, takes off in GUIDED mode, then switches to AUTO.

```python
#!/usr/bin/env python3
"""
MAVLink Chapter 3 — Mission planning: build and upload a waypoint mission.

Correct flow:
  1. Connect and confirm heartbeat
  2. Read home GPS position (GLOBAL_POSITION_INT)
  3. Build mission list (seq 0 = home placeholder, seq 1+ = real waypoints)
  4. Upload mission via handshake protocol
  5. Switch to GUIDED mode (confirmed via HEARTBEAT)
  6. Arm (with force-arm retry for SITL)
  7. Take off in GUIDED to 20m (poll altitude until reached)
  8. Switch to AUTO mode starting from item 1
  9. Monitor MISSION_CURRENT / MISSION_ITEM_REACHED messages
"""

import time
import math
from pymavlink import mavutil


# ── connection ────────────────────────────────────────────────────────────────

def connect(connection_string='tcp:127.0.0.1:5762'):
    print(f"Connecting to {connection_string}...")
    master = mavutil.mavlink_connection(connection_string)
    time.sleep(1)
    master.wait_heartbeat()
    print(f"  Connected! System {master.target_system}, "
          f"Component {master.target_component}\n")
    return master


# ── flight mode ───────────────────────────────────────────────────────────────

def set_mode(master, custom_mode):
    """
    Switch to an ArduCopter flight mode by its custom_mode number.
    param1=1 is the required base_mode flag.
    param2=custom_mode is the ArduCopter-specific mode number.

    Common values: STABILIZE=0, AUTO=3, GUIDED=4, LOITER=5, RTL=6, LAND=9
    """
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        1,           # param1: MAV_MODE_FLAG_CUSTOM_MODE_ENABLED (always 1)
        custom_mode, # param2: ArduCopter mode number
        0, 0, 0, 0, 0
    )

def wait_for_mode(master, custom_mode, timeout=10):
    """
    Poll HEARTBEAT until custom_mode is confirmed.
    Always wait for mode confirmation before continuing — arming can happen
    before the mode switch completes if you don't wait.
    """
    start = time.time()
    while time.time() - start < timeout:
        hb = master.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
        if hb and hb.custom_mode == custom_mode:
            mode_names = {0:'STABILIZE', 3:'AUTO', 4:'GUIDED', 5:'LOITER',
                          6:'RTL', 9:'LAND'}
            print(f"  Mode confirmed: {mode_names.get(custom_mode, custom_mode)}")
            return True
    print(f"  Mode confirmation timed out (custom_mode={custom_mode})")
    return False

def set_guided_mode(master):
    """Switch to GUIDED mode (custom_mode=4 in ArduCopter)."""
    print("Switching to GUIDED mode...")
    set_mode(master, 4)
    return wait_for_mode(master, 4)

def set_auto_mode(master):
    """Switch to AUTO mode (custom_mode=3 in ArduCopter)."""
    print("Switching to AUTO mode...")
    set_mode(master, 3)
    return wait_for_mode(master, 3)


# ── arming ────────────────────────────────────────────────────────────────────

def arm(master, max_retries=3):
    """
    Arm the drone's motors. Retries up to max_retries times.
    On the second attempt, uses force-arm (param2=21196) to bypass SITL
    pre-arm checks (GPS accuracy, EKF variance, etc.).

    Never use force-arm on a real drone — it bypasses safety checks.
    """
    for attempt in range(max_retries):
        force = attempt > 0  # Use force-arm after first failure
        force_value = 21196 if force else 0
        label = "force-arm" if force else "normal arm"

        print(f"  Arm attempt {attempt + 1}/{max_retries} ({label})...")
        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1,           # param1: 1 = ARM
            force_value, # param2: 0 = normal, 21196 = force bypass
            0, 0, 0, 0, 0
        )

        ack = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
        if ack and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            print("  Armed!")
            return True
        else:
            result = ack.result if ack else 'no ACK'
            print(f"  Arm attempt {attempt + 1} failed. Result: {result}")
            time.sleep(1)

    print("  Arming failed after all retries.")
    return False


# ── guided takeoff ────────────────────────────────────────────────────────────

def takeoff_guided(master, target_alt_m):
    """
    Command the drone to take off in GUIDED mode.
    Polls GLOBAL_POSITION_INT.relative_alt until 95% of target altitude is reached.

    relative_alt is in millimetres — divide by 1000 to get metres.
    We use 95% threshold to avoid waiting for the final centimetres of wobble.
    """
    print(f"  Sending takeoff command — target: {target_alt_m}m...")
    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0, 0, 0, 0,      # params 1-4: unused
        0, 0,            # params 5-6: lat/lon (0 = current position)
        target_alt_m     # param7: target altitude in metres
    )

    target_threshold = target_alt_m * 0.95
    print(f"  Climbing to {target_alt_m}m (waiting for {target_threshold:.1f}m)...")

    while True:
        pos = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=2)
        if pos:
            current_alt = pos.relative_alt / 1000  # mm to m
            print(f"    Altitude: {current_alt:.1f}m")
            if current_alt >= target_threshold:
                print(f"  Takeoff complete — at {current_alt:.1f}m")
                return True


# ── mission building ──────────────────────────────────────────────────────────

def make_mission_item(seq, frame, command, current, autocontinue,
                      param1, param2, param3, param4,
                      lat, lon, alt):
    """
    Returns a MISSION_ITEM_INT message dict.

    lat/lon are in degrees (floats). They are converted to int (×1e7) internally.

    The frame parameter is used as-is — never hardcoded.
    frame=MAV_FRAME_GLOBAL_RELATIVE_ALT (3): altitude relative to home point.
    frame=MAV_FRAME_GLOBAL (0): absolute altitude above sea level.
    """
    return dict(
        seq=seq,
        frame=frame,           # Use the frame that was passed in (not hardcoded)
        command=command,
        current=current,
        autocontinue=autocontinue,
        param1=param1, param2=param2, param3=param3, param4=param4,
        x=int(lat * 1e7),     # latitude as int32 (degrees × 1e7)
        y=int(lon * 1e7),     # longitude as int32 (degrees × 1e7)
        z=alt,                # altitude in metres
    )

def build_mission(home_lat, home_lon):
    """
    Build a simple multi-waypoint mission.

    seq 0  → Home placeholder  (MAV_FRAME_GLOBAL, absolute, alt=0)
              ArduCopter reserves seq 0 as home. It is stored, never executed.
    seq 1  → Waypoint A  (20m alt, ~100m north)
    seq 2  → Waypoint B  (30m alt, ~100m north + east, hover 3s)
    seq 3  → Waypoint C  (20m alt, near home)
    seq 4  → RTL (Return To Launch)

    1 degree latitude = ~111,000m → 100m ≈ 0.0009 degrees
    """
    items = []

    # Item 0: Home placeholder — REQUIRED as first item.
    # ArduCopter always reserves seq 0 for the home position.
    # Must use MAV_FRAME_GLOBAL (absolute coordinates, alt=0).
    items.append(make_mission_item(
        seq=0,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL,  # Absolute, not relative — home is special
        command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        current=0,          # Not the current waypoint (mission starts at item 1)
        autocontinue=1,
        param1=0, param2=0, param3=0, param4=0,
        lat=home_lat, lon=home_lon,
        alt=0               # Home is at altitude 0
    ))

    # Item 1: Waypoint A — move ~100m north at 20m altitude
    items.append(make_mission_item(
        seq=1,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,  # Alt relative to home
        command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        current=0, autocontinue=1,
        param1=0,             # Hold time (seconds) at this waypoint
        param2=2,             # Acceptance radius (metres) — arrive within 2m
        param3=0,             # Pass radius (0 = stop at WP)
        param4=float('nan'),  # Yaw (NaN = keep heading)
        lat=home_lat + 0.0009,
        lon=home_lon,
        alt=20
    ))

    # Item 2: Waypoint B — north + east, climb to 30m, hover 3 seconds
    items.append(make_mission_item(
        seq=2,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        current=0, autocontinue=1,
        param1=3,   # Hover for 3 seconds at this waypoint
        param2=2, param3=0, param4=float('nan'),
        lat=home_lat + 0.0009,
        lon=home_lon + 0.0009,
        alt=30      # Climb to 30m on this leg
    ))

    # Item 3: Waypoint C — back toward home at 20m
    items.append(make_mission_item(
        seq=3,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        current=0, autocontinue=1,
        param1=0, param2=2, param3=0, param4=float('nan'),
        lat=home_lat + 0.0002,
        lon=home_lon,
        alt=20
    ))

    # Item 4: Return To Launch
    items.append(make_mission_item(
        seq=4,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        command=mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
        current=0, autocontinue=1,
        param1=0, param2=0, param3=0, param4=0,
        lat=0, lon=0, alt=0   # RTL ignores lat/lon/alt
    ))

    return items


# ── upload protocol ───────────────────────────────────────────────────────────

def upload_mission(master, items):
    """
    Implements the MAVLink mission upload handshake:
      1. Send MISSION_COUNT
      2. Respond to each MISSION_REQUEST_INT with the matching item
      3. Wait for MISSION_ACK
    """
    print(f"Uploading {len(items)} mission items...")

    master.mav.mission_count_send(
        master.target_system,
        master.target_component,
        len(items),
        mavutil.mavlink.MAV_MISSION_TYPE_MISSION
    )

    upload_start = time.time()
    while time.time() - upload_start < 15:
        msg = master.recv_match(
            type=['MISSION_REQUEST_INT', 'MISSION_REQUEST', 'MISSION_ACK'],
            blocking=True, timeout=3
        )
        if msg is None:
            print("  Timeout waiting for drone response!")
            return False

        msg_type = msg.get_type()

        if msg_type in ('MISSION_REQUEST_INT', 'MISSION_REQUEST'):
            seq = msg.seq
            print(f"  Drone requested item #{seq}")
            item = items[seq]

            master.mav.mission_item_int_send(
                master.target_system,
                master.target_component,
                item['seq'],
                item['frame'],
                item['command'],
                item['current'],
                item['autocontinue'],
                item['param1'], item['param2'],
                item['param3'], item['param4'],
                item['x'],      # lat × 1e7
                item['y'],      # lon × 1e7
                item['z'],      # alt (m)
                mavutil.mavlink.MAV_MISSION_TYPE_MISSION
            )

        elif msg_type == 'MISSION_ACK':
            if msg.type == mavutil.mavlink.MAV_MISSION_ACCEPTED:
                print("  Mission accepted by drone!\n")
                return True
            else:
                print(f"  Mission REJECTED — error code {msg.type}")
                return False

    print("  Upload timed out!")
    return False


# ── start AUTO mission from item 1 ────────────────────────────────────────────

def start_mission(master):
    """
    Switches to AUTO mode and starts the mission from item 1.

    We start from item 1 (not 0) because:
    - The drone is already airborne from the GUIDED takeoff.
    - Item 0 is the home placeholder — it is never executed.
    """
    print("Starting AUTO mission from item 1...")

    # Set mission start item to 1 — skip the home placeholder
    master.mav.mission_set_current_send(
        master.target_system,
        master.target_component,
        1   # Start from item 1 — drone is already airborne
    )
    time.sleep(0.5)

    set_auto_mode(master)
    print("Mission running — drone is flying autonomously.\n")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print(" MAVLink Chapter 3 — Mission Upload & Autonomous Flight")
    print("=" * 60 + "\n")

    master = connect()

    # Get current home position using GLOBAL_POSITION_INT (EKF-fused, not raw GPS)
    # This gives us relative_alt alongside lat/lon, which is cleaner than GPS_RAW_INT.
    print("Reading home position...")
    pos = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=10)
    if pos is None:
        print("Could not get position! Is SITL running?")
        return

    home_lat = pos.lat / 1e7
    home_lon = pos.lon / 1e7
    print(f"  Home: lat={home_lat:.6f}, lon={home_lon:.6f}\n")

    # Build mission
    items = build_mission(home_lat, home_lon)
    print(f"Built mission with {len(items)} items:")
    for i, item in enumerate(items):
        cmd_name = mavutil.mavlink.enums['MAV_CMD'][item['command']].name
        print(f"  [{i}] {cmd_name}  alt={item['z']}m")
    print()

    # Upload
    if not upload_mission(master, items):
        print("Upload failed. Exiting.")
        return

    # Switch to GUIDED — confirm via HEARTBEAT before arming
    if not set_guided_mode(master):
        print("Could not enter GUIDED mode. Exiting.")
        return

    # Arm — retries with force-arm if pre-arm checks block
    if not arm(master):
        print("Could not arm. Exiting.")
        return
    time.sleep(1)

    # Takeoff in GUIDED mode — this works without RC in SITL
    takeoff_guided(master, target_alt_m=20)

    # Switch to AUTO and start from item 1 (drone is already airborne)
    start_mission(master)

    print("Mission is running. Watch the map in SITL!")
    print("Press Ctrl+C to exit the monitor.\n")

    # Mission monitor
    while True:
        msg = master.recv_match(
            type=['MISSION_CURRENT', 'MISSION_ITEM_REACHED'],
            blocking=False
        )
        if msg:
            if msg.get_type() == 'MISSION_CURRENT':
                print(f"  Current waypoint: #{msg.seq}")
            elif msg.get_type() == 'MISSION_ITEM_REACHED':
                print(f"  Reached waypoint #{msg.seq}!")
        time.sleep(0.5)

if __name__ == "__main__":
    main()
```

---

## Key Concepts in mission_upload.py

### MAV_FRAME_GLOBAL_RELATIVE_ALT

The most important frame for beginners. Altitude is relative to the home/takeoff point, not sea level. So `alt=20` means 20m above where it took off, regardless of the terrain's actual elevation. The alternative `MAV_FRAME_GLOBAL` uses absolute altitude (sea level), which is only needed for the home placeholder at seq 0.

### x and y are integers, not floats

`MISSION_ITEM_INT` stores latitude and longitude as `int32` multiplied by 10,000,000. So `lat=35.7749` becomes `x=357749000`. Always convert with `int(lat * 1e7)`.

### param2 — acceptance radius

The drone considers a waypoint "reached" when it comes within this many metres. Set it to 2–5m for simulation. A value of 0 means "stop exactly at the waypoint," which can cause the drone to hover and try to precisely hit the point forever.

### autocontinue=1

After reaching this waypoint, automatically proceed to the next one. Setting it to `0` makes the drone pause and wait for a manual command.

### float('nan') for yaw

Passing `NaN` as the yaw parameter tells ArduPilot "I don't care about heading, fly the most efficient route." Passing a specific angle forces a heading change at that waypoint.

### Coordinate encoding

| Value | What it means | Conversion |
|---|---|---|
| `x` (int32) | Latitude × 1e7 | `35.7749 degrees × 1e7 = 357749000` |
| `y` (int32) | Longitude × 1e7 | Same pattern |
| `z` (float) | Altitude in metres | Already in metres — no conversion |
| 1 degree lat | ~111,000 metres | 100m north ≈ lat + 0.0009 |

---

## Common Pitfalls and Their Fixes

These are real bugs from debugging SITL-based mission scripts. Each one has a subtle failure mode.

### Bug 1 — Takeoff inside AUTO mission doesn't work in SITL

**What happened:** Mission item 0 was `MAV_CMD_NAV_TAKEOFF`. After arming, the script switched to AUTO and the drone just sat there.

**Why it failed:** ArduCopter's AUTO-mode takeoff requires an RC throttle input above a minimum threshold. In SITL (no RC controller), there is no throttle input, so the drone never leaves the ground.

**Fix:** Do the takeoff separately in GUIDED mode *before* starting the AUTO mission. GUIDED-mode takeoff uses the MAVLink command directly and works without RC.

---

### Bug 2 — Mission item 0 must be the home placeholder

**What happened:** Mission item 0 was the takeoff command with `current=1`. The drone never flew the first item.

**Why it failed:** ArduCopter **always** reserves sequence 0 as the home position placeholder. It stores item 0 but never executes it. Execution always begins from item 1.

**Fix:** Item 0 must be a home placeholder (any `MAV_CMD_NAV_WAYPOINT` with `MAV_FRAME_GLOBAL`, absolute coordinates, `alt=0`). Real mission items start at seq 1.

---

### Bug 3 — `set_guided_mode` sent the wrong `custom_mode`

**What happened:** The mode command was sent but the drone never entered GUIDED mode.

**Root cause:** `MAV_CMD_DO_SET_MODE` takes two relevant parameters:
- `param1` = base_mode flag (must be `1` to signal a custom mode change)
- `param2` = **custom_mode** (the flight mode number)

Sending `param2=0` leaves the drone in whatever mode it was already in. For ArduCopter, GUIDED = `custom_mode=4`.

```python
# Wrong — param2=0 silently fails
master.mav.command_long_send(
    ..., MAV_CMD_DO_SET_MODE,
    0,
    1,    # base_mode
    0,    # custom_mode = 0 (STABILIZE, not GUIDED!)
    0, 0, 0, 0, 0
)

# Correct
master.mav.command_long_send(
    ..., MAV_CMD_DO_SET_MODE,
    0,
    1,    # base_mode flag
    4,    # custom_mode = 4 (GUIDED in ArduCopter)
    0, 0, 0, 0, 0
)
```

**Fix:** Always send `custom_mode=4` for GUIDED. Also add `wait_for_mode()` — poll HEARTBEAT until `custom_mode == 4` is confirmed before continuing. Without confirmation, arming can happen before the mode switch completes.

---

### Bug 4 — `make_mission_item` ignored the `frame` parameter

**What happened:** The home placeholder item (seq 0) was rejected by the drone.

**Root cause:** The original `make_mission_item` function accepted a `frame` argument but hardcoded `MAV_FRAME_GLOBAL_RELATIVE_ALT` internally:

```python
# Wrong — frame parameter silently ignored
def make_mission_item(seq, frame, ...):
    return dict(
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,  # Hardcoded!
        ...
    )
```

The home placeholder requires `MAV_FRAME_GLOBAL` (absolute). Sending it as relative caused the drone to reject it.

**Fix:** Use the `frame` parameter that was passed in:

```python
# Correct — use what the caller specified
def make_mission_item(seq, frame, ...):
    return dict(
        frame=frame,   # Use the passed-in value
        ...
    )
```

---

### Bug 5 — Arming had no retry / no force-arm for SITL

**What happened:** The first arm attempt was rejected. The script failed without retrying.

**Why it fails:** SITL frequently fails the first arm attempt due to pre-arm checks (GPS accuracy, EKF variance, etc.).

**Fix:** Retry arming. On the second attempt, use force-arm with `param2=21196`. This magic value bypasses pre-arm checks in SITL. Never use it on a real drone.

---

### Bug 6 — Wrong GPS message for home position

**What happened:** The original script used `GPS_RAW_INT` to get the home position.

**Why it's suboptimal:** `GPS_RAW_INT` gives raw sensor data. `GLOBAL_POSITION_INT` gives EKF-fused data and also includes `relative_alt` (altitude above home in millimetres), making it a cleaner source for both position and altitude.

**Fix:** Use `GLOBAL_POSITION_INT` instead.

---

### Bug 7 — `start_mission` started from item 0 instead of item 1

**What happened:** After the GUIDED takeoff, the script sent `mission_set_current` to item 0 (the home placeholder). This confused ArduCopter.

**Why it failed:** The drone is already airborne. Item 0 is the home placeholder — it is never executed. Starting from item 0 after an airborne takeoff is meaningless.

**Fix:** Set current to item 1 so AUTO picks up from the first real waypoint.

---

### Summary of all fixes

| # | What changed | Why |
|---|---|---|
| 1 | Takeoff moved to `takeoff_guided()` in GUIDED mode | AUTO takeoff needs RC throttle; GUIDED does not |
| 2 | Mission seq 0 is now home placeholder | ArduCopter reserves seq 0 as home; never executes it |
| 3 | `set_guided_mode` now sends `custom_mode=4` | Sending 0 made mode change silently fail |
| 4 | Added `wait_for_mode()` confirmation | Without it, arming can happen before mode switch completes |
| 5 | `make_mission_item` now uses the `frame` parameter | It was hardcoded before, breaking the home item's frame |
| 6 | Arm now has force-arm retry (`param2=21196`) | SITL pre-arm checks often block first attempt |
| 7 | Home position now from `GLOBAL_POSITION_INT` | Gives `relative_alt` and is cleaner than `GPS_RAW_INT` |
| 8 | `start_mission` starts from item 1 not item 0 | Drone is already airborne; item 0 is the unused home placeholder |

---

## Script 2: telemetry_monitor.py

This script builds a live dashboard from all key MAVLink telemetry messages.

```python
#!/usr/bin/env python3
"""
MAVLink Chapter 3 — Live Telemetry Monitor
Parsing GPS, attitude, battery, IMU, and system messages.
"""

import time
import math
from pymavlink import mavutil


# ── message parsers ───────────────────────────────────────────────────────────

def parse_gps(msg):
    """
    GPS_RAW_INT — raw GPS sensor data.
    lat/lon are int32 (×1e7), alt is int32 (mm).
    fix_type: 0=no fix, 1=no fix, 2=2D, 3=3D, 4=DGPS, 5=RTK float, 6=RTK fixed
    """
    fix_names = {0:"No GPS", 1:"No fix", 2:"2D fix", 3:"3D fix",
                 4:"DGPS", 5:"RTK float", 6:"RTK fixed"}
    return {
        'lat':        msg.lat / 1e7,
        'lon':        msg.lon / 1e7,
        'alt_m':      msg.alt / 1000,        # mm to m
        'fix':        fix_names.get(msg.fix_type, "Unknown"),
        'satellites': msg.satellites_visible,
        'hdop':       msg.eph / 100 if msg.eph != 65535 else None,
        # HDOP (horizontal dilution of precision): <1.0 ideal, <2.0 good
    }

def parse_global_position(msg):
    """
    GLOBAL_POSITION_INT — fused position (GPS + EKF filter).
    More accurate than raw GPS for control purposes.
    vx/vy/vz are cm/s.
    """
    return {
        'lat':       msg.lat / 1e7,
        'lon':       msg.lon / 1e7,
        'alt_m':     msg.alt / 1000,          # mm to m (MSL)
        'rel_alt_m': msg.relative_alt / 1000, # mm to m (above home)
        'vx_ms':     msg.vx / 100,            # cm/s to m/s (north)
        'vy_ms':     msg.vy / 100,            # cm/s to m/s (east)
        'vz_ms':     msg.vz / 100,            # cm/s to m/s (down, +ve = down)
        'hdg_deg':   msg.hdg / 100 if msg.hdg != 65535 else None,
    }

def parse_attitude(msg):
    """
    ATTITUDE — Euler angles from the EKF.
    All values are in radians. Convert to degrees for display.
    """
    return {
        'roll_deg':   math.degrees(msg.roll),
        'pitch_deg':  math.degrees(msg.pitch),
        'yaw_deg':    math.degrees(msg.yaw),
        'roll_rate':  math.degrees(msg.rollspeed),   # deg/s
        'pitch_rate': math.degrees(msg.pitchspeed),
        'yaw_rate':   math.degrees(msg.yawspeed),
    }

def parse_raw_imu(msg):
    """
    RAW_IMU — direct accelerometer and gyroscope readings.
    xacc/yacc/zacc: raw accelerometer (milli-g or raw units depending on hardware)
    xgyro/ygyro/zgyro: raw gyro
    xmag/ymag/zmag: magnetometer (milli-Gauss)
    """
    return {
        'accel_x': msg.xacc,
        'accel_y': msg.yacc,
        'accel_z': msg.zacc,
        'gyro_x':  msg.xgyro,
        'gyro_y':  msg.ygyro,
        'gyro_z':  msg.zgyro,
        'mag_x':   msg.xmag,
        'mag_y':   msg.ymag,
        'mag_z':   msg.zmag,
    }

def parse_battery(msg):
    """
    BATTERY_STATUS — battery info (MAVLink 2).
    voltage_battery: mV per cell (array of up to 10 cells), 65535 = not present
    current_battery: cA (centamps), -1 = not measured
    battery_remaining: 0-100%, -1 = not estimated
    """
    voltage_mv = msg.voltages[0] if msg.voltages[0] != 65535 else None
    return {
        'voltage_v':     voltage_mv / 1000 if voltage_mv else None,
        'current_a':     msg.current_battery / 100 if msg.current_battery >= 0 else None,
        'remaining_pct': msg.battery_remaining,
        'capacity_mah':  msg.capacity_consumed if msg.capacity_consumed >= 0 else None,
    }

def parse_sys_status(msg):
    """
    SYS_STATUS — overall system health.
    load: CPU load (0-1000 = 0-100%)
    drop_rate_comm: communication drop rate 0-10000 (0.01% units)
    """
    return {
        'cpu_load_pct':    msg.load / 10,              # 0-1000 to 0-100%
        'voltage_v':       msg.voltage_battery / 1000, # mV to V
        'current_a':       msg.current_battery / 100 if msg.current_battery >= 0 else None,
        'drop_rate_pct':   msg.drop_rate_comm / 100,   # 0.01% units to %
        'sensors_present': msg.onboard_control_sensors_present,
        'sensors_healthy': msg.onboard_control_sensors_health,
    }

def parse_vfr_hud(msg):
    """
    VFR_HUD — the "heads up display" data.
    Cleanest source for airspeed, groundspeed, and climb rate.
    """
    return {
        'airspeed_ms':    msg.airspeed,       # m/s (from airspeed sensor)
        'groundspeed_ms': msg.groundspeed,    # m/s (from GPS)
        'heading_deg':    msg.heading,        # 0-359 degrees
        'throttle_pct':   msg.throttle,       # 0-100%
        'alt_m':          msg.alt,            # m (barometric)
        'climb_ms':       msg.climb,          # m/s (+ve = climbing)
    }


# ── sensor health decoder ─────────────────────────────────────────────────────

SENSOR_FLAGS = {
    1:        "3D gyro",
    2:        "3D accel",
    4:        "3D mag",
    8:        "absolute pressure",
    16:       "differential pressure",
    32:       "GPS",
    64:       "optical flow",
    128:      "vision position",
    256:      "laser position",
    512:      "external ground truth",
    1024:     "3D angular rate control",
    2048:     "attitude stabilization",
    4096:     "yaw position",
    8192:     "altitude control",
    16384:    "X/Y position control",
    32768:    "motor outputs",
    65536:    "RC receiver",
    131072:   "3D gyro 2",
    262144:   "3D accel 2",
    524288:   "3D mag 2",
    1048576:  "geofence",
    2097152:  "AHRS",
    4194304:  "terrain",
    16777216: "logging",
    33554432: "battery",
}

def decode_sensor_health(bitmask):
    """Return list of sensor names that are marked as present and healthy."""
    return [name for bit, name in SENSOR_FLAGS.items() if bitmask & bit]


# ── dashboard display ─────────────────────────────────────────────────────────

def print_dashboard(state):
    print("\n" + "─" * 60)

    pos = state.get('position') or state.get('gps')
    if pos:
        rel_alt = pos.get('rel_alt_m', pos.get('alt_m', '?'))
        print(f"  Position  lat={pos['lat']:.6f}  lon={pos['lon']:.6f}"
              f"  alt={rel_alt:.1f}m (rel)")

    hud = state.get('hud')
    if hud:
        print(f"  Flight    hdg={hud['heading_deg']}  "
              f"gnd={hud['groundspeed_ms']:.1f}m/s  "
              f"climb={hud['climb_ms']:+.1f}m/s  "
              f"throttle={hud['throttle_pct']}%")

    att = state.get('attitude')
    if att:
        print(f"  Attitude  roll={att['roll_deg']:+.1f}  "
              f"pitch={att['pitch_deg']:+.1f}  "
              f"yaw={att['yaw_deg']:+.1f}")

    gps = state.get('gps')
    if gps:
        hdop_str = f"{gps['hdop']:.2f}" if gps['hdop'] else "?"
        print(f"  GPS       {gps['fix']}  "
              f"sats={gps['satellites']}  HDOP={hdop_str}")

    bat = state.get('battery')
    sys = state.get('sys')
    if bat and bat.get('voltage_v'):
        rem = bat['remaining_pct']
        pct_str = f"{rem}%" if rem >= 0 else "?"
        print(f"  Battery   {bat['voltage_v']:.2f}V  {pct_str} remaining")
    elif sys:
        print(f"  Battery   {sys['voltage_v']:.2f}V  (from SYS_STATUS)")

    if sys:
        print(f"  System    CPU={sys['cpu_load_pct']:.1f}%  "
              f"drop_rate={sys['drop_rate_pct']:.2f}%")

    print("─" * 60)


# ── live monitor ──────────────────────────────────────────────────────────────

def monitor(master, duration_seconds=60):
    """
    Collect and display all key telemetry messages for `duration_seconds`.
    Uses recv_match with blocking=False so we process whatever arrives.
    Stores the latest reading of each message type and prints every 2 seconds.
    """
    print(f"Monitoring telemetry for {duration_seconds}s...\n")

    state = {
        'gps': None, 'position': None, 'attitude': None,
        'imu': None, 'battery': None, 'sys': None, 'hud': None,
    }

    parsers = {
        'GPS_RAW_INT':         ('gps',      parse_gps),
        'GLOBAL_POSITION_INT': ('position', parse_global_position),
        'ATTITUDE':            ('attitude', parse_attitude),
        'RAW_IMU':             ('imu',      parse_raw_imu),
        'BATTERY_STATUS':      ('battery',  parse_battery),
        'SYS_STATUS':          ('sys',      parse_sys_status),
        'VFR_HUD':             ('hud',      parse_vfr_hud),
    }

    start = time.time()
    last_print = 0

    while time.time() - start < duration_seconds:
        msg = master.recv_match(blocking=False)

        if msg:
            msg_type = msg.get_type()
            if msg_type in parsers:
                key, parser_fn = parsers[msg_type]
                try:
                    state[key] = parser_fn(msg)
                except Exception:
                    pass  # Skip malformed messages silently

        now = time.time()
        if now - last_print >= 2.0 and any(v is not None for v in state.values()):
            last_print = now
            print_dashboard(state)

        time.sleep(0.01)  # 100 Hz poll


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print(" MAVLink Chapter 3 — Live Telemetry Monitor")
    print("=" * 60 + "\n")

    master = mavutil.mavlink_connection('tcp:127.0.0.1:5762')
    time.sleep(1)
    master.wait_heartbeat()
    print("Connected.\n")

    # Request all data streams at 4 Hz
    # SITL doesn't always stream everything by default
    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL,
        4,   # 4 Hz
        1    # 1 = start streaming
    )
    time.sleep(0.5)

    monitor(master, duration_seconds=120)

if __name__ == "__main__":
    main()
```

---

## Understanding the Key Telemetry Messages

### Raw sensor data vs filtered data

There is a critical distinction that trips up most beginners:

**GPS_RAW_INT** is the direct output of the GPS chip — unfiltered, can jitter, updates at the GPS rate (usually 5–10 Hz). **GLOBAL_POSITION_INT** is the EKF (Extended Kalman Filter) output — GPS blended with IMU and barometer, much smoother, updates at 50 Hz. For displaying position to a user, prefer `GLOBAL_POSITION_INT`. For diagnosing GPS hardware issues, use `GPS_RAW_INT`.

Similarly, **RAW_IMU** gives you direct accelerometer/gyro numbers in raw hardware units. **ATTITUDE** gives you computed Euler angles after EKF processing. Use `ATTITUDE` for any flight logic. Use `RAW_IMU` only if you're debugging sensor calibration.

**VFR_HUD** is the cleanest message for a ground station display — specifically designed to give you speed, altitude, heading, climb rate, and throttle without combining multiple messages.

### Telemetry message field reference

| Message | Key Fields | Units / Notes |
|---|---|---|
| `GLOBAL_POSITION_INT` | `lat`, `lon` | int32 × 1e7; divide by 1e7 for degrees |
| `GLOBAL_POSITION_INT` | `alt` | int32 mm above MSL; divide by 1000 for metres |
| `GLOBAL_POSITION_INT` | `relative_alt` | int32 mm above home; divide by 1000 for metres |
| `GLOBAL_POSITION_INT` | `vx`, `vy`, `vz` | int16 cm/s; divide by 100 for m/s; vz positive = down |
| `GLOBAL_POSITION_INT` | `hdg` | uint16 centidegrees; divide by 100 for degrees; 65535 = unknown |
| `GPS_RAW_INT` | `fix_type` | 0=no GPS, 2=2D, 3=3D, 4=DGPS, 5=RTK float, 6=RTK fixed |
| `GPS_RAW_INT` | `eph` | Horizontal position uncertainty × 100 (HDOP × 100) |
| `ATTITUDE` | `roll`, `pitch`, `yaw` | float radians; multiply by `180/pi` for degrees |
| `ATTITUDE` | `rollspeed`, `pitchspeed`, `yawspeed` | float rad/s |
| `SYS_STATUS` | `voltage_battery` | uint16 millivolts; divide by 1000 for volts |
| `SYS_STATUS` | `load` | uint16, range 0-1000 representing 0-100% CPU; divide by 10 |
| `SYS_STATUS` | `drop_rate_comm` | uint16 drop rate in 0.01% units; divide by 100 for % |
| `BATTERY_STATUS` | `voltages[0]` | uint16 mV per cell; 65535 = cell not present |
| `BATTERY_STATUS` | `current_battery` | int16 in 10mA units; -1 = not measured |
| `VFR_HUD` | `airspeed`, `groundspeed`, `climb` | float m/s |
| `VFR_HUD` | `heading` | uint16 degrees, 0-359 |
| `STATUSTEXT` | `severity` | 0=EMERGENCY, 4=WARNING, 6=INFO, 7=DEBUG |

---

## Running Everything Together

**Terminal 1 — start SITL:**
```bash
cd ~/workspace/ardupilot
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map
```

**Terminal 2 — run telemetry monitor** (watch what messages arrive):
```bash
cd ~/workspace/mavlink_tutorial
python3 telemetry_monitor.py
```

**Terminal 3 — upload and run a mission:**
```bash
cd ~/workspace/mavlink_tutorial
python3 mission_upload.py
```

Watch the SITL map window — you should see the drone take off in GUIDED mode, then follow the waypoint path automatically in AUTO mode.

---

## Requesting Data Streams

SITL doesn't always stream all messages by default. Call `request_data_stream_send` to start receiving everything:

```python
master.mav.request_data_stream_send(
    master.target_system,
    master.target_component,
    mavutil.mavlink.MAV_DATA_STREAM_ALL,
    4,   # rate in Hz
    1    # 1 = start, 0 = stop
)
```

You can also request specific groups instead of `ALL`:

| Constant | What it enables |
|---|---|
| `MAV_DATA_STREAM_RAW_SENSORS` | `RAW_IMU`, `SCALED_IMU`, `RAW_PRESSURE` |
| `MAV_DATA_STREAM_EXTENDED_STATUS` | `SYS_STATUS`, `GPS_RAW_INT` |
| `MAV_DATA_STREAM_RC_CHANNELS` | `RC_CHANNELS_SCALED`, `SERVO_OUTPUT_RAW` |
| `MAV_DATA_STREAM_POSITION` | `GLOBAL_POSITION_INT`, `LOCAL_POSITION_NED` |
| `MAV_DATA_STREAM_EXTRA1` | `ATTITUDE`, `SIMSTATE` |
| `MAV_DATA_STREAM_EXTRA2` | `VFR_HUD` |
| `MAV_DATA_STREAM_EXTRA3` | `AHRS`, `WIND`, `RANGEFINDER` |

---

## Recap — Key Takeaways

- **Sequence 0 is always the home placeholder** — ArduCopter stores it, never flies it. Real commands start at seq 1.
- **Takeoff must happen in GUIDED mode** — AUTO takeoff requires RC throttle input which SITL doesn't provide.
- **MAV_CMD_DO_SET_MODE needs both `param1=1` AND `param2=mode_number`** — sending `param2=0` silently fails.
- **Always wait for mode confirmation** via HEARTBEAT before arming or sending the next command.
- **Use `GLOBAL_POSITION_INT` for position feedback**, not `GPS_RAW_INT` — it's EKF-fused and includes `relative_alt`.
- **Force-arm (`param2=21196`) bypasses SITL pre-arm checks** — useful for simulation, dangerous on real hardware.
- **`start_mission` starts from item 1**, not 0 — the drone is already airborne after GUIDED takeoff.
- **`GLOBAL_POSITION_INT.relative_alt` is in millimetres** — always divide by 1000 to get metres.

---

## Check Yourself

**Question 1 — Conceptual:**
Why does ArduCopter require a separate GUIDED-mode takeoff before switching to AUTO in SITL? What would happen if you skipped the GUIDED takeoff and went straight to AUTO with a `MAV_CMD_NAV_TAKEOFF` as mission item 1?

**Question 2 — Code:**
Identify the two bugs in this mission upload code:
```python
def set_guided_mode(master):
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        1, 0, 0, 0, 0, 0, 0
    )
    time.sleep(1)

def make_mission_item(seq, frame, command, ...):
    return dict(
        seq=seq,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        command=command,
        ...
    )
```

**Question 3 — Applied:**
You want to build a mission where the drone: takes off to 15m (in GUIDED), then flies a triangle (3 waypoints at 25m), then returns to launch. Write the `build_mission()` call structure — how many items does the mission list need, what is seq 0, and what happens between the GUIDED takeoff and AUTO mission start?

---

*Tutorial covers MAVLink mission planning and telemetry monitoring for ArduPilot SITL. All examples tested with ArduCopter 4.x and pymavlink 2.x.*
