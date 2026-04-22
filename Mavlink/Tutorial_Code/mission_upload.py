#!/usr/bin/env python3
"""
MAVLink Tutorial - Chapter 2, Part A
Mission planning: build and upload a waypoint mission
"""

import time
from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink2

# ── helpers ──────────────────────────────────────────────────────────────────

def connect(connection_string='udp:127.0.0.1:14550'):
    print(f"Connecting to {connection_string}...")
    master = mavutil.mavlink_connection(connection_string)
    time.sleep(1)
    master.wait_heartbeat()
    print(f"  Connected! System {master.target_system}, "
          f"Component {master.target_component}\n")
    return master

def wait_for_mode(master, custom_mode, timeout=5):
    """Block until HEARTBEAT confirms the requested custom_mode."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        hb = master.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
        if hb and hb.custom_mode == custom_mode:
            return True
    return False

def set_guided_mode(master):
    """Switch to GUIDED so we can arm and take control."""
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        1,    # custom mode enabled
        4,    # GUIDED mode (ArduCopter)
        0, 0, 0, 0, 0
    )
    if wait_for_mode(master, 4):
        print("Mode set to GUIDED")
    else:
        print("WARNING: GUIDED mode not confirmed!")

def arm(master):
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1,      # ARM
        0, 0, 0, 0, 0, 0
    )
    ack = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
    if ack and ack.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
        print("Armed")
    else:
        result = ack.result if ack else "timeout"
        print(f"WARNING: Arm failed (result={result}). Retrying with force-arm...")
        master.mav.command_long_send(
            master.target_system, master.target_component,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0,
            1,
            21196,  # force-arm: bypasses pre-arm checks in SITL
            0, 0, 0, 0, 0
        )
        ack2 = master.recv_match(type='COMMAND_ACK', blocking=True, timeout=5)
        if ack2 and ack2.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
            print("Armed (forced)")
        else:
            print(f"ERROR: Force-arm also failed! result={ack2.result if ack2 else 'timeout'}")

def takeoff_guided(master, target_alt):
    """
    Take off in GUIDED mode to target_alt (metres, relative to home).

    AUTO mode's built-in TAKEOFF command depends on RC throttle input which
    is unavailable in a pure MAVLink / SITL setup.  Issuing the TAKEOFF
    command while already in GUIDED mode bypasses that interlock entirely —
    ArduCopter just climbs to the requested altitude autonomously.
    """
    print(f"Taking off to {target_alt}m (GUIDED)...")
    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0, 0, 0, 0,         # params 1-4 unused for copter takeoff
        0, 0, target_alt    # lat/lon ignored; alt = target metres AGL
    )

    # Poll GLOBAL_POSITION_INT until we reach 95 % of target altitude
    while True:
        msg = master.recv_match(type='GLOBAL_POSITION_INT',
                                blocking=True, timeout=5)
        if msg is None:
            print("  WARNING: no GPS message received")
            continue
        current_alt = msg.relative_alt / 1e3   # mm → m
        print(f"  Altitude: {current_alt:.1f} / {target_alt}m", end='\r')
        if current_alt >= target_alt * 0.95:
            print(f"\n  Reached {current_alt:.1f}m\n")
            break

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
        frame=frame,
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
    Waypoint mission (takeoff is handled separately in GUIDED mode):
      0 → Home placeholder  (ArduCopter never executes seq=0)
      1 → Waypoint A  (+100 m north)
      2 → Waypoint B  (+100 m north, +100 m east, climb to 30 m)
      3 → Waypoint C  (back near home)
      4 → Return To Launch
    """
    items = []

    # Item 0: Home position — ArduCopter reserves seq=0 as home; it is stored
    #         but never executed. Execution always starts from item 1.
    items.append(make_mission_item(
        seq=0,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL,   # absolute, not relative
        command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        current=0, autocontinue=1,
        param1=0, param2=0, param3=0, param4=0,
        lat=home_lat, lon=home_lon, alt=0
    ))

    # Item 1: Waypoint A (move ~100 m north)
    # 1 degree latitude ≈ 111 000 m  →  100 m ≈ 0.0009 degrees
    items.append(make_mission_item(
        seq=1,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        current=1, autocontinue=1,
        param1=0,            # hold time (seconds) at this waypoint
        param2=2,            # acceptance radius (metres)
        param3=0,            # pass radius (0 = stop at WP)
        param4=float('nan'), # yaw (NaN = keep heading)
        lat=home_lat + 0.0009,
        lon=home_lon,
        alt=20
    ))

    # Item 2: Waypoint B (north + east, climb to 30 m)
    items.append(make_mission_item(
        seq=2,
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        command=mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        current=0, autocontinue=1,
        param1=3,            # hover for 3 seconds
        param2=2, param3=0, param4=float('nan'),
        lat=home_lat + 0.0009,
        lon=home_lon + 0.0009,
        alt=30
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
    Switch to AUTO mode.  The drone is already airborne (GUIDED takeoff
    completed), so AUTO picks up from item 1 and flies the waypoints.
    """
    print("Switching to AUTO mode to begin waypoint mission...")

    master.mav.mission_set_current_send(
        master.target_system,
        master.target_component,
        1   # item 0 is home placeholder; start execution from item 1
    )
    time.sleep(0.3)

    master.mav.command_long_send(
        master.target_system, master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        1,      # base_mode flag
        3,      # custom_mode = 3 (AUTO for ArduCopter)
        0, 0, 0, 0, 0
    )
    if wait_for_mode(master, 3):
        print("Mission started! Drone is now flying autonomously.\n")
    else:
        print("WARNING: AUTO mode not confirmed — mission may not start!\n")

# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print(" MAVLink Chapter 2 — Mission Upload & Autonomous Flight")
    print("=" * 55 + "\n")

    master = connect()

    # Get current home position from GPS
    print("Reading home position from GPS...")
    gps = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=10)
    if gps is None:
        print("Could not get GPS fix! Is SITL running?")
        return

    home_lat = gps.lat / 1e7
    home_lon = gps.lon / 1e7
    home_alt = gps.relative_alt / 1e3  # mm -> metres, relative to home
    print(f"  Home: lat={home_lat:.6f}, lon={home_lon:.6f}, rel_alt={home_alt:.1f}m\n")

    # Build and upload mission
    items = build_mission(home_lat, home_lon)
    print(f"Built mission with {len(items)} items:")
    for i, item in enumerate(items):
        cmd_name = mavutil.mavlink.enums['MAV_CMD'][item['command']].name
        print(f"  [{i}] {cmd_name}  alt={item['z']}m")
    print()

    if not upload_mission(master, items):
        print("Upload failed. Exiting.")
        return

    # Arm in GUIDED, take off to 20 m, then hand off to AUTO
    set_guided_mode(master)
    arm(master)
    takeoff_guided(master, target_alt=20)
    start_mission(master)

    print("Mission is running. Watch the map in SITL!")
    print("Press Ctrl+C to exit the monitor.\n")

    last_wp = -1
    while True:
        msg = master.recv_match(
            type=['MISSION_CURRENT', 'MISSION_ITEM_REACHED'],
            blocking=False
        )
        if msg:
            if msg.get_type() == 'MISSION_CURRENT':
                if msg.seq != last_wp:
                    last_wp = msg.seq
                    print(f"  Current waypoint: #{msg.seq}")
            elif msg.get_type() == 'MISSION_ITEM_REACHED':
                print(f"  Reached waypoint #{msg.seq}!")
        time.sleep(0.5)

if __name__ == "__main__":
    main()
