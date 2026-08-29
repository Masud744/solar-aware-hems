# Hardware Wiring Architecture & Pinout Specification

> **Firmware Version:** ESP32 Dual-Bank Dual-Core HEMS Firmware (Authoritative)  
> **Status:** `[AUTHORITATIVE PIN SPECIFICATION]`

---

## 1. Authoritative Hardware Pinout Matrix

The table below defines the authoritative physical GPIO wiring configured in `firmware/config.h`:

| Function / Component | Physical Channel | ESP32 GPIO | Electrical Specs & Conditioning | Authoritative Status |
|---|---|:---:|---|:---:|
| **DHT22 Sensor** | Ambient Temp & Humidity | **GPIO 4** | 10kΩ pull-up resistor to 3.3V | `[VERIFIED]` |
| **Status / SmartProv LED**| Onboard Indicator | **GPIO 2** | Active-HIGH (Shared with SmartProv indicator) | `[VERIFIED]` |
| **SmartProv Reset Button**| Factory Reset | **GPIO 0** | Active-LOW (BOOT button) | `[VERIFIED]` |
| **Current Sensor (ACS712)**| Aggregate AC Current | **GPIO 34** | ADC1_CH6 via 10kΩ/15kΩ resistor divider (0.600 ratio) | `[VERIFIED]` |
| **Voltage Sensor (ZMPT101B)**| AC Mains Voltage | **GPIO 35** | ADC1_CH7 input-only analog channel | `[VERIFIED]` |
| **Grid Relay Bank** | Load 1 Grid | **GPIO 16** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[VERIFIED]` |
| | Load 2 Grid | **GPIO 17** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[VERIFIED]` |
| | Load 3 Grid | **GPIO 18** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[VERIFIED]` |
| | Load 4 Grid | **GPIO 19** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[VERIFIED]` |
| **Represented-Solar Bank**| Load 1 Solar | **GPIO 21** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[VERIFIED]` |
| | Load 2 Solar | **GPIO 22** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[VERIFIED]` |
| | Load 3 Solar | **GPIO 23** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[VERIFIED]` |
| | Load 4 Solar | **GPIO 13** | Active-LOW (Reassigned from GPIO 25) | `[VERIFIED]` |
| **Source Selector Switches**| Load 1 Selector | **GPIO 26** | 3.3V $\rightarrow$ Switch $\rightarrow$ GPIO (10kΩ pull-down to GND) | `[VERIFIED]` |
| | Load 2 Selector | **GPIO 27** | 3.3V $\rightarrow$ Switch $\rightarrow$ GPIO (10kΩ pull-down to GND) | `[VERIFIED]` |
| | Load 3 Selector | **GPIO 32** | 3.3V $\rightarrow$ Switch $\rightarrow$ GPIO (10kΩ pull-down to GND) | `[VERIFIED]` |
| | Load 4 Selector | **GPIO 33** | 3.3V $\rightarrow$ Switch $\rightarrow$ GPIO (10kΩ pull-down to GND) | `[VERIFIED]` |

---

## 2. Legacy Diagram Disclosure: `esp32_hems_wiring.png`

> [!WARNING]
> **ARCHIVED LEGACY DIAGRAM (`esp32_hems_wiring.png`):**  
> The image file `esp32_hems_wiring.png` preserved in this directory illustrates the **early 4-relay single-bank prototype (Firmware v1)**. It does NOT depict:
> 1. The 8-relay dual-bank matrix (Grid L1–L4 on GPIO 16/17/18/19, Solar L1–L3 on GPIO 21/22/23, Solar L4 on GPIO 13).
> 2. The 4 physical low-voltage toggle selector switches on GPIO 26, 27, 32, and 33.
> 3. The 10kΩ/15kΩ ACS712 voltage divider on GPIO 34.
> 
> Refer strictly to `firmware/config.h` and the table above for the authoritative wiring schematic of the dual-bank production system.
