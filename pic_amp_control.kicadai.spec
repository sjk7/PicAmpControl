// PicAmpControl - MCU fan protection circuit with 12V input, 5V regulated output, NMOS fan driver

CircuitName: PicAmpControl
Description: Microcontroller-based fan protection circuit with 12V to 5V regulation and NMOS fan control

// Power Supply Section
Input_12V: DC_12V_1A  // From connector J2
Output_5V: DC_5V_500mA  // For MCU and logic circuits
Output_12V_Switched: DC_12V_500mA  // Switched output for fan on J3

// Regulator: 12V to 5V (L7805)
Regulator_U2: L7805
  Input: Input_12V
  Output: Output_5V
  InputCap_C1: 100n_ceramic
  OutputCap_C2: 100n_ceramic
  BulkCap_C3: 10u_electrolytic

// Microcontroller (PIC16F18855)
MCU_U1: PIC16F18855-I/SP
  Supply: Output_5V
  Decap_C4: 100n_ceramic
  ResetPin_MCLR: Pulled_High_with_10k  // R1
  ControlOutput_RB5: FanControl_Signal

// Pull-up Resistors
PullUp_R1: 10k_to_5V  // MCLR reset
PullUp_R3: 10k_to_5V  // Unused MCU pin (example)
PullUp_R4: 10k_to_5V  // Unused MCU pin (example)

// Fan Control Circuit (NMOS + Gate Drive + Protection)
GateResistor_R2: 220R  // Current limiting on NMOS gate
GateClamp_D1: Zener_5V1  // Overvoltage protection
FanDriver_Q1: LogicLevel_NMOS
  Gate: GateControl_from_R2
  Drain: Output_12V_Switched
  Source: GND
  GateResistor_R2: 220R
  GateClamp_D1: Zener_5V1

// Connectors
Connector_J2: Conn_02x1  // 12V input (12V, GND)
Connector_J3: Conn_02x1  // Fan output (12V_Switched, GND)

// Net Connections
Net_12V_Raw: [J2.1, U2.In, C1.1, Q1.D, J3.1]
Net_5V: [U2.Out, C2.1, C3.1, U1.Vdd, C4.1, R1.1, R3.1, R4.1]
Net_GND: [J2.2, U2.GND, C1.2, C2.2, C3.2, U1.Vss, C4.2, R1.2, R3.2, R4.2, D1.K, Q1.S, J3.2]
Net_MCLR: [U1.1, R1.1]
Net_FAN_CTRL: [U1.25, R2.1]
Net_NMOS_GATE: [R2.2, D1.A, Q1.G]

// Constraints & Design Rules
Constraint_NoShort_12V_GND: voltage_isolation = 12V
Constraint_NoShort_5V_GND: voltage_isolation = 5V
Constraint_FanControl_LogicLevel: signal_0to5V
Constraint_GateProtection: zener_clamp_above_5p1V
