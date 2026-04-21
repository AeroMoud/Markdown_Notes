# Complete C++ Object-Oriented Programming Tutorial

**Target Audience:** Robotics engineers working with ROS2 and C++ projects.
**Purpose:** A comprehensive, revisable reference covering fundamental to advanced OOP concepts.

---

## Table of Contents

1.  [Core Concepts: The Four Pillars](#1-core-concepts-the-four-pillars)
2.  [Classes & Objects: The Blueprint](#2-classes--objects-the-blueprint)
3.  [Access Modifiers: Controlling Visibility](#3-access-modifiers-controlling-visibility)
4.  [Constructors & Destructors: Object Lifecycle](#4-constructors--destructors-object-lifecycle)
    - Move semantics & RAII
    - Rule of Three/Five/Zero
    - `explicit` and `noexcept`
5.  [The Member Initializer List: A Critical Tool](#5-the-member-initializer-list-a-critical-tool)
6.  [Pointers & Objects: Two Ways to Access](#6-pointers--objects-two-ways-to-access)
7.  [References vs. Values: Passing Data](#7-references-vs-values-passing-data)
    - `const` correctness
8.  [Inheritance: Reusing Code](#8-inheritance-reusing-code)
    - `final` and `override`
9.  [Polymorphism & Virtual Functions: Dynamic Behavior](#9-polymorphism--virtual-functions-dynamic-behavior)
    - Abstract classes & interfaces
10. [Base Class Pointers: The Key to Polymorphism](#10-base-class-pointers-the-key-to-polymorphism)
11. [Downcasting & Run-Time Type Identification](#11-downcasting--run-time-type-identification)
12. [Smart Pointers: Modern Memory Management](#12-smart-pointers-modern-memory-management)
13. [Templates: Generic Programming](#13-templates-generic-programming)
    - `using` type aliases and alias templates
    - CRTP
14. [Lambda Expressions: Functional Callbacks](#14-lambda-expressions-functional-callbacks)
15. [Complete Working Example: A Robotic Fleet](#15-complete-working-example-a-robotic-fleet)
16. [Quick Reference Cheat Sheet](#16-quick-reference-cheat-sheet)

---

## 1. Core Concepts: The Four Pillars

| Pillar | Definition | Benefit in Robotics |
| :--- | :--- | :--- |
| **Encapsulation** | Bundling data (attributes) and methods (functions) within a class, hiding internal state. | Prevents accidental modification of a robot's battery level or motor status. |
| **Inheritance** | Creating a new class (derived) from an existing class (base). | Create a `Robot` base class, then `WheeledRobot` and `FlyingRobot` derived classes. |
| **Polymorphism** | The ability of objects of different classes to respond to the same function call in their own way. | Send a `move()` command to a fleet of mixed robots; each executes its own movement logic. |
| **Abstraction** | Showing only essential features and hiding complex implementation details. | Using a `drive()` method without needing to know the low-level PWM signals sent to motors. |

---

## 2. Classes & Objects: The Blueprint

- A **class** is a user-defined data type that contains data members (variables) and member functions (methods).
- An **object** is an instance of a class created in memory.

```cpp
#include <iostream>
#include <string>

class Robot {
private: // Encapsulated data
    std::string name_;
    int battery_level_;

public:
    // Constructor (discussed in detail later)
    Robot(const std::string& name, int battery) 
        : name_(name), battery_level_(battery) {}

    // Member function
    void move() {
        if (battery_level_ > 0) {
            std::cout << name_ << " is moving. Battery: " << battery_level_ << "%\n";
            battery_level_ -= 10;
        } else {
            std::cout << name_ << " is out of battery!\n";
        }
    }
};

int main() {
    Robot r2d2("R2-D2", 100); // Object 'r2d2' is an instance of class 'Robot'
    r2d2.move();              // Calling a member function
    return 0;
}
```

---

## 3. Access Modifiers: Controlling Visibility

Used to enforce encapsulation.

| Modifier | Accessible from Same Class | Accessible from Derived Class | Accessible from Outside Class |
| :--- | :---: | :---: | :---: |
| `private` | ✓ | ✗ | ✗ |
| `protected` | ✓ | ✓ | ✗ |
| `public` | ✓ | ✓ | ✓ |

**Rule of Thumb:**
- Default to `private` for data members.
- Use `protected` for members that derived classes will need direct access to.
- Make interface functions `public`.

```cpp
class Sensor {
private:
    int serial_id_;       // Only Sensor class methods can access this.

protected:
    float sampling_rate_; // Sensor and its children (e.g., Lidar) can access.

public:
    void read() {         // Anyone can call this method.
        // ... reading logic ...
    }
};
```

---

## 4. Constructors & Destructors: Object Lifecycle

- **Constructor:** Called automatically when an object is created. Used for initialization.
- **Destructor:** Called automatically when an object is destroyed. Used for cleanup (closing files, freeing memory, etc.).

### Types of Constructors

```cpp
class Robot {
public:
    // 1. Default Constructor (no parameters)
    Robot() : name_("Unnamed"), battery_level_(100) {
        std::cout << "Default constructor called\n";
    }

    // 2. Parameterized Constructor
    Robot(std::string name, int battery) : name_(name), battery_level_(battery) {
        std::cout << "Parameterized constructor called for " << name_ << "\n";
    }

    // 3. Copy Constructor (creates object as a copy of another)
    Robot(const Robot& other) : name_(other.name_), battery_level_(other.battery_level_) {
        std::cout << "Copy constructor called for " << name_ << "\n";
    }

    // Destructor (denoted by ~)
    ~Robot() {
        std::cout << "Destructor called for " << name_ << "\n";
    }

private:
    std::string name_;
    int battery_level_;
};

int main() {
    Robot r1;                // Default constructor
    Robot r2("T-800", 95);   // Parameterized constructor
    Robot r3(r2);            // Copy constructor
    return 0; // Destructors for r3, r2, r1 called automatically here (reverse order)
}
```

### `explicit` Keyword
When a constructor takes a single argument, using `explicit` prevents unintended implicit conversions.

```cpp
class RobotID {
    int id_;
public:
    explicit RobotID(int id) : id_(id) {}
};

void processRobot(const RobotID& r) {}

int main() {
    // processRobot(42);      // ERROR with explicit
    processRobot(RobotID(42)); // OK
}
```

If you remove `explicit`:

```cpp
class RobotID {
    int id_;
public:
    RobotID(int id) : id_(id) {}  // no explicit
};

void processRobot(const RobotID& r) {}

int main() {
    processRobot(42);  // COMPILES! C++ converts 42 → RobotID(42)
}
```
C++ says: You gave me an int, but the function wants a RobotID. I see RobotID has a constructor that takes an int — I'll use it automatically.

### Move Semantics & RAII
Modern C++ uses move semantics to transfer ownership instead of copying large resources.

```cpp
class RobotResource {
private:
    std::string* data_; // Heap-allocated data
    size_t size_;

public:
    RobotResource(const std::string& initial, size_t size)
        : data_(new std::string[size]), size_(size) {
        std::fill(data_, data_ + size_, initial);
    }

    // Copy Constructor (deep copy)
    RobotResource(const RobotResource& other)
        : size_(other.size_), data_(new std::string[other.size_]) {
        std::copy(other.data_, other.data_ + size_, data_);
        std::cout << "Copy constructor (deep copy)\n";
    }

    // Move Constructor (transfer ownership)
    RobotResource(RobotResource&& other) noexcept
        : data_(other.data_), size_(other.size_) {
        other.data_ = nullptr;
        other.size_ = 0;
        std::cout << "Move constructor (steals resources)\n";
    }

    // Move Assignment Operator
    RobotResource& operator=(RobotResource&& other) noexcept {
        if (this != &other) {
            delete[] data_; // Clean up our resources
            data_ = other.data_;
            size_ = other.size_;
            other.data_ = nullptr;
            other.size_ = 0;
        }
        return *this;
    }

    ~RobotResource() {
        delete[] data_; // RAII: Resource Acquisition Is Initialization
    }
};

RobotResource createRobot() {
    RobotResource temp("Temporary", 100);
    return temp; // Move semantics (not copy) - MUCH faster!
}
```

### Rule of Three / Rule of Five / Rule of Zero
Follow these rules when your class manages resources manually.

```cpp
// RULE OF THREE (if you manage resources manually)
class ResourceManager {
public:
    ~ResourceManager();
    ResourceManager(const ResourceManager&);
    ResourceManager& operator=(const ResourceManager&);
};

// RULE OF FIVE (add move operations)
class ModernManager {
public:
    ~ModernManager();
    ModernManager(const ModernManager&);
    ModernManager& operator=(const ModernManager&);
    ModernManager(ModernManager&&);
    ModernManager& operator=(ModernManager&&);
};

// RULE OF ZERO (PREFERRED - use smart pointers)
class BestManager {
    std::unique_ptr<int> ptr_;
    std::vector<double> data_;
    // No user-defined destructor, copy, or move needed!
};
```

### Exception Safety & `noexcept`
Marking operations as `noexcept` helps the STL optimize moves and makes your code more robust.

```cpp
class RobotSafe {
    int battery_;
public:
    RobotSafe(int battery) : battery_(battery) {}

    int getBattery() const noexcept { return battery_; }

    RobotSafe(RobotSafe&& other) noexcept : battery_(other.battery_) {
        other.battery_ = 0;
    }

    void riskyOperation() {
        if (battery_ < 10) {
            throw std::runtime_error("Battery too low!");
        }
    }
};

void safeFunction() {
    RobotSafe r(100);
    r.riskyOperation(); // If this throws, r's destructor still runs, preventing leaks.
}
```

---

## 5. The Member Initializer List: A Critical Tool

The initializer list is the preferred way to initialize member variables, placed between the constructor parameters and the body.

```cpp
class Robot {
private:
    const int id_;          // const member
    std::string& name_ref_; // Reference member
    std::string name_;      // Regular member

public:
    // Syntax: Constructor(parameters) : member1(value1), member2(value2) {}
    Robot(int id, std::string& name, std::string assigned_name)
        : id_(id),           // REQUIRED for const members
          name_ref_(name),   // REQUIRED for reference members
          name_(assigned_name) { // RECOMMENDED for efficiency
        // Constructor body is now for complex logic, not basic assignment.
    }
};
```

**Why is this so important?**
1.  **Required:** `const` and reference members **must** be initialized here.
2.  **Efficiency:** Without the initializer list, a member is default-constructed, then assigned in the body. The initializer list constructs it directly with the correct value.
    ```cpp
    // Less efficient
    Robot(std::string name) {
        name_ = name; // name_ is default-constructed (empty), then assigned.
    }

    // More efficient (PREFERRED)
    Robot(std::string name) : name_(name) {} // name_ is constructed directly as 'name'.
    ```

---

## 6. Pointers & Objects: Two Ways to Access

When you have a pointer to an object, you can access its members using either syntax.

- **`ptr->member` (Arrow Operator):** Syntactic sugar, preferred for clarity.
- **`(*ptr).member` (Dereference then Dot):** Explicitly shows the two-step process.

```cpp
class Robot {
public:
    void move() { std::cout << "Moving...\n"; }
};

int main() {
    Robot* robot_ptr = new Robot(); // Pointer to a Robot object on the heap

    // Method 1: Arrow operator (PREFERRED)
    robot_ptr->move();

    // Method 2: Dereference + dot operator
    (*robot_ptr).move(); // Does exactly the same thing as above

    delete robot_ptr; // IMPORTANT: Manually free heap memory
    return 0;
}
```

---

## 7. References vs. Values: Passing Data

Choosing how to pass arguments to functions affects performance and behavior.

```cpp
// Pass by Value: A COPY is made. Original is safe.
void set_battery_copy(int battery_level) {
    battery_level = 50; // Modifies the local copy only.
}

// Pass by Reference: No copy. Operates on the ORIGINAL variable.
void set_battery_ref(int& battery_level) {
    battery_level = 50; // Modifies the original variable passed in.
}

// Pass by const Reference: No copy, cannot modify. BEST for read-only large objects.
void print_name(const std::string& name) {
    // name = "New Name"; // ERROR: name is const.
    std::cout << name << std::endl;
}

int main() {
    int main_battery = 100;
    set_battery_copy(main_battery);
    std::cout << main_battery << std::endl; // Output: 100 (unchanged)

    set_battery_ref(main_battery);
    std::cout << main_battery << std::endl; // Output: 50 (changed!)
}
```

### Const Correctness
Const correctness is essential in ROS2 APIs and prevents accidental modification of objects.

```cpp
class Robot {
private:
    std::string name_;
    mutable int log_count_;

public:
    std::string getName() const {
        log_count_++; // OK: mutable member
        return name_;
    }

    void setName(const std::string& new_name) {
        name_ = new_name;
    }

    const std::string& getNameRef() const & {
        return name_;
    }
};

void printRobotName(const Robot& robot) {
    std::cout << robot.getName() << "\n";
    // robot.setName("New"); // ERROR: cannot call non-const on const ref
}
```

---

## 8. Inheritance: Reusing Code

A derived class inherits members from a base class.

```cpp
class Robot { // Base class
protected:
    std::string name_;
public:
    Robot(const std::string& name) : name_(name) {}
    void move() { std::cout << name_ << " is moving\n"; }
};

// 'public' inheritance means public -> public, protected -> protected
class WheeledRobot : public Robot { // Derived class
private:
    int wheel_count_;
public:
    // IMPORTANT: The derived constructor MUST call the base constructor.
    WheeledRobot(const std::string& name, int wheels)
        : Robot(name), // Initialize the base part of the object
          wheel_count_(wheels) {
        std::cout << "WheeledRobot created with " << wheel_count_ << " wheels\n";
    }
    
    void honk_horn() {
        std::cout << name_ << " says Beep Beep!\n"; // Can access 'name_' as it's protected
    }
};

### `final` and `override` Specifiers
Using `override` and `final` helps catch inheritance bugs and makes your intent explicit.

```cpp
class RobotBase {
public:
    virtual void move() { std::cout << "Moving\n"; }
    virtual void stop() { std::cout << "Stopping\n"; }
};

class WheeledRobotFinal : public RobotBase {
public:
    void move() override final {
        std::cout << "Rolling\n";
    }
};

class SealedRobot final : public RobotBase {
    // No class can inherit from SealedRobot.
};
```

---

## 9. Polymorphism & Virtual Functions: Dynamic Behavior

To get polymorphic behavior, you need **virtual functions**.

- Without `virtual`, the function call is resolved at **compile-time** (static binding) based on the pointer type.
- With `virtual`, the function call is resolved at **run-time** (dynamic binding) based on the actual object type.

```cpp
class Robot {
public:
    void move_normal() { std::cout << "Robot moves slowly\n"; }
    virtual void move_virtual() { std::cout << "Robot moves slowly\n"; }
    virtual ~Robot() {} // Virtual destructor is CRITICAL for clean up!
};

class FlyingRobot : public Robot {
public:
    void move_normal() { std::cout << "FlyingRobot flies fast\n"; }
    void move_virtual() override { std::cout << "FlyingRobot flies fast\n"; } // 'override' is optional but good practice
};

int main() {
    Robot* ptr = new FlyingRobot();

    ptr->move_normal();  // Output: Robot moves slowly (resolved by compiler: ptr is Robot*)
    ptr->move_virtual(); // Output: FlyingRobot flies fast (resolved at runtime: *ptr is FlyingRobot)

    delete ptr; // Virtual destructor ensures FlyingRobot's destructor is called.
    return 0;
}
```

### Abstract Classes & Interfaces
Pure abstract classes define interfaces for static and dynamic polymorphism.

```cpp
class ISensor {
public:
    virtual ~ISensor() = default;
    virtual double read() = 0;
    virtual void calibrate() = 0;
};

class Lidar : public ISensor {
public:
    double read() override {
        return 1.5;
    }
    void calibrate() override {
        std::cout << "Calibrating Lidar...\n";
    }
};

void processSensor(ISensor& sensor) {
    sensor.calibrate();
    double value = sensor.read();
    std::cout << "Sensor value: " << value << "\n";
}
```

---

## 10. Base Class Pointers: The Key to Polymorphism

A pointer of a base class type can point to an object of any derived class type. This is the foundation of polymorphic collections.

```cpp
class Robot { public: virtual void move() = 0; virtual ~Robot(){} }; // Abstract class
class WheeledRobot : public Robot { public: void move() override { std::cout << "Rolling\n"; } };
class FlyingRobot : public Robot { public: void move() override { std::cout << "Flying\n"; } };

int main() {
    // Create a heterogeneous collection of Robots
    Robot* fleet[2];
    fleet[0] = new WheeledRobot();
    fleet[1] = new FlyingRobot();

    // Polymorphic loop: each robot moves its own way
    for (int i = 0; i < 2; ++i) {
        fleet[i]->move(); // Calls the correct 'move' for the actual object type
    }

    for (int i = 0; i < 2; ++i) delete fleet[i];
}
```

---

## 11. Downcasting & Run-Time Type Identification

A base class pointer cannot directly access methods unique to a derived class. To do this, you must **downcast** the pointer.

```cpp
FlyingRobot* fly_ptr = dynamic_cast<FlyingRobot*>(base_pointer);
if (fly_ptr) { // Check if the cast was successful
    fly_ptr->take_off(); // Call the derived-specific method
}
```

- **`dynamic_cast`** is safe for polymorphic classes (classes with virtual functions). It returns `nullptr` if the cast fails.
- **Always check the result** of a `dynamic_cast` before using it.

---

## 12. Smart Pointers: Modern Memory Management

Manual `new`/`delete` is error-prone. Smart pointers from `<memory>` automate memory management.

| Smart Pointer | Ownership | Use Case |
| :--- | :--- | :--- |
| **`std::unique_ptr<T>`** | Exclusive | A robot node that owns its motor driver. Cannot be copied, only moved. |
| **`std::shared_ptr<T>`** | Shared | Multiple nodes or systems sharing access to a single, common sensor data stream. |
| **`std::weak_ptr<T>`** | Non-owning observer | Breaking circular references with `shared_ptr`. Observing an object without keeping it alive. |

```cpp
#include <memory>

int main() {
    // 1. unique_ptr
    auto motor = std::make_unique<MotorDriver>(); // Preferred creation
    // auto motor2 = motor; // ERROR: unique_ptr cannot be copied
    auto motor2 = std::move(motor); // Ownership is transferred.

    // 2. shared_ptr
    auto sensor1 = std::make_shared<Lidar>();
    auto sensor2 = sensor1; // Both now share ownership
    std::cout << "Use count: " << sensor1.use_count() << std::endl; // Output: 2

    // 3. weak_ptr (observing a shared_ptr)
    std::weak_ptr<Lidar> weak_sensor = sensor1;
    if (auto locked_sensor = weak_sensor.lock()) { // Get a shared_ptr if object still exists
        locked_sensor->scan();
    }
    return 0; // Memory automatically freed for all smart pointers.
}
```

---

## 13. Templates: Generic Programming

Templates allow you to write code that works with any data type.

### Function Template
```cpp
template <typename T>
T max(T a, T b) {
    return (a > b) ? a : b;
}
// Usage: max<int>(5, 3), max<double>(2.2, 3.3), max<std::string>("hi", "bye")
```

### Class Template
```cpp
template <typename T>
class Container {
    T value;
public:
    Container(const T& v) : value(v) {}
    T get() { return value; }
};
// Usage: Container<int> intContainer(10);
//        Container<std::string> stringContainer("Hello");
```

### Link to Smart Pointers (`make_shared`, `make_unique`)
```cpp
// make_shared is a FUNCTION TEMPLATE
// <Robot> is the TEMPLATE ARGUMENT (the type)
// ("Car", 5) are the CONSTRUCTOR ARGUMENTS for Robot
auto robot_ptr = std::make_shared<Robot>("Car", 5);
```

### Type Aliases with `using`
Modern C++ prefers `using` for type aliases, especially with templates.

```cpp
// Old C++ style
typedef std::shared_ptr<Robot> RobotPtr;
typedef std::vector<RobotPtr> RobotFleet;

// Modern C++ style
using RobotPtr = std::shared_ptr<Robot>;
using RobotFleet = std::vector<RobotPtr>;

// Alias template
template<typename T>
using SharedPtr = std::shared_ptr<T>;

SharedPtr<Robot> robot = std::make_shared<Robot>("R2D2", 100);
```

### CRTP (Curiously Recurring Template Pattern)
Static polymorphism through CRTP avoids virtual function overhead.

```cpp
template<typename Derived>
class RobotBase {
public:
    void move() {
        static_cast<Derived*>(this)->moveImpl();
    }

    void commonBehavior() {
        std::cout << "Common robot behavior\n";
        move();
    }
};

class WheeledRobotCRTP : public RobotBase<WheeledRobotCRTP> {
public:
    void moveImpl() {
        std::cout << "Rolling on wheels\n";
    }
};

class FlyingRobotCRTP : public RobotBase<FlyingRobotCRTP> {
public:
    void moveImpl() {
        std::cout << "Flying through air\n";
    }
};
```

---

## 14. Lambda Expressions: Functional Callbacks

Lambda expressions are especially useful for ROS2 callbacks and STL algorithms.

```cpp
#include <algorithm>
#include <vector>

int main() {
    std::vector<int> battery_levels = {85, 92, 78, 96};

    auto isLow = [](int level) { return level < 80; };
    auto low_it = std::find_if(battery_levels.begin(), battery_levels.end(), isLow);

    int threshold = 80;
    auto checkThreshold = [threshold](int level) {
        return level < threshold;
    };

    int count = 0;
    auto counter = [count]() mutable {
        return ++count;
    };

    auto generic_add = [](auto a, auto b) { return a + b; };

    // ROS2 callback style example inside a class method
    class NodeExample {
    public:
        void publish_data() {}
        void setupTimer() {
            auto timer_callback = [this]() {
                RCLCPP_INFO(this->get_logger(), "Timer triggered");
                this->publish_data();
            };
        }
        void* get_logger() { return nullptr; }
    } node;
}
```

---

## 15. Complete Working Example: A Robotic Fleet

This example combines classes, inheritance, polymorphism, pointers, and smart pointers.

```cpp
#include <iostream>
#include <memory>
#include <vector>

// Abstract Base Class
class Robot {
protected:
    std::string name_;
public:
    Robot(const std::string& name) : name_(name) {}
    virtual ~Robot() = default; // Virtual destructor for polymorphism
    
    virtual void move() = 0; // Pure virtual function (makes Robot abstract)
    
    void identify() const {
        std::cout << "I am " << name_ << ". ";
    }
};

// Derived Class 1
class WheeledRobot : public Robot {
    int wheels_;
public:
    WheeledRobot(const std::string& name, int wheels) : Robot(name), wheels_(wheels) {}
    void move() override {
        identify();
        std::cout << "Rolling on " << wheels_ << " wheels.\n";
    }
};

// Derived Class 2
class FlyingRobot : public Robot {
    double max_altitude_;
public:
    FlyingRobot(const std::string& name, double altitude) : Robot(name), max_altitude_(altitude) {}
    void move() override {
        identify();
        std::cout << "Flying up to " << max_altitude_ << " meters.\n";
    }
};

int main() {
    // Use smart pointers for automatic memory management
    std::vector<std::unique_ptr<Robot>> fleet;
    
    fleet.push_back(std::make_unique<WheeledRobot>("Rover", 6));
    fleet.push_back(std::make_unique<FlyingRobot>("Drone", 120.5));
    fleet.push_back(std::make_unique<WheeledRobot>("Robot Car", 4));
    
    std::cout << "--- Fleet Movement ---\n";
    for (const auto& robot_ptr : fleet) {
        robot_ptr->move(); // Polymorphic call
    }
    
    // Accessing via base pointer
    std::cout << "\n--- Direct access via pointer ---\n";
    FlyingRobot* fly_ptr = dynamic_cast<FlyingRobot*>(fleet[1].get());
    if (fly_ptr) {
        std::cout << "Found a flying robot named: ";
        fly_ptr->identify();
        std::cout << std::endl;
    }
    
    // fleet goes out of scope, all unique_ptrs automatically delete their Robots
    return 0;
}
```

---

## 16. Quick Reference Cheat Sheet

| Concept | Syntax Example |
| :--- | :--- |
| **Class definition** | `class MyClass { private: int x_; public: void func(); };` |
| **Member initializer list** | `MyClass(int x) : x_(x) {}` |
| **Inheritance (public)** | `class Derived : public Base { ... };` |
| **Virtual function** | `virtual void move() = 0;` (pure) or `virtual void move() {}` |
| **Override in derived** | `void move() override { ... }` |
| **Access via pointer** | `ptr->member` or `(*ptr).member` |
| **Pass by reference** | `void func(Type& ref)` or `const Type& ref` |
| **`unique_ptr`** | `auto ptr = std::make_unique<MyClass>(args);` |
| **`shared_ptr`** | `auto ptr = std::make_shared<MyClass>(args);` |
| **Downcasting** | `Derived* d = dynamic_cast<Derived*>(base_ptr); if (d) { ... }` |
| **Template function** | `template <typename T> T myFunc(T a) { ... }` |
| **Template class** | `template <typename T> class MyClass { T data; };` |
| **`explicit` constructor** | `explicit MyType(int value);` |
| **`noexcept`** | `void func() noexcept;` |
| **Lambda** | `auto fn = []() { return 42; };` |

---