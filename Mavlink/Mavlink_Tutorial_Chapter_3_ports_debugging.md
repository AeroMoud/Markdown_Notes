# 🔌 MAVLink SITL — Port Debugging & Connection Guide

## 📋 Table of Contents
- [The Big Picture](#-the-big-picture)
- [What Actually Starts When You Run SITL](#-what-actually-starts-when-you-run-sitl)
- [The Ports and What They Mean](#-the-ports-and-what-they-mean)
- [TCP vs UDP — The Real Difference](#-tcp-vs-udp--the-real-difference)
- [The WSL IP Problem](#-the-wsl-ip-problem)
- [How to Debug Step by Step](#-how-to-debug-step-by-step)
- [Reading the Tools](#-reading-the-tools)
- [Writing the Connection String](#-writing-the-connection-string)
- [Real Debugging Sessions](#-real-debugging-sessions)
- [Common Mistakes](#-common-mistakes)
- [Recap — Key Takeaways](#-recap--key-takeaways)

---

## 🧠 The Big Picture

Before any ports or commands, get this mental model right.

When you run SITL, you are not running one program. You are running **two programs talking to each other**, and your Python script talks to the **middleman**, not the simulator directly.

```
arducopter  ──►  MAVProxy  ──►  your Python script
(simulator)      (middleman)     (your code)
```

**MAVProxy is the middleman.** It opens ports so that external programs — your Python script, QGroundControl, APM Planner — can connect. You never talk to `arducopter` directly.

> ⚠️ **Important:** When you launch with `sim_vehicle.py`, the script itself is a Python process that connects to `arducopter` internally to manage it. This occupies one connection slot before you even run your script.

---

## 🏗️ What Actually Starts When You Run SITL

When you run this:

```bash
./Tools/autotest/sim_vehicle.py -v ArduCopter --console --map
```

Three things start simultaneously:

```
┌─────────────────────────────────────────────────────────────┐
│                    sim_vehicle.py                           │
│                                                             │
│   ┌─────────────────┐      ┌──────────────────────────┐    │
│   │  arducopter     │ ◄──► │  MAVProxy                │    │
│   │  (the actual    │      │  (the middleman)         │    │
│   │   simulator)    │      │                          │    │
│   │                 │      │  Opens ports:            │    │
│   │  Listens on     │      │  TCP 5760  (primary)     │    │
│   │  TCP 5760       │      │  TCP 5762  (secondary)   │    │
│   │                 │      │  UDP 14550 (broadcast)   │    │
│   └─────────────────┘      │  UDP 14551 (secondary)   │    │
│                             └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

The moment SITL starts, it prints every port it opened. **Always read this startup output** — it is your most reliable source of truth:

```
bind port 5760 for SERIAL0
bind port 5762 for SERIAL1
```

If you don't see these lines, SITL didn't fully start. Wait longer or restart it.

---

## 🚪 The Ports and What They Mean

MAVProxy opens several ports. Each one is a door your script can walk through.

```
┌─────────────────────────────────────────────────────┐
│                    MAVProxy                         │
│                                                     │
│   TCP door 5760  ──  primary connection             │
│   TCP door 5762  ──  secondary connection           │
│   UDP door 14550 ──  broadcast stream               │
│   UDP door 14551 ──  second broadcast stream        │
└─────────────────────────────────────────────────────┘
```

| Port | Protocol | What it is |
|---|---|---|
| **5760** | TCP | The main door. Most reliable. But only ONE client at a time. |
| **5762** | TCP | A second door. Identical behavior to 5760. Usually free. |
| **14550** | UDP | A broadcast. MAVProxy sends data out here continuously. |
| **14551** | UDP | A second broadcast stream. |

### ⚠️ The Critical Rule About TCP 5760

TCP only allows **one client at a time.** When you launch `sim_vehicle.py`, it internally connects to 5760 itself. That means:

```
sim_vehicle.py (internal)  ──► occupies 5760
your Python script         ──► gets refused or starves
```

This is the most common cause of `wait_heartbeat()` hanging forever even though SITL is running fine.

**Port 5762 is your solution** — `sim_vehicle.py` does not connect internally to 5762, so it stays free for your script.

---

## 📻 TCP vs UDP — The Real Difference

Think of TCP and UDP like two different types of communication:

**TCP is like a phone call.**
- You dial a specific number (connect to an IP and port)
- The other side picks up (connection is established)
- You talk back and forth with guaranteed delivery
- Only **one person** can use that phone line at a time
- If you hang up, the line is free again

**UDP is like a radio broadcast.**
- The station (MAVProxy) transmits continuously
- **Anyone** with a receiver can tune in simultaneously
- No "connection" — you just listen
- Packets are not guaranteed to arrive in order

| Property | TCP (5760, 5762) | UDP (14550) |
|---|---|---|
| Clients allowed | One at a time | Unlimited |
| Reliability | Guaranteed delivery | Fire and forget |
| Best for | Reliable scripting | Multiple listeners |
| Python string | `'tcp:127.0.0.1:5760'` | `'udp:0.0.0.0:14550'` |

> **Always try TCP 5762 first** when 5760 is occupied. UDP becomes useful when you need multiple tools connected at the same time.

---

## 🌐 The WSL IP Problem

This is the single most common source of confusion when developing on Windows with WSL.

**The IP address you use depends on where your Python script is running — not where SITL is running.**

Every machine has a loopback address: `127.0.0.1`. This means "this machine talking to itself." The problem with WSL is that WSL and Windows are **two different machines** from a networking perspective, even though they share the same physical computer.

```
┌──────────────────────────────────────────────────────┐
│  Your Physical Computer                              │
│                                                      │
│  ┌─────────────────┐      ┌──────────────────────┐  │
│  │  WSL (Linux)    │      │  Windows             │  │
│  │                 │      │                      │  │
│  │  127.0.0.1 ─────│─ ✗ ──│──── 127.0.0.1        │  │
│  │  (WSL's self)   │      │     (Windows' self)  │  │
│  │                 │      │                      │  │
│  │  172.x.x.x ─────│──────│──── 172.x.x.x        │  │
│  │  (shared bridge)│      │     (same address)   │  │
│  └─────────────────┘      └──────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

| Where is SITL | Where is Python | IP to use |
|---|---|---|
| WSL | WSL (same terminal) | `127.0.0.1` — always works |
| WSL | Windows | Try `127.0.0.1` first. If it fails, use WSL IP (`172.x.x.x`) |
| Native Linux | Native Linux | `127.0.0.1` — always works |

### How to find your WSL IP

Run this **inside WSL**:
```bash
hostname -I
# Output example: 172.25.144.55
```

Or from **Windows PowerShell**:
```powershell
wsl hostname -I
```

That number is what you put in your Python connection string when Python runs on Windows.

---

## 🔍 How to Debug Step by Step

Follow this exact sequence every time you have a connection problem. **Do not skip steps.** Stop the moment you find the problem.

```
START: Python script can't connect / wait_heartbeat() hangs
              │
              ▼
┌─────────────────────────────────────┐
│ Step 1                              │
│ Is SITL actually running?           │
│                                     │
│ Read the SITL terminal — look for:  │
│ "bind port 5760 for SERIAL0"        │
└──────────────┬──────────────────────┘
               │ Yes, I see it
               ▼
┌─────────────────────────────────────┐
│ Step 2                              │
│ Is the port actually open?          │
│                                     │
│ netstat -tlnp | grep 5760           │
│                                     │
│ Look for: LISTEN                    │
└──────────────┬──────────────────────┘
               │ I see LISTEN
               ▼
┌─────────────────────────────────────┐
│ Step 3                              │
│ Is something already connected?     │
│                                     │
│ netstat -tnp | grep 5760            │
│                                     │
│ Look for: ESTABLISHED               │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
  No ESTABLISHED    ESTABLISHED found
       │                │
       ▼                ▼
┌────────────┐   ┌────────────────────────┐
│ Step 4     │   │ Who owns it?           │
│ Raw test   │   │                        │
│            │   │ Is it sim_vehicle.py?  │
│ nc -zv     │   │ → Use port 5762        │
│ 127.0.0.1  │   │                        │
│ 5760       │   │ Is it your old script? │
└─────┬──────┘   │ → kill <PID>           │
      │          └────────────────────────┘
  succeeded
      │
      ▼
┌─────────────────────────────────────┐
│ Step 5                              │
│ Fix connection string in Python     │
│ and run your script                 │
└─────────────────────────────────────┘
```

---

## 📖 Reading the Tools

### `netstat -tlnp | grep 5760` — Is the port open?

```bash
netstat -tlnp | grep 5760
```

**What to look for:**

```
Proto  Local Address      Foreign Address    State    PID/Program
tcp    0.0.0.0:5760       0.0.0.0:*          LISTEN   9671/arducopter
```

| Column | What to look at |
|---|---|
| `0.0.0.0:5760` | Listening on ALL interfaces — reachable from anywhere |
| `127.0.0.1:5760` | Listening on localhost ONLY — not reachable from Windows |
| `LISTEN` | Port is open and waiting |
| `PID/Program` | Which process owns the port |

> **`0.0.0.0` vs `127.0.0.1` is critical.** If you see `127.0.0.1:5760` and Python is on Windows — that is your problem. The port is invisible to Windows.

---

### `netstat -tnp | grep 5760` — Is someone already connected?

```bash
netstat -tnp | grep 5760
```

**Reading the State column:**

| State | Meaning | What to do |
|---|---|---|
| `LISTEN` only | Port open, nobody connected | Connect freely |
| `ESTABLISHED` | Someone is connected right now | Find who and decide |
| `TIME_WAIT` | Previous connection just closed | Wait a few seconds |

**Reading an ESTABLISHED pair — always comes in two lines:**

```
127.0.0.1:5760   127.0.0.1:42110   ESTABLISHED   9671/arducopter
127.0.0.1:42110  127.0.0.1:5760    ESTABLISHED   9668/python3
```

These two lines are two sides of the same connection:

```
python3 (port 42110)  ←──connected──►  arducopter (port 5760)
PID 9668                                PID 9671
```

**How to identify who the connected Python process is:**

```bash
ps aux | grep 9668
```

If it is `sim_vehicle.py` — that is expected and normal. Use port 5762.
If it is your old script — kill it with `kill 9668`.

---

### `nc -zv 127.0.0.1 5760` — Raw connection test

```bash
nc -zv 127.0.0.1 5760
```

This tests the port **without involving Python at all.**

| Output | Meaning |
|---|---|
| `Connection to 127.0.0.1 5760 port succeeded!` | Network is fine — debug Python |
| `Connection refused` | Port is closed — fix SITL first |
| Hangs with no output | Wrong IP address — packet not reaching host |

> **Always run `nc` before running your Python script.** If `nc` fails, Python will also fail. Fix the network side first.

---

### MAVProxy `output` command — inspect UDP streams

Type this directly into the running MAVProxy console:

```
output
```

Output:

```
3 outputs
0: 127.0.0.1:14550
1: 172.25.144.1:14550
2: 127.0.0.1:14551
```

These are every UDP stream MAVProxy is currently broadcasting. To add a new one:

```
output add udp:127.0.0.1:14560
```

---

## ✍️ Writing the Connection String

Your connection string has exactly three parts:

```
'protocol:ip_address:port'
```

**Answer these three questions from `netstat` — never guess:**

### Question 1 — What protocol?
Read the first column of `netstat -tlnp`. It says `tcp` or `udp`.

### Question 2 — What IP?
| Situation | IP to use |
|---|---|
| Python and SITL both in WSL | `127.0.0.1` |
| Python in Windows, SITL in WSL | Run `hostname -I` in WSL, use that IP |

### Question 3 — What port?
Read the Local Address column from `netstat`. The number after the colon.

**Worked example — reading from real `netstat` output:**

```
tcp   0.0.0.0:5760   0.0.0.0:*   LISTEN   9671/arducopter
```

- Protocol → `tcp`
- Python is in WSL, same machine → `127.0.0.1`
- Port → `5760`

Result:
```python
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
```

---

## 🩺 Real Debugging Sessions

These are real outputs with full explanations of what they mean and what to do.

---

### Session 1 — Port occupied by sim_vehicle.py

**`netstat -tnp | grep 5760` output:**
```
tcp   127.0.0.1:42110   127.0.0.1:5760   ESTABLISHED   9668/python3
tcp   127.0.0.1:5760    127.0.0.1:42110  ESTABLISHED   9671/arducopter
```

**Diagnosis:**
- Two ESTABLISHED lines = one connection, two sides
- PID 9668 is a Python process — check with `ps aux | grep 9668`
- That Python process is `sim_vehicle.py` which started internally
- Port 5760 is occupied

**Fix:**
```bash
# Check port 5762 instead
netstat -tlnp | grep 5762
# If it shows LISTEN, use:
master = mavutil.mavlink_connection('tcp:127.0.0.1:5762')
```

---

### Session 2 — Old script still running

**`netstat -tnp | grep 5760` output:**
```
tcp   127.0.0.1:54072   127.0.0.1:5760   ESTABLISHED   6217/python3
tcp   127.0.0.1:5760    127.0.0.1:54072  ESTABLISHED   6220/arducopter
tcp   127.0.0.1:5760    127.0.0.1:39758  TIME_WAIT     -
```

**Diagnosis:**
- PID 6217 is a Python process holding the connection
- TIME_WAIT line shows a previous connection just closed
- Your new script will starve — old script is consuming all heartbeat packets

**Fix:**
```bash
kill 6217
# Wait a few seconds, then run your script
```

---

### Session 3 — Nothing connected, ready to go

**`netstat -tlnp | grep 5760` output:**
```
tcp   0.0.0.0:5760   0.0.0.0:*   LISTEN   9671/arducopter
```

**`netstat -tnp | grep 5760` output:**
```
(nothing)
```

**Diagnosis:**
- Port is open (`LISTEN`)
- No established connections
- Port is listening on all interfaces (`0.0.0.0`)

**Action:**
```python
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
# Safe to connect — slot is free
```

---

## ⚠️ Common Mistakes

### Mistake 1 — Not reading SITL startup output

❌ **Wrong:** Skip the terminal output and immediately try to connect.

✅ **Right:** Always look for `bind port 5760 for SERIAL0` in the SITL terminal before running anything. If you don't see it, SITL is not ready.

---

### Mistake 2 — Using TCP 5760 when sim_vehicle.py is running

❌ **Wrong:** Connecting to 5760 while `sim_vehicle.py` is the launcher.
```python
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
# Hangs on wait_heartbeat() forever
```

✅ **Right:** Use 5762 which stays free for your scripts.
```python
master = mavutil.mavlink_connection('tcp:127.0.0.1:5762')
```

---

### Mistake 3 — Not checking for existing connections before debugging Python

❌ **Wrong:** Staring at Python error messages when the real problem is a stale process on port 5760.

✅ **Right:** Always run `netstat -tnp | grep 5760` first. If you see `ESTABLISHED`, fix that before touching Python.

---

### Mistake 4 — Wrong IP when Python is on Windows

❌ **Wrong:** Using `127.0.0.1` from Windows assuming it reaches WSL.
```python
master = mavutil.mavlink_connection('tcp:127.0.0.1:5760')
# May hang because 127.0.0.1 on Windows is Windows loopback, not WSL
```

✅ **Right:** Find WSL IP and use it.
```bash
# Inside WSL:
hostname -I
# Returns: 172.25.144.55
```
```python
master = mavutil.mavlink_connection('tcp:172.25.144.55:5760')
```

---

### Mistake 5 — Running `nc` or port checks from Windows to verify WSL ports

❌ **Wrong:** Running port checks from Windows PowerShell expecting to see WSL's ports.

✅ **Right:** Always run `netstat` and `nc` from **inside WSL** where SITL is running.

---

### Mistake 6 — UDP connection string using specific IP instead of 0.0.0.0

❌ **Wrong:** Treating UDP like TCP and specifying the server IP.
```python
master = mavutil.mavlink_connection('udp:127.0.0.1:14550')
# Wrong — you are not connecting TO something, you are listening
```

✅ **Right:** Bind to all interfaces so you catch the broadcast.
```python
master = mavutil.mavlink_connection('udp:0.0.0.0:14550')
# 0.0.0.0 means "listen on all interfaces for incoming UDP"
```

---

## 🔁 Recap — Key Takeaways

- **MAVProxy is the middleman** — your Python script never talks to `arducopter` directly
- **`sim_vehicle.py` occupies port 5760 internally** — always use port 5762 when launching with `sim_vehicle.py`
- **TCP allows only one client at a time** — if anything is ESTABLISHED on 5760, your script will starve
- **UDP has no client limit** — use it when multiple tools need to connect simultaneously
- **`netstat -tlnp | grep 5760`** tells you if the port is open and who owns it
- **`netstat -tnp | grep 5760`** tells you if someone is already connected
- **`nc -zv 127.0.0.1 5760`** is the fastest raw test — do this before touching Python
- **`0.0.0.0:5760` vs `127.0.0.1:5760`** in netstat matters — only `0.0.0.0` is reachable from Windows
- **When Python is on Windows and SITL is in WSL** — use `hostname -I` inside WSL to find the correct IP
- **Three questions build your connection string** — protocol (from netstat), IP (same machine or WSL?), port (from netstat)

---

## ✅ Check Yourself

**Question 1 — Conceptual:**
You run `netstat -tnp | grep 5760` and see one ESTABLISHED line where the program is `python3`. You did not run your script yet. What is that Python process, why is it there, and what port should you use instead?

**Question 2 — Applied:**
You run `netstat -tlnp | grep 5760` and see `127.0.0.1:5760 LISTEN`. Your Python script is on Windows. Will it connect? What do you check next and what do you change?

**Question 3 — Debugging:**
Your `nc -zv 127.0.0.1 5760` succeeds. Your Python script still hangs on `wait_heartbeat()`. Walk through every possible cause in order and what command you run to check each one.
