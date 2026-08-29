/**
 * @file control_switches.cpp
 * @brief Implementation of debounced 4-channel low-voltage source selector inputs.
 */

#include "control_switches.h"

ControlSwitches::ControlSwitches() {
    _selectors[0] = {PIN_SOURCE_SELECTOR_LOAD1, false, false, 0, false};
    _selectors[1] = {PIN_SOURCE_SELECTOR_LOAD2, false, false, 0, false};
    _selectors[2] = {PIN_SOURCE_SELECTOR_LOAD3, false, false, 0, false};
    _selectors[3] = {PIN_SOURCE_SELECTOR_LOAD4, false, false, 0, false};
}

void ControlSwitches::begin() {
    // 1. Configure all selector GPIOs with internal pull-down
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        pinMode(_selectors[i].pin, INPUT_PULLDOWN);
    }

    // 2. Allow hardware settling window for internal pull-down and line capacitance
    delay(50);

    // 3. Establish initial settled raw and debounced baseline
    unsigned long now = millis();
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        bool settled_raw = digitalRead(_selectors[i].pin);
        _selectors[i].raw_last = settled_raw;
        _selectors[i].stable_state = settled_raw;
        _selectors[i].last_change_ms = now;
        _selectors[i].edge_detected = false; // Strictly false: boot baseline is NOT an edge
    }
}

void ControlSwitches::pollAndDebounce() {
    unsigned long now = millis();

    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        bool raw = digitalRead(_selectors[i].pin);

        if (raw != _selectors[i].raw_last) {
            _selectors[i].last_change_ms = now;
            _selectors[i].raw_last = raw;
        }

        if ((now - _selectors[i].last_change_ms) >= SELECTOR_DEBOUNCE_MS) {
            if (_selectors[i].stable_state != raw) {
                _selectors[i].stable_state = raw;
                _selectors[i].edge_detected = true;
            }
        }
    }
}

SourceState ControlSwitches::getSelectorSource(uint8_t load_idx) const {
    if (load_idx >= NUM_LOADS) return SRC_GRID;
    return _selectors[load_idx].stable_state ? SRC_SOLAR : SRC_GRID;
}

bool ControlSwitches::hasEdgeChanged(uint8_t load_idx) const {
    if (load_idx >= NUM_LOADS) return false;
    return _selectors[load_idx].edge_detected;
}

void ControlSwitches::clearEdgeFlag(uint8_t load_idx) {
    if (load_idx < NUM_LOADS) {
        _selectors[load_idx].edge_detected = false;
    }
}

bool ControlSwitches::hasAnyEdgeChanged() const {
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        if (_selectors[i].edge_detected) return true;
    }
    return false;
}

bool ControlSwitches::getRawState(uint8_t load_idx) const {
    if (load_idx >= NUM_LOADS) return false;
    return digitalRead(_selectors[load_idx].pin);
}

uint8_t ControlSwitches::getPin(uint8_t load_idx) const {
    if (load_idx >= NUM_LOADS) return 0;
    return _selectors[load_idx].pin;
}
