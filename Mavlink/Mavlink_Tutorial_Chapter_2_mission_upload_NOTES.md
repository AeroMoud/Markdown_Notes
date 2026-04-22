# MAVLink Chapter 2 — Mission Upload: Notes & Tutorial

## What We Were Trying To Do

Upload a multi-waypoint autonomous mission to ArduCopter (in SITL) using
pure MAVLink, arm the drone, take off, and watch it fly the route.

---

## The Problems in the Original Code

### Problem 1 — Takeoff inside AUTO mission doesn't work in SITL

**Original approach:**
- Mission item 0 was `MAV_CMD_NAV_TAKEOFF` with `current=1`.
- Script armed the drone, then immediately called `start_mission()`, which
  switched to AUTO mode and told the drone to start from item 0 (takeoff).

**Why it failed:**
ArduCopter's AUTO-mode takeoff requires an RC throttle input above a minimum
threshold. In SITL (and in pure MAVLink setups with no RC), there is no RC
input, so the drone sits on the ground and never takes off.

**Fix:**
Do the takeoff separately in GUIDED mode *before* starting the mission.
GUIDED-mode takeoff uses the MAVLink command directly and does not depend on
RC throttle at all.

```
Old flow:  arm → switch AUTO → item 0 (TAKEOFF) → waypoints
New flow:  switch GUIDED → arm → takeoff_guided() → switch AUTO → item 1 …
```

---

### Problem 2 — Mission item 0 must be the home placeholder

**Original approach:**
Item 0 was the takeoff command (`current=1`).

**Why it's wrong:**
ArduCopter **always** reserves sequence 0 as the home position placeholder.
It stores item 0 but never executes it. Execution always begins from item 1.
If you put a real command at seq 0, the drone silently skips it.

**Fix:**
Item 0 → home placeholder (`MAV_CMD_NAV_WAYPOINT`, `frame=MAV_FRAME_GLOBAL`,
absolute coordinates, alt=0). Actual waypoints start at seq 1.

---

### Problem 3 — `set_guided_mode` sent the wrong custom_mode

**Original:**
```python
master.mav.command_long_send(
    ..., MAV_CMD_DO_SET_MODE,
    0,
    1,    # base_mode = GUIDED
    0, 0, 0, 0, 0, 0   # ← custom_mode was 0!
)
```

**Why it failed:**
`MAV_CMD_DO_SET_MODE` takes two relevant parameters: param1 = base_mode flag
(always `1` to signal a custom mode change), and param2 = **custom_mode**
(the flight mode number). Sending `0` leaves the drone in whatever mode it
was in. For ArduCopter, GUIDED = custom_mode **4**.

**Fix:**
```python
master.mav.command_long_send(
    ..., MAV_CMD_DO_SET_MODE,
    0,
    1,   # base_mode flag
    4,   # custom_mode = 4 → GUIDED (ArduCopter)
    0, 0, 0, 0, 0
)
```
Also added `wait_for_mode()` — polls HEARTBEAT until `custom_mode == 4`
is confirmed before continuing.

---

### Problem 4 — `make_mission_item` ignored the `frame` parameter

**Original:**
```python
def make_mission_item(seq, frame, ...):
    return dict(
        frame=mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,  # hardcoded!
        ...
    )
```

The `frame` argument was accepted but silently thrown away, so the home
placeholder (which needs `MAV_FRAME_GLOBAL`) was always sent as relative.

**Fix:** Use the `frame` parameter that was passed in:
```python
return dict(
    frame=frame,   # use what the caller specified
    ...
)
```

---

### Problem 5 — Arming had no retry / no force-arm for SITL

SITL frequently fails the first arm attempt due to pre-arm checks
(GPS accuracy, EKF variance, etc.). Added a force-arm retry using the
magic param2 value `21196`, which bypasses pre-arm checks in SITL only.

---

### Problem 6 — Wrong GPS message for home position

Original used `GPS_RAW_INT` (raw sensor data, integer degrees × 1e7).
Replaced with `GLOBAL_POSITION_INT` which also gives `relative_alt`
(altitude above home in mm), making the home-position read-back cleaner.

---

### Problem 7 — `start_mission` started from item 0 instead of item 1

After the GUIDED takeoff is complete, the drone is already airborne.
Sending `mission_set_current` to item 0 (home placeholder) would confuse
ArduCopter. The fix sets current to item 1 so AUTO picks up from the
first real waypoint.

---

## The Fixed Code — Design & Methodology

### Step-by-step plan we followed

```
1. Connect and confirm heartbeat
2. Read home GPS position (GLOBAL_POSITION_INT)
3. Build the mission list in memory
4. Upload the mission to the drone (handshake protocol)
5. Switch to GUIDED mode (confirmed via HEARTBEAT)
6. Arm (with force-arm retry for SITL)
7. Take off in GUIDED to 20 m (poll altitude until reached)
8. Switch to AUTO mode starting from item 1
9. Monitor MISSION_CURRENT / MISSION_ITEM_REACHED messages
```

---

### Phase 1 — Connect

```python
master = mavutil.mavlink_connection('udp:127.0.0.1:14550')
master.wait_heartbeat()
```

`wait_heartbeat()` blocks until the drone sends its first HEARTBEAT message.
That message also sets `master.target_system` and `master.target_component`,
which every subsequent command needs.

UDP (`14550`) is the standard SITL ground-station port. The original code
used TCP (`5760`) which is the direct SITL port — either works but UDP is
the normal GCS convention.

---

### Phase 2 — Build the mission

Each waypoint is a `MISSION_ITEM_INT` message. We build them as plain
Python dicts with `make_mission_item()` and collect them in a list.

```
seq 0  →  Home placeholder  (MAV_FRAME_GLOBAL, absolute, alt=0)
seq 1  →  Waypoint A  (20 m alt, ~100 m north)
seq 2  →  Waypoint B  (30 m alt, ~100 m north + east, hover 3 s)
seq 3  →  Waypoint C  (20 m alt, near home)
seq 4  →  RTL (Return To Launch)
```

Key points:
- **seq 0 is always home.** ArduCopter stores it, never flies it.
- **`MAV_FRAME_GLOBAL_RELATIVE_ALT` (= 3)** means altitude is metres above
  the takeoff point, not above sea level. This is what you almost always want.
- **lat/lon are stored as integers × 1e7** (MISSION_ITEM_INT format):
  `35.123456° → 351234560`. This gives ~1 cm precision in a 32-bit integer.
- **param2 = acceptance radius (metres)**: the drone considers a waypoint
  "reached" when it comes within this distance.
- **param4 = NaN** for yaw means "keep whatever heading you have."

---

### Phase 3 — Upload the mission (handshake protocol)

MAVLink uses a request/response handshake — you cannot just blast all items:

```
GCS                         Drone
 │── MISSION_COUNT(5) ──────►│   "I have 5 items"
 │◄── MISSION_REQUEST_INT(0) ─│   "Send me item 0"
 │── MISSION_ITEM_INT(0) ────►│
 │◄── MISSION_REQUEST_INT(1) ─│   "Send me item 1"
 │── MISSION_ITEM_INT(1) ────►│
 │   … (repeat for all) …
 │◄── MISSION_ACK ────────────│   "All received, mission accepted"
```

If `MISSION_ACK.type != MAV_MISSION_ACCEPTED`, the upload failed and
the error code tells you why (invalid sequence, unsupported frame, etc.).

---

### Phase 4 — GUIDED takeoff (the critical fix)

```python
def takeoff_guided(master, target_alt):
    master.mav.command_long_send(
        ..., MAV_CMD_NAV_TAKEOFF,
        0, 0, 0, 0, 0,   # params unused for copter
        0, 0, target_alt
    )
    # poll GLOBAL_POSITION_INT.relative_alt until >= 95% of target
```

`GLOBAL_POSITION_INT.relative_alt` is in **millimetres**, so we divide by
1000 to get metres. We wait for 95% to avoid waiting for the last few
centimetres of wobble.

---

### Phase 5 — Switch to AUTO and monitor

```python
master.mav.mission_set_current_send(..., 1)   # start from item 1
master.mav.command_long_send(..., MAV_CMD_DO_SET_MODE, 0, 1, 3, ...)
# custom_mode 3 = AUTO for ArduCopter
```

Monitoring messages:
- `MISSION_CURRENT` — sent each time the active waypoint changes.
  `.seq` = which waypoint is next.
- `MISSION_ITEM_REACHED` — sent once when the drone arrives at a waypoint.
  `.seq` = which waypoint was just reached.

---

## Quick Cheat-Sheet: ArduCopter Custom Mode Numbers

| Mode | custom_mode |
|------|------------|
| STABILIZE | 0 |
| AUTO | 3 |
| GUIDED | 4 |
| LOITER | 5 |
| RTL | 6 |

These are passed as param2 in `MAV_CMD_DO_SET_MODE`.

---

## Summary of All Changes

| # | What changed | Why |
|---|---|---|
| 1 | Takeoff moved out of mission into `takeoff_guided()` | AUTO takeoff needs RC throttle; GUIDED does not |
| 2 | Mission seq 0 is now home placeholder | ArduCopter reserves seq 0 as home; never executes it |
| 3 | `set_guided_mode` now sends `custom_mode=4` | Missing param made mode change silently fail |
| 4 | Added `wait_for_mode()` confirmation | Without it, arming could happen before mode switch completes |
| 5 | `make_mission_item` now uses the `frame` parameter | It was hardcoded before, breaking the home item's frame |
| 6 | Arm now has force-arm retry (`param2=21196`) | SITL pre-arm checks often block first attempt |
| 7 | Home position now from `GLOBAL_POSITION_INT` | Gives `relative_alt` and is cleaner than `GPS_RAW_INT` |
| 8 | `start_mission` starts from item 1 not item 0 | Drone is already airborne; item 0 is the unused home placeholder |
