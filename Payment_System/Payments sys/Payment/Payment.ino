/**
 * NEOSHOP ESP32 — Payment Station (RFID + Coin Acceptor + Banknote Acceptor +
 *                                   Change Return + Refill Alert)
 * =================================================================
 * RFID + CH-926 Coin Acceptor + Raspberry Pi Banknote Link + MQTT +
 * PCA9685 Servo Change Dispenser + IR Feedback
 *
 * NOTE: The 1.8" TFT SPI Display (ST7735) has been REMOVED from this
 * sketch — the physical unit appears burned out. All display-related
 * code (Adafruit_GFX / Adafruit_ST7735 includes, the tft object,
 * setupDisplay(), updateDisplayStatus(), showAcceptingScreen(), and every
 * call site that used to update the screen) has been deleted. Nothing
 * else was changed: WiFi, MQTT, Coin Acceptor, PCA9685, Servo, IR
 * Sensors, Raspberry Pi UART link, Payment Logic, and RFID reading logic
 * all behave exactly as before. A replacement display can be re-added
 * later by restoring these pieces.
 *
 * Flow:
 *   1. Read RFID → Send payment_request
 *   2. Receive invoice from Backend
 *   3. Accept coins AND banknotes until amount is fulfilled
 *      - Coins are counted directly via the CH-926 pulse train (unchanged).
 *      - Banknotes are DETECTED AND VALIDATED on a Raspberry Pi (IR sensor +
 *        UV LED + camera + utils.fast_uv_validator) — that is the Pi's ONLY
 *        job now. The Pi reports its verdict to THIS board over a dedicated
 *        UART link — see "Raspberry Pi Banknote Link" below — and THIS
 *        board is the one that physically swings the accept/reject gate
 *        servo, on the same PCA9685 servo module already used for coin
 *        change (see "Banknote Accept/Reject Gate Servo" below).
 *   4. Payment complete → Dispense physical change (PCA9685 servos + IR feedback, greedy algorithm)
 *      4a. If tubes run out mid-dispense (IR never confirms a drop after retries,
 *          for BOTH the failing denomination AND every smaller one) → PAUSE the
 *          payment (do NOT cancel it), alert the shop owner over MQTT, and wait.
 *      4b. Once the owner confirms the machine is refilled, resume dispensing
 *          ONLY the amount that was still missing — then complete the payment
 *          on the SAME invoice, exactly as if nothing had happened.
 *   5. Publish payment_complete → Backend confirms → Reset for next customer
 *
 * ─────────────────────────────────────────────────────────────────────────
 * Raspberry Pi Banknote Link (Pi = detection/validation ONLY)
 * ─────────────────────────────────────────────────────────────────────────
 * The Raspberry Pi owns the banknote chamber's SENSING side only: IR
 * insertion sensor, UV LED, camera, and the fast_uv_validator pipeline.
 * It does NOT own a servo and does NOT touch the accept/reject gate
 * anymore — that moved to this board (see below). The Pi never talks to
 * MQTT or the backend directly — after every banknote it sends exactly
 * ONE line over this UART link, newline-terminated:
 *
 *     VALID:<denomination>     e.g. "VALID:50"   — banknote accepted, worth
 *                               that many NIS. Treated exactly like a coin:
 *                               added to totalInserted, published to the
 *                               backend on payment/coins. This board ALSO
 *                               swings the banknote gate servo +45°
 *                               (accept) and back to neutral.
 *     FAKE                                       — banknote rejected
 *                               (counterfeit / unreadable / no note).
 *                               Totals are left completely untouched,
 *                               mirroring how an unknown coin is handled.
 *                               This board ALSO swings the banknote gate
 *                               servo -45° (reject) and back to neutral.
 *
 * Banknote lines are only acted on while state == STATE_ACCEPTING_COINS —
 * exactly like inserted coins, a VALID/FAKE received outside that window
 * (e.g. before an invoice exists) is logged and ignored so a stray note fed
 * in at idle can't silently create a phantom balance (and the gate is left
 * alone — it only moves in response to a verdict during an active sale).
 *
 * ─────────────────────────────────────────────────────────────────────────
 * Banknote Accept/Reject Gate Servo (moved from the Pi to here)
 * ─────────────────────────────────────────────────────────────────────────
 * The MG996R gate servo that physically accepts or rejects a banknote used
 * to be wired to, and driven by, the Raspberry Pi directly. It is now
 * wired to CHANNEL 4 of the SAME PCA9685 servo module this board already
 * uses for the four coin-change tubes — no new driver hardware, just one
 * more channel on the existing module. The Pi no longer drives any servo
 * at all; it only reports VALID/FAKE over UART (see above), and THIS
 * board decides what the gate does:
 *   - On "VALID:<denomination>"  → swingBanknoteGate(true)  → 55° (accept),
 *     brief hold, back to neutral (105°).
 *   - On "FAKE"                  → swingBanknoteGate(false) → 155° (reject),
 *     brief hold, back to neutral (105°).
 * These are ABSOLUTE angles measured directly on the physical gate with
 * calibrate_channel4_servo.ino — NOT symmetric around neutral (accept is
 * -50° from neutral, reject is +50° from neutral) and NOT tied to
 * SERVO_REST_ANGLE (that constant is only the coin-tube servos' own
 * reference point, unrelated to this gate). See BANKNOTE_SERVO_* below.
 *
 * Wiring:
 *   RC522:  SDA=5, RST=27, SCK=13, MISO=19, MOSI=23
 *   CH-926: COIN → 10kΩ → GPIO 34, GND shared, DC12V external
 *
 *   Change Return Servos — driven via PCA9685 PWM driver (I2C), NOT direct GPIO:
 *     PCA9685 VCC  -> 3.3V (ESP32)
 *     PCA9685 GND  -> GND (ESP32)
 *     PCA9685 SCL  -> GPIO 33 (ESP32)
 *     PCA9685 SDA  -> GPIO 32 (ESP32)
 *     PCA9685 V+   -> +5V from separate external power supply (green terminal block)
 *     PCA9685 GND  -> shared GND with ESP32 and the external supply (same terminal block)
 *
 *     Servo -> PCA9685 channel mapping (CORRECTED to match actual physical wiring):
 *       1 Shekel   -> Channel 0
 *       2 Shekels  -> Channel 1
 *       10 Shekels -> Channel 2   (tube not physically installed yet, still programmed)
 *       5 Shekels  -> Channel 3
 *       Banknote accept/reject gate -> Channel 4   (moved here from the Pi;
 *                                                    MG996R, same servo that used
 *                                                    to be wired to the Pi's GPIO18)
 *
 *   Change Return IR Sensors (confirm coin dropped):
 *     1 Shekel  -> GPIO 26
 *     2 Shekels -> GPIO 15
 *     5 Shekels -> GPIO 22
 *     10 Shekels-> GPIO 2    (not physically installed yet, still programmed)
 *     (The banknote gate servo has no IR confirmation — it's a pass/block
 *      gate, not a dispenser, so there's nothing to detect a "drop".)
 *
 *   Vibration Motor (settles coins on the acceptor's track) — driven via one
 *   channel of an L298N dual H-bridge driver module:
 *     ESP32 GPIO 21 -> L298N IN1
 *     L298N IN2     -> GND (fixed direction, motor only needs ON/OFF)
 *     L298N ENA     -> leave jumper cap in place (always full power)
 *     L298N OUT1/OUT2 -> motor terminals (either order)
 *     L298N VS      -> external supply matching motor's rated voltage
 *                      (L298N has ~2V internal drop; add ~2V if you want
 *                      the motor to see its full rated voltage)
 *     L298N GND     -> shared GND (ESP32 + external supply)
 *     L298N +5V     -> leave disconnected (onboard regulator handles it
 *                      via the 5V jumper, if populated)
 *   Triggers briefly:
 *     - the moment coin-accepting starts (on invoice_ready), AND
 *     - immediately whenever GPIO 34 (CH-926 coin pulse line) goes active,
 *       i.e. right as a coin pulse is detected, so the track keeps getting
 *       settled while coins are actually being inserted/counted.
 *
 *   Raspberry Pi Banknote Link — plain USB cable, NOT GPIO wires:
 *     Plug a standard data-capable USB cable from the Raspberry Pi into
 *     this board's USB port (the same one used to flash it). The board's
 *     onboard USB-serial chip bridges that straight to Serial (UART0) —
 *     the exact port already used below for debug output — so no RX/TX
 *     pins, no baud-pin defines, and (importantly) no separate GND wire
 *     to forget: the USB cable's own ground conductor handles it.
 *     Serial.begin() below therefore runs at 115200 for BOTH debug
 *     printing and the VALID:/FAKE protocol from the Pi, since it's one
 *     physical UART carrying both. hardware/uart.py on the Pi side must
 *     use the matching 115200 baud and point UART_CONFIG.PORT at
 *     whatever /dev/ttyUSB* (or ttyACM*) device the ESP32 enumerates as.
 *     The Pi no longer has any servo wiring at all — its GPIO18 (formerly
 *     the gate servo signal pin) is now free.
 *
 *   NOTE (refill-pause flow):
 *     - returnChange() now RETURNS the remaining un-dispensed amount (int)
 *       instead of a plain bool. 0 = fully dispensed, >0 = still owes that
 *       many NIS because one or more tubes ran out.
 *     - If change can't be fully returned, the device does NOT reset or
 *       cancel the sale. It enters STATE_WAITING_REFILL, publishes a
 *       "refill_needed" message on payment/refill_request (with the invoice
 *       code, payment id, and exact NIS still owed), and just waits — MQTT
 *       stays alive via mqtt.loop() in the main loop() as usual.
 *     - The backend/shop-owner app is expected to publish an event named
 *       "refill_done" back on the existing payment/status topic (same topic
 *       already used for invoice_ready / no_invoice / payment_confirmed)
 *       once the tubes have been physically refilled.
 *     - On receiving refill_done, the device retries dispensing ONLY the
 *       amount that was still owed (not the full original change), then
 *       completes the payment exactly like a normal successful change
 *       return. If it's STILL short after refill (e.g. wrong denomination
 *       refilled), it pauses again and re-alerts the owner with the new
 *       remaining amount — it does not silently give up.
 *
 *   FIX LOG:
 *     - VIBRATION_MOTOR_PIN was previously mis-defined as GPIO 4, which
 *       collided with the (now-removed) TFT's CS pin (also GPIO 4). That
 *       collision forced the TFT's chip-select LOW at boot (via
 *       digitalWrite(VIBRATION_MOTOR_PIN, LOW) in setup()), leaving the
 *       TFT permanently "selected" on the shared SPI bus and corrupting
 *       all RC522 communication (constant STATUS_ERROR / status=1 on
 *       every PICC_RequestA). Moved the vibration motor to GPIO 21.
 *       (The TFT itself has since been removed entirely from this sketch.)
 *     - Vibration motor was originally driven with a BLOCKING safeDelay()
 *       inside triggerVibrationMotor(), called synchronously from
 *       mqttCallback() on invoice_ready. At 800ms this was barely
 *       noticeable, but bumping it to a full 1-minute buzz would have
 *       frozen the ENTIRE device for that minute (no RFID reads, no coin
 *       processing) since it's called from inside the MQTT callback.
 *       Rewrote as non-blocking: startVibrationMotor() turns the pin on
 *       and records a start time; updateVibrationMotor(), polled every
 *       loop() iteration, turns it back off once the duration has
 *       elapsed. The invoice flow and coin acceptance now work normally
 *       while the motor buzzes in the background.
 *     - Added the Raspberry Pi banknote link over USB (Serial/UART0,
 *       shared with the debug console — no separate GPIO wires) so
 *       accepted/rejected banknotes join the same totalInserted /
 *       backend flow as coins instead of needing a second, disconnected
 *       acceptance path.
 *     - Corrected PCA_CH_5 / PCA_CH_10 channel definitions: they were
 *       swapped relative to the actual physical wiring (channel 2 is
 *       physically the 10-shekel tube servo, channel 3 is physically the
 *       5-shekel tube servo). Fixed so the correct servo moves for each
 *       denomination during change return.
 *     - Added an ISR-safe flag (coinPulseSeen) so the vibration motor now
 *       also fires immediately the instant GPIO 34 (the CH-926 coin pulse
 *       line) goes active — not only on invoice_ready — without doing any
 *       Serial/GPIO work inside the ISR itself.
 *     - MOVED the banknote accept/reject gate servo from the Raspberry Pi
 *       to this board: added PCA_CH_BANKNOTE (channel 4) on the existing
 *       PCA9685, added swingBanknoteGate(), and wired it into
 *       handleBanknoteValid()/handleBanknoteFake() so this board now
 *       physically actuates the gate itself in direct response to the
 *       Pi's VALID/FAKE verdicts, instead of the Pi doing it. The Pi's
 *       hardware/servo.py was removed entirely on that side — the Pi's
 *       only remaining job is detection + validation.
 *     - Calibrated the banknote gate servo's three angles directly on the
 *       physical hardware (using a standalone interactive serial sketch,
 *       calibrate_channel4_servo.ino) instead of assuming a generic ±45°
 *       swing off SERVO_REST_ANGLE: neutral=105°, accept=55° (-50° off
 *       neutral), reject=155° (+50° off neutral). Updated
 *       BANKNOTE_SERVO_NEUTRAL_ANGLE / _ACCEPT_ANGLE / _REJECT_ANGLE to
 *       these measured absolute values.
 *     - RFID reading rewritten from PICC_RequestA()-based polling (which
 *       was unreliable in this project — STATUS_ERROR / status=1/4 on
 *       every attempt) to PICC_IsNewCardPresent() + PICC_ReadCardSerial(),
 *       confirmed working against the same RC522 + ESP32 hardware in an
 *       isolated test. No RFID pins, SPI init, or downstream payment
 *       logic were changed — only the detection call itself.
 *     - REMOVED the 1.8" TFT SPI display (ST7735) entirely — the physical
 *       unit is burned out. Deleted Adafruit_GFX/Adafruit_ST7735 includes,
 *       the tft object, TFT_CS/RST/DC pin defines, setupDisplay(),
 *       updateDisplayStatus(), showAcceptingScreen(), the TFT_CS
 *       deselect lines in setup(), and every call site that used to push
 *       status text to the screen. Nothing else changed. A new display
 *       can be wired back in later.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// ─── WiFi & MQTT Config ───────────────────────────────────────────────────────
const char* WIFI_SSID   = "CELab";
const char* WIFI_PASS   = "CELabC207";
const char* MQTT_BROKER = "192.168.0.100";
const int   MQTT_PORT   = 1883;
const char* MQTT_USER   = "neoshop";
const char* MQTT_PASS_S = "neoshop_mqtt_pass";
const char* DEVICE_ID   = "ESP32-PAYMENT-01";

// ─── MQTT Topics ────────────────────────────────────────────────────────────
const char* TOPIC_PAYMENT_REQUEST  = "payment/request";
const char* TOPIC_PAYMENT_STATUS   = "payment/status";        // subscribed — also carries refill_done now
const char* TOPIC_PAYMENT_COINS    = "payment/coins";
const char* TOPIC_PAYMENT_COMPLETE = "payment/complete";
const char* TOPIC_REFILL_REQUEST   = "payment/refill_request"; // published when tubes run out

// ─── RFID Pins ──────────────────────────────────────────────────────────────
#define RFID_SS_PIN   5
#define RFID_RST_PIN  27
#define RFID_SCK_PIN  13
#define RFID_MISO_PIN 19
#define RFID_MOSI_PIN 23

// ─── Coin Pin ───────────────────────────────────────────────────────────────
#define COIN_PIN 34

// ─── PCA9685 (Servo Driver) I2C Pins ─────────────────────────────────────────
#define PCA_SDA_PIN  32
#define PCA_SCL_PIN  33
#define PCA_I2C_ADDR 0x40

// ─── Change Return PCA9685 Channels ──────────────────────────────────────────
// CORRECTED: channel 2 is physically wired to the 10-shekel tube servo and
// channel 3 to the 5-shekel tube servo (opposite of what was previously
// defined here) — see FIX LOG above.
#define PCA_CH_1  0
#define PCA_CH_2  1
#define PCA_CH_10 2
#define PCA_CH_5  3

// ─── Banknote Accept/Reject Gate — PCA9685 Channel ───────────────────────────
// Moved here from the Raspberry Pi (was gpiozero AngularServo on GPIO18).
// Same PCA9685 module as the coin tubes above, one more channel.
#define PCA_CH_BANKNOTE 5

// ─── Change Return IR Sensor Pins ────────────────────────────────────────────
#define IR_PIN_1  26
#define IR_PIN_2  15
#define IR_PIN_5  22
#define IR_PIN_10 2

// ─── Vibration Motor Pin (aligns coins on the track when coin-accepting starts) ─
// Moved to GPIO 21 (was mistakenly GPIO 4, which collided with the
// now-removed TFT's CS pin).
#define VIBRATION_MOTOR_PIN 21
#define VIBRATION_DURATION_MS 60000   // how long the motor buzzes for (1 minute)

// ─── Raspberry Pi Banknote Link (over USB, via Serial/UART0) ────────────────
// The Pi connects over a plain USB cable into this board's USB port — NOT
// GPIO wires. That port is bridged internally to Serial (UART0), the same
// one used for flashing and for Serial.println() debug output below, so
// there's no separate pin/baud pair here anymore; PI_LINK_BAUD must match
// Serial.begin(...) in setup() since it's the same physical UART.
#define PI_LINK_BAUD 115200
#define BANKNOTE_REJECT_DISPLAY_MS 1200   // kept for the non-blocking alert timer window (see below)

// ─── IR Detection Calibration ────────────────────────────────────────────────
#define IR_DETECTION_WINDOW  600
#define IR_ACTIVE_STATE      LOW
#define MAX_RETRY_PER_COIN   1

// ─── Change Return Calibration ───────────────────────────────────────────────
#define SERVO_REST_ANGLE     90
#define PUSH_DELTA_ANGLE    -38
#define PUSH_DIRECTION       (+1)
#define SERVO_PUSH_ANGLE     (SERVO_REST_ANGLE + (PUSH_DIRECTION * PUSH_DELTA_ANGLE))

#define SERVO_MOVE_DELAY     350
#define SERVO_SETTLE_DELAY   150

#define SERVO_PWM_MIN  102
#define SERVO_PWM_MAX  512

// ─── Banknote Gate Servo Calibration ─────────────────────────────────────────
// Measured directly on the physical gate with calibrate_channel4_servo.ino
// (interactive serial calibration sketch) — these are ABSOLUTE angles fed
// straight into setServoAngle(), independent of SERVO_REST_ANGLE (which is
// only the coin-tube servos' own reference point, unrelated to this gate).
// NOTE this gate's convention is NOT symmetric around neutral like the
// coin tubes: accept swings DOWN 50° from neutral, reject swings UP 50°.
//   105° -> neutral / resting (gate idle, measured)
//    55° -> "accept" swing (VALID banknote), i.e. neutral - 50°
//   155° -> "reject" swing (FAKE banknote), i.e. neutral + 50°
#define BANKNOTE_SERVO_NEUTRAL_ANGLE  105
#define BANKNOTE_SERVO_ACCEPT_ANGLE   55
#define BANKNOTE_SERVO_REJECT_ANGLE   155
#define BANKNOTE_SERVO_MOVE_DELAY     350   // time to let the servo physically swing
#define BANKNOTE_SERVO_HOLD_DELAY     400   // dwell time at accept/reject before returning to neutral

// ─── Per-Servo Calibration Offsets ───────────────────────────────────────────
// index = PCA9685 channel number. Index 4 (banknote gate) starts at 0 —
// tune it the same way the coin-tube offsets were tuned, once the gate
// servo is physically mounted.
const int SERVO_OFFSET[5] = { 30, 32, 32, 28, 0 };

// ─── Coin Denominations (Acceptor) ───────────────────────────────────────────
struct Coin {
  int   pulses;
  float value;
  const char* label;
};

const Coin COINS[] = {
  { 1,  1.0,  "1 Shekel"  },
  { 2,  2.0,  "2 Shekels" },
  { 5,  5.0,  "5 Shekels" },
};
const int COIN_COUNT = 3;

// ─── Change Return Channels (Dispenser, sorted descending for greedy) ─────────
struct CoinChannel {
  int   value;
  int   pwmChannel;
  int   irPin;
  const char* label;
};

CoinChannel coinChannels[4] = {
  { 10, PCA_CH_10, IR_PIN_10, "10 Shekels" },
  {  5, PCA_CH_5,  IR_PIN_5,  "5 Shekels"  },
  {  2, PCA_CH_2,  IR_PIN_2,  "2 Shekels"  },
  {  1, PCA_CH_1,  IR_PIN_1,  "1 Shekel"   }
};
const int NUM_CHANNELS = 4;

// ─── Coin ISR Variables ───────────────────────────────────────────────────────
volatile int           pulseCount   = 0;
volatile unsigned long lastPulseTime = 0;
// Set (from the ISR) the instant a coin pulse is detected on GPIO 34.
// Only ISR-safe work happens inside coinISR() itself (no Serial, no
// digitalWrite/servo calls) — loop() polls this flag and does the actual
// vibration-motor trigger.
volatile bool          coinPulseSeen = false;
const int DEBOUNCE_MS = 120;
const int TIMEOUT_MS  = 400;

// ─── Objects ──────────────────────────────────────────────────────────────────
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);
MFRC522      rfid(RFID_SS_PIN, RFID_RST_PIN);
Adafruit_PWMServoDriver pwm(PCA_I2C_ADDR);

// ─── Payment State Machine ────────────────────────────────────────────────────
enum PaymentState {
  STATE_IDLE,               // Waiting for RFID scan
  STATE_WAITING_INVOICE,    // RFID read, waiting for Backend response
  STATE_ACCEPTING_COINS,    // Invoice received, accepting coins/banknotes
  STATE_WAITING_REFILL,     // Change dispense stalled, waiting for owner to refill tubes
  STATE_PAYMENT_COMPLETE    // Payment done
};

PaymentState state = STATE_IDLE;

// ─── Payment Data ─────────────────────────────────────────────────────────────
String  currentRFID          = "";
String  invoiceCode          = "";
int     invoiceId            = 0;
int     paymentId            = 0;
int     sessionId            = 0;
float   totalDue             = 0.0;
float   totalInserted        = 0.0;
int     pendingChangeRemaining = 0;   // NIS still owed to the customer while paused for refill

// ─── Timers ───────────────────────────────────────────────────────────────────
unsigned long lastRFIDCheck       = 0;
unsigned long lastMQTTReconnect   = 0;
unsigned long rfidTimestamp       = 0;
unsigned long paymentDoneTimestamp = 0;
const int RFID_TIMEOUT_MS    = 10000;
const int RESULT_DISPLAY_MS  = 6000;

// ─── Vibration Motor State (non-blocking) ──────────────────────────────────────
bool          vibrationActive    = false;
unsigned long vibrationStartTime = 0;
unsigned long vibrationDuration  = VIBRATION_DURATION_MS;

// ─── Banknote Reject Alert State (non-blocking timer; previously also drove
//     the TFT "REJECTED" message — display removed, timer kept in case
//     something downstream still keys off banknoteRejectActive) ─────────────
bool          banknoteRejectActive    = false;
unsigned long banknoteRejectStartTime = 0;

// ─────────────────────────────────────────────────────────────────────────────
// Coin ISR
// ─────────────────────────────────────────────────────────────────────────────
void IRAM_ATTR coinISR() {
  unsigned long now = millis();
  if (now - lastPulseTime > DEBOUNCE_MS) {
    pulseCount++;
    lastPulseTime = now;
    coinPulseSeen = true;   // flag only — actual motor trigger handled in loop()
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// MQTT-Safe Delay
// ─────────────────────────────────────────────────────────────────────────────
void reconnectMQTT();

void safeDelay(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    mqtt.loop();
    if (!mqtt.connected()) {
      reconnectMQTT();
    }
    delay(1);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
float getCoinValue(int pulses) {
  for (int i = 0; i < COIN_COUNT; i++)
    if (COINS[i].pulses == pulses) return COINS[i].value;
  return -1.0;
}

const char* getCoinLabel(int pulses) {
  for (int i = 0; i < COIN_COUNT; i++)
    if (COINS[i].pulses == pulses) return COINS[i].label;
  return "Unknown";
}

// ─────────────────────────────────────────────────────────────────────────────
// Vibration Motor — buzzes for `durationMs` to settle/align coins on the
// acceptor's track, WITHOUT blocking the rest of the program (RFID reads,
// coin processing, MQTT). Turned on here, turned back off from
// updateVibrationMotor() which is polled every loop() iteration.
// ─────────────────────────────────────────────────────────────────────────────
void startVibrationMotor(unsigned long durationMs = VIBRATION_DURATION_MS) {
  Serial.println("[Vibration] Motor ON (" + String(durationMs) + " ms)");
  digitalWrite(VIBRATION_MOTOR_PIN, HIGH);
  vibrationActive    = true;
  vibrationStartTime = millis();
  vibrationDuration  = durationMs;
}

void updateVibrationMotor() {
  if (vibrationActive && millis() - vibrationStartTime >= vibrationDuration) {
    digitalWrite(VIBRATION_MOTOR_PIN, LOW);
    vibrationActive = false;
    Serial.println("[Vibration] Motor OFF");
  }
}

// Polled every loop() iteration — the instant coinISR() has flagged that
// GPIO 34 went active (a coin pulse arrived), fire the vibration motor
// right away. Kept out of the ISR itself since Serial/digitalWrite calls
// inside startVibrationMotor() aren't ISR-safe.
void checkCoinPulseVibration() {
  if (coinPulseSeen) {
    noInterrupts();
    coinPulseSeen = false;
    interrupts();
    startVibrationMotor();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Servo Helper (PCA9685)
// ─────────────────────────────────────────────────────────────────────────────
void setServoAngle(uint8_t channel, int angleDeg) {
  int calibratedAngle = angleDeg + SERVO_OFFSET[channel];
  calibratedAngle = constrain(calibratedAngle, 0, 180);
  int pulse = map(calibratedAngle, 0, 180, SERVO_PWM_MIN, SERVO_PWM_MAX);
  pwm.setPWM(channel, 0, pulse);
}

// ─────────────────────────────────────────────────────────────────────────────
// Banknote Accept/Reject Gate Servo (see header comment for context)
//
// Swings PCA_CH_BANKNOTE to +45° (accept) or -45° (reject) off neutral,
// holds briefly so the note actually clears the gate, then returns to
// neutral. Uses safeDelay() (like dispenseOneCoin()) so MQTT stays alive
// during the brief swing — this mirrors the coin-dispense pattern rather
// than introducing a new non-blocking state machine, since the whole
// swing is only ~1 second end-to-end.
// ─────────────────────────────────────────────────────────────────────────────
void swingBanknoteGate(bool accept) {
  int targetAngle = accept ? BANKNOTE_SERVO_ACCEPT_ANGLE : BANKNOTE_SERVO_REJECT_ANGLE;

  Serial.println(String("[Banknote Gate] Swinging ") + (accept ? "ACCEPT (+45)" : "REJECT (-45)"));

  setServoAngle(PCA_CH_BANKNOTE, targetAngle);
  safeDelay(BANKNOTE_SERVO_MOVE_DELAY);
  safeDelay(BANKNOTE_SERVO_HOLD_DELAY);

  setServoAngle(PCA_CH_BANKNOTE, BANKNOTE_SERVO_NEUTRAL_ANGLE);
  safeDelay(BANKNOTE_SERVO_MOVE_DELAY);

  Serial.println("[Banknote Gate] Back to neutral");
}

// ─────────────────────────────────────────────────────────────────────────────
// Change Return Hardware Setup
// ─────────────────────────────────────────────────────────────────────────────
void setupChangeReturnHardware() {
  Serial.println("[Change] Initializing PCA9685 servo driver + IR sensors...");

  Wire.begin(PCA_SDA_PIN, PCA_SCL_PIN);

  Serial.println("[I2C][DEBUG] Scanning bus...");
  int foundDevices = 0;
  for (uint8_t addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.println("[I2C][DEBUG] Device found at 0x" + String(addr, HEX));
      foundDevices++;
    }
  }
  if (foundDevices == 0) {
    Serial.println("[I2C][DEBUG] NO I2C devices found! Check wiring (SDA=32, SCL=33) and PCA9685 power.");
  }

  pwm.begin();
  pwm.setPWMFreq(50);

  delay(10);

  for (int i = 0; i < NUM_CHANNELS; i++) {
    setServoAngle(coinChannels[i].pwmChannel, SERVO_REST_ANGLE);
    pinMode(coinChannels[i].irPin, INPUT);
  }

  // Banknote gate servo (channel 4) — rest at neutral, same as the coin
  // tubes above. No IR pin for this one (see header comment).
  setServoAngle(PCA_CH_BANKNOTE, BANKNOTE_SERVO_NEUTRAL_ANGLE);

  delay(300);
  Serial.println("[Change] Change return hardware ready (PCA9685 + IR)");
  Serial.println("[Change] Banknote gate servo ready on PCA9685 channel " + String(PCA_CH_BANKNOTE));
}

// ─────────────────────────────────────────────────────────────────────────────
// Change Return Logic (Greedy Algorithm + IR Feedback)
// ─────────────────────────────────────────────────────────────────────────────
bool dispenseOneCoin(CoinChannel &channel) {
  setServoAngle(channel.pwmChannel, SERVO_PUSH_ANGLE);
  safeDelay(SERVO_MOVE_DELAY);
  safeDelay(SERVO_SETTLE_DELAY);

  bool detected = false;
  unsigned long startTime = millis();
  while (millis() - startTime < IR_DETECTION_WINDOW) {
    if (digitalRead(channel.irPin) == IR_ACTIVE_STATE) {
      detected = true;
      break;
    }
    mqtt.loop();
    delay(10);
  }

  setServoAngle(channel.pwmChannel, SERVO_REST_ANGLE);
  safeDelay(SERVO_MOVE_DELAY);

  return detected;
}

// ─────────────────────────────────────────────────────────────────────────────
// returnChange — returns the REMAINING un-dispensed amount (int) instead of
// a bool. 0 means fully dispensed successfully; any value > 0 means that
// many NIS are still owed because one or more tubes ran out. The
// greedy/IR-confirmation logic itself is unchanged.
// ─────────────────────────────────────────────────────────────────────────────
int returnChange(int startingRemaining) {
  int remaining = startingRemaining;

  Serial.println("\n[Change] Starting change return");
  Serial.println("[Change] Amount due: " + String(remaining) + " NIS");

  if (remaining <= 0) {
    Serial.println("[Change] No change to return");
    return 0;
  }

  for (int i = 0; i < NUM_CHANNELS && remaining > 0; i++) {
    CoinChannel &channel = coinChannels[i];

    while (remaining >= channel.value) {
      Serial.println("[Change] Attempting to dispense: " + String(channel.label));

      bool success = false;
      int attempts = 0;

      while (attempts <= MAX_RETRY_PER_COIN && !success) {
        success = dispenseOneCoin(channel);
        attempts++;
        if (!success && attempts <= MAX_RETRY_PER_COIN) {
          Serial.println("[Change] Coin not detected, retrying...");
          safeDelay(150);
        }
      }

      if (success) {
        Serial.println("[Change] Dispensed " + String(channel.value) + " NIS successfully (IR confirmed)");
        remaining -= channel.value;
      } else {
        Serial.println("[Change] Tube empty: " + String(channel.label) + " - moving to lower denomination");
        safeDelay(800);
        break;   // move on to the next (lower) denomination channel
      }
    }
  }

  if (remaining == 0) {
    Serial.println("[Change] Full change returned successfully (IR confirmed)\n");
  } else {
    Serial.println("[Change] Could not return full change, remaining: " + String(remaining) + " NIS\n");
  }

  return remaining;
}

// ─────────────────────────────────────────────────────────────────────────────
void resetPaymentState() {
  state                  = STATE_IDLE;
  currentRFID            = "";
  invoiceCode            = "";
  invoiceId              = 0;
  paymentId              = 0;
  sessionId              = 0;
  totalDue               = 0.0;
  totalInserted          = 0.0;
  pendingChangeRemaining = 0;
  pulseCount             = 0;
  lastPulseTime          = 0;
  banknoteRejectActive   = false;
  Serial.println("[System] State reset — Ready for next customer");
  Serial.println("[System] Waiting for RFID card...");
}

// ─────────────────────────────────────────────────────────────────────────────
// MQTT Publish Helpers
// ─────────────────────────────────────────────────────────────────────────────
void publishCoinInserted(float denomination, float total) {
  StaticJsonDocument<256> doc;
  doc["cart_rfid"]      = currentRFID;
  doc["denomination"]   = denomination;
  doc["count"]          = 1;
  doc["payment_id"]     = paymentId;
  doc["total_inserted"] = total;
  String payload;
  serializeJson(doc, payload);
  mqtt.publish(TOPIC_PAYMENT_COINS, payload.c_str(), false);
}

void publishPaymentComplete(bool changeDispensed) {
  float change = totalInserted - totalDue;

  StaticJsonDocument<512> doc;
  doc["cart_rfid"]        = currentRFID;
  doc["payment_id"]       = paymentId;
  doc["invoice_id"]       = invoiceId;
  doc["invoice_code"]     = invoiceCode;
  doc["session_id"]       = sessionId;
  doc["amount_inserted"]  = totalInserted;
  doc["change_returned"]  = change;
  doc["change_dispensed"] = changeDispensed;
  doc["total_due"]        = totalDue;
  doc["device_id"]        = DEVICE_ID;
  String payload;
  serializeJson(doc, payload);
  mqtt.publish(TOPIC_PAYMENT_COMPLETE, payload.c_str(), false);

  Serial.println("════════════════════════════════════");
  Serial.println("[Payment] COMPLETE!");
  Serial.println("[Payment] Invoice:  " + invoiceCode);
  Serial.println("[Payment] Due:      " + String(totalDue, 2) + " NIS");
  Serial.println("[Payment] Inserted: " + String(totalInserted, 2) + " NIS");
  Serial.println("[Payment] Change:   " + String(change, 2) + " NIS");
  Serial.println("[Payment] Dispensed:" + String(changeDispensed ? "YES" : "PARTIAL/NO"));
  Serial.println("════════════════════════════════════");

  paymentDoneTimestamp = millis();
}

// ─────────────────────────────────────────────────────────────────────────────
// publishRefillRequest — alerts the shop owner that one or more coin tubes
// are empty and the current sale is paused waiting for a refill.
// ─────────────────────────────────────────────────────────────────────────────
void publishRefillRequest() {
  StaticJsonDocument<384> doc;
  doc["event"]            = "refill_needed";
  doc["cart_rfid"]        = currentRFID;
  doc["payment_id"]       = paymentId;
  doc["invoice_id"]       = invoiceId;
  doc["invoice_code"]     = invoiceCode;
  doc["session_id"]       = sessionId;
  doc["remaining_change"] = pendingChangeRemaining;
  doc["device_id"]        = DEVICE_ID;
  String payload;
  serializeJson(doc, payload);
  mqtt.publish(TOPIC_REFILL_REQUEST, payload.c_str(), false);

  Serial.println("════════════════════════════════════");
  Serial.println("[Refill] Coin tubes could not complete the change!");
  Serial.println("[Refill] Invoice:        " + invoiceCode);
  Serial.println("[Refill] Still owed:     " + String(pendingChangeRemaining) + " NIS");
  Serial.println("[Refill] Alert sent to shop owner (topic: " + String(TOPIC_REFILL_REQUEST) + ")");
  Serial.println("[Refill] Payment PAUSED — waiting for refill_done confirmation...");
  Serial.println("════════════════════════════════════");
}

// ─────────────────────────────────────────────────────────────────────────────
// attemptChangeCompletion — shared by both the initial dispense attempt and
// the retry that happens after a refill is confirmed. Tries to dispense
// exactly `pendingChangeRemaining` NIS. If it fully succeeds, completes the
// payment. If it's still short, (re)enters the refill-wait state and sends
// a fresh alert with the updated remaining amount.
// ─────────────────────────────────────────────────────────────────────────────
void attemptChangeCompletion() {
  int stillOwed = returnChange(pendingChangeRemaining);

  if (stillOwed == 0) {
    pendingChangeRemaining = 0;
    state = STATE_PAYMENT_COMPLETE;
    publishPaymentComplete(true);
    Serial.println("[Payment] Waiting for Backend confirmation...");
  } else {
    pendingChangeRemaining = stillOwed;
    state = STATE_WAITING_REFILL;
    publishRefillRequest();
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Payment-completion check — shared by both the coin path and the banknote
// path below, since either one can be what finally reaches totalDue.
// ─────────────────────────────────────────────────────────────────────────────
void checkForPaymentComplete() {
  if (totalInserted < totalDue) return;

  float change = totalInserted - totalDue;

  if (change > 0.001) {
    pendingChangeRemaining = (int)round(change);
    attemptChangeCompletion();
  } else {
    state = STATE_PAYMENT_COMPLETE;
    publishPaymentComplete(true);
    Serial.println("[Payment] Waiting for Backend confirmation...");
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Raspberry Pi Banknote Link — message handlers
//
// Mirrors the coin-accepted / coin-rejected branches in loop() below so a
// banknote and a coin are indistinguishable to the invoice/backend logic
// from this point on; the only difference is where the value came from —
// AND that this board now also drives the physical accept/reject gate
// servo itself, since the Pi doesn't touch it anymore (see header comment).
// ─────────────────────────────────────────────────────────────────────────────
void handleBanknoteValid(const String &denomStr) {
  if (state != STATE_ACCEPTING_COINS) {
    Serial.println("[Banknote] VALID:" + denomStr + " received outside an active sale — ignoring (gate left alone)");
    return;
  }

  float value = denomStr.toFloat();
  if (value <= 0.0) {
    Serial.println("[Banknote] Ignoring malformed VALID message: '" + denomStr + "'");
    return;
  }

  totalInserted += value;

  Serial.println("[Banknote] Accepted: " + String(value, 0) + " NIS note");
  Serial.println("[Banknote] Inserted: " + String(totalInserted, 2) + " NIS" +
                 " / Due: " + String(totalDue, 2) + " NIS" +
                 " / Remaining: " + String(max(0.0f, totalDue - totalInserted), 2) + " NIS");

  publishCoinInserted(value, totalInserted);   // same event shape the backend already expects

  banknoteRejectActive = false;   // a new result always takes priority over a stale alert

  // Physically let the note through: swing the gate +45° and back.
  swingBanknoteGate(true);

  checkForPaymentComplete();
}

void handleBanknoteFake() {
  Serial.println("[Banknote] REJECTED (counterfeit/unreadable). Invoice unchanged: " +
                  String(totalDue, 2) + " | Inserted: " + String(totalInserted, 2));

  if (state != STATE_ACCEPTING_COINS) {
    // No sale to protect the gate for — just log it, no servo movement outside a sale.
    return;
  }

  banknoteRejectActive    = true;
  banknoteRejectStartTime = millis();

  // Physically block the note: swing the gate -45° and back.
  swingBanknoteGate(false);
}

// Polled every loop() iteration — clears the (display-less) reject alert
// flag once BANKNOTE_REJECT_DISPLAY_MS has elapsed.
void updateBanknoteRejectAlert() {
  if (banknoteRejectActive &&
      millis() - banknoteRejectStartTime >= BANKNOTE_REJECT_DISPLAY_MS) {
    banknoteRejectActive = false;
  }
}

// Parses one line received from the Raspberry Pi over the USB/Serial link
// and dispatches it to the right handler. Protocol matches hardware/uart.py
// exactly:
//   VALID:<denomination>   e.g. "VALID:50"
//   FAKE
void handlePiLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  Serial.println("[Pi-UART] Received: " + line);

  if (line.startsWith("VALID:")) {
    handleBanknoteValid(line.substring(6));
  } else if (line == "FAKE") {
    handleBanknoteFake();
  } else {
    Serial.println("[Pi-UART] Unknown message, ignoring: '" + line + "'");
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// MQTT Callback
// ─────────────────────────────────────────────────────────────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];

  StaticJsonDocument<4096> doc;
  if (deserializeJson(doc, msg)) {
    Serial.println("[MQTT] JSON parse error");
    return;
  }

  String event = doc["event"] | "";

  if (String(topic) == TOPIC_PAYMENT_STATUS) {

    // ── Invoice Ready ─────────────────────────────────────────────────────
    if (event == "invoice_ready") {
      invoiceCode   = String(doc["invoice_code"] | "");
      invoiceId     = doc["invoice_id"]   | 0;
      paymentId     = doc["payment_id"]   | 0;
      sessionId     = doc["session_id"]   | 0;
      totalDue      = doc["total_amount"] | 0.0;
      totalInserted = 0.0;
      state         = STATE_ACCEPTING_COINS;

      Serial.println("════════════════════════════════════");
      Serial.println("[Invoice] RECEIVED!");
      Serial.println("[Invoice] Code:    " + invoiceCode);
      Serial.println("[Invoice] Session: " + String(sessionId));
      Serial.println("[Invoice] Total:   " + String(totalDue, 2) + " NIS");
      Serial.println("[Invoice] Items:");
      JsonArray items = doc["items"].as<JsonArray>();
      for (JsonObject item : items) {
        Serial.println("  - " +
          String(item["product_name"] | "") +
          " x" + String((int)(item["quantity"] | 0)) +
          " = " + String((float)(item["subtotal"] | 0.0), 2) + " NIS");
      }
      Serial.println("════════════════════════════════════");
      Serial.println("[Payment] Amount due: " + String(totalDue, 2) + " NIS");
      Serial.println("[Payment] Insert coins or banknotes...");

      startVibrationMotor();   // buzz (non-blocking) to settle/align the coin track as we start accepting

    // ── No Invoice ────────────────────────────────────────────────────────
    } else if (event == "no_invoice") {
      Serial.println("[Payment] No invoice found — finish shopping first");
      safeDelay(2500);
      resetPaymentState();

    // ── Payment Confirmed by Backend ──────────────────────────────────────
    } else if (event == "payment_confirmed") {
      Serial.println("[Backend] Payment confirmed and saved to database");
      Serial.println("[Backend] Session " + String(sessionId) + " closed");

    // ── Refill Done (shop owner confirmed the tubes were refilled) ────────
    } else if (event == "refill_done") {
      if (state != STATE_WAITING_REFILL) {
        Serial.println("[Refill] refill_done received but no payment is paused — ignoring");
        return;
      }

      // Optional safety check: make sure this refill confirmation is for
      // the payment we're actually paused on, not a stale/unrelated message.
      int refillPaymentId = doc["payment_id"] | -1;
      if (refillPaymentId != -1 && refillPaymentId != paymentId) {
        Serial.println("[Refill] refill_done received for a different payment_id — ignoring");
        return;
      }

      Serial.println("[Refill] Refill confirmed by shop owner. Resuming change dispense for invoice " + invoiceCode + "...");
      attemptChangeCompletion();
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// MQTT Reconnect
// ─────────────────────────────────────────────────────────────────────────────
void reconnectMQTT() {
  if (mqtt.connected()) return;
  Serial.print("[MQTT] Connecting...");
  String clientId = String(DEVICE_ID) + "-" + String(random(0xffff), HEX);
  if (mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS_S)) {
    Serial.println(" Connected!");
    mqtt.subscribe(TOPIC_PAYMENT_STATUS, 1);
  } else {
    Serial.println(" Failed! rc=" + String(mqtt.state()));
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Setup
// ─────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n[NEOSHOP] Payment Station Starting...");

  pinMode(VIBRATION_MOTOR_PIN, OUTPUT);
  digitalWrite(VIBRATION_MOTOR_PIN, LOW);

  // The (now-removed) TFT display's CS line (GPIO 4) is still physically
  // wired to the shared SPI bus (SCK/MOSI shared with the RC522). Left
  // floating, it lets the disconnected/burned display interfere with
  // RC522 communication. Pin it HIGH (deselected) so it stays silent on
  // the bus — no display library or object involved, just this GPIO.
  pinMode(4, OUTPUT);
  digitalWrite(4, HIGH);

  // Raspberry Pi banknote link — over USB now, riding on the SAME Serial
  // (UART0) opened above at 115200. No separate Serial2.begin(): the Pi's
  // USB cable IS this port. Nothing else to initialize here. The Pi only
  // ever sends VALID:/FAKE — it no longer drives any servo on its side.
  Serial.println("[Pi-UART] Also listening for Raspberry Pi banknote "
                  "messages on this same USB/Serial link @ 115200 baud");

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("[WiFi] Connecting");
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 20) {
    delay(500); Serial.print("."); tries++;
  }
  if (WiFi.status() == WL_CONNECTED)
    Serial.println("\n[WiFi] Connected: " + WiFi.localIP().toString());
  else
    Serial.println("\n[WiFi] Connection FAILED!");

  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(4096);
  mqtt.setKeepAlive(60);
  reconnectMQTT();

  SPI.begin(RFID_SCK_PIN, RFID_MISO_PIN, RFID_MOSI_PIN, RFID_SS_PIN);
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);
  Serial.println("[RFID] Firmware: 0x" +
    String(rfid.PCD_ReadRegister(rfid.VersionReg), HEX));

  pinMode(COIN_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), coinISR, FALLING);
  delay(2000);
  noInterrupts();
  pulseCount    = 0;
  lastPulseTime = 0;
  coinPulseSeen = false;
  interrupts();
  Serial.println("[Coin] CH-926 ready on GPIO " + String(COIN_PIN));

  setupChangeReturnHardware();

  Serial.println("[NEOSHOP] Ready! Waiting for RFID card...");
}

// ─────────────────────────────────────────────────────────────────────────────
// Loop
// ─────────────────────────────────────────────────────────────────────────────
void loop() {

  // ── MQTT ────────────────────────────────────────────────────────────────────
  if (!mqtt.connected()) {
    unsigned long now = millis();
    if (now - lastMQTTReconnect > 5000) {
      lastMQTTReconnect = now;
      reconnectMQTT();
    }
  }
  mqtt.loop();

  // ── Raspberry Pi banknote link — read newline-terminated messages ──────────
  // Reading from Serial now (the USB link), not Serial2 — see setup() and
  // the "Raspberry Pi Banknote Link" note at the top of this file. Debug
  // Serial.println() calls elsewhere in this sketch only ever WRITE out;
  // they don't touch this incoming buffer, so mixing debug output and the
  // Pi protocol on one port is safe in this direction.
  static String piBuffer;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      handlePiLine(piBuffer);
      piBuffer = "";
    } else if (c != '\r') {
      piBuffer += c;
    }
  }

  // ── Vibration Motor (non-blocking timer) ────────────────────────────────────
  updateVibrationMotor();

  // ── Vibration Motor — fire immediately on any GPIO 34 coin pulse ────────────
  checkCoinPulseVibration();

  // ── Banknote "REJECTED" alert (non-blocking timer) ──────────────────────────
  updateBanknoteRejectAlert();

  // ── RFID Timeout ────────────────────────────────────────────────────────────
  if (state == STATE_WAITING_INVOICE &&
      millis() - rfidTimestamp > RFID_TIMEOUT_MS) {
    Serial.println("[RFID] Timeout — no response from Backend");
    safeDelay(1500);
    resetPaymentState();
  }

  // ── Auto-reset after showing the payment result ────────────────────────────
  // NOTE: STATE_WAITING_REFILL is intentionally NOT auto-reset here — it
  // waits indefinitely for refill_done, since the sale must not be lost.
  if (state == STATE_PAYMENT_COMPLETE &&
      millis() - paymentDoneTimestamp > RESULT_DISPLAY_MS) {
    resetPaymentState();
  }

  // ── STATE: IDLE — Read RFID ─────────────────────────────────────────────────
  if (state == STATE_IDLE && millis() - lastRFIDCheck > 500) {
    lastRFIDCheck = millis();

    if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
      String uid = "";
      for (byte i = 0; i < rfid.uid.size; i++) {
        if (rfid.uid.uidByte[i] < 0x10) uid += "0";
        uid += String(rfid.uid.uidByte[i], HEX);
        if (i < rfid.uid.size - 1) uid += ":";
      }
      uid.toUpperCase();
      rfid.PICC_HaltA();
      rfid.PCD_StopCrypto1();

      currentRFID   = uid;
      state         = STATE_WAITING_INVOICE;
      rfidTimestamp = millis();

      Serial.println("[RFID] Card detected: " + uid);
      Serial.println("[RFID] Fetching invoice from Backend...");

      StaticJsonDocument<256> doc;
      doc["cart_rfid"] = uid;
      doc["event"]     = "payment_request";
      doc["device_id"] = DEVICE_ID;
      String payload;
      serializeJson(doc, payload);
      mqtt.publish(TOPIC_PAYMENT_REQUEST, payload.c_str(), false);
    }
  }

  // ── STATE: ACCEPTING_COINS — Process coin pulses ────────────────────────────
  if (state == STATE_ACCEPTING_COINS &&
      pulseCount > 0 &&
      millis() - lastPulseTime > TIMEOUT_MS) {

    noInterrupts();
    int pulses = pulseCount;
    pulseCount = 0;
    interrupts();

    float value = getCoinValue(pulses);

    if (value > 0) {
      totalInserted += value;

      Serial.println("[Coin] Accepted: " + String(getCoinLabel(pulses)) +
                     " (" + String(value, 1) + " NIS)");
      Serial.println("[Coin] Inserted: " + String(totalInserted, 2) + " NIS" +
                     " / Due: " + String(totalDue, 2) + " NIS" +
                     " / Remaining: " + String(max(0.0f, totalDue - totalInserted), 2) + " NIS");

      publishCoinInserted(value, totalInserted);

      banknoteRejectActive = false;   // a coin result also clears a stale banknote alert

      checkForPaymentComplete();

    } else {
      Serial.println("[Coin] REJECTED — unknown coin (" + String(pulses) + " pulses)");
      safeDelay(1200);
    }
  }
}
