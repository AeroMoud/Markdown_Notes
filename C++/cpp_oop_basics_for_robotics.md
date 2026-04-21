# Tutorial 1: C++ OOP for Robotics (Robots, Inheritance, Pointers)

Save as: `cpp_oop_basics_for_robotics.md`

***

## Table of Contents

1. Introduction  
2. Classes and Objects  
3. Access Modifiers: `private`, `protected`, `public`  
4. Constructors, Destructors, and Initializer Lists  
5. Inheritance and Base-Class Constructors  
6. Polymorphism: `virtual` and `override`  
7. Pointers, References, and Dereferencing Objects  
8. Putting It All Together  

***

## 1. Introduction

This tutorial refreshes the **core OOP ideas in C++** using robots as examples:

- How to define classes and objects  
- `private` vs `protected` vs `public`  
- Constructors, destructors, and initializer lists  
- Inheritance (`Robot` → `WheeledRobot`)  
- Polymorphism (virtual functions, base pointers)  
- Pointers, references, and dereferencing objects  

These are the foundations you’ll see everywhere in ROS2 code and robotics C++ projects .

***

## 2. Classes and Objects

### Simple `Robot` Class

```cpp
#include <iostream>
#include <string>
using namespace std;

class Robot {
public:
    Robot(const string& name)
        : name_(name) {
        cout << "Robot " << name_ << " created\n";
    }
    
    ~Robot() {
        cout << "Robot " << name_ << " destroyed\n";
    }
    
    void move() {
        cout << name_ << " is moving\n";
    }
    
private:
    string name_;
};

int main() {
    Robot r("R2D2");  // Constructor called
    r.move();         // Call method
}  // Destructor called automatically
```

Key points:

- `class Robot { ... };` defines a new type.  
- `name_` is a **member variable** (object state).  
- `move()` is a **member function** (object behavior).  
- Constructor runs when object is created; destructor runs when object dies .

***

## 3. Access Modifiers

### `private` vs `protected` vs `public`

```cpp
class Robot {
public:
    void move();        // Everyone can call
    
protected:
    string name_;       // Robot + derived classes can access
    
private:
    int secret_id_;     // Only Robot can access
};
```

Access table:

| Location            | `public` | `protected` | `private` |
|---------------------|---------:|------------:|----------:|
| Same class          |    ✓     |      ✓      |     ✓     |
| Derived class       |    ✓     |      ✓      |     ✗     |
| Outside class (main)|    ✓     |      ✗      |     ✗     |

- Use **`private`** for internal details that nobody outside should touch.  
- Use **`protected`** when derived classes need access (e.g., `name_` in child robots) .

***

## 4. Constructors, Destructors, Initializer Lists

### Constructor with Member Initializer List

```cpp
class Robot {
public:
    Robot(const string& name, int battery)
        : name_(name), battery_(battery) {
        // Body (optional)
    }

private:
    string name_;
    int battery_;
};
```

Why use `: name_(name), battery_(battery)` instead of assigning inside the body?

- Members are **constructed before** the constructor body runs.  
- The initializer list constructs them directly with given values.  
- Required for:
  - `const` members  
  - reference members  
  - base classes .

### Example with `const` and reference

```cpp
class Robot {
public:
    Robot(int id, int& battery_ref)
        : id_(id), battery_ref_(battery_ref) {}

private:
    const int id_;    // must be initialized in initializer list
    int& battery_ref_; // must be initialized in initializer list
};
```

You **cannot** do `id_ = 5;` in the body because `id_` is const.

### Destructor

```cpp
~Robot() {
    cout << "Robot " << name_ << " destroyed\n";
}
```

Used for cleanup (closing files, freeing resources, etc.) .

***

## 5. Inheritance and Base Constructors

### Basic Inheritance

```cpp
class Robot {
public:
    Robot(const string& name)
        : name_(name) {}

    void move() {
        cout << name_ << " moves slowly\n";
    }

protected:
    string name_;
};

class WheeledRobot : public Robot {
public:
    WheeledRobot(const string& name, int wheels)
        : Robot(name),       // call base constructor
          wheels_(wheels) {} // init own member

    void printInfo() {
        cout << name_ << " has " << wheels_ << " wheels\n";
    }

private:
    int wheels_;
};
```

- `class WheeledRobot : public Robot` → WheeledRobot **is-a** Robot.  
- `: Robot(name)` → calls **base class constructor** to build the `Robot` part.  
- `name_` belongs to the `Robot` subobject, so only `Robot`’s constructor can initialize it .

### Why not `name_(name)` in `WheeledRobot`?

This would be illegal:

```cpp
WheeledRobot(const string& name, int wheels)
    : name_(name), wheels_(wheels) {} // ERROR
```

Because `name_` is a member of `Robot`, not `WheeledRobot`.  
The derived class **cannot** directly initialize base-class members; it must call the base constructor .

***

## 6. Polymorphism: `virtual` and `override`

### Without `virtual` (no polymorphism)

```cpp
class Robot {
public:
    void move() {
        cout << "Robot moves slowly\n";
    }
};

class WheeledRobot : public Robot {
public:
    void move() {  // hides base, but no polymorphism
        cout << "Wheeled robot rolls\n";
    }
};

int main() {
    WheeledRobot w("Car", 4);
    Robot* r_ptr = &w;
    r_ptr->move();  // calls Robot::move(), NOT WheeledRobot::move()
}
```

### With `virtual` and `override`

```cpp
class Robot {
public:
    Robot(const string& name) : name_(name) {}
    virtual ~Robot() {}  // virtual destructor

    virtual void move() {   // virtual: can be overridden
        cout << name_ << " moves slowly\n";
    }

protected:
    string name_;
};

class WheeledRobot : public Robot {
public:
    WheeledRobot(const string& name, int wheels)
        : Robot(name), wheels_(wheels) {}

    void move() override {   // override base
        cout << name_ << " rolls on " << wheels_ << " wheels\n";
    }

private:
    int wheels_;
};

int main() {
    WheeledRobot wr("RoboCar", 4);
    Robot* r_ptr = &wr;   // base pointer to derived object
    r_ptr->move();        // calls WheeledRobot::move() (polymorphism)
}
```

- `virtual` in base tells C++: choose function at **runtime** based on real object type.  
- `override` in derived tells compiler: “this overrides a virtual function; check signature” .  
- Always make base class destructors virtual if you will delete via a base pointer.

***

## 7. Pointers, References, and Dereferencing Objects

### Object vs Pointer to Object

```cpp
Robot r("R2D2");     // object
Robot* p = &r;       // pointer to object
p->move();           // pointer access
(*p).move();         // equivalent
```

Forms:

- `obj.member` → direct object  
- `ptr->member` → pointer to object (arrow)  
- `(*ptr).member` → explicit dereference then dot .

### Pointer to Base, Instance of Derived

```cpp
WheeledRobot wr("Car", 4);
Robot* r_ptr = &wr;   // base pointer, derived object

r_ptr->move();        // with virtual → calls WheeledRobot::move
```

This is the core of runtime polymorphism: **one base pointer type, many possible actual types** .

### References

```cpp
Robot r("R2D2");
Robot& ref = r;   // reference, alias for r
ref.move();       // same as r.move()
```

Reference to base, derived instance:

```cpp
WheeledRobot wr("Car", 4);
Robot& r_ref = wr;
r_ref.move();   // with virtual → calls WheeledRobot::move
```

***

## 8. Putting It All Together

### Full Example

```cpp
#include <iostream>
#include <string>
using namespace std;

class Robot {
public:
    Robot(const string& name, int id)
        : name_(name), id_(id) {
        cout << "Robot " << name_ << " (ID " << id_ << ") created\n";
    }

    virtual ~Robot() {
        cout << "Robot " << name_ << " destroyed\n";
    }

    virtual void move() {
        cout << name_ << " moves slowly\n";
    }

    void status() const {
        cout << "Robot " << name_ << " (ID " << id_ << ")\n";
    }

protected:
    string name_;

private:
    const int id_;  // must be initialized in initializer list
};

class WheeledRobot : public Robot {
public:
    WheeledRobot(const string& name, int id, int wheels)
        : Robot(name, id), wheels_(wheels) {
        cout << "WheeledRobot with " << wheels_ << " wheels created\n";
    }

    ~WheeledRobot() override {
        cout << "WheeledRobot " << name_ << " destroyed\n";
    }

    void move() override {
        cout << name_ << " rolls on " << wheels_ << " wheels\n";
    }

    void printInfo() {
        status();
        cout << "Wheels: " << wheels_ << "\n";
    }

private:
    int wheels_;
};

int main() {
    // Stack objects
    Robot base("BaseBot", 1);
    WheeledRobot wheeled("RoboCar", 2, 4);

    cout << "\n--- Direct calls ---\n";
    base.move();
    wheeled.move();

    cout << "\n--- Polymorphism with pointer ---\n";
    Robot* r_ptr = &wheeled;
    r_ptr->move();      // calls WheeledRobot::move()
    r_ptr->status();    // calls Robot::status()

    cout << "\n--- Polymorphism with reference ---\n";
    Robot& r_ref = wheeled;
    r_ref.move();       // calls WheeledRobot::move()

    cout << "\n--- End of main ---\n";
    return 0;
}
```

This example shows:

- `private` vs `protected` vs `public`  
- Constructor and initializer list (including `const id_`)  
- Inheritance and base constructor call `: Robot(name, id)`  
- Virtual function `move()` and polymorphic behavior  
- Base class pointer/reference to derived object  
