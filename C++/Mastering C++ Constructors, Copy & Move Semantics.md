## Your Go-To Revision Guide for Deep Memory Management

---

## 📑 Table of Contents

1. [The Core Problem: Raw Pointers & Memory](#1-the-core-problem-raw-pointers--memory)
2. [The Main Constructor & Destructor](#2-the-main-constructor--destructor)
3. [The Copy Constructor (Deep Copy)](#3-the-copy-constructor-deep-copy)
4. [The Copy Assignment Operator](#4-the-copy-assignment-operator)
5. [The Move Constructor (Steal, Don't Copy)](#5-the-move-constructor-steal-dont-copy)
6. [The Move Assignment Operator](#6-the-move-assignment-operator)
7. [std::move: The Enabler](#7-stdmove-the-enabler)
8. [Full Working Code Example](#8-full-working-code-example)
9. [Quick Reference Decision Table](#9-quick-reference-decision-table)
10. [Memory Diagram Summary](#10-memory-diagram-summary)

---

## 1. The Core Problem: Raw Pointers & Memory

When your class manages heap memory (using `new`), the **default** copy behavior from C++ is **shallow** - it only copies the pointer, not the actual data. This leads to **double deletion** and crashes.

```cpp
// ❌ DANGEROUS: Default copy would cause double delete
class DangerousBox {
public:
    int* data;
    DangerousBox(int v) { data = new int(v); }
    ~DangerousBox() { delete data; }
    // No copy constructor - C++ makes a shallow one!
    
    // Memory layout after shallow copy:
    // 
    //   Object A (other)          Object B (this)
    //   ┌──────────────┐          ┌──────────────┐
    //   │ data = 0x100 │          │ data = 0x100 │  ← SAME address!
    //   └──────┬───────┘          └──────┬───────┘
    //          │                         │
    //          └─────────┬───────────────┘
    //                    ▼
    //              ┌─────────────┐
    //              │  Value: 42  │  ← ONLY ONE copy of data!
    //              └─────────────┘
    //
    // PROBLEM: When A and B both delete the same pointer → DOUBLE FREE 💥
};

DangerousBox a(10);
DangerousBox b = a; // 💥 CRASH: Both point to same memory, double delete!
```

**The Rule of Three/Five:** If you need a custom destructor, you almost always need custom copy and move operations.

---

## 2. The Main Constructor & Destructor

The starting point: allocate in constructor, deallocate in destructor.

```cpp
class Box {
public:
    int* data;  // Pointer to heap memory

    // 🏗️ Constructor: Allocates memory
    Box(int v) { 
        data = new int(v); 
        std::cout << "Constructor: allocated " << data << " with value " << *data << "\n";
    }

    // 🧹 Destructor: Frees memory
    ~Box() { 
        std::cout << "Destructor: freeing " << data << "\n";
        delete data; 
    }
    
    // Other methods will be added here...
};
```

### 📝 Key Points:
- `new int(v)` allocates heap memory and initializes it with `v`
- `delete data` must be called exactly once per `new`
- The destructor runs automatically when the object goes out of scope

### ✅ Usage:
```cpp
Box a(42);  // Constructor called
// ... when 'a' goes out of scope, destructor called automatically
```

---

## 3. The Copy Constructor (Deep Copy)

Creates a new, independent copy of an existing object.

```cpp
class Box {
public:
    int* data;

    // Main constructor
    Box(int v) { data = new int(v); }
    
    // 📋 Copy Constructor: Creates a deep copy
    Box(const Box& other) {
        data = new int(*other.data);  // Allocate NEW memory, copy value
        std::cout << "Copy Constructor: new copy at " << data << "\n";
    }

    // Memory layout after deep copy:
    //
    //   Object A (other)          Object B (this)
    //   ┌──────────────┐          ┌──────────────┐
    //   │ data = 0x100 │          │ data = 0x200 │  ← DIFFERENT addresses!
    //   └──────┬───────┘          └──────┬───────┘
    //          │                         │
    //          ▼                         ▼
    //   ┌─────────────┐            ┌─────────────┐
    //   │  Value: 42  │            │  Value: 42  │  ← TWO independent copies!
    //   └─────────────┘            └─────────────┘
    //
    // SAFE: Each object deletes its own memory independently ✅
    
    // Destructor
    ~Box() { delete data; }
};
```

### 🔄 When is it called?
```cpp
Box a(42);      // Main constructor
Box b = a;      // 📋 Copy constructor (initialization)
Box c(a);       // 📋 Copy constructor (direct)
void func(Box param); // 📋 Copy constructor (pass by value)
```

### 🧠 Memory Mental Model:
```
Before:               After Copy:
a.data → [42]         a.data → [42]
b.data → ???          b.data → [42]  (brand new copy)
```

---

## 4. The Copy Assignment Operator

Assigns one existing object to another existing object.

```cpp
class Box {
public:
    int* data;

    Box(int v) { data = new int(v); }
    Box(const Box& other) { data = new int(*other.data); }
    
    // 📋 Copy Assignment: Replace contents with a copy
    Box& operator=(const Box& other) {
        if (this == &other) return *this;  // 🛡️ Guard: self-assignment (a = a)
        
        delete data;                       // 🧹 Free old memory
        data = new int(*other.data);       // 📋 Allocate & copy new value
        
        std::cout << "Copy Assignment: " << data << " now has " << *data << "\n";
        return *this;                      // 🔗 Return *this for chaining
    }
    
    ~Box() { delete data; }
};
```

### 🔄 When is it called?
```cpp
Box a(42);
Box b(100);
b = a;  // 📋 Copy assignment (b already exists)
```

### ⚠️ Critical Steps:
1. **Self-assignment guard** - Prevents `delete this->data` when `&other == this`
2. **Free old resources** - Avoid memory leak
3. **Allocate and copy** - Deep copy the data
4. **Return `*this`** - Enables `a = b = c`

### 🧠 Memory Mental Model:
```
Before:               Operation:              After:
a.data → [42]         delete b.data     →    a.data → [42]
b.data → [100]        new int(42)       →    b.data → [42]
```

---

## 5. The Move Constructor (Steal, Don't Copy)

Transfers ownership of resources from a temporary object. **No new allocation!**

```cpp
class Box {
public:
    int* data;

    Box(int v) { data = new int(v); }
    
    // 🚀 Move Constructor: Steal the pointer
    Box(Box&& other) noexcept : data(nullptr) {
        data = other.data;      // 🔪 Steal the pointer
        other.data = nullptr;   // 👐 Leave source in empty, destructible state
        
        std::cout << "Move Constructor: stole " << data << "\n";
    }
    
    ~Box() { delete data; }
    
    // Copy members omitted for brevity...
};
```
```
The Critical Difference Visualized
text
╔═══════════════════════════════════════════════════════════════════╗
║                    COPY CONSTRUCTOR (DEEP COPY)                   ║
╚═══════════════════════════════════════════════════════════════════╝

Before Copy:
┌──────────────┐     ┌─────────────┐
│   other      │     │   this      │
├──────────────┤     ├─────────────┤
│ data = 0x1000┼──┐  │ data = ???  │
└──────────────┘  │  └─────────────┘
                  ▼
            ┌─────────┐
            │   42    │  (ONE memory block)
            │ 0x1000  │
            └─────────┘

During Copy (new int(*other.data)):
┌──────────────┐     ┌──────────────┐
│   other      │     │   this       │
├──────────────┤     ├──────────────┤
│ data = 0x1000┼──┐  │ data = 0x2000┼──┐
└──────────────┘  │  └──────────────┘  │
                  ▼                    ▼
            ┌─────────┐          ┌─────────┐
            │   42    │          │   42    │  ← NEW allocation!
            │ 0x1000  │          │ 0x2000  │
            └─────────┘          └─────────┘

Result: TWO memory blocks (0x1000 and 0x2000) = DOUBLE SPACE! 📦📦

╔═══════════════════════════════════════════════════════════════════╗
║                    MOVE CONSTRUCTOR (STEAL)                       ║
╚═══════════════════════════════════════════════════════════════════╝

Before Move:
┌──────────────┐     ┌───────────────┐
│   other      │     │   this        │
├──────────────┤     ├───────────────┤
│ data = 0x1000┼──┐  │ data = nullptr│
└──────────────┘  │  └───────────────┘
                  ▼
            ┌─────────┐
            │   42    │  (ONE memory block)
            │ 0x1000  │
            └─────────┘

During Move (data = other.data):
┌──────────────┐     ┌──────────────┐
│   other      │     │   this       │
├──────────────┤     ├──────────────┤
│ data = 0x1000┼──┐  │ data = 0x1000┼──┐
└──────────────┘  │  └──────────────┘  │
                  ▼                    ▼
            ┌─────────┐          ┌─────────┐
            │   42    │          │   42    │  ← SAME memory!
            │ 0x1000  │          │ 0x1000  │  ← Just two pointers to same block!
            └─────────┘          └─────────┘

After Move (other.data = nullptr):
┌───────────────┐     ┌───────────────┐
│   other       │     │   this        │
├───────────────┤     ├───────────────┤
│ data = nullptr│     │ data = 0x1000 ┼──┐
└───────────────┘     └───────────────┘  │
                                         ▼
                                ┌─────────┐
                                │   42    │  (STILL ONE memory block!)
                                │ 0x1000  │
                                └─────────┘

Result: ONE memory block, TWO pointers (one now null) = NO DOUBLE SPACE! 📦
```

### 🔄 When is it called?
```cpp
Box a(42);
Box b = std::move(a);  // 🚀 Move constructor

// Also with temporaries:
Box c = Box(100);      // 🚀 Move constructor (or copy elision)
```

### 🧠 Memory Mental Model:
```
Before:               Move:                   After:
a.data → [42]         b.data = a.data    →   b.data → [42]
b.data → ???          a.data = nullptr   →   a.data → nullptr
```

### 💡 Key Insights:
- **`noexcept`** is critical - standard containers (like `vector`) only use move if it's noexcept
- Source object is left in a "valid but unspecified state" (here: `nullptr`)
- Destructor can safely `delete nullptr` (does nothing)

---

## 6. The Move Assignment Operator

Transfers ownership to an existing object.

```cpp
class Box {
public:
    int* data;

    Box(int v) { data = new int(v); }
    
    // 🚀 Move Assignment: Replace contents by stealing
    Box& operator=(Box&& other) noexcept {
        if (this == &other) return *this;  // 🛡️ Self-move guard
        
        delete data;                       // 🧹 Free our old memory
        data = other.data;                 // 🔪 Steal the pointer
        other.data = nullptr;              // 👐 Disarm the source
        
        std::cout << "Move Assignment: stole " << data << "\n";
        return *this;
    }
    
    ~Box() { delete data; }
};
```

### 🔄 When is it called?
```cpp
Box a(42);
Box b(100);
b = std::move(a);  // 🚀 Move assignment
```

### 🧠 Memory Mental Model:
```
Before:               Operation:              After:
a.data → [42]         delete b.data     →    a.data → nullptr
b.data → [100]        b.data = a.data   →    b.data → [42]
```

---

## 7. std::move: The Enabler

`std::move` is **just a cast** - it doesn't move anything by itself!

```cpp
Box a(42);
Box b = std::move(a);  // std::move casts 'a' to Box&&
                       // Compiler sees: Box(Box&&) - MATCHES move constructor!
```

### 🎭 What `std::move` Really Does:
```cpp
// Simplified view of what std::move does:
static_cast<Box&&>(a);  // Just changes the type from Box& to Box&&
```

### 🚫 After a Move:
```cpp
Box a(42);
Box b = std::move(a);

// a is now in a "moved-from" state (data = nullptr)
// You can:
// - Destroy a (destructor runs fine)
// - Assign a new value to a (a = Box(99))
// 
// You should NOT:
// - Use the value of a without checking (if you wrote a proper API)
```

---

## 8. Full Working Code Example

Here's a complete, runnable example showing all operations:

```cpp
#include <iostream>
#include <utility>  // for std::move

class Box {
private:
    int* data;
    
public:
    // 🏗️ Constructor
    Box(int v) : data(new int(v)) {
        std::cout << "[Construct] " << data << " = " << *data << "\n";
    }
    
    // 📋 Copy Constructor
    Box(const Box& other) : data(new int(*other.data)) {
        std::cout << "[Copy Construct] " << data << " = " << *data << "\n";
    }
    
    // 📋 Copy Assignment
    Box& operator=(const Box& other) {
        if (this == &other) return *this;
        std::cout << "[Copy Assign] " << data << " -> ";
        delete data;
        data = new int(*other.data);
        std::cout << data << " = " << *data << "\n";
        return *this;
    }
    
    // 🚀 Move Constructor
    Box(Box&& other) noexcept : data(other.data) {
        other.data = nullptr;
        std::cout << "[Move Construct] stole " << data << "\n";
    }
    
    // 🚀 Move Assignment
    Box& operator=(Box&& other) noexcept {
        if (this == &other) return *this;
        std::cout << "[Move Assign] " << data << " -> ";
        delete data;
        data = other.data;
        other.data = nullptr;
        std::cout << "stole " << data << "\n";
        return *this;
    }
    
    // 🧹 Destructor
    ~Box() {
        std::cout << "[Destruct] " << data << "\n";
        delete data;
    }
    
    int getValue() const { return data ? *data : 0; }
};

int main() {
    std::cout << "=== CREATION ===\n";
    Box a(42);                    // Constructor
    
    std::cout << "\n=== COPY ===\n";
    Box b = a;                    // Copy constructor
    Box c(0);
    c = a;                        // Copy assignment
    
    std::cout << "\n=== MOVE ===\n";
    Box d = std::move(a);         // Move constructor
    Box e(99);
    e = std::move(b);             // Move assignment
    
    std::cout << "\n=== VALUES ===\n";
    std::cout << "a (moved-from): " << a.getValue() << "\n";
    std::cout << "d: " << d.getValue() << "\n";
    std::cout << "e: " << e.getValue() << "\n";
    
    std::cout << "\n=== DESTRUCTION ===\n";
    return 0;
}
```

### 🖥️ Expected Output (addresses will vary):
```
=== CREATION ===
[Construct] 0x... = 42

=== COPY ===
[Copy Construct] 0x... = 42
[Copy Assign] 0x... -> 0x... = 42

=== MOVE ===
[Move Construct] stole 0x...
[Move Assign] 0x... -> stole 0x...

=== VALUES ===
a (moved-from): 0
d: 42
e: 42

=== DESTRUCTION ===
[Destruct] 0x...
[Destruct] 0x...
[Destruct] 0x...
[Destruct] 0x...
[Destruct] 0x...
```

---

## 9. Quick Reference Decision Table

| Syntax | What's Called | When to Use | Performance |
|--------|--------------|-------------|-------------|
| `Box b(42);` | Constructor | Creating new object with value | N/A |
| `Box b = a;` | Copy Constructor | Need independent copy | 🐢 O(n) |
| `b = a;` | Copy Assignment | Reassign existing object | 🐢 O(n) |
| `Box b = std::move(a);` | Move Constructor | Transfer ownership, `a` no longer needed | 🚀 O(1) |
| `b = std::move(a);` | Move Assignment | Transfer to existing object | 🚀 O(1) |
| `Box(Box&&) noexcept` | Move Constructor | Required for `vector` growth | 🚀 O(1) |

---

## 10. Memory Diagram Summary

### 📋 Copy Semantics
```
┌─────────┐     ┌─────────┐
│ Object A │     │ Object B │
├─────────┤     ├─────────┤
│ data ───┼──┐  │ data ───┼──┐
└─────────┘  │  └─────────┘  │
             ▼               ▼
        ┌─────────┐     ┌─────────┐
        │  Value  │     │  Value  │
        │   42    │     │   42    │
        └─────────┘     └─────────┘
        
Two separate allocations! Independent copies.
```

### 🚀 Move Semantics
```
BEFORE MOVE:
┌─────────┐     ┌─────────┐
│ Object A │     │ Object B │
├─────────┤     ├─────────┤
│ data ───┼──┐  │ data ───┼──→ nullptr
└─────────┘  │  └─────────┘
             ▼
        ┌─────────┐
        │  Value  │
        │   42    │
        └─────────┘

AFTER MOVE:
┌─────────┐     ┌─────────┐
│ Object A │     │ Object B │
├─────────┤     ├─────────┤
│ data ───┼──→ nullptr    │
└─────────┘     │ data ───┼──┐
                └─────────┘  │
                             ▼
                        ┌─────────┐
                        │  Value  │
                        │   42    │
                        └─────────┘

Zero allocations! Just pointer transfer.
```

---

## 🎯 Final Pro-Tips

1. **Rule of Five:** If you define one of {destructor, copy constructor, copy assignment, move constructor, move assignment}, define all five.

2. **Use `noexcept` on moves:** Standard containers (vector, etc.) will use copy instead of move if move isn't noexcept.

3. **After move:** Always leave source in a state that can be destroyed (nullptr works great).

4. **Self-assignment check:** Always check `if (this == &other)` in assignment operators.

5. **Prefer `std::make_unique` over raw pointers:** Modern C++ avoids manual `new`/`delete` when possible.

---

*Happy coding! This guide is your reference for mastering move semantics in C++.* 🚀
```