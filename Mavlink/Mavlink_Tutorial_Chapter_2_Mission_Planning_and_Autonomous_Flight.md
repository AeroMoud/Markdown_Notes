Perfect — two great topics that naturally connect. Here's what Chapter 2 will cover:Here's the plan for **Chapter 2**:

**Part A — Mission Planning & Waypoints**: how to build autonomous missions, upload waypoint sequences, monitor mission execution, and handle mission items (takeoff → waypoints → RTL).

**Part B — Telemetry & Sensors**: deep dive into the key MAVLink messages (GPS, IMU, battery, airspeed), how to parse them properly, and building a live telemetry monitor.

Let's start with a visual overview of how all the pieces connect before diving into code.---

## 📚 MAVLink Tutorial — Chapter 2

### Part A: Mission Planning & Autonomous Flight

---

#### Concept: How missions work in MAVLink

A "mission" is a list of **mission items** stored on the drone. Each item is one command with coordinates and parameters — takeoff here, go to this waypoint, land there. Your Python script builds that list, uploads it to the drone, then starts it. The drone handles the rest.

The upload follows a specific **handshake protocol**:

1. You send `MISSION_COUNT` (how many items)
2. Drone replies asking for item `#0`
3. You send `MISSION_ITEM_INT` for item `#0`
4. Drone asks for `#1`, you send it… and so on
5. Drone sends `MISSION_ACK` when done

Let's build this step by step.

---

#### Script 1: `mission_upload.py` — Build and upload a mission

Create this file in `~/workspace/mavlink_tutorial/`:

```python
#!/usr/bin/env python3
"""
MAVLink Tutorial - Chapter 2, Part A
Mission planning: build and upload a waypoint mission
"""

import time
from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink

# ── helpers ──────────────────────────────────────────────────────────────────

def connect(connection_string='tcp:127.0.0.1:5760'):
    print(f"Connecting to {connection_string}...")
    master = mavutil.mavlink_connection(connection_string)
    time.sleep(1)
    master.wait_heartbeat()
    print(f"  Connected! System {master.target_system}, "
          f"Component {master.target_component}\n")
    return master

def set_guided_mode(master):
    """Switch to GUIDED so we can arm and take control."""
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        1,    # base_mode = GUIDED
        0, 0, 0, 0, 0, 0
    )
    time.sleep(1)
    print("Mode set to GUIDED")

def arm(master):
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1,      # ARM
        0, 0, 0, 0, 0, 0
    )
    time.sleep(2)
    print("Armed")

# ── mission building ──────────────────────────────────────────────────────────

def make_mission_item(seq, frame, command, current, autocontinue,
                      param1, param2, param3, param4,
                      lat, lon, alt):
    """
    Returns a MISSION_ITEM_INT message dict.
    
    lat/lon are in degrees (floats). We convert to int (×1e7) internally.
    frame:
      MAV_FRAME_GLOBAL_RELATIVE_ALT = 3  → altitude relative to home
    """
    return dict(
        seq=seq,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        command=command,
        current=current,
        autocontinue=autocontinue,
        param1=param1, param2=param2, param3=param3, param4=param4,
        x=int(lat * 1e7),   # latitude  as int32
        y=int(lon * 1e7),   # longitude as int32
        z=alt,              # altitude in metres
    )

def build_mission(home_lat, home_lon):
    """
    Simple mission:
      0 → Takeoff to 20 m
      1 → Waypoint A  (+100 m north)
      2 → Waypoint B  (+100 m north, +100 m east)
      3 → Waypoint C  (back near home)
      4 → Return To Launch
    """
    items = []

    # Item 0: Takeoff
    items.append(make_mission_item(
        seq=0,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        command=mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        current=1,          # 1 = this is where we start
        autocontinue=1,
        param1=0, param2=0, param3=0, param4=0,
        lat=home_lat, lon=home_lon,
        alt=20              # take off to 20 m
    ))

    # Item 1: Waypoint A (move ~100 m north)
    # 1 degree latitude ≈ 111 000 m  →  100 m ≈ 0.0009 degrees
    items.append(make_mission_item(
        seq=1,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        current=0, autocontinue=1,
        param1=0,   # hold time (seconds) at this waypoint
        param2=2,   # acceptance radius (metres) — arrive within 2 m
        param3=0,   # pass radius (0 = stop at WP)
        param4=float('nan'),  # yaw (NaN = keep heading)
        lat=home_lat + 0.0009,
        lon=home_lon,
        alt=20
    ))

    # Item 2: Waypoint B (north + east)
    items.append(make_mission_item(
        seq=2,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        current=0, autocontinue=1,
        param1=3,   # hover for 3 seconds at this waypoint
        param2=2, param3=0, param4=float('nan'),
        lat=home_lat + 0.0009,
        lon=home_lon + 0.0009,
        alt=30      # climb to 30 m on this leg
    ))

    # Item 3: Waypoint C (back toward home)
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

    # Step 1: Tell the drone how many items are coming
    master.mav.mission_count_send(
        master.target_system,
        master.target_component,
        len(items),
        mavutil.mavlink.MAV_MISSION_TYPE_MISSION
    )

    # Step 2: Respond to each request
    upload_start = time.time()
    while time.time() - upload_start < 15:   # 15 s timeout
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
                item['x'],      # lat ×1e7
                item['y'],      # lon ×1e7
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

# ── start mission ─────────────────────────────────────────────────────────────

def start_mission(master):
    """
    Switches to AUTO mode and starts the mission from item 0.
    AUTO mode tells the drone to follow the uploaded mission.
    """
    print("Starting mission (switching to AUTO mode)...")

    # Set mission start item to 0
    master.mav.mission_set_current_send(
        master.target_system,
        master.target_component,
        0   # start from item 0
    )
    time.sleep(0.5)

    # Switch to AUTO mode (mode ID = 3 for ArduCopter AUTO)
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        1,      # base_mode flag
        3,      # custom_mode = 3 (AUTO for ArduCopter)
        0, 0, 0, 0, 0
    )
    time.sleep(1)
    print("Mission started! Drone is now flying autonomously.\n")

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print(" MAVLink Chapter 2 — Mission Upload & Autonomous Flight")
    print("=" * 55 + "\n")

    master = connect()

    # Get current home position from GPS
    print("Reading home position from GPS...")
    gps = master.recv_match(type='GPS_RAW_INT', blocking=True, timeout=10)
    if gps is None:
        print("Could not get GPS fix! Is SITL running?")
        return

    home_lat = gps.lat / 1e7
    home_lon = gps.lon / 1e7
    print(f"  Home: lat={home_lat:.6f}, lon={home_lon:.6f}\n")

    # Build mission around home position
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

    # Arm and start
    set_guided_mode(master)
    arm(master)
    start_mission(master)

    print("Mission is running. Watch the map in SITL!")
    print("Press Ctrl+C to exit the monitor.\n")

    # Basic mission monitor (Part B covers this in detail)
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

#### Key concepts in this script

**`MAV_FRAME_GLOBAL_RELATIVE_ALT`** — the most important frame for beginners. Altitude is relative to the home/takeoff point, not sea level. So `alt=20` means 20 m above where it took off, regardless of the terrain's actual elevation. The alternative `MAV_FRAME_GLOBAL` uses absolute altitude (sea level), which is confusing in SITL.

**`x` and `y` are integers, not floats** — MAVLink's `MISSION_ITEM_INT` stores latitude and longitude as `int32` multiplied by 10,000,000. So `lat=35.7749` becomes `x=357749000`. Always convert with `int(lat * 1e7)`.

**`param2` (acceptance radius)** — the drone considers a waypoint "reached" when it comes within this many metres. Set it to 2–5 m for simulation. A value of 0 means "stop exactly at the waypoint," which can cause the drone to hover and try to precisely hit the point forever.

**`autocontinue=1`** — after reaching this waypoint, automatically proceed to the next one. Setting it to `0` makes the drone pause and wait for a command.

**`float('nan')` for yaw** — passing `NaN` as the yaw parameter tells ArduPilot "I don't care about heading, fly the most efficient route." Passing a specific angle forces a heading.

---

#### Script 2: `telemetry_monitor.py` — Part B: Live sensor dashboard

```python
#!/usr/bin/env python3
"""
MAVLink Tutorial - Chapter 2, Part B
Telemetry deep dive: parsing GPS, attitude, battery, and system messages
"""

import time
import math
from pymavlink import mavutil

# ── message parsers ───────────────────────────────────────────────────────────

def parse_gps(msg):
    """
    GPS_RAW_INT — raw GPS sensor data
    lat/lon are int32 (×1e7), alt is int32 (mm)
    fix_type: 0=no fix, 1=no fix, 2=2D, 3=3D, 4=DGPS, 5=RTK float, 6=RTK fixed
    """
    fix_names = {0:"No GPS", 1:"No fix", 2:"2D fix", 3:"3D fix",
                 4:"DGPS", 5:"RTK float", 6:"RTK fixed"}
    return {
        'lat':       msg.lat / 1e7,
        'lon':       msg.lon / 1e7,
        'alt_m':     msg.alt / 1000,        # mm → m
        'fix':       fix_names.get(msg.fix_type, "Unknown"),
        'satellites': msg.satellites_visible,
        'hdop':      msg.eph / 100 if msg.eph != 65535 else None,
        # HDOP (horizontal dilution of precision): <1.0 ideal, <2.0 good
    }

def parse_global_position(msg):
    """
    GLOBAL_POSITION_INT — fused position (GPS + EKF filter)
    More accurate than raw GPS for control purposes.
    vx/vy/vz are cm/s
    """
    return {
        'lat':       msg.lat / 1e7,
        'lon':       msg.lon / 1e7,
        'alt_m':     msg.alt / 1000,         # mm → m (MSL)
        'rel_alt_m': msg.relative_alt / 1000, # mm → m (above home)
        'vx_ms':     msg.vx / 100,            # cm/s → m/s (north)
        'vy_ms':     msg.vy / 100,            # cm/s → m/s (east)
        'vz_ms':     msg.vz / 100,            # cm/s → m/s (down, +ve = down)
        'hdg_deg':   msg.hdg / 100 if msg.hdg != 65535 else None,
    }

def parse_attitude(msg):
    """
    ATTITUDE — Euler angles from the EKF
    All values are in radians. Convert to degrees for display.
    rollspeed/pitchspeed/yawspeed are rad/s
    """
    return {
        'roll_deg':  math.degrees(msg.roll),
        'pitch_deg': math.degrees(msg.pitch),
        'yaw_deg':   math.degrees(msg.yaw),
        'roll_rate': math.degrees(msg.rollspeed),   # deg/s
        'pitch_rate':math.degrees(msg.pitchspeed),
        'yaw_rate':  math.degrees(msg.yawspeed),
    }

def parse_raw_imu(msg):
    """
    RAW_IMU — direct accelerometer and gyroscope readings
    xacc/yacc/zacc:  raw accelerometer (milli-g or raw units depending on hw)
    xgyro/ygyro/zgyro: raw gyro (milli-degrees/s or raw units)
    xmag/ymag/zmag:  magnetometer (milli-Gauss)
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
    BATTERY_STATUS — battery info (MAVLink 2)
    voltage_battery: mV per cell (array of up to 10 cells), 65535 = not present
    current_battery: cA (centamps), -1 = not measured
    battery_remaining: 0-100 %, -1 = not estimated
    """
    # First cell voltage (most drones report one pack as cell[0])
    voltage_mv = msg.voltages[0] if msg.voltages[0] != 65535 else None
    return {
        'voltage_v':   voltage_mv / 1000 if voltage_mv else None,
        'current_a':   msg.current_battery / 100 if msg.current_battery >= 0 else None,
        'remaining_pct': msg.battery_remaining,
        'capacity_mah':  msg.capacity_consumed if msg.capacity_consumed >= 0 else None,
    }

def parse_sys_status(msg):
    """
    SYS_STATUS — overall system health
    onboard_control_sensors_present: bitmask of what sensors exist
    onboard_control_sensors_health:  bitmask of what sensors are healthy
    load: CPU load (0-1000 = 0-100%)
    voltage_battery: mV (from the power module, not cell-level)
    drop_rate_comm: communication drop rate 0-10000 (0.01 % units)
    """
    return {
        'cpu_load_pct':   msg.load / 10,              # 0-1000 → 0-100 %
        'voltage_v':      msg.voltage_battery / 1000,  # mV → V
        'current_a':      msg.current_battery / 100 if msg.current_battery >= 0 else None,
        'drop_rate_pct':  msg.drop_rate_comm / 100,   # 0.01% units → %
        'sensors_present': msg.onboard_control_sensors_present,
        'sensors_healthy': msg.onboard_control_sensors_health,
    }

def parse_vfr_hud(msg):
    """
    VFR_HUD — the "heads up display" data (designed for easy ground display)
    This is the cleanest source for airspeed, groundspeed, and climb rate.
    """
    return {
        'airspeed_ms':   msg.airspeed,       # m/s (from airspeed sensor)
        'groundspeed_ms':msg.groundspeed,    # m/s (from GPS)
        'heading_deg':   msg.heading,        # 0-359 degrees
        'throttle_pct':  msg.throttle,       # 0-100 %
        'alt_m':         msg.alt,            # m (barometric)
        'climb_ms':      msg.climb,          # m/s (+ve = climbing)
    }

# ── sensor health decoder ─────────────────────────────────────────────────────

SENSOR_FLAGS = {
    1:       "3D gyro",
    2:       "3D accel",
    4:       "3D mag",
    8:       "absolute pressure",
    16:      "differential pressure",
    32:      "GPS",
    64:      "optical flow",
    128:     "vision position",
    256:     "laser position",
    512:     "external ground truth",
    1024:    "3D angular rate control",
    2048:    "attitude stabilization",
    4096:    "yaw position",
    8192:    "altitude control",
    16384:   "X/Y position control",
    32768:   "motor outputs",
    65536:   "RC receiver",
    131072:  "3D gyro 2",
    262144:  "3D accel 2",
    524288:  "3D mag 2",
    1048576: "geofence",
    2097152: "AHRS",
    4194304: "terrain",
    8388608: "reverse motor",
    16777216:"logging",
    33554432:"battery",
    67108864:"proximity",
    134217728:"satcom",
    268435456:"prearm check",
    536870912:"obstacle avoidance",
}

def decode_sensor_health(bitmask):
    """Return list of sensor names that are marked as present and healthy."""
    return [name for bit, name in SENSOR_FLAGS.items() if bitmask & bit]

# ── live monitor ──────────────────────────────────────────────────────────────

def monitor(master, duration_seconds=60):
    """
    Collect and display all key telemetry messages for `duration_seconds`.
    Uses recv_match with blocking=False so we process whatever arrives.
    """
    print(f"Monitoring telemetry for {duration_seconds}s...\n")

    # We'll store the latest reading of each message type
    state = {
        'gps':       None,
        'position':  None,
        'attitude':  None,
        'imu':       None,
        'battery':   None,
        'sys':       None,
        'hud':       None,
    }

    parsers = {
        'GPS_RAW_INT':          ('gps',      parse_gps),
        'GLOBAL_POSITION_INT':  ('position', parse_global_position),
        'ATTITUDE':             ('attitude', parse_attitude),
        'RAW_IMU':              ('imu',      parse_raw_imu),
        'BATTERY_STATUS':       ('battery',  parse_battery),
        'SYS_STATUS':           ('sys',      parse_sys_status),
        'VFR_HUD':              ('hud',      parse_vfr_hud),
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
                except Exception as e:
                    pass  # silently skip malformed messages

        # Print a dashboard every 2 seconds
        now = time.time()
        if now - last_print >= 2.0 and any(v is not None for v in state.values()):
            last_print = now
            print_dashboard(state)

        time.sleep(0.01)  # 100 Hz poll

def print_dashboard(state):
    print("\n" + "─" * 55)

    pos = state.get('position') or state.get('gps')
    if pos:
        rel_alt = pos.get('rel_alt_m', pos.get('alt_m', '?'))
        print(f"  Position  lat={pos['lat']:.6f}  lon={pos['lon']:.6f}"
              f"  alt={rel_alt:.1f} m (rel)")

    hud = state.get('hud')
    if hud:
        print(f"  Flight    hdg={hud['heading_deg']}°  "
              f"gnd={hud['groundspeed_ms']:.1f} m/s  "
              f"climb={hud['climb_ms']:+.1f} m/s  "
              f"throttle={hud['throttle_pct']}%")

    att = state.get('attitude')
    if att:
        print(f"  Attitude  roll={att['roll_deg']:+.1f}°  "
              f"pitch={att['pitch_deg']:+.1f}°  "
              f"yaw={att['yaw_deg']:+.1f}°")

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
        print(f"  Battery   {bat['voltage_v']:.2f} V  "
              f"{pct_str} remaining")
    elif sys:
        print(f"  Battery   {sys['voltage_v']:.2f} V  "
              f"(from SYS_STATUS)")

    if sys:
        print(f"  System    CPU={sys['cpu_load_pct']:.1f}%  "
              f"drop_rate={sys['drop_rate_pct']:.2f}%")

    print("─" * 55)

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print(" MAVLink Chapter 2 — Live Telemetry Monitor")
    print("=" * 55 + "\n")

    master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
    time.sleep(1)
    master.wait_heartbeat()
    print("Connected.\n")

    # Request all data streams at 4 Hz
    # This is important — SITL doesn't always stream everything by default
    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL,
        4,   # 4 Hz
        1    # start streaming
    )
    time.sleep(0.5)

    monitor(master, duration_seconds=120)

if __name__ == "__main__":
    main()
```

---

#### Understanding the key telemetry messages

There's an important distinction between **raw sensor data** and **filtered/fused data** that trips up most beginners:

`GPS_RAW_INT` is the direct output of the GPS chip — unfiltered, can jitter, updates at the GPS rate (usually 5–10 Hz). `GLOBAL_POSITION_INT` is the EKF (Extended Kalman Filter) output — GPS blended with IMU and barometer, much smoother, updates at 50 Hz. For displaying position to a user, prefer `GLOBAL_POSITION_INT`. For diagnosing GPS hardware issues, use `GPS_RAW_INT`.

Similarly, `RAW_IMU` gives you the direct accelerometer/gyro numbers in raw hardware units. `ATTITUDE` gives you the computed Euler angles after the EKF has processed everything. Use `ATTITUDE` for any flight logic. Use `RAW_IMU` only if you're debugging sensor calibration.

`VFR_HUD` is the cleanest message for a ground station display — it's specifically designed to give you the most useful numbers (speed, altitude, heading, climb rate, throttle) without requiring you to combine multiple messages.

---

#### Running everything together

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

Watch the SITL map window — you should see the drone follow the waypoint path automatically.

---

#### One important `request_data_stream_send` note

SITL doesn't always stream all messages by default. The call:

```python
master.mav.request_data_stream_send(
    master.target_system, master.target_component,
    mavutil.mavlink.MAV_DATA_STREAM_ALL,
    4,   # rate in Hz
    1    # 1 = start, 0 = stop
)
```

tells the drone to start sending everything at 4 Hz. You can also request specific groups instead of `ALL`:

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

#### What's next

Once you're comfortable with these two scripts, natural next steps in a Chapter 3 would be:

- **GeoFence** — define a boundary the drone can't leave
- **Parameter reading/writing** — tune ArduPilot PIDs from Python
- **Real drone connection** — swap `tcp:127.0.0.1:5760` for `/dev/ttyUSB0` and it works on actual hardware
- **Companion computer patterns** — running your Python script *on* a Raspberry Pi attached to the drone

Let me know if you want to dig deeper into any specific part — the mission handshake protocol, the EKF sensor fusion, or anything else!