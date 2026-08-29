/**
 * @file control_switches.h
 * @brief Manages 4 independent low-voltage source-selector toggle switches.
 *
 * SAFETY NOTE:
 * These switches are LOW-VOLTAGE ESP32 inputs only (3.3V logic).
 * They are NEVER connected to 230V AC mains or relay AC contact terminals.
 *
 * MAPPING:
 * - Load 1: GPIO 26
 * - Load 2: GPIO 27
 * - Load 3: GPIO 32
 * - Load 4: GPIO 33
 *
 * LOGIC:
 * - 0V (LOW)  = GRID
 * - 3.3V (HIGH) = SOLAR
 *
 * EDGE-TRIGGERED BEHAVIOR:
 * A physical switch level change (rising or falling edge) is a local override event.
 * An unchanged physical level does NOT repeatedly override a remote OFF command.
 */

#ifndef CONTROL_SWITCHES_H
#define CONTROL_SWITCHES_H

#include <Arduino.h>
#include "config.h"

// Forward declaration of SourceState (matches relay_controller.h)
enum SourceState : uint8_t {
    SRC_OFF = 0,
    SRC_GRID = 1,
    SRC_SOLAR = 2
};

struct SelectorPinInfo {
    uint8_t pin;
    bool raw_last;
    bool stable_state;          // false = LOW (GRID), true = HIGH (SOLAR)
    unsigned long last_change_ms;
    bool edge_detected;         // true on the exact poll tick when stable state changed
};

class ControlSwitches {
public:
    ControlSwitches();

    void begin();

    // Debounced polling. Call once per main loop iteration.
    void pollAndDebounce();

    // Returns current debounced physical switch position (SRC_GRID or SRC_SOLAR)
    SourceState getSelectorSource(uint8_t load_idx) const;

    // True ONLY on the poll tick where this specific switch changed state
    bool hasEdgeChanged(uint8_t load_idx) const;

    // Clears the edge flag for a given load after it has been handled
    void clearEdgeFlag(uint8_t load_idx);

    // True if ANY of the 4 switches changed on the current poll tick
    bool hasAnyEdgeChanged() const;

    // Diagnostic queries for raw pin level and GPIO number
    bool getRawState(uint8_t load_idx) const;
    uint8_t getPin(uint8_t load_idx) const;

private:
    SelectorPinInfo _selectors[NUM_LOADS];
};

#endif // CONTROL_SWITCHES_H
