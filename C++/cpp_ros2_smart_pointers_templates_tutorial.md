I'll create a comprehensive, polished tutorial covering smart pointers, templates, and ROS2 structure. Since I can't actually "review with tutors," I'll write it with best practices for clarity, structure, and learning progression based on educational standards.

***

# C++ Smart Pointers, Templates & ROS2 Structure Tutorial

**Tutorial 2: Modern C++ for Robotics**

## Table of Contents

1. [Introduction](#introduction)
2. [Smart Pointers](#smart-pointers)
3. [Templates](#templates)
4. [ROS2 Code Hierarchy](#ros2-code-hierarchy)
5. [ROS2 Namespaces](#ros2-namespaces)
6. [Complete ROS2 Example](#complete-ros2-example)
7. [Common Patterns](#common-patterns)
8. [Common Pitfalls](#common-pitfalls)
9. [Practice Exercises](#practice-exercises)
10. [Quick Reference](#quick-reference)

***

## Introduction

This tutorial covers essential modern C++ concepts used extensively in ROS2:
- **Smart pointers**: Automatic memory management
- **Templates**: Generic programming for reusable code
- **ROS2 structure**: Package organization and namespaces

**Prerequisites:** Basic C++ (classes, pointers, inheritance from Tutorial 1)

**Learning Goals:**
- Understand when to use `unique_ptr` vs `shared_ptr` vs `weak_ptr`
- Read and write template functions and classes
- Navigate ROS2 package structure and long namespaces
- Apply these concepts in real ROS2 nodes

***

## Smart Pointers

### Why Smart Pointers?

**Old way (raw pointers):**
```cpp
Robot* robot = new Robot("R1");
robot->move();
delete robot;  // Easy to forget! Memory leak if exception occurs
```

**Modern way (smart pointers):**
```cpp
auto robot = std::make_unique<Robot>("R1");
robot->move();
// Automatically deleted when robot goes out of scope
```

Smart pointers manage memory automatically, preventing leaks and dangling pointers.

***

### The Three Smart Pointer Types

| Type | Ownership | Use Case |
|------|-----------|----------|
| `unique_ptr` | Single owner | Default choice; exclusive ownership |
| `shared_ptr` | Multiple owners | Shared resources; reference counted |
| `weak_ptr` | Non-owning observer | Break circular references |

***

### 1. `unique_ptr` - Single Ownership

**Concept:** "I own this object exclusively."

```cpp
#include <memory>
#include <iostream>
using namespace std;

class Robot {
public:
    Robot(string name) : name_(name) {
        cout << name_ << " created\n";
    }
    ~Robot() {
        cout << name_ << " destroyed\n";
    }
    void move() {
        cout << name_ << " moving\n";
    }
private:
    string name_;
};

int main() {
    // Create unique_ptr
    auto robot1 = std::make_unique<Robot>("R1");
    robot1->move();
    
    // Cannot copy (single owner)
    // auto robot2 = robot1;  // ERROR
    
    // Can transfer ownership with move
    auto robot2 = std::move(robot1);
    // robot1 is now nullptr
    
    if (robot1) {
        robot1->move();  // Won't execute
    }
    
    robot2->move();  // OK
    
    // robot2 automatically deleted here
}
```

**Output:**
```
R1 created
R1 moving
R1 moving
R1 destroyed
```

**Key Points:**
- Use `std::make_unique<Type>(args)` to create
- Cannot be copied (compile error)
- Can be moved with `std::move()`
- Automatically deletes object when destroyed

***

### 2. `shared_ptr` - Shared Ownership

**Concept:** "We all own this object together."

```cpp
#include <memory>
#include <iostream>
using namespace std;

class Sensor {
public:
    Sensor(string name) : name_(name) {
        cout << name_ << " initialized\n";
    }
    ~Sensor() {
        cout << name_ << " destroyed\n";
    }
    int read() { return 42; }
private:
    string name_;
};

void processData(shared_ptr<Sensor> sensor) {
    cout << "Processing data from sensor\n";
    cout << "Use count in function: " << sensor.use_count() << "\n";
}

int main() {
    auto sensor1 = std::make_shared<Sensor>("Lidar");
    cout << "Use count: " << sensor1.use_count() << "\n";  // 1
    
    {
        auto sensor2 = sensor1;  // Share ownership
        cout << "Use count: " << sensor1.use_count() << "\n";  // 2
        
        processData(sensor1);  // Pass to function (count becomes 3 temporarily)
        
    }  // sensor2 destroyed, count back to 1
    
    cout << "Use count: " << sensor1.use_count() << "\n";  // 1
    
    // Sensor destroyed when sensor1 goes out of scope
}
```

**Output:**
```
Lidar initialized
Use count: 1
Use count: 2
Processing data from sensor
Use count in function: 3
Use count: 1
Lidar destroyed
```

**Key Points:**
- Use `std::make_shared<Type>(args)` to create
- Can be copied (shares ownership)
- Reference counted (`.use_count()`)
- Object deleted when last `shared_ptr` is destroyed

***

### 3. `weak_ptr` - Non-Owning Observer

**Concept:** "I want to observe, but not keep it alive."

```cpp
#include <memory>
#include <iostream>
using namespace std;

int main() {
    shared_ptr<int> sp = std::make_shared<int>(42);
    weak_ptr<int> wp = sp;  // Observe, don't own
    
    cout << "use_count: " << sp.use_count() << "\n";  // 1 (wp doesn't count)
    
    // Check if object still exists
    if (auto locked = wp.lock()) {  // Get temporary shared_ptr
        cout << "Value: " << *locked << "\n";
    } else {
        cout << "Object destroyed\n";
    }
    
    sp.reset();  // Destroy the int
    
    // Try again after destruction
    if (auto locked = wp.lock()) {
        cout << "Value: " << *locked << "\n";
    } else {
        cout << "Object destroyed\n";  // This executes
    }
}
```

**Output:**
```
use_count: 1
Value: 42
Object destroyed
```

**Key Points:**
- Created from `shared_ptr`
- Does NOT increase reference count
- Use `.lock()` to get temporary `shared_ptr`
- Mainly used to break circular references

***

### Smart Pointers: When to Use What

```cpp
class RobotNode : public rclcpp::Node {
public:
    RobotNode() : Node("robot") {
        // unique_ptr: node exclusively owns motor
        motor_ = std::make_unique<MotorDriver>();
        
        // shared_ptr: sensor data shared with callbacks
        sensor_ = std::make_shared<Sensor>();
        
        // Pass shared sensor to subscriber callback
        sub_ = create_subscription<SensorMsg>(
            "sensor_data", 10,
            [this, sensor = sensor_](const SensorMsg::SharedPtr msg) {
                // Both 'this' and callback share sensor
            }
        );
    }

private:
    std::unique_ptr<MotorDriver> motor_;  // Exclusive
    std::shared_ptr<Sensor> sensor_;      // Shared
};
```

**Decision Tree:**
1. Does only one thing own it? → `unique_ptr`
2. Do multiple things share it? → `shared_ptr`
3. Do you need to observe without owning? → `weak_ptr`

***

### Smart Pointer Operations

```cpp
// Creation
auto up = std::make_unique<Robot>("R1");
auto sp = std::make_shared<Robot>("R2");

// Access members
up->move();           // Arrow operator
(*up).move();         // Dereference + dot

// Get raw pointer (rare, avoid)
Robot* raw = up.get();

// Check if valid
if (up) {
    up->move();
}

// Release ownership (unique_ptr)
Robot* raw = up.release();  // up is now null
delete raw;  // Must manually delete

// Reset (destroy current, optionally assign new)
up.reset();                      // Destroy, set to null
up.reset(new Robot("R3"));       // Destroy old, manage new

// Transfer ownership (unique_ptr)
auto up2 = std::move(up);  // up is now null

// Share ownership (shared_ptr)
auto sp2 = sp;  // Both own the same object
```

***

## Templates

### What Are Templates?

Templates let you write code that works with any type.

**Without templates (repetitive):**
```cpp
int add_int(int a, int b) { return a + b; }
double add_double(double a, double b) { return a + b; }
string add_string(string a, string b) { return a + b; }
```

**With templates (generic):**
```cpp
template<typename T>
T add(T a, T b) {
    return a + b;
}

// Use with any type
int x = add(1, 2);           // T = int
double y = add(1.5, 2.5);    // T = double
string z = add(string("Hello"), string(" World"));  // T = string
```

***

### Template Functions

**Syntax:**
```cpp
template<typename T>
ReturnType functionName(Parameters) {
    // Body
}
```

**Example 1: Simple Generic Function**
```cpp
template<typename T>
T max(T a, T b) {
    return (a > b) ? a : b;
}

int main() {
    cout << max(10, 20) << "\n";       // 20
    cout << max(3.14, 2.71) << "\n";   // 3.14
    cout << max('a', 'z') << "\n";     // z
}
```

**Example 2: Generic Print Function**
```cpp
template<typename T>
void print(const T& value) {
    std::cout << value << std::endl;
}

int main() {
    print(42);           // int
    print(3.14);         // double
    print("Hello");      // const char*
    print(std::string("World"));  // string
}
```

**Example 3: Multiple Template Parameters**
```cpp
template<typename T1, typename T2>
void printPair(const T1& first, const T2& second) {
    std::cout << first << ", " << second << std::endl;
}

int main() {
    printPair(1, 2.5);           // int, double
    printPair("Age", 25);        // const char*, int
    printPair(3.14, "pi");       // double, const char*
}
```

***

### Template Classes

**Syntax:**
```cpp
template<typename T>
class ClassName {
public:
    T memberVariable;
    T memberFunction(T param);
};
```

**Example 1: Generic Box**
```cpp
template<typename T>
class Box {
public:
    Box(const T& value) : value_(value) {}
    
    T get() const { return value_; }
    void set(const T& value) { value_ = value; }
    
    void print() const {
        std::cout << "Box contains: " << value_ << std::endl;
    }

private:
    T value_;
};

int main() {
    Box<int> intBox(42);
    intBox.print();          // Box contains: 42
    
    Box<string> strBox("Hello");
    strBox.print();          // Box contains: Hello
    
    Box<double> doubleBox(3.14);
    doubleBox.print();       // Box contains: 3.14
}
```

**Example 2: Generic Pair**
```cpp
template<typename T1, typename T2>
class Pair {
public:
    Pair(const T1& first, const T2& second)
        : first_(first), second_(second) {}
    
    T1 getFirst() const { return first_; }
    T2 getSecond() const { return second_; }
    
    void print() const {
        std::cout << "(" << first_ << ", " << second_ << ")" << std::endl;
    }

private:
    T1 first_;
    T2 second_;
};

int main() {
    Pair<int, double> p1(1, 2.5);
    p1.print();  // (1, 2.5)
    
    Pair<string, int> p2("Age", 25);
    p2.print();  // (Age, 25)
}
```

**Example 3: Sensor Template (Robotics)**
```cpp
template<typename T>
class Sensor {
public:
    Sensor(const std::string& name) : name_(name) {
        std::cout << "Sensor " << name_ << " created\n";
    }
    
    void update(T value) {
        last_value_ = value;
        std::cout << name_ << " = " << value << "\n";
    }
    
    T read() const {
        return last_value_;
    }
    
    std::string getName() const { return name_; }

private:
    std::string name_;
    T last_value_{};
};

int main() {
    Sensor<double> lidar("Lidar");
    lidar.update(2.5);
    std::cout << "Reading: " << lidar.read() << " m\n";
    
    Sensor<int> battery("Battery");
    battery.update(85);
    std::cout << "Reading: " << battery.read() << "%\n";
}
```

**Output:**
```
Sensor Lidar created
Lidar = 2.5
Reading: 2.5 m
Sensor Battery created
Battery = 85
Reading: 85%
```

***

### Template Syntax Breakdown

```cpp
std::make_shared<Robot>("R1", 5)
//              ^^^^^^^ ^^^^^^^^^
//              |       |
//              Type    Constructor arguments
```

- `<Robot>` → Template argument (what type to create)
- `("R1", 5)` → Constructor arguments (passed to Robot constructor)

Another example:
```cpp
rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pub_;
//                ^^^^^^^^^^^^^^^^^^^^^^^  ^^^^^^^^^
//                |                        |
//                Template argument        Typedef for shared_ptr
```

***

### Templates with Smart Pointers

```cpp
template<typename T>
void printValue(const std::shared_ptr<T>& ptr) {
    if (ptr) {
        std::cout << "Value: " << *ptr << std::endl;
        std::cout << "Use count: " << ptr.use_count() << std::endl;
    }
}

template<typename T>
std::shared_ptr<T> makeAndLog(T value) {
    auto ptr = std::make_shared<T>(value);
    std::cout << "Created object with value: " << *ptr << std::endl;
    return ptr;
}

int main() {
    auto iptr = makeAndLog<int>(42);
    auto dptr = makeAndLog<double>(3.14);
    
    printValue(iptr);
    printValue(dptr);
}
```

**Output:**
```
Created object with value: 42
Created object with value: 3.14
Value: 42
Use count: 1
Value: 3.14
Use count: 1
```

***

## ROS2 Code Hierarchy

### Overview: Workspace to Class

```
Workspace (~/ros2_ws/)
  ├── build/              (generated by colcon)
  ├── install/            (generated by colcon)
  ├── log/                (generated by colcon)
  └── src/
       ├── package_1/
       │    ├── package.xml
       │    ├── CMakeLists.txt
       │    ├── include/
       │    │    └── package_1/
       │    │         └── my_class.hpp
       │    ├── src/
       │    │    └── my_node.cpp
       │    └── launch/
       │         └── my_launch.py
       └── package_2/
            └── ...
```

***

### 1. Workspace

**Definition:** Top-level directory containing all your ROS2 packages.

```bash
cd ~/ros2_ws
colcon build              # Build all packages
source install/setup.bash # Source the workspace
```

**Structure:**
- `src/` → Your source code (packages)
- `build/` → Build artifacts (auto-generated)
- `install/` → Installed files (auto-generated)
- `log/` → Build logs (auto-generated)

**Key Point:** Only `src/` should be version controlled (git).

***

### 2. Package

**Definition:** A unit of organization containing nodes, libraries, config files.

**Required files:**
- `package.xml` → Package metadata (dependencies, version, author)
- `CMakeLists.txt` → Build instructions

**Example `package.xml`:**
```xml
<?xml version="1.0"?>
<package format="3">
  <name>my_robot</name>
  <version>1.0.0</version>
  <description>My robot controller</description>
  <maintainer email="you@example.com">Your Name</maintainer>
  <license>Apache-2.0</license>

  <buildtool_depend>ament_cmake</buildtool_depend>
  
  <depend>rclcpp</depend>
  <depend>std_msgs</depend>
  <depend>geometry_msgs</depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
```

**Create a package:**
```bash
cd ~/ros2_ws/src
ros2 pkg create my_robot --build-type ament_cmake --dependencies rclcpp std_msgs
```

***

### 3. Node

**Definition:** An executable program that does ONE specific job.

**Examples:**
- `motor_controller_node` → Controls motors
- `camera_node` → Publishes camera images
- `lidar_processor_node` → Processes lidar data

**Key concept:** Nodes communicate via:
- **Topics** (publish/subscribe)
- **Services** (request/response)
- **Actions** (long-running tasks)

***

### 4. Files

**Types:**
- **Source files (`.cpp`)**: Implementation
- **Header files (`.hpp`)**: Declarations
- **Launch files (`.py`, `.xml`)**: Start multiple nodes
- **Config files (`.yaml`)**: Parameters

**Typical structure:**
```
my_robot_pkg/
  ├── include/my_robot_pkg/
  │    ├── robot_controller.hpp
  │    └── sensor_interface.hpp
  ├── src/
  │    ├── robot_controller.cpp
  │    ├── sensor_interface.cpp
  │    └── main.cpp
  ├── launch/
  │    └── robot.launch.py
  └── config/
       └── params.yaml
```

***

### 5. Classes

**In ROS2, classes typically:**
- Inherit from `rclcpp::Node`
- Manage publishers, subscribers, timers
- Contain business logic

**Example:**
```cpp
namespace my_robot {

class RobotController : public rclcpp::Node {
public:
    RobotController();
private:
    void timer_callback();
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
};

}  // namespace my_robot
```

***

### Complete Hierarchy Example

**File: `~/ros2_ws/src/my_robot/src/controller_node.cpp`**

```cpp
// 1. Workspace: ~/ros2_ws/
// 2. Package: my_robot
// 3. File: controller_node.cpp

#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/twist.hpp>

// 4. Namespace: my_robot
namespace my_robot {

// 5. Class: RobotController (inherits from Node)
class RobotController : public rclcpp::Node {
public:
    RobotController() : Node("robot_controller") {
        publisher_ = this->create_publisher<geometry_msgs::msg::Twist>(
            "cmd_vel", 10
        );
        
        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(100),
            std::bind(&RobotController::timer_callback, this)
        );
    }

private:
    void timer_callback() {
        auto msg = geometry_msgs::msg::Twist();
        msg.linear.x = 0.5;
        publisher_->publish(msg);
    }
    
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
};

}  // namespace my_robot

// 6. Main function (creates node instance)
int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<my_robot::RobotController>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
```

***

## ROS2 Namespaces

### Why Long Namespaces?

ROS2 uses nested C++ namespaces to organize thousands of classes and functions.

**Example:**
```cpp
rclcpp::executors::SingleThreadedExecutor
```

Think of it like a folder structure:
```
rclcpp/
  ├── Node
  ├── Publisher
  ├── Subscription
  └── executors/
       ├── SingleThreadedExecutor
       └── MultiThreadedExecutor
```

***

### Common ROS2 Namespaces

| Namespace | Purpose | Example |
|-----------|---------|---------|
| `rclcpp::` | ROS2 C++ client library | `rclcpp::Node` |
| `std_msgs::msg::` | Standard message types | `std_msgs::msg::String` |
| `geometry_msgs::msg::` | Geometry messages | `geometry_msgs::msg::Twist` |
| `sensor_msgs::msg::` | Sensor messages | `sensor_msgs::msg::Image` |
| `rclcpp::executors::` | Executor classes | `rclcpp::executors::SingleThreadedExecutor` |

***

### Breaking Down Long Namespaces

```cpp
rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
```

Let's decompose it:

1. `rclcpp::` → ROS2 C++ library namespace
2. `Publisher<...>` → Template class for publishing messages
3. `<std_msgs::msg::String>` → Template argument (message type)
   - `std_msgs` → Package name
   - `msg` → Sub-namespace for message types
   - `String` → Message class
4. `::SharedPtr` → Typedef inside Publisher class for `shared_ptr<Publisher<...>>`

**Equivalent to:**
```cpp
std::shared_ptr<rclcpp::Publisher<std_msgs::msg::String>> publisher_;
```

***

### Simplifying with `using`

**Instead of:**
```cpp
rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;
rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr laser_pub_;
rclcpp::Subscription<std_msgs::msg::String>::SharedPtr sub_;
```

**Use type aliases:**
```cpp
using TwistPublisher = rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr;
using LaserPublisher = rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr;
using StringSubscription = rclcpp::Subscription<std_msgs::msg::String>::SharedPtr;

TwistPublisher cmd_vel_pub_;
LaserPublisher laser_pub_;
StringSubscription sub_;
```

**Or namespace shortcuts:**
```cpp
namespace msg = std_msgs::msg;
namespace geom = geometry_msgs::msg;

rclcpp::Publisher<msg::String>::SharedPtr string_pub_;
rclcpp::Publisher<geom::Twist>::SharedPtr twist_pub_;
```

***

### Your Package Namespace

**Always wrap your code in your package namespace:**

```cpp
// File: my_robot/src/controller.cpp

namespace my_robot {

class Controller : public rclcpp::Node {
    // Your class
};

}  // namespace my_robot
```

**Why?**
- Avoids naming conflicts with other packages
- Makes code origin clear
- Standard ROS2 practice

***

## Complete ROS2 Example

Let's build a realistic robot controller using everything we've learned.

### Project Structure

```
ros2_ws/
  └── src/
       └── robot_controller/
            ├── package.xml
            ├── CMakeLists.txt
            ├── include/
            │    └── robot_controller/
            │         ├── motor_driver.hpp
            │         └── sensor.hpp
            └── src/
                 └── controller_node.cpp
```

***

### File 1: `include/robot_controller/motor_driver.hpp`

```cpp
#ifndef ROBOT_CONTROLLER_MOTOR_DRIVER_HPP
#define ROBOT_CONTROLLER_MOTOR_DRIVER_HPP

#include <iostream>
#include <string>

namespace robot_controller {

class MotorDriver {
public:
    MotorDriver(const std::string& name)
        : name_(name), speed_(0.0) {
        std::cout << "MotorDriver " << name_ << " initialized\n";
    }
    
    ~MotorDriver() {
        std::cout << "MotorDriver " << name_ << " shutdown\n";
    }
    
    void setSpeed(double speed) {
        speed_ = speed;
        std::cout << name_ << " speed: " << speed_ << " m/s\n";
    }
    
    double getSpeed() const {
        return speed_;
    }
    
    std::string getName() const {
        return name_;
    }

private:
    std::string name_;
    double speed_;
};

}  // namespace robot_controller

#endif
```

***

### File 2: `include/robot_controller/sensor.hpp`

```cpp
#ifndef ROBOT_CONTROLLER_SENSOR_HPP
#define ROBOT_CONTROLLER_SENSOR_HPP

#include <iostream>
#include <string>

namespace robot_controller {

// Template class for different sensor types
template<typename T>
class Sensor {
public:
    Sensor(const std::string& name)
        : name_(name), last_value_{} {
        std::cout << "Sensor<" << typeid(T).name() << "> "
                  << name_ << " created\n";
    }
    
    ~Sensor() {
        std::cout << "Sensor " << name_ << " destroyed\n";
    }
    
    void update(T value) {
        last_value_ = value;
        std::cout << name_ << " updated: " << value << "\n";
    }
    
    T read() const {
        return last_value_;
    }
    
    std::string getName() const {
        return name_;
    }

private:
    std::string name_;
    T last_value_;
};

}  // namespace robot_controller

#endif
```

***

### File 3: `src/controller_node.cpp`

```cpp
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/float64.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <memory>
#include <chrono>

#include "robot_controller/motor_driver.hpp"
#include "robot_controller/sensor.hpp"

using namespace std::chrono_literals;

namespace robot_controller {

class ControllerNode : public rclcpp::Node {
public:
    ControllerNode() : Node("robot_controller"), counter_(0) {
        RCLCPP_INFO(this->get_logger(), "Starting robot controller...");
        
        // unique_ptr: Node exclusively owns motors
        left_motor_ = std::make_unique<MotorDriver>("left_motor");
        right_motor_ = std::make_unique<MotorDriver>("right_motor");
        
        // shared_ptr: Sensors might be shared with multiple callbacks
        distance_sensor_ = std::make_shared<Sensor<double>>("distance_sensor");
        battery_sensor_ = std::make_shared<Sensor<int>>("battery_sensor");
        temperature_sensor_ = std::make_shared<Sensor<float>>("temp_sensor");
        
        // Initialize sensors
        distance_sensor_->update(1.5);
        battery_sensor_->update(100);
        temperature_sensor_->update(25.0f);
        
        // Pass shared sensor to monitoring function
        monitor_sensor(battery_sensor_);
        
        // ROS2 publishers (SharedPtr managed by ROS2)
        cmd_vel_pub_ = this->create_publisher<geometry_msgs::msg::Twist>(
            "cmd_vel", 10
        );
        
        distance_pub_ = this->create_publisher<std_msgs::msg::Float64>(
            "distance", 10
        );
        
        battery_pub_ = this->create_publisher<std_msgs::msg::Float64>(
            "battery", 10
        );
        
        // Timer for control loop
        timer_ = this->create_wall_timer(
            1s,
            std::bind(&ControllerNode::control_loop, this)
        );
        
        RCLCPP_INFO(this->get_logger(), "Robot controller initialized");
    }
    
    ~ControllerNode() {
        RCLCPP_INFO(this->get_logger(), "Shutting down robot controller");
    }

private:
    // Main control loop
    void control_loop() {
        // Simulate sensor updates
        double distance = 1.5 + (rand() % 100) / 100.0;
        int battery = std::max(0, 100 - counter_ * 2);
        float temperature = 25.0f + (rand() % 20) / 10.0f;
        
        distance_sensor_->update(distance);
        battery_sensor_->update(battery);
        temperature_sensor_->update(temperature);
        
        // Read sensor values
        double dist = distance_sensor_->read();
        int batt = battery_sensor_->read();
        float temp = temperature_sensor_->read();
        
        RCLCPP_INFO(this->get_logger(),
            "Distance: %.2f m | Battery: %d%% | Temp: %.1f°C",
            dist, batt, temp);
        
        // Control logic based on sensors
        if (dist < 1.0) {
            // Obstacle detected
            left_motor_->setSpeed(0.0);
            right_motor_->setSpeed(0.0);
            RCLCPP_WARN(this->get_logger(), "Obstacle detected! Stopping.");
        } else if (batt < 20) {
            // Low battery
            left_motor_->setSpeed(0.2);
            right_motor_->setSpeed(0.2);
            RCLCPP_WARN(this->get_logger(), "Low battery! Slow mode.");
        } else if (temp > 40.0f) {
            // High temperature
            left_motor_->setSpeed(0.5);
            right_motor_->setSpeed(0.5);
            RCLCPP_WARN(this->get_logger(), "High temperature! Reduced speed.");
        } else {
            // Normal operation
            left_motor_->setSpeed(1.0);
            right_motor_->setSpeed(1.0);
        }
        
        // Publish ROS2 messages
        publish_cmd_vel();
        publish_sensor_data();
        
        counter_++;
    }
    
    // Publish velocity command
    void publish_cmd_vel() {
        auto msg = geometry_msgs::msg::Twist();
        double left = left_motor_->getSpeed();
        double right = right_motor_->getSpeed();
        
        msg.linear.x = (left + right) / 2.0;
        msg.angular.z = (right - left) / 2.0;
        
        cmd_vel_pub_->publish(msg);
    }
    
    // Publish sensor data
    void publish_sensor_data() {
        auto dist_msg = std_msgs::msg::Float64();
        dist_msg.data = distance_sensor_->read();
        distance_pub_->publish(dist_msg);
        
        auto batt_msg = std_msgs::msg::Float64();
        batt_msg.data = static_cast<double>(battery_sensor_->read());
        battery_pub_->publish(batt_msg);
    }
    
    // Template function accepting shared sensor
    template<typename T>
    void monitor_sensor(std::shared_ptr<Sensor<T>> sensor) {
        RCLCPP_INFO(this->get_logger(),
            "Monitoring sensor: %s (use_count: %ld)",
            sensor->getName().c_str(),
            sensor.use_count());
    }
    
    // Motors (unique ownership)
    std::unique_ptr<MotorDriver> left_motor_;
    std::unique_ptr<MotorDriver> right_motor_;
    
    // Sensors (shared ownership)
    std::shared_ptr<Sensor<double>> distance_sensor_;
    std::shared_ptr<Sensor<int>> battery_sensor_;
    std::shared_ptr<Sensor<float>> temperature_sensor_;
    
    // ROS2 publishers
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_pub_;
    rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr distance_pub_;
    rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr battery_pub_;
    
    rclcpp::TimerBase::SharedPtr timer_;
    int counter_;
};

}  // namespace robot_controller

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    
    // Smart pointer to node (shared with executor)
    auto node = std::make_shared<robot_controller::ControllerNode>();
    
    rclcpp::spin(node);
    rclcpp::shutdown();
    
    return 0;
}
```

***

### File 4: `CMakeLists.txt`

```cmake
cmake_minimum_required(VERSION 3.8)
project(robot_controller)

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

# Include directories
include_directories(include)

# Executable
add_executable(controller_node src/controller_node.cpp)

ament_target_dependencies(controller_node
  rclcpp
  std_msgs
  geometry_msgs
)

# Install
install(TARGETS
  controller_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include
)

ament_package()
```

***

### File 5: `package.xml`

```xml
<?xml version="1.0"?>
<package format="3">
  <name>robot_controller</name>
  <version>1.0.0</version>
  <description>Robot controller with smart pointers and templates</description>
  <maintainer email="you@example.com">Your Name</maintainer>
  <license>Apache-2.0</license>

  <buildtool_depend>ament_cmake</buildtool_depend>

  <depend>rclcpp</depend>
  <depend>std_msgs</depend>
  <depend>geometry_msgs</depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
```

***

### Building and Running

```bash
# Build
cd ~/ros2_ws
colcon build --packages-select robot_controller
source install/setup.bash

# Run
ros2 run robot_controller controller_node

# In another terminal, check topics
ros2 topic list
ros2 topic echo /cmd_vel
ros2 topic echo /distance
```

***

## Common Patterns

### Pattern 1: Node with Exclusive Resources

```cpp
class MyNode : public rclcpp::Node {
public:
    MyNode() : Node("my_node") {
        // Node owns hardware drivers exclusively
        motor_ = std::make_unique<MotorDriver>();
        camera_ = std::make_unique<CameraDriver>();
    }
private:
    std::unique_ptr<MotorDriver> motor_;
    std::unique_ptr<CameraDriver> camera_;
};
```

***

### Pattern 2: Shared Sensor Data

```cpp
class SensorNode : public rclcpp::Node {
public:
    SensorNode() : Node("sensor_node") {
        sensor_ = std::make_shared<Sensor>();
        
        // Multiple subscribers can share sensor
        sub1_ = create_subscription<SensorMsg>(
            "topic1", 10,
            [this, s = sensor_](auto msg) { /* use s */ }
        );
        
        sub2_ = create_subscription<SensorMsg>(
            "topic2", 10,
            [this, s = sensor_](auto msg) { /* use s */ }
        );
    }
private:
    std::shared_ptr<Sensor> sensor_;
};
```

***

### Pattern 3: Template Helper Functions

```cpp
template<typename MsgT>
typename rclcpp::Publisher<MsgT>::SharedPtr
createPublisher(rclcpp::Node* node, const std::string& topic) {
    return node->create_publisher<MsgT>(topic, 10);
}

// Usage
auto twist_pub = createPublisher<geometry_msgs::msg::Twist>(
    this, "cmd_vel"
);
```

***

### Pattern 4: Type Aliases for Clarity

```cpp
namespace robot {

// Message type aliases
using Twist = geometry_msgs::msg::Twist;
using String = std_msgs::msg::String;
using LaserScan = sensor_msgs::msg::LaserScan;

// Publisher type aliases
using TwistPub = rclcpp::Publisher<Twist>::SharedPtr;
using StringPub = rclcpp::Publisher<String>::SharedPtr;
using LaserPub = rclcpp::Publisher<LaserScan>::SharedPtr;

class MyNode : public rclcpp::Node {
private:
    TwistPub cmd_vel_pub_;
    LaserPub laser_pub_;
};

}  // namespace robot
```

***

## Common Pitfalls

### Pitfall 1: Forgetting to Initialize Smart Pointers

```cpp
// BAD
class MyNode : public rclcpp::Node {
public:
    MyNode() : Node("my_node") {
        // motor_ is null!
    }
    
    void use_motor() {
        motor_->setSpeed(1.0);  // CRASH: nullptr dereference
    }
private:
    std::unique_ptr<Motor> motor_;
};

// GOOD
class MyNode : public rclcpp::Node {
public:
    MyNode() : Node("my_node") {
        motor_ = std::make_unique<Motor>();  // Initialize!
    }
private:
    std::unique_ptr<Motor> motor_;
};
```

***

### Pitfall 2: Copying unique_ptr

```cpp
// BAD
auto motor1 = std::make_unique<Motor>();
auto motor2 = motor1;  // ERROR: cannot copy unique_ptr

// GOOD (move)
auto motor1 = std::make_unique<Motor>();
auto motor2 = std::move(motor1);  // Transfer ownership
// motor1 is now nullptr
```

***

### Pitfall 3: Using auto for Class Members

```cpp
// BAD
class Robot {
private:
    auto motor_;  // ERROR: auto not allowed for members
};

// GOOD
class Robot {
private:
    std::unique_ptr<Motor> motor_;
};
```

***

### Pitfall 4: Forgetting virtual Destructor with Polymorphism

```cpp
// BAD
class Base {
public:
    ~Base() {}  // NOT virtual
};

class Derived : public Base {
public:
    ~Derived() { /* cleanup */ }
};

Base* ptr = new Derived();
delete ptr;  // Only calls Base destructor! Memory leak!

// GOOD
class Base {
public:
    virtual ~Base() {}  // Virtual destructor
};
```

***

### Pitfall 5: Not Checking weak_ptr

```cpp
// BAD
std::weak_ptr<int> wp;
*wp = 5;  // ERROR: cannot dereference weak_ptr

// GOOD
std::weak_ptr<int> wp;
if (auto sp = wp.lock()) {
    *sp = 5;  // OK: temporary shared_ptr
}
```

***

### Pitfall 6: Template Instantiation Issues

```cpp
// BAD - Implementation in .cpp (won't link)
// sensor.hpp
template<typename T>
class Sensor {
    T read();
};

// sensor.cpp
template<typename T>
T Sensor<T>::read() { /* ... */ }  // Linker error!

// GOOD - Implementation in header
// sensor.hpp
template<typename T>
class Sensor {
    T read() { /* implementation here */ }
};
```

***

## Practice Exercises

### Exercise 1: Smart Pointer Basics

Create a simple `Robot` class and:
1. Create a `unique_ptr` to a Robot
2. Transfer ownership to another `unique_ptr`
3. Create a `shared_ptr` to a Robot
4. Share ownership with another `shared_ptr`
5. Print the use count

<details>
<summary>Solution</summary>

```cpp
#include <iostream>
#include <memory>
using namespace std;

class Robot {
public:
    Robot(string name) : name_(name) {
        cout << name_ << " created\n";
    }
    ~Robot() {
        cout << name_ << " destroyed\n";
    }
private:
    string name_;
};

int main() {
    // 1 & 2: unique_ptr
    auto r1 = make_unique<Robot>("R1");
    auto r2 = move(r1);  // Transfer
    
    // 3 & 4: shared_ptr
    auto r3 = make_shared<Robot>("R3");
    auto r4 = r3;  // Share
    
    // 5: Use count
    cout << "Use count: " << r3.use_count() << "\n";  // 2
}
```
</details>

***

### Exercise 2: Template Function

Write a template function `swap` that swaps two values of any type.

<details>
<summary>Solution</summary>

```cpp
template<typename T>
void swap(T& a, T& b) {
    T temp = a;
    a = b;
    b = temp;
}

int main() {
    int x = 5, y = 10;
    swap(x, y);
    cout << x << ", " << y << "\n";  // 10, 5
    
    string s1 = "hello", s2 = "world";
    swap(s1, s2);
    cout << s1 << ", " << s2 << "\n";  // world, hello
}
```
</details>

***

### Exercise 3: Template Class

Create a template `Stack<T>` class with `push`, `pop`, and `top` methods.

<details>
<summary>Solution</summary>

```cpp
template<typename T>
class Stack {
public:
    void push(const T& value) {
        data_.push_back(value);
    }
    
    T pop() {
        T value = data_.back();
        data_.pop_back();
        return value;
    }
    
    T top() const {
        return data_.back();
    }
    
    bool empty() const {
        return data_.empty();
    }

private:
    std::vector<T> data_;
};

int main() {
    Stack<int> s;
    s.push(1);
    s.push(2);
    s.push(3);
    
    cout << s.pop() << "\n";  // 3
    cout << s.top() << "\n";  // 2
}
```
</details>

***

### Exercise 4: ROS2 Publisher Node

Create a ROS2 node that publishes a counter using smart pointers and proper structure.

<details>
<summary>Solution</summary>

```cpp
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/int32.hpp>
#include <memory>

class CounterNode : public rclcpp::Node {
public:
    CounterNode() : Node("counter"), count_(0) {
        pub_ = this->create_publisher<std_msgs::msg::Int32>(
            "count", 10
        );
        
        timer_ = this->create_wall_timer(
            std::chrono::seconds(1),
            std::bind(&CounterNode::timer_callback, this)
        );
    }

private:
    void timer_callback() {
        auto msg = std_msgs::msg::Int32();
        msg.data = count_++;
        pub_->publish(msg);
        RCLCPP_INFO(this->get_logger(), "Published: %d", msg.data);
    }
    
    rclcpp::Publisher<std_msgs::msg::Int32>::SharedPtr pub_;
    rclcpp::TimerBase::SharedPtr timer_;
    int count_;
};

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<CounterNode>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
```
</details>

***

### Exercise 5: Template Sensor with Smart Pointers

Combine templates and smart pointers to create a generic sensor manager.

<details>
<summary>Solution</summary>

```cpp
template<typename T>
class Sensor {
public:
    Sensor(string name) : name_(name) {}
    void update(T val) { value_ = val; }
    T read() const { return value_; }
private:
    string name_;
    T value_{};
};

class SensorManager {
public:
    SensorManager() {
        lidar_ = make_shared<Sensor<double>>("lidar");
        battery_ = make_shared<Sensor<int>>("battery");
    }
    
    void updateAll() {
        lidar_->update(2.5);
        battery_->update(85);
    }
    
    void printAll() {
        cout << "Lidar: " << lidar_->read() << " m\n";
        cout << "Battery: " << battery_->read() << "%\n";
    }

private:
    shared_ptr<Sensor<double>> lidar_;
    shared_ptr<Sensor<int>> battery_;
};
```
</details>

***

## Quick Reference

### Smart Pointers Cheat Sheet

```cpp
// Creation
auto up = std::make_unique<T>(args);
auto sp = std::make_shared<T>(args);
std::weak_ptr<T> wp = sp;

// Access
ptr->member();
(*ptr).member();

// Check validity
if (ptr) { /* valid */ }

// unique_ptr only
auto up2 = std::move(up);  // Transfer
T* raw = up.release();     // Release ownership
up.reset(new T());         // Replace

// shared_ptr only
auto sp2 = sp;             // Share
long count = sp.use_count();  // Reference count

// weak_ptr only
if (auto sp = wp.lock()) { /* use sp */ }
```

***

### Template Syntax Cheat Sheet

```cpp
// Template function
template<typename T>
T func(T param) { return param; }

// Template class
template<typename T>
class Class {
    T member_;
};

// Multiple type parameters
template<typename T1, typename T2>
class Pair { T1 first_; T2 second_; };

// Usage
func<int>(5);              // Explicit
func(5);                   // Deduced
Class<int> obj;
Pair<int, double> p;
```

***

### ROS2 Structure Cheat Sheet

```
Workspace
  └── Package
       └── Node (executable)
            └── Class (inherits rclcpp::Node)

Files:
  ├── include/pkg/header.hpp
  ├── src/source.cpp
  ├── launch/launch.py
  └── config/params.yaml
```

***

### ROS2 Namespace Patterns

```cpp
// Standard pattern
rclcpp::Publisher<std_msgs::msg::String>::SharedPtr pub_;

// With type alias
using StringPub = rclcpp::Publisher<std_msgs::msg::String>::SharedPtr;
StringPub pub_;

// With namespace alias
namespace msg = std_msgs::msg;
rclcpp::Publisher<msg::String>::SharedPtr pub_;
```

***

### Common ROS2 Node Template

```cpp
#include <rclcpp/rclcpp.hpp>

namespace my_pkg {

class MyNode : public rclcpp::Node {
public:
    MyNode() : Node("node_name") {
        // Initialize members
    }

private:
    // Publishers, subscribers, timers
    // unique_ptr for exclusive resources
    // shared_ptr for shared resources
};

}  // namespace my_pkg

int main(int argc, char** argv) {
    rclcpp::init(argc, argv);
    auto node = std::make_shared<my_pkg::MyNode>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
```

***

## Summary

### Key Concepts

**Smart Pointers:**
- `unique_ptr`: Single ownership, default choice
- `shared_ptr`: Shared ownership, reference counted
- `weak_ptr`: Non-owning observer

**Templates:**
- Functions: Generic algorithms
- Classes: Generic containers/wrappers
- Syntax: `<Type>` for what, `(args)` for how

**ROS2 Structure:**
- Workspace → Package → Node → File → Class
- Packages contain nodes (executables)
- Nodes are usually classes inheriting `rclcpp::Node`

**ROS2 Namespaces:**
- Nested for organization: `pkg::subpkg::Class`
- Templates common: `Publisher<MsgType>::SharedPtr`
- Use aliases to simplify long names

***

### Decision Trees

**Which smart pointer?**
1. Single owner? → `unique_ptr`
2. Multiple owners? → `shared_ptr`
3. Just observing? → `weak_ptr`

**Template or not?**
1. Works with any type? → Template
2. Type-specific logic? → Regular class

**Where in ROS2?**
1. Organizational unit? → Package
2. Executable program? → Node
3. Code organization? → Class
4. Prevent name conflicts? → Namespace

***

## Next Steps

1. **Practice:** Build the example robot controller
2. **Read code:** Explore MoveIt/Nav2 source code
3. **Refactor:** Convert old code to use smart pointers
4. **Create:** Build your own template sensor class
5. **Integrate:** Use in your robot projects

***

**End of Tutorial 2**

You now understand modern C++ features essential for ROS2 development. Combined with Tutorial 1 (OOP basics), you have a solid foundation for robotics programming.

Keep this as a reference and practice with real ROS2 projects!