/**
 * NEOSHOP ESP32 — Payment Station (RFID + Coin Acceptor + Change Return + Refill Alert + TFT Display)
 * =================================================================
 * RFID + CH-926 Coin Acceptor + MQTT + PCA9685 Servo Change Dispenser + IR Feedback + 1.8" TFT SPI Display
 *
 * Flow:
 *   1. Read RFID → Send payment_request
 *   2. Receive invoice from Backend
 *   3. Accept coins until amount is fulfilled
 *   4. Payment complete → Dispense physical change (PCA9685 servos + IR feedback, greedy algorithm)
 *      4a. If tubes run out mid-dispense (IR never confirms a drop after retries,
 *          for BOTH the failing denomination AND every smaller one) → PAUSE the
 *          payment (do NOT cancel it), alert the shop owner over MQTT, and wait.
 *      4b. Once the owner confirms the machine is refilled, resume dispensing
 *          ONLY the amount that was still missing — then complete the payment
 *          on the SAME invoice, exactly as if nothing had happened.
 *   5. Publish payment_complete → Backend confirms → Reset for next customer
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
 *     Servo -> PCA9685 channel mapping:
 *       1 Shekel  -> Channel 0
 *       2 Shekels -> Channel 1
 *       5 Shekels -> Channel 2
 *       10 Shekels-> Channel 3   (tube not physically installed yet, still programmed)
 *
 *   Change Return IR Sensors (confirm coin dropped):
 *     1 Shekel  -> GPIO 26
 *     2 Shekels -> GPIO 15
 *     5 Shekels -> GPIO 22
 *     10 Shekels-> GPIO 2    (not physically installed yet, still programmed)
 *
 *   1.8" TFT SPI Display (128x160, ST7735):
 *     Shares the SPI bus (SCK/MOSI) with the RC522 RFID reader; only CS/DC/RST are dedicated.
 *     VCC    -> 3.3V
 *     GND    -> GND (shared)
 *     CS     -> GPIO 4
 *     RESET  -> GPIO 17
 *     A0(DC) -> GPIO 16
 *     SDA    -> GPIO 23 (shared with RFID MOSI)
 *     SCK    -> GPIO 13 (shared with RFID SCK)
 *     LED    -> VCC directly (backlight always on, NOT GPIO-controlled)
 *     (SD card slot on the display board is NOT used)
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
 *   Triggers briefly the moment coin-accepting starts (on invoice_ready).
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
 *       collided with TFT_CS (also GPIO 4). That collision forced the TFT's
 *       chip-select LOW at boot (via digitalWrite(VIBRATION_MOTOR_PIN, LOW)
 *       in setup()), leaving the TFT permanently "selected" on the shared
 *       SPI bus and corrupting all RC522 communication (constant
 *       STATUS_ERROR / status=1 on every PICC_RequestA). Moved the
 *       vibration motor to GPIO 21, which was freed up after wiring the
 *       TFT backlight (LED) directly to VCC instead of a GPIO pin.
 *     - Vibration motor was originally driven with a BLOCKING safeDelay()
 *       inside triggerVibrationMotor(), called synchronously from
 *       mqttCallback() on invoice_ready. At 800ms this was barely
 *       noticeable, but bumping it to a full 1-minute buzz would have
 *       frozen the ENTIRE device for that minute (no RFID reads, no coin
 *       processing, no display updates) since it's called from inside the
 *       MQTT callback. Rewrote as non-blocking: startVibrationMotor() turns
 *       the pin on and records a start time; updateVibrationMotor(), polled
 *       every loop() iteration, turns it back off once the duration has
 *       elapsed. The invoice screen and coin acceptance now work normally
 *       while the motor buzzes in the background.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>

// ─── WiFi & MQTT Config ───────────────────────────────────────────────────────
const char* WIFI_SSID   = "C203";
const char* WIFI_PASS   = "15159519";
const char* MQTT_BROKER = "10.3.20.22";
const int   MQTT_PORT   = 1883;
const char* MQTT_USER   = "neoshop";
const char* MQTT_PASS_S = "neoshop_mqtt_pass";
const char* DEVICE_ID   = "ESP32-PAYMENT-01";

// ─── MQTT Topics ──────────────────────────────────────────────────────────────
const char* TOPIC_PAYMENT_REQUEST  = "payment/request";
const char* TOPIC_PAYMENT_STATUS   = "payment/status";        // subscribed — also carries refill_done now
const char* TOPIC_PAYMENT_COINS    = "payment/coins";
const char* TOPIC_PAYMENT_COMPLETE = "payment/complete";
const char* TOPIC_REFILL_REQUEST   = "payment/refill_request"; // published when tubes run out

// ─── RFID Pins ────────────────────────────────────────────────────────────────
#define RFID_SS_PIN   5
#define RFID_RST_PIN  27
#define RFID_SCK_PIN  13
#define RFID_MISO_PIN 19
#define RFID_MOSI_PIN 23

// ─── Coin Pin ─────────────────────────────────────────────────────────────────
#define COIN_PIN 34

// ─── PCA9685 (Servo Driver) I2C Pins ───────────────────────────────────────────
#define PCA_SDA_PIN  32
#define PCA_SCL_PIN  33
#define PCA_I2C_ADDR 0x40

// ─── Change Return PCA9685 Channels ────────────────────────────────────────────
#define PCA_CH_1  0
#define PCA_CH_2  1
#define PCA_CH_5  2
#define PCA_CH_10 3

// ─── Change Return IR Sensor Pins ──────────────────────────────────────────────
#define IR_PIN_1  26
#define IR_PIN_2  15
#define IR_PIN_5  22
#define IR_PIN_10 2

// ─── TFT Display Pins (shares SCK/MOSI with the RC522 on the SPI bus) ─────────
// NOTE: LED (backlight) is wired directly to VCC now — no GPIO needed for it.
#define TFT_CS    4
#define TFT_RST   17
#define TFT_DC    16

// ─── Vibration Motor Pin (aligns coins on the track when coin-accepting starts) ─
// Moved to GPIO 21 (was mistakenly GPIO 4, which collided with TFT_CS).
#define VIBRATION_MOTOR_PIN 21
#define VIBRATION_DURATION_MS 60000   // how long the motor buzzes for (1 minute)

// ─── IR Detection Calibration ──────────────────────────────────────────────────
#define IR_DETECTION_WINDOW  600
#define IR_ACTIVE_STATE      LOW
#define MAX_RETRY_PER_COIN   1

// ─── Change Return Calibration ─────────────────────────────────────────────────
#define SERVO_REST_ANGLE     90
#define PUSH_DELTA_ANGLE    -35
#define PUSH_DIRECTION       (+1)
#define SERVO_PUSH_ANGLE     (SERVO_REST_ANGLE + (PUSH_DIRECTION * PUSH_DELTA_ANGLE))

#define SERVO_MOVE_DELAY     350
#define SERVO_SETTLE_DELAY   150

#define SERVO_PWM_MIN  102
#define SERVO_PWM_MAX  512

// ─── Per-Servo Calibration Offsets ─────────────────────────────────────────────
const int SERVO_OFFSET[4] = { 30, 32, 30, 30 };   // index = PCA9685 channel number

// ─── Coin Denominations (Acceptor) ─────────────────────────────────────────────
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
const int DEBOUNCE_MS = 120;
const int TIMEOUT_MS  = 400;

// ─── Objects ──────────────────────────────────────────────────────────────────
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);
MFRC522      rfid(RFID_SS_PIN, RFID_RST_PIN);
Adafruit_PWMServoDriver pwm(PCA_I2C_ADDR);
Adafruit_ST7735 tft = Adafruit_ST7735(TFT_CS, TFT_DC, TFT_RST);

// ─── Payment State Machine ────────────────────────────────────────────────────
enum PaymentState {
  STATE_IDLE,               // Waiting for RFID scan
  STATE_WAITING_INVOICE,    // RFID read, waiting for Backend response
  STATE_ACCEPTING_COINS,    // Invoice received, accepting coins
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

// ─────────────────────────────────────────────────────────────────────────────
// Coin ISR
// ─────────────────────────────────────────────────────────────────────────────
void IRAM_ATTR coinISR() {
  unsigned long now = millis();
  if (now - lastPulseTime > DEBOUNCE_MS) {
    pulseCount++;
    lastPulseTime = now;
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
// TFT Display Helpers
// ─────────────────────────────────────────────────────────────────────────────
void setupDisplay() {
  // Backlight (LED) is wired directly to VCC now — always on, no GPIO control needed.

  tft.initR(INITR_BLACKTAB);     // most common for this 128x160 V1.1 board
  // If colors look swapped/inverted on your unit, try INITR_GREENTAB instead.
  tft.setRotation(1);
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextColor(ST77XX_WHITE);
  tft.setTextSize(1);
  tft.setCursor(5, 5);
  tft.println("NEOSHOP");
  tft.println("Scan your card...");

  // FIX: Adafruit_ST7735's initR() internally calls SPI.begin() with no
  // arguments, which resets SCK/MISO/MOSI/SS back to ESP32's default VSPI
  // pins (18/19/23/5) and breaks the RC522, which needs SCK on GPIO 13.
  // Re-assert our custom SPI pin mapping right after the display init.
  SPI.begin(RFID_SCK_PIN, RFID_MISO_PIN, RFID_MOSI_PIN, RFID_SS_PIN);
}

void updateDisplayStatus(String line1, String line2 = "", String line3 = "", uint16_t color = ST77XX_WHITE) {
  tft.fillScreen(ST77XX_BLACK);
  tft.setTextColor(color);
  tft.setCursor(5, 5);
  tft.println(line1);
  if (line2.length()) { tft.setCursor(5, 25); tft.println(line2); }
  if (line3.length()) { tft.setCursor(5, 45); tft.println(line3); }
  tft.setTextColor(ST77XX_WHITE); // reset default color for next call
}

// ─────────────────────────────────────────────────────────────────────────────
// Vibration Motor — buzzes for `durationMs` to settle/align coins on the
// acceptor's track, WITHOUT blocking the rest of the program (RFID reads,
// coin processing, display updates, MQTT). Turned on here, turned back off
// from updateVibrationMotor() which is polled every loop() iteration.
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

  delay(300);
  Serial.println("[Change] Change return hardware ready (PCA9685 + IR)");
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
  updateDisplayStatus("Dispensing change...", String(remaining) + " NIS");

  if (remaining <= 0) {
    Serial.println("[Change] No change to return");
    return 0;
  }

  for (int i = 0; i < NUM_CHANNELS && remaining > 0; i++) {
    CoinChannel &channel = coinChannels[i];

    while (remaining >= channel.value) {
      Serial.println("[Change] Attempting to dispense: " + String(channel.label));
      updateDisplayStatus("Dispensing:", channel.label, "Remaining: " + String(remaining) + " NIS");

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
  Serial.println("[System] State reset — Ready for next customer");
  Serial.println("[System] Waiting for RFID card...");
  updateDisplayStatus("NEOSHOP", "Scan your card...");
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

  updateDisplayStatus("Payment Complete!", "Change: " + String(change, 2) + " NIS", "Thank you!", ST77XX_GREEN);

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

  updateDisplayStatus("Please wait...", "Refilling change", "Owed: " + String(pendingChangeRemaining) + " NIS", ST77XX_YELLOW);
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
      Serial.println("[Payment] Insert coins...");

      updateDisplayStatus("Due: " + String(totalDue, 2) + " NIS", "Insert coins");
      startVibrationMotor();   // buzz (non-blocking) to settle/align the coin track as we start accepting

    // ── No Invoice ────────────────────────────────────────────────────────
    } else if (event == "no_invoice") {
      Serial.println("[Payment] No invoice found — finish shopping first");
      updateDisplayStatus("No invoice found", "Finish shopping first", "", ST77XX_RED);
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
      updateDisplayStatus("Refill confirmed", "Resuming...");
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

  // On a shared SPI bus, every device's CS line must be HIGH (deselected)
  // except the one currently being talked to. Deselect the TFT immediately,
  // before any SPI traffic happens, so it doesn't interfere with the RC522.
  pinMode(TFT_CS, OUTPUT);
  digitalWrite(TFT_CS, HIGH);

  pinMode(VIBRATION_MOTOR_PIN, OUTPUT);
  digitalWrite(VIBRATION_MOTOR_PIN, LOW);

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
  interrupts();
  Serial.println("[Coin] CH-926 ready on GPIO " + String(COIN_PIN));

  setupChangeReturnHardware();
  setupDisplay();   // TFT display init — must come after SPI.begin() above

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

  // ── Vibration Motor (non-blocking timer) ────────────────────────────────────
  updateVibrationMotor();

  // ── RFID Timeout ────────────────────────────────────────────────────────────
  if (state == STATE_WAITING_INVOICE &&
      millis() - rfidTimestamp > RFID_TIMEOUT_MS) {
    Serial.println("[RFID] Timeout — no response from Backend");
    updateDisplayStatus("Timeout", "No response from server", "", ST77XX_RED);
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

    byte bufferATQA[2];
    byte bufferSize = sizeof(bufferATQA);
    MFRC522::StatusCode status = rfid.PICC_RequestA(bufferATQA, &bufferSize);

    if (status != MFRC522::STATUS_TIMEOUT) {
      Serial.println("[RFID][DEBUG] PICC_RequestA status = " + String(status));
    }

    if (status == MFRC522::STATUS_OK || status == MFRC522::STATUS_COLLISION) {
      if (rfid.PICC_ReadCardSerial()) {
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
        updateDisplayStatus("Card detected", uid, "Loading invoice...");

        StaticJsonDocument<256> doc;
        doc["cart_rfid"] = uid;
        doc["event"]     = "payment_request";
        doc["device_id"] = DEVICE_ID;
        String payload;
        serializeJson(doc, payload);
        mqtt.publish(TOPIC_PAYMENT_REQUEST, payload.c_str(), false);
      }
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

      updateDisplayStatus(
        "Inserted: " + String(totalInserted, 2) + " NIS",
        "Due: " + String(totalDue, 2) + " NIS",
        "Left: " + String(max(0.0f, totalDue - totalInserted), 2) + " NIS"
      );

      // Check if payment is complete
      if (totalInserted >= totalDue) {
        float change = totalInserted - totalDue;

        if (change > 0.001) {
          // Kick off change dispensing. attemptChangeCompletion() will either
          // finish the payment right away, or — if tubes run out — switch to
          // STATE_WAITING_REFILL and alert the owner. Either way the state
          // is set inside that function, so we don't set STATE_PAYMENT_COMPLETE
          // here anymore.
          pendingChangeRemaining = (int)round(change);
          attemptChangeCompletion();
        } else {
          // No change owed — complete immediately, same as before.
          state = STATE_PAYMENT_COMPLETE;
          publishPaymentComplete(true);
          Serial.println("[Payment] Waiting for Backend confirmation...");
        }
      }

    } else {
      Serial.println("[Coin] REJECTED — unknown coin (" + String(pulses) + " pulses)");
      updateDisplayStatus("Coin rejected", "Unknown coin", "", ST77XX_RED);
      safeDelay(1200);
      // restore the normal "accepting coins" screen after showing the rejection
      updateDisplayStatus(
        "Inserted: " + String(totalInserted, 2) + " NIS",
        "Due: " + String(totalDue, 2) + " NIS",
        "Left: " + String(max(0.0f, totalDue - totalInserted), 2) + " NIS"
      );
    }
  }
}
