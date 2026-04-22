#!/usr/bin/env python3
"""
MAVLink Tutorial - Script 2: Complete Drone Control (WORKING ALTITUDE)
"""

import time
from pymavlink import mavutil

def connect_drone():
    """Establish connection to the drone"""
    print("🔌 Connecting to drone...")
    drone = mavutil.mavlink_connection('udp:127.0.0.1:14550')
    time.sleep(1)
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
        1,
        mode_id,
        0, 0, 0, 0, 0
    )
    
    # Wait for mode change confirmation
    time.sleep(2)
    print(f"✅ Mode set\n")

def get_current_mode(drone):
    """Get and print current flight mode"""
    # Request a heartbeat (or wait for next one)
    heartbeat = drone.recv_match(type='HEARTBEAT', blocking=True, timeout=2)
    
    if heartbeat:
        # Custom mode number (ArduPilot specific)
        custom_mode = heartbeat.custom_mode
        
        # Map mode numbers to names (ArduPilot Copter)
        mode_map = {
            0: "STABILIZE",
            1: "ACRO", 
            2: "ALT_HOLD",
            3: "AUTO",
            4: "GUIDED",
            5: "LOITER",
            6: "RTL",
            7: "CIRCLE",
            8: "POSITION",
            9: "LAND",
            10: "OF_LOITER",
            11: "DRIFT",
            13: "SPORT",
            14: "FLIP",
            15: "AUTOTUNE",
            16: "POSHOLD",
            17: "BRAKE",
            18: "THROW",
            19: "AVOID_ADSB",
            20: "GUIDED_NOGPS",
            21: "SMART_RTL",
            22: "FLOWHOLD",
            23: "FOLLOW",
            24: "ZIGZAG",
            25: "SYSTEMID",
            26: "AUTOROTATE",
            27: "AUTO_RTL"
        }
        
        mode_name = mode_map.get(custom_mode, f"UNKNOWN({custom_mode})")
        
        # Also check base mode flags
        is_armed = (heartbeat.base_mode & 128) != 0
        is_guided = (heartbeat.base_mode & 8) != 0
        is_auto = (heartbeat.base_mode & 4) != 0
        
        print(f"📊 Current Mode Status:")
        print(f"   Custom Mode Number: {custom_mode}")
        print(f"   Mode Name: {mode_name}")
        print(f"   Armed: {is_armed}")
        print(f"   Guided Flag: {is_guided}")
        print(f"   Auto Flag: {is_auto}")
        
        return mode_name
    else:
        print("⚠️ No heartbeat received")
        return None


def arm_drone(drone, force=False):
    """Arm the drone"""
    print("⚙️ Arming motors...")
    force_value = 21196 if force else 0
    drone.mav.command_long_send(
        drone.target_system,
        drone.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1,
        force_value,
        0, 0, 0, 0, 0
    )
    
    # Wait for arming
    time.sleep(3)
    
    # Check arming status
    armed = False
    for _ in range(5):
        msg = drone.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
        if msg and (msg.base_mode & 128):  # 128 = MAV_MODE_FLAG_SAFETY_ARMED
            armed = True
            break
    
    if armed:
        print("✅ Motors armed!\n")
    else:
        print("⚠️ Arming might have failed!\n")

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

class AltitudeTracker:
    """Track altitude using multiple sources"""
    def __init__(self, drone):
        self.drone = drone
        self.home_altitude = None
        
    def set_home(self):
        """Capture home altitude at takeoff"""
        print("\n📍 Waiting for home altitude...")
        
        # Try multiple times to get GPS fix
        for attempt in range(10):
            # Use non-blocking to keep trying
            msg = self.drone.recv_match(type='GPS_RAW_INT', blocking=False)
            if msg:
                self.home_altitude = msg.alt / 1000.0
                print(f"🏠 Home altitude set: {self.home_altitude:.2f} meters (MSL)")
                return True
            time.sleep(0.5)
        # Fallback: assume sea level
        print("⚠️ Could not get home altitude, assuming 0 meters")
        self.home_altitude = 0
        return False
    
    def get_altitude(self):
        """Get relative altitude using GLOBAL_POSITION_INT"""
        # This is the most reliable for relative altitude
        msg = self.drone.recv_match(type='GLOBAL_POSITION_INT', blocking=False)
        if msg and hasattr(msg, 'relative_alt'):
            # relative_alt is in millimeters, convert to meters
            return msg.relative_alt / 1000.0
        
        # Fallback to other methods
        vfr_msg = self.drone.recv_match(type='VFR_HUD', blocking=False)
        if vfr_msg and hasattr(vfr_msg, 'alt'):
            return vfr_msg.alt
        
        return None

def monitor_altitude(drone, alt_tracker, duration):
    """Monitor altitude during hover"""
    print("\n📊 Monitoring altitude:")
    print("   (Should climb to ~5 meters then hold)")
    print("-" * 50)
    
    for i in range(duration):
        altitude = alt_tracker.get_altitude()
        
        if altitude is not None:
            # Show altitude with trend indicator
            if i == 0:
                trend = "🚀 Takeoff!"
            elif altitude < 1.0 and i > 2:
                trend = "⚠️ Still on ground?"
            elif altitude < 4.5:
                trend = "⬆️ Climbing"
            elif altitude > 5.5:
                trend = "⬇️ Overshooting"
            else:
                trend = "✅ At target"
            
            print(f"  Second {i+1:2d}: {altitude:5.2f}m  {trend}")
        else:
            print(f"  Second {i+1:2d}: ⚠️ Waiting for data...")
        
        time.sleep(1)
    
    print("-" * 50)

def main():
    print("🚁 MAVLink Drone Control Script (FIXED ALTITUDE)")
    print("⚠️ SIMULATION MODE - Use with SITL")
    print("=" * 50)
    
    # Connect
    drone = connect_drone()
    
    # Create altitude tracker
    alt_tracker = AltitudeTracker(drone)
    
    # Set GUIDED mode
    set_mode(drone, 4)  # 4 = GUIDED

    get_current_mode(drone)
    
    # Give GPS time to get fix
    print("\n📡 Waiting for GPS fix...")
    time.sleep(3)
    
    # Set home altitude BEFORE arming
    alt_tracker.set_home()
    time.sleep(1)
    
    # Arm
    arm_drone(drone, force=False)
    
    # Takeoff to 5 meters
    takeoff(drone, altitude_meters=5)
    
    # Monitor climb and hover
    monitor_altitude(drone, alt_tracker, duration=15)
    
    # Land
    land(drone)
    
    # Wait for landing
    print("\n🛬 Descending...")
    for i in range(20):
        altitude = alt_tracker.get_altitude()
        if altitude is not None:
            print(f"  Altitude: {altitude:.2f}m")
        time.sleep(1)
    
    # Disarm
    print("\n⚙️ Disarming motors...")
    drone.mav.command_long_send(
        drone.target_system,
        drone.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        0, 0, 0, 0, 0, 0, 0
    )
    time.sleep(2)
    
    print("\n" + "=" * 50)
    print("🎉 Mission complete!")

if __name__ == "__main__":
    main()