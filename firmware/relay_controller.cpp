/**
 * @file relay_controller.cpp
 * @brief Implementation of per-load Grid/Solar dual-bank relay controller.
 */

#include "relay_controller.h"

RelayController::RelayController() {
    _loads[0] = {PIN_GRID_RELAY_LOAD1, PIN_SOLAR_RELAY_LOAD1, LOAD1_NAME, SRC_GRID, SRC_OFF, SRC_OFF};
    _loads[1] = {PIN_GRID_RELAY_LOAD2, PIN_SOLAR_RELAY_LOAD2, LOAD2_NAME, SRC_GRID, SRC_OFF, SRC_OFF};
    _loads[2] = {PIN_GRID_RELAY_LOAD3, PIN_SOLAR_RELAY_LOAD3, LOAD3_NAME, SRC_GRID, SRC_OFF, SRC_OFF};
    _loads[3] = {PIN_GRID_RELAY_LOAD4, PIN_SOLAR_RELAY_LOAD4, LOAD4_NAME, SRC_GRID, SRC_OFF, SRC_OFF};
}

void RelayController::writeRelay(uint8_t pin, bool energize) {
    // Active-LOW relay boards: LOW = Coil ON (Contacts Closed), HIGH = Coil OFF (Contacts Open)
    digitalWrite(pin, energize ? LOW : HIGH);
}

void RelayController::begin() {
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        // Drive pins HIGH (de-energized) before setting pinMode to prevent boot chatter
        digitalWrite(_loads[i].grid_pin, HIGH);
        digitalWrite(_loads[i].solar_pin, HIGH);
        pinMode(_loads[i].grid_pin, OUTPUT);
        pinMode(_loads[i].solar_pin, OUTPUT);
        digitalWrite(_loads[i].grid_pin, HIGH);
        digitalWrite(_loads[i].solar_pin, HIGH);

        _loads[i].applied_source = SRC_OFF;
        _loads[i].desired_source = SRC_OFF;
        _loads[i].selector_source = SRC_GRID;
    }
}

bool RelayController::setDesiredSource(uint8_t load_index, SourceState source) {
    if (load_index >= NUM_LOADS) return false;
    _loads[load_index].desired_source = source;
    return true;
}

void RelayController::setSelectorSource(uint8_t load_index, SourceState source) {
    if (load_index < NUM_LOADS) {
        _loads[load_index].selector_source = source;
    }
}

SourceState RelayController::getSelectorSource(uint8_t load_index) const {
    if (load_index >= NUM_LOADS) return SRC_GRID;
    return _loads[load_index].selector_source;
}

SourceState RelayController::getDesiredSource(uint8_t load_index) const {
    if (load_index >= NUM_LOADS) return SRC_OFF;
    return _loads[load_index].desired_source;
}

SourceState RelayController::getAppliedSource(uint8_t load_index) const {
    if (load_index >= NUM_LOADS) return SRC_OFF;
    return _loads[load_index].applied_source;
}

const char* RelayController::getLoadName(uint8_t load_index) const {
    if (load_index >= NUM_LOADS) return "Unknown";
    return _loads[load_index].name;
}

uint8_t RelayController::getGridPin(uint8_t load_index) const {
    if (load_index >= NUM_LOADS) return 0;
    return _loads[load_index].grid_pin;
}

uint8_t RelayController::getSolarPin(uint8_t load_index) const {
    if (load_index >= NUM_LOADS) return 0;
    return _loads[load_index].solar_pin;
}

void RelayController::transitionLoad(uint8_t idx, SourceState target) {
    LoadChannel &ch = _loads[idx];
    if (ch.applied_source == target) return;

    SourceState prev = ch.applied_source;

    Serial.printf("[INTERLOCK] Load %d (%s): Starting transition from %s -> %s\n",
                  idx + 1, ch.name, sourceToStr(prev), sourceToStr(target));

    // Step 1: De-energize active relay coil
    if (prev == SRC_GRID) {
        writeRelay(ch.grid_pin, false);
    } else if (prev == SRC_SOLAR) {
        writeRelay(ch.solar_pin, false);
    }

    // Step 2: Set intermediate applied state to OFF
    ch.applied_source = SRC_OFF;

    // Step 3: Software break-before-make dead-time delay
    // Both relays for this load are guaranteed OFF during this window.
    if (prev != SRC_OFF || target != SRC_OFF) {
        Serial.printf("[INTERLOCK] Load %d: Both coils OFF. Enforcing %d ms dead-time...\n",
                      idx + 1, BREAK_BEFORE_MAKE_MS);
        delay(BREAK_BEFORE_MAKE_MS);
    }

    // Step 4: Energize target relay coil
    if (target == SRC_GRID) {
        writeRelay(ch.grid_pin, true);
    } else if (target == SRC_SOLAR) {
        writeRelay(ch.solar_pin, true);
    }

    // Step 5: Update applied state
    ch.applied_source = target;

    Serial.printf("[RELAY] Load %d (%s): Transition complete. Applied source is now %s\n",
                  idx + 1, ch.name, sourceToStr(ch.applied_source));
}

bool RelayController::update() {
    bool changed = false;

    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        if (_loads[i].applied_source != _loads[i].desired_source) {
            transitionLoad(i, _loads[i].desired_source);
            changed = true;
        }
    }

    return changed;
}

void RelayController::allOff() {
    Serial.println(F("[RELAY] FORCE ALL OFF requested. De-energizing all relays immediately."));
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        _loads[i].desired_source = SRC_OFF;
        writeRelay(_loads[i].grid_pin, false);
        writeRelay(_loads[i].solar_pin, false);
        _loads[i].applied_source = SRC_OFF;
    }
}

bool RelayController::anyLoadEnergized() const {
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        if (_loads[i].applied_source != SRC_OFF) return true;
    }
    return false;
}

const char* RelayController::sourceToStr(SourceState s) {
    switch (s) {
        case SRC_GRID:  return "grid";
        case SRC_SOLAR: return "solar";
        default:        return "off";
    }
}

String RelayController::getStatesJson() const {
    String json = "{";
    for (uint8_t i = 0; i < NUM_LOADS; i++) {
        if (i > 0) json += ",";
        json += "\"load_" + String(i + 1) + "\":{";
        json += "\"name\":\"" + String(_loads[i].name) + "\",";
        json += "\"selector_source\":\"" + String(sourceToStr(_loads[i].selector_source)) + "\",";
        json += "\"desired_source\":\"" + String(sourceToStr(_loads[i].desired_source)) + "\",";
        json += "\"applied_source\":\"" + String(sourceToStr(_loads[i].applied_source)) + "\"";
        json += "}";
    }
    json += "}";
    return json;
}
