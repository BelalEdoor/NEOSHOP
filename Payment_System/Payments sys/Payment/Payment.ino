/**
 * NEOSHOP ESP32 — Payment Station (RFID + Coin Acceptor + Change Return + TFT)
 * =================================================================
 * RFID + CH-926 Coin Acceptor + MQTT + PCA9685 Servo Change Dispenser + IR Feedback + TFT Display
 *
 * Flow:
 *   1. Read RFID → Send payment_request
 *   2. Receive invoice from Backend
 *   3. Accept coins until amount is fulfilled
 *   4. Payment complete → Dispense physical change (PCA9685 servos + IR feedback, greedy algorithm)
 *   5. Publish payment_complete → Backend confirms → Reset for next customer
 *
 * Wiring:
 *   RC522:  SDA=5, RST=27, SCK=13, MISO=19, MOSI=23
 *   CH-926: COIN → 10kΩ → GPIO 34, GND shared, DC12V external
 *
 *   TFT 1.8" SPI 128x160 (ST7735):
 *     VCC   -> 3.3V
 *     GND   -> GND
 *     CS    -> GPIO 15
 *     RESET -> GPIO 4
 *     A0/DC -> GPIO 2
 *     SDA   -> shares RFID's SPI bus (MOSI = GPIO 23, already configured)
 *     SCK   -> shares RFID's SPI bus (SCK  = GPIO 13, already configured)
 *     LED   -> 3.3V directly (backlight always on)
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
 *   Change Return IR Sensors (confirm coin dropped) — RESTORED, same wiring as
 *   the original direct-GPIO design (these are plain digital GPIO reads, not
 *   affected by the servo driver being on PCA9685 now):
 *     1 Shekel  -> GPIO 26   (FIXED: was GPIO 15, which conflicted with TFT_CS_PIN)
 *     2 Shekels -> GPIO 21
 *     5 Shekels -> GPIO 22
 *     10 Shekels-> GPIO 25   (not physically installed yet, still programmed)
 *
 *   NOTE (reliability update):
 *     - mqtt.setKeepAlive(60) added to reduce broker timeout disconnects.
 *     - All runtime delay() calls replaced with safeDelay(), which keeps
 *       calling mqtt.loop() (and reconnects if needed) while waiting, so
 *       long operations (servo moves, screen holds) don't starve MQTT.
 *     - Coin pulse count is now read with interrupts briefly disabled to
 *       avoid a race condition with the ISR.
 *     - Currency labels changed from "$" to "NIS" in Serial output.
 *     - Change return servos switched from direct-GPIO (ESP32Servo) to a
 *       PCA9685 I2C PWM driver, matching the actual hardware wiring.
 *
 *   NOTE (servo calibration update):
 *     - Rest position changed to be VERTICAL (90°) instead of 0°, matching
 *       the physical arm mounting (popsicle-stick pusher sits upright at rest).
 *     - Push travel reduced to a short 15-20° swing instead of the old 0->75°
 *       full swing, since the arm only needs a small nudge to drop a coin.
 *     - PUSH_DIRECTION lets you flip whether the push angle is REST+delta or
 *       REST-delta without rewriting the angle math, in case an arm needs to
 *       swing the other way depending on how it's mounted.
 *
 *   NOTE (IR sensors restored):
 *     - Each coin channel now has an irPin again. After a servo push,
 *       dispenseOneCoin() watches that channel's IR sensor for
 *       IR_DETECTION_WINDOW ms to confirm a coin actually broke the beam.
 *     - If the beam is NOT broken (no coin fell) it retries the SAME
 *       denomination up to MAX_RETRY_PER_COIN times.
 *     - If it still fails after retries, the tube is treated as EMPTY and
 *       returnChange() moves on to the next (lower) denomination instead of
 *       getting stuck — exactly like the original direct-GPIO version.
 *
 *   NOTE (TFT display removed):
 *     - The TFT display is NOT physically wired up yet, so all TFT pins,
 *       objects, setup, and screen-update calls have been removed from this
 *       build. Serial logging now carries all the status info that used to
 *       also go to the screen. Re-add the display block later once the
 *       screen is actually connected.
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
const char* MQTT_BROKER = "192.168.0.147";
const int   MQTT_PORT   = 1883;
const char* MQTT_USER   = "neoshop";
const char* MQTT_PASS_S = "neoshop_mqtt_pass";
const char* DEVICE_ID   = "ESP32-PAYMENT-01";

// ─── MQTT Topics ──────────────────────────────────────────────────────────────
const char* TOPIC_PAYMENT_REQUEST  = "payment/request";
const char* TOPIC_PAYMENT_STATUS   = "payment/status";
const char* TOPIC_PAYMENT_COINS    = "payment/coins";
const char* TOPIC_PAYMENT_COMPLETE = "payment/complete";

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
#define PCA_I2C_ADDR 0x40   // default Adafruit PCA9685 address — change if yours differs

// ─── Change Return PCA9685 Channels ────────────────────────────────────────────
#define PCA_CH_1  0   // 1 Shekel
#define PCA_CH_2  1   // 2 Shekels
#define PCA_CH_5  2   // 5 Shekels
#define PCA_CH_10 3   // 10 Shekels (tube not installed yet)

// ─── Change Return IR Sensor Pins (RESTORED) ───────────────────────────────────
#define IR_PIN_1  26   // 1 Shekel  (FIXED: was 15, which conflicted with the old TFT_CS_PIN)
#define IR_PIN_2  15   // 2 Shekels
#define IR_PIN_5  22   // 5 Shekels
#define IR_PIN_10 25   // 10 Shekels (not physically installed yet)

// ─── IR Detection Calibration (RESTORED) ───────────────────────────────────────
#define IR_DETECTION_WINDOW  600   // ms window to detect coin passing
#define IR_ACTIVE_STATE      LOW   // most IR obstacle modules pull LOW when beam is broken
#define MAX_RETRY_PER_COIN   1     // retries before considering a tube empty

// ─── Change Return Calibration ─────────────────────────────────────────────────
// Rest position is vertical (90°), and the push is a short 15-20° nudge away
// from rest instead of a big 0->75° swing.
#define SERVO_REST_ANGLE     90    // resting angle — vertical. Fine-tune
                                   // +/-5° if your servo horn's true vertical
                                   // isn't exactly at 90 on this PWM calibration.
#define PUSH_DELTA_ANGLE    -22    // how far the arm swings from rest (15-20°)
#define PUSH_DIRECTION       (+1)  // +1 => push angle = REST + delta
                                   // -1 => push angle = REST - delta
                                   // flip this if the arm needs to swing the
                                   // other way to drop the coin
#define SERVO_PUSH_ANGLE     (SERVO_REST_ANGLE + (PUSH_DIRECTION * PUSH_DELTA_ANGLE))

#define SERVO_MOVE_DELAY     350   // ms between rest <-> push
#define SERVO_SETTLE_DELAY   150   // ms settle after push before returning to rest

// PCA9685 pulse-length range for typical SG90/MG90 servos at 50Hz, 12-bit
// resolution (4096 steps/cycle). Calibrate these two values against your
// actual servos if 0°/180° don't land where expected.
#define SERVO_PWM_MIN  102   // pulse count corresponding to ~0°   (~0.5ms pulse)
#define SERVO_PWM_MAX  512   // pulse count corresponding to ~180° (~2.5ms pulse)

// ─── Per-Servo Calibration Offsets ─────────────────────────────────────────────
// Each servo horn sits at a slightly different angle on its spline, so even
// sending the same logical angle (e.g. 90° = vertical) to every channel, each
// one physically lands differently. This array corrects the difference per
// channel, so SERVO_REST_ANGLE / SERVO_PUSH_ANGLE stay uniform logical
// numbers, and setServoAngle() adds the correction automatically per channel.
//
// Values from the actual calibration via NEOSHOP_Servo_Calibration.ino:
//   Channel 0 (1 Shekel)   -> angle=110  -> offset +20
//   Channel 1 (2 Shekels)  -> angle=95   -> offset +5
//   Channel 2 (5 Shekels)  -> angle=145  -> offset +55
//   Channel 3 (10 Shekels) -> angle=120  -> offset +30
const int SERVO_OFFSET[4] = { 20, 5, 55, 30 };   // index = PCA9685 channel number

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
  int   pwmChannel;   // PCA9685 channel number (0-15)
  int   irPin;        // RESTORED: digital IR "coin dropped" sensor pin
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

// ─── Payment State Machine ────────────────────────────────────────────────────
enum PaymentState {
  STATE_IDLE,               // Waiting for RFID scan
  STATE_WAITING_INVOICE,    // RFID read, waiting for Backend response
  STATE_ACCEPTING_COINS,    // Invoice received, accepting coins
  STATE_PAYMENT_COMPLETE    // Payment done
};

PaymentState state = STATE_IDLE;

// ─── Payment Data ─────────────────────────────────────────────────────────────
String  currentRFID      = "";
String  invoiceCode      = "";
int     invoiceId        = 0;
int     paymentId        = 0;
int     sessionId        = 0;
float   totalDue         = 0.0;
float   totalInserted    = 0.0;

// ─── Timers ───────────────────────────────────────────────────────────────────
unsigned long lastRFIDCheck       = 0;
unsigned long lastMQTTReconnect   = 0;
unsigned long rfidTimestamp       = 0;
unsigned long paymentDoneTimestamp = 0;
const int RFID_TIMEOUT_MS    = 10000;
const int RESULT_DISPLAY_MS  = 6000;  // how long to keep the payment-complete state before resetting

// ─────────────────────────────────────────────────────────────────────────────
// Coin ISR
// ─────────────────────────────────────────────────────────────────────────────
// NOTE: kept intentionally lightweight — no MQTT, Serial, String calls in
// here. Only plain integer/millis() work, as required for an ISR.
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
// Replaces blocking delay() calls at runtime so mqtt.loop() keeps running and
// the broker doesn't see us as "timed out" during long waits (servo moves,
// etc). Also auto-reconnects MQTT if it drops mid-wait.
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
// Servo Helper (PCA9685) — converts a 0-180° LOGICAL angle to a PCA9685 pulse
// count, after applying that channel's calibration offset (SERVO_OFFSET[]).
//
// "Logical" angle = the value the rest of the code thinks in (SERVO_REST_ANGLE,
// SERVO_PUSH_ANGLE — same numbers for every coin type). This function is the
// ONLY place that turns that logical angle into the actual physical angle for
// a specific channel's servo, by adding its offset before mapping to PWM.
// ─────────────────────────────────────────────────────────────────────────────
void setServoAngle(uint8_t channel, int angleDeg) {
  int calibratedAngle = angleDeg + SERVO_OFFSET[channel];
  calibratedAngle = constrain(calibratedAngle, 0, 180);   // safety clamp
  int pulse = map(calibratedAngle, 0, 180, SERVO_PWM_MIN, SERVO_PWM_MAX);
  pwm.setPWM(channel, 0, pulse);
}

// ─────────────────────────────────────────────────────────────────────────────
// Change Return Hardware Setup
// ─────────────────────────────────────────────────────────────────────────────
void setupChangeReturnHardware() {
  Serial.println("[Change] Initializing PCA9685 servo driver + IR sensors...");

  Wire.begin(PCA_SDA_PIN, PCA_SCL_PIN);

  // TEMP DIAGNOSTIC: scan the I2C bus to confirm the PCA9685 actually
  // responds on SDA=32/SCL=33 before we trust pwm.begin(). Remove once
  // servo dispensing is confirmed working reliably.
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
  pwm.setPWMFreq(50);   // standard servo frequency

  delay(10);   // boot-time settle delay for the PCA9685 oscillator

  for (int i = 0; i < NUM_CHANNELS; i++) {
    setServoAngle(coinChannels[i].pwmChannel, SERVO_REST_ANGLE);
    pinMode(coinChannels[i].irPin, INPUT);   // RESTORED: IR sensor input
  }

  delay(300);   // boot-time init delay — left as plain delay() intentionally
  Serial.println("[Change] Change return hardware ready (PCA9685 + IR)");
}

// ─────────────────────────────────────────────────────────────────────────────
// Change Return Logic (Greedy Algorithm + IR Feedback, RESTORED)
// ─────────────────────────────────────────────────────────────────────────────
// Pushes the servo once and watches the channel's IR sensor for
// IR_DETECTION_WINDOW ms to confirm a coin actually broke the beam.
// Returns true if a coin was detected, false if the beam was never broken
// (likely an empty tube or a jam).
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
    // Keep MQTT alive during the detection window too, same spirit as
    // safeDelay(), since this loop can take up to IR_DETECTION_WINDOW ms.
    mqtt.loop();
    delay(10);
  }

  setServoAngle(channel.pwmChannel, SERVO_REST_ANGLE);
  safeDelay(SERVO_MOVE_DELAY);

  return detected;
}

bool returnChange(float amountFloat) {
  int remaining = (int)round(amountFloat);

  Serial.println("\n[Change] Starting change return");
  Serial.println("[Change] Amount due: " + String(remaining) + " NIS");

  if (remaining <= 0) {
    Serial.println("[Change] No change to return");
    return true;
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
    return true;
  } else {
    Serial.println("[Change] Could not return full change, remaining: " + String(remaining) + " NIS\n");
    return false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
void resetPaymentState() {
  state          = STATE_IDLE;
  currentRFID    = "";
  invoiceCode    = "";
  invoiceId      = 0;
  paymentId      = 0;
  sessionId      = 0;
  totalDue       = 0.0;
  totalInserted  = 0.0;
  pulseCount     = 0;
  lastPulseTime  = 0;
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

  if (change > 0.001) {
    Serial.println("[Payment] Change due to customer: " + String(change, 2) + " NIS");
  } else {
    Serial.println("[Payment] No change due — Thank you!");
  }

  paymentDoneTimestamp = millis();
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

    // ── No Invoice ────────────────────────────────────────────────────────
    } else if (event == "no_invoice") {
      Serial.println("[Payment] No invoice found — finish shopping first");
      safeDelay(2500);
      resetPaymentState();

    // ── Payment Confirmed by Backend ──────────────────────────────────────
    } else if (event == "payment_confirmed") {
      Serial.println("[Backend] Payment confirmed and saved to database");
      Serial.println("[Backend] Session " + String(sessionId) + " closed");
      // The result stays "visible" (logged) until RESULT_DISPLAY_MS elapses
      // in the main loop, then resets automatically.
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

  // WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("[WiFi] Connecting");
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 20) {
    delay(500); Serial.print("."); tries++;   // boot-time delay — left as-is
  }
  if (WiFi.status() == WL_CONNECTED)
    Serial.println("\n[WiFi] Connected: " + WiFi.localIP().toString());
  else
    Serial.println("\n[WiFi] Connection FAILED!");

  // MQTT
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(4096);
  mqtt.setKeepAlive(60);   // raises keepalive so long operations (servo
                           // dispensing, etc) don't trip the broker's
                           // timeout and cause disconnects
  reconnectMQTT();

  // RFID (also configures the shared hardware SPI bus: SCK=13, MISO=19, MOSI=23)
  SPI.begin(RFID_SCK_PIN, RFID_MISO_PIN, RFID_MOSI_PIN, RFID_SS_PIN);
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);
  Serial.println("[RFID] Firmware: 0x" +
    String(rfid.PCD_ReadRegister(rfid.VersionReg), HEX));

  // Coin Acceptor
  pinMode(COIN_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), coinISR, FALLING);
  delay(2000);   // boot-time settle delay — left as-is
  noInterrupts();
  pulseCount    = 0;
  lastPulseTime = 0;
  interrupts();
  Serial.println("[Coin] CH-926 ready on GPIO " + String(COIN_PIN));

  // Change Return Hardware (PCA9685 servos + IR sensors)
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

  // ── RFID Timeout ────────────────────────────────────────────────────────────
  if (state == STATE_WAITING_INVOICE &&
      millis() - rfidTimestamp > RFID_TIMEOUT_MS) {
    Serial.println("[RFID] Timeout — no response from Backend");
    resetPaymentState();
  }

  // ── Auto-reset after showing the payment result ────────────────────────────
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

    // TEMP DIAGNOSTIC: print every non-timeout status so we can see whether
    // the reader is sensing anything at all near the antenna, even partial
    // reads (collisions, CRC errors, etc). Remove this block once RFID
    // reading is confirmed working reliably.
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

    // Interrupts briefly disabled around the read+reset of pulseCount so the
    // ISR can't increment it mid-read (race condition fix).
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

      // Notify Backend of coin inserted (real-time tracking)
      publishCoinInserted(value, totalInserted);

      // Check if payment is complete
      if (totalInserted >= totalDue) {
        state = STATE_PAYMENT_COMPLETE;

        float change = totalInserted - totalDue;
        bool changeDispensed = true;

        // Dispense physical change FIRST (PCA9685 servos + IR feedback, greedy algorithm)
        if (change > 0.001) {
          changeDispensed = returnChange(change);
        }

        // Then proceed with the invoice/payment flow exactly as before
        // (state change, backend save, session save are all triggered by this
        //  publish + the payment_confirmed response, unchanged)
        publishPaymentComplete(changeDispensed);
        Serial.println("[Payment] Waiting for Backend confirmation...");
      }

    } else {
      Serial.println("[Coin] REJECTED — unknown coin (" + String(pulses) + " pulses)");
      safeDelay(1200);
    }
  }
}
