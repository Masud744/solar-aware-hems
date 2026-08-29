/**
 * @file relay_controller.h
 * @brief Per-load Grid/Solar dual-bank relay source-selection controller.
 *
 * THREE-STATE MODEL:
 * Each load tracks:
 * 1. selector_source: Physical switch position (GRID / SOLAR)
 * 2. desired_source: System requested target (GRID / SOLAR / OFF)
 * 3. applied_source: Currently energized relay coil (GRID / SOLAR / OFF)
 *
 * BREAK-BEFORE-MAKE SAFETY:
 * Switching between sources strictly enforces:
 * Current relay coil OFF -> Both coils OFF -> 300 ms dead-time -> Target coil ON.
 * Under no circumstances are both Grid and Solar relays for the same load
 * energized simultaneously.
 *
 * NOTE: This is a software interlock only — not a certified ATS hardware interlock.
 */

#ifndef RELAY_CONTROLLER_H
#define RELAY_CONTROLLER_H

#include <Arduino.h>
#include "config.h"
#include "control_switches.h"

struct LoadChannel {
    uint8_t grid_pin;
    uint8_t solar_pin;
    const char* name;
    SourceState selector_source; // Live debounced physical switch (GRID / SOLAR)
    SourceState desired_source;  // Target commanded source (GRID / SOLAR / OFF)
    SourceState applied_source;  // Live energized relay state (GRID / SOLAR / OFF)
};

class RelayController {
public:
    RelayController();

    void begin();

    // Setters & Getters
    bool setDesiredSource(uint8_t load_index, SourceState source);
    void setSelectorSource(uint8_t load_index, SourceState source);

    SourceState getSelectorSource(uint8_t load_index) const;
    SourceState getDesiredSource(uint8_t load_index) const;
    SourceState getAppliedSource(uint8_t load_index) const;

    const char* getLoadName(uint8_t load_index) const;
    uint8_t getGridPin(uint8_t load_index) const;
    uint8_t getSolarPin(uint8_t load_index) const;

    // Evaluates desired_source vs applied_source for all loads and applies
    // required break-before-make transitions.
    // Returns true if at least one load's applied state changed.
    bool update();

    // Emergency / Force All OFF
    void allOff();

    // True if any load currently has applied_source != SRC_OFF
    bool anyLoadEnergized() const;

    // Formatted JSON string of the three-state model for telemetry
    String getStatesJson() const;

    // Helper to format source state as string
    static const char* sourceToStr(SourceState s);

private:
    LoadChannel _loads[NUM_LOADS];

    void writeRelay(uint8_t pin, bool energize);
    void transitionLoad(uint8_t idx, SourceState target);
};

#endif // RELAY_CONTROLLER_H
