# Hardware Wiring Architecture & Power Distribution Specification

> **Firmware Version:** ESP32 Dual-Bank Dual-Core HEMS Firmware (Authoritative)  
> **Status:** `[AUTHORITATIVE HARDWARE & WIRING SPECIFICATION]`  
> **Classification:** Physical Prototype Bench Setup (Non-Certified Academic Prototype)

---

## 1. Physical Power Distribution & Common Ground Topology

The physical Solar-Aware HEMS prototype implements a stepped-down DC power chain to isolate and regulate power for the ESP32 microcontroller, analog sensing frontend, and 8-channel relay actuation coils:

```
 [230V AC Mains]
        │
        ▼
 ┌────────────────────────┐
 │   AC-to-DC Adapter     │ (7.5V DC Output)
 └──────────┬─────────────┘
            │
            ▼
 ┌────────────────────────┐
 │  PJ-102A DC Power Jack │ (2.1mm DC Barrel Connector)
 └──────────┬─────────────┘
            │
            ▼
 ┌────────────────────────┐
 │  Buck Converter Module │ (Step-down: 7.5V DC ──► Regulated 5.0V DC Rail)
 └──────────┬─────────────┘
            │
            ├──────────────────────────────────────────────────────────────────────────┐
            │ +5V Regulated Power Rail                                                 │ Common Ground Rail (GND)
            ▼                                                                          ▼
 ┌──────────────────────────────────────────────────┐               ┌──────────────────────────────────────────────────┐
 │ • ESP32 DevKit V1: VIN / 5V Input                │               │ • ESP32 DevKit V1: GND Pins                      │
 │ • ACS712-20A Current Sensor: VCC (Pin 1)         │               │ • ACS712-20A Current Sensor: GND (Pin 2)         │
 │ • ZMPT101B Voltage Sensor: VCC                   │               │ • ZMPT101B Voltage Sensor: GND                   │
 │ • 4-Channel Grid Relay Module Power              │               │ • DHT22 Temperature/Humidity: GND (Pin 4)        │
 │ • 4-Channel Solar Relay Module Power             │               │ • 4-Channel Grid Relay Module: GND               │
 │                                                  │               │ • 4-Channel Solar Relay Module: GND              │
 │                                                  │               │ • 4x Source Selector Switch 10kΩ Pull-Downs      │
 │                                                  │               │ • ACS712 Resistor Divider 15kΩ Resistor (R2)     │
 └──────────────────────────────────────────────────┘               └──────────────────────────────────────────────────┘
```

### 1.1 Power Distribution Architecture Details
1. **AC-to-DC Adapter:** Converts high-voltage AC mains to an intermediate $7.5\text{V DC}$ output.
2. **PJ-102A DC Power Connector:** Standard barrel power jack ($2.1\text{mm} \times 5.5\text{mm}$ center-positive) feeding the DC input of the step-down converter.
3. **Step-Down (Buck) Converter:** Regulates the $7.5\text{V DC}$ input down to a steady $+5.0\text{V DC}$ distribution rail ($2\text{A}+$ current headroom).
4. **Subsystem 5V Distribution:**
   - **ESP32 DevKit V1 (VIN):** Powered via VIN pin; the ESP32 onboard regulator provides the internal $+3.3\text{V DC}$ rail for the Xtensa core, DHT22, and selector switches.
   - **ACS712-20A ($V_{CC}$):** Powered from $+5\text{V}$ rail (Hall element operates on $5\text{V}$ nominal supply).
   - **ZMPT101B ($V_{CC}$):** Powered from $+5\text{V}$ rail to drive the active LM358 op-amp conditioning stage.
   - **Relay Modules:** Relay module supply wiring follows the actual board labeling and installed jumper/isolation configuration, drawing coil actuation power from the regulated $+5\text{V}$ rail.
5. **Common Ground Reference:** The negative output terminal of the buck converter serves as the **unified low-voltage common ground** shared by the ESP32, all sensor modules, resistor networks, and relay boards.

---

## 2. Complete Hardware Bill of Materials (BOM)

| Component Category | Component & Model Identifier | Qty | Key Specifications & Role |
|---|---|:---:|---|
| **Microcontroller** | **ESP32 DevKit V1 (30-Pin)** | 1 | Xtensa Dual-Core 32-bit LX6 @ 240 MHz, 4MB Flash, 520KB SRAM, 3.3V logic. |
| **Power Supply** | **AC-to-DC Power Adapter (7.5V Output)** | 1 | External AC mains adapter supplying 7.5V DC to the prototype power stage. |
| **DC Connector** | **PJ-102A DC Power Jack** | 1 | Panel/PCB mount 2.1mm DC barrel connector. |
| **Step-Down Voltage** | **DC-DC Buck Converter Module** | 1 | Steps down 7.5V DC input to a stable, regulated 5.0V DC distribution rail. |
| **Current Sensor** | **ACS712-20A (Allegro ACS712ELCTR-20A-T)** | 1 | Hall-effect AC current sensor ($5\text{V}$ $V_{CC}$, $100\text{ mV/A}$ nominal sensitivity). |
| **Voltage Sensor** | **ZMPT101B Active AC Transformer Module** | 1 | Active micro-PT with onboard LM358 op-amp stage ($230\text{V AC}$ input). |
| **Environmental Sensor** | **DHT22 / AM2302** | 1 | Digital indoor temperature & relative humidity sensor (1-Wire, $3.3\text{V}$). |
| **Relay Modules** | **Songle 4-Channel 5V Relay Modules (SRD-05VDC-SL-C)** | 2 | Active-LOW optoisolated modules ($250\text{V AC} / 10\text{A}$ rating):<br>• Bank 1: Grid Relays (L1–L4)<br>• Bank 2: Solar Relays (L1–L4) |
| **Resistors** | **$10\text{ k}\Omega$ Metal-Film Resistors ($\pm 1\%$)** | 6 | • 1x ACS712 divider ($R_1$ series)<br>• 1x DHT22 pull-up to $3.3\text{V}$<br>• 4x Source selector pull-downs to GND |
| **Resistors** | **$15\text{ k}\Omega$ Metal-Film Resistors ($\pm 1\%$)** | 1 | 1x ACS712 divider ($R_2$ to GND; divider ratio $\alpha = 0.600$). |
| **Source Selectors** | **Low-Voltage Toggle Switches (SPST/SPDT)** | 4 | Miniature switches for manual source selection ($3.3\text{V}$ logic only). |
| **Downstream Switches** | **Manual AC Inline / Wall Switches** | 4 | Downstream mechanical cutoff switches on AC load lines (no ESP32 connection). |
| **Reference Appliance** | **Walton WTF9M3 Table/Stand Fan** | 1 | Bench calibration load on Load 1 ($60\text{W}$ rated active power, $226\text{V AC}, 0.28\text{A AC}, S = 63.28\text{ VA}$). |

---

## 3. Authoritative Hardware Pinout Matrix

The table below defines the authoritative physical GPIO wiring configured in `firmware/config.h`:

| Function / Component | Physical Channel | ESP32 GPIO | Electrical Specs & Signal Conditioning | Provenance / Evidence Classification |
|---|---|:---:|---|:---:|
| **DHT22 Sensor** | Ambient Temp & Humidity | **GPIO 4** | 1-Wire Digital, external 10kΩ pull-up to 3.3V | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| **Status / SmartProv LED**| Onboard Indicator | **GPIO 2** | Active-HIGH (Shared with SmartProv AP indicator) | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| **SmartProv Reset Button**| Factory Reset | **GPIO 0** | Active-LOW (BOOT button, hold 5s) | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| **Current Sensor (ACS712)**| Aggregate AC Current | **GPIO 34** | ADC1_CH6 via 10kΩ/15kΩ resistor divider (0.600 ratio, max 3.0V) | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| **Voltage Sensor (ZMPT101B)**| AC Mains Voltage | **GPIO 35** | ADC1_CH7 input-only analog channel; physical connection verified, full output amplitude relative to ESP32 ADC-safe limits requires empirical verification | `[PHYSICAL WIRING OBSERVED / PENDING AMPLITUDE VERIFICATION]` |
| **Grid Relay Bank** | Load 1 Grid | **GPIO 16** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| | Load 2 Grid | **GPIO 17** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| | Load 3 Grid | **GPIO 18** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| | Load 4 Grid | **GPIO 19** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| **Represented-Solar Bank**| Load 1 Solar | **GPIO 21** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| | Load 2 Solar | **GPIO 22** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| | Load 3 Solar | **GPIO 23** | Active-LOW, 5V Songle SRD-05VDC-SL-C | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| | Load 4 Solar | **GPIO 13** | Active-LOW (Reassigned from GPIO 25) | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| **Source Selector Switches**| Load 1 Selector | **GPIO 26** | 3.3V $\rightarrow$ Switch $\rightarrow$ GPIO (10kΩ pull-down to GND) | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| | Load 2 Selector | **GPIO 27** | 3.3V $\rightarrow$ Switch $\rightarrow$ GPIO (10kΩ pull-down to GND) | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| | Load 3 Selector | **GPIO 32** | 3.3V $\rightarrow$ Switch $\rightarrow$ GPIO (10kΩ pull-down to GND) | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| | Load 4 Selector | **GPIO 33** | 3.3V $\rightarrow$ Switch $\rightarrow$ GPIO (10kΩ pull-down to GND) | `[PHYSICAL WIRING OBSERVED & MEASURED]` |

---

## 4. Comprehensive Hardware Connection Table

| Component | Component Pin | ESP32 Pin / Power Node | Connection Purpose & Signal Conditioning | Provenance Status |
|---|---|:---:|---|:---:|
| **Buck Converter Output (+)** | `+5V OUT` | `ESP32 VIN` | Main 5V DC power feed to ESP32 onboard regulator | `[PHYSICAL WIRING OBSERVED]` |
| **Buck Converter Output (-)** | `GND OUT` | `ESP32 GND` | Primary system ground reference | `[PHYSICAL WIRING OBSERVED]` |
| **ACS712-20A** | `VCC` | `+5V Rail` | 5.0V power for Hall element and amplifier | `[PHYSICAL WIRING OBSERVED]` |
| **ACS712-20A** | `GND` | `Common GND` | DC ground reference | `[PHYSICAL WIRING OBSERVED]` |
| **ACS712-20A** | `OUT` | **GPIO 34** (via divider) | OUT $\rightarrow$ $R_1$ ($10\text{k}\Omega$) $\rightarrow$ GPIO 34; $R_2$ ($15\text{k}\Omega$) from GPIO 34 to GND | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| **ACS712-20A** | `IP+ / IP-` | *AC Neutral Bus* | In series with aggregate AC neutral return line | `[PHYSICAL WIRING OBSERVED]` |
| **ZMPT101B** | `VCC` | `+5V Rail` | 5.0V power for onboard LM358 op-amp | `[PHYSICAL WIRING OBSERVED]` |
| **ZMPT101B** | `GND` | `Common GND` | DC ground reference | `[PHYSICAL WIRING OBSERVED]` |
| **ZMPT101B** | `OUT` | **GPIO 35** | Physical connection verified; full output amplitude relative to ESP32 ADC-safe limits requires empirical verification | `[PHYSICAL WIRING OBSERVED / PENDING AMPLITUDE VERIFICATION]` |
| **ZMPT101B** | `AC IN` | *AC Mains (L, N)* | Parallel connection across 230V AC Live & Neutral | `[PHYSICAL WIRING OBSERVED]` |
| **DHT22** | `Pin 1 (VCC)` | `ESP32 3V3` | 3.3V power supply | `[PHYSICAL WIRING OBSERVED]` |
| **DHT22** | `Pin 2 (DATA)` | **GPIO 4** | 1-Wire data bus with 10kΩ pull-up to 3.3V | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| **DHT22** | `Pin 4 (GND)` | `Common GND` | DC ground reference | `[PHYSICAL WIRING OBSERVED]` |
| **Grid Relay Module** | Power Terminals | `+5V Rail` | Relay module supply wiring follows actual board labeling and installed jumper/isolation configuration | `[PHYSICAL WIRING OBSERVED]` |
| **Grid Relay Module** | `GND` | `Common GND` | DC ground reference | `[PHYSICAL WIRING OBSERVED]` |
| **Grid Relay Module** | `IN1, IN2, IN3, IN4` | **GPIO 16, 17, 18, 19** | Active-LOW control inputs for Grid loads 1–4 | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| **Solar Relay Module** | Power Terminals | `+5V Rail` | Relay module supply wiring follows actual board labeling and installed jumper/isolation configuration | `[PHYSICAL WIRING OBSERVED]` |
| **Solar Relay Module** | `GND` | `Common GND` | DC ground reference | `[PHYSICAL WIRING OBSERVED]` |
| **Solar Relay Module** | `IN1, IN2, IN3, IN4` | **GPIO 21, 22, 23, 13** | Active-LOW control inputs for Solar loads 1–4 | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| **Source Selectors 1–4**| `Switch Inputs` | `ESP32 3V3` | 3.3V supply to switch common/input terminal | `[PHYSICAL WIRING OBSERVED]` |
| **Source Selectors 1–4**| `Switch Outputs` | **GPIO 26, 27, 32, 33** | Switch output to GPIO with 10kΩ pull-down to GND | `[PHYSICAL WIRING OBSERVED & MEASURED]` |
| **Downstream AC Switches** | `Switch Contacts` | *No ESP32 Pin* | Mechanical inline AC cutoff switches on load lines | `[DOCUMENTED / UNVERIFIED]` |
| **Relay AC Contacts** | `COM / NO` | *AC Power Lines* | COM to Load Live, NO to Grid/Solar Live | `[INFERRED / THEORETICAL]` |

---

## 5. Circuit Subsystem Schematics

### 5.1 ACS712 Resistor Divider Conditioning (GPIO 34)
```
       +5V Regulated Rail
           │
     ┌─────┴─────┐
     │  ACS712   │
     │  Current  │─── OUT (0V to 5V AC/DC swing)
     │  Sensor   │     │
     └─────┬─────┘     │
        Common         └───[ R1: 10 kΩ ]───┬───► ESP32 GPIO 34 (ADC1_CH6)
          GND                              │
                                     [ R2: 15 kΩ ]
                                           │
                                       Common GND
```

### 5.2 Low-Voltage Source Selectors (GPIO 26, 27, 32, 33)
```
   +3.3V Rail ─────[ SPST / SPDT Switch ]─────┬─────► ESP32 GPIO (26, 27, 32, or 33)
                                              │
                                        [ 10 kΩ Pull-Down ]
                                              │
                                          Common GND
```

### 5.3 Dual-Bank AC Source Selection per Load Channel
```
 [Grid AC Live Bus] ──────────── NO ──┐ (Grid Relay, e.g., GPIO 16)
                                      ├─── COM ────► [Downstream AC Switch] ────► [Load Appliance (L1)]
 [Solar AC Live Bus] ─────────── NO ──┘ (Solar Relay, e.g., GPIO 21)                   │
                                                                                       │
 [Aggregate Neutral Bus] ───[ ACS712 Current Sensor (IP+ -> IP-) ]─────────────────────┘
```

---

## 6. Circuit Designer Step-by-Step Build Order

When laying out the circuit in a visual CAD/schematic tool (Fritzing, EasyEDA, KiCad, Wokwi):

1. **Place Power Subsystem:**
   - Place the **7.5V AC-DC Adapter** symbol and **PJ-102A DC Jack**.
   - Place the **Buck Converter** module; connect 7.5V DC from PJ-102A to Buck input.
   - Establish the **Regulated +5.0V DC Rail** and **Common Ground (GND) Rail**.
2. **Place Primary Controller:**
   - Place the **ESP32 30-Pin DevKit V1**.
   - Connect Buck $+5\text{V}$ output to ESP32 **VIN** pin; connect Buck GND to ESP32 **GND**.
   - Establish the **+3.3V DC Logic Rail** from the ESP32 `3V3` output pin.
3. **Add Analog Sensing Circuitry:**
   - Place the **ACS712-20A** module: `VCC` $\rightarrow$ $+5\text{V}$, `GND` $\rightarrow$ Common GND.
   - Wire the voltage divider: ACS712 `OUT` $\rightarrow$ $R_1$ ($10\text{k}\Omega$) $\rightarrow$ **GPIO 34**, and $R_2$ ($15\text{k}\Omega$) from **GPIO 34** $\rightarrow$ Common GND.
   - Place the **ZMPT101B** module: `VCC` $\rightarrow$ $+5\text{V}$, `GND` $\rightarrow$ Common GND, `OUT` $\rightarrow$ **GPIO 35**.
4. **Add DHT22 Environmental Sensor:**
   - Place **DHT22**: Pin 1 $\rightarrow$ $+3.3\text{V}$, Pin 4 $\rightarrow$ Common GND, Pin 2 (DATA) $\rightarrow$ **GPIO 4**.
   - Add $10\text{ k}\Omega$ pull-up resistor between Pin 2 and $+3.3\text{V}$.
5. **Add 4x Manual Source Selectors:**
   - Place 4 miniature toggle switches; connect one terminal of each to $+3.3\text{V}$.
   - Connect the output terminals to **GPIO 26 (L1)**, **GPIO 27 (L2)**, **GPIO 32 (L3)**, and **GPIO 33 (L4)**.
   - Connect a $10\text{ k}\Omega$ pull-down resistor from each GPIO to Common GND.
6. **Add Relay Actuation Modules (2x 4-Channel):**
   - Place **Grid Relay Module**: `IN1..IN4` $\rightarrow$ **GPIO 16, 17, 18, 19**; power wiring follows actual board labeling and installed jumper/isolation configuration to $+5\text{V}$; `GND` $\rightarrow$ Common GND.
   - Place **Solar Relay Module**: `IN1..IN4` $\rightarrow$ **GPIO 21, 22, 23, 13**; power wiring follows actual board labeling and installed jumper/isolation configuration to $+5\text{V}$; `GND` $\rightarrow$ Common GND.
7. **Add AC Mains & Load Distribution:**
   - Wire AC Grid Live to Grid Relay `NO` contacts 1–4.
   - Wire AC Solar Live to Solar Relay `NO` contacts 1–4.
   - Connect paired `COM` terminals (Grid L$i$ + Solar L$i$) through downstream mechanical switches to Load appliances 1–4.
   - Route aggregate Neutral return through ACS712 `IP+/IP-` terminals back to AC Mains Neutral.

---

## 7. Safety, ATS Non-Certification & Academic Prototype Disclosures

> [!WARNING]
> **Safety & Architectural Disclosures:**
> 1. **No Real Solar Power Delivery:** "Solar" is a grid-derived representation used exclusively to validate transfer-switching and decision logic in a laboratory evaluation setting. Never describe this prototype as demonstrating real solar power generation or delivery.
> 2. **Software Break-Before-Make Only:** The $300\text{ ms}$ break-before-make interlock between Grid and Solar relays is enforced strictly in firmware (`firmware/relay_controller.cpp`). It is **NOT** a certified mechanical Automatic Transfer Switch (ATS) interlock. Software timing cannot protect against welded relay contacts or internal component failures.
> 3. **Non-Certified Prototype:** The DC power distribution stage (7.5V Adapter $\rightarrow$ PJ-102A $\rightarrow$ Buck Converter $\rightarrow$ 5V Rail) represents the **physical implementation of our laboratory evaluation prototype**. It does **NOT** constitute certified industrial galvanic isolation or electrical safety certification (e.g. UL/IEC 60950/62368).

---

## 8. Legacy Diagram Disclosure: `esp32_hems_wiring.png`

> [!WARNING]
> **ARCHIVED LEGACY DIAGRAM (`esp32_hems_wiring.png`):**  
> The image file `esp32_hems_wiring.png` preserved in this directory illustrates the **early 4-relay single-bank prototype (Firmware v1)**. It does NOT depict:
> 1. The 8-relay dual-bank matrix (Grid L1–L4 on GPIO 16/17/18/19, Solar L1–L3 on GPIO 21/22/23, Solar L4 on GPIO 13).
> 2. The 4 physical low-voltage toggle selector switches on GPIO 26, 27, 32, and 33.
> 3. The 10kΩ/15kΩ ACS712 voltage divider on GPIO 34.
> 4. The 7.5V $\rightarrow$ PJ-102A $\rightarrow$ Buck Converter 5V power chain and common ground topology.
> 
> Refer strictly to `firmware/config.h` and the specifications above for the authoritative wiring schematic of the dual-bank production system.


