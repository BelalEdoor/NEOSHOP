/**
 * NEOSHOP ESP32 — Payment Station (RFID + Coin Acceptor, No TFT)
 * =================================================================
 * RFID + CH-926 Coin Acceptor + MQTT
 *
 * Flow:
 *   1. Read RFID → Send payment_request
 *   2. Receive invoice from Backend
 *   3. Accept coins until amount is fulfilled
 *   4. Payment complete → Backend confirms → Reset for next customer
 *
 * Wiring:
 *   RC522:  SDA=5, RST=27, SCK=18, MISO=19, MOSI=23
 *   CH-926: COIN → 10kΩ → GPIO 34, GND shared, DC12V external
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>

// ─── WiFi & MQTT Config ───────────────────────────────────────────────────────
const char* WIFI_SSID   = "CELab";
const char* WIFI_PASS   = "CELabC207";
const char* MQTT_BROKER = "192.168.0.125";
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

// ─── Coin Denominations ───────────────────────────────────────────────────────
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

// ─── Coin ISR Variables ───────────────────────────────────────────────────────
volatile int           pulseCount   = 0;
volatile unsigned long lastPulseTime = 0;
const int DEBOUNCE_MS = 120;
const int TIMEOUT_MS  = 400;

// ─── Objects ──────────────────────────────────────────────────────────────────
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);
MFRC522      rfid(RFID_SS_PIN, RFID_RST_PIN);

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
const int RESULT_DISPLAY_MS  = 6000;  // how long to keep showing the result before resetting

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

void publishPaymentComplete() {
  float change = totalInserted - totalDue;

  StaticJsonDocument<512> doc;
  doc["cart_rfid"]       = currentRFID;
  doc["payment_id"]      = paymentId;
  doc["invoice_id"]      = invoiceId;
  doc["invoice_code"]    = invoiceCode;
  doc["session_id"]      = sessionId;
  doc["amount_inserted"] = totalInserted;
  doc["change_returned"] = change;
  doc["total_due"]       = totalDue;
  doc["device_id"]       = DEVICE_ID;
  String payload;
  serializeJson(doc, payload);
  mqtt.publish(TOPIC_PAYMENT_COMPLETE, payload.c_str(), false);

  Serial.println("════════════════════════════════════");
  Serial.println("[Payment] COMPLETE!");
  Serial.println("[Payment] Invoice:  " + invoiceCode);
  Serial.println("[Payment] Due:      $" + String(totalDue, 2));
  Serial.println("[Payment] Inserted: $" + String(totalInserted, 2));
  Serial.println("[Payment] Change:   $" + String(change, 2));
  Serial.println("════════════════════════════════════");

  if (change > 0.001) {
    Serial.println("[Payment] Change due to customer: $" + String(change, 2));
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
      Serial.println("[Invoice] Total:   $" + String(totalDue, 2));
      Serial.println("[Invoice] Items:");
      JsonArray items = doc["items"].as<JsonArray>();
      for (JsonObject item : items) {
        Serial.println("  - " +
          String(item["product_name"] | "") +
          " x" + String((int)(item["quantity"] | 0)) +
          " = $" + String((float)(item["subtotal"] | 0.0), 2));
      }
      Serial.println("════════════════════════════════════");
      Serial.println("[Payment] Amount due: $" + String(totalDue, 2));
      Serial.println("[Payment] Insert coins...");

    // ── No Invoice ────────────────────────────────────────────────────────
    } else if (event == "no_invoice") {
      Serial.println("[Payment] No invoice found — finish shopping first");
      delay(2500);
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
    delay(500); Serial.print("."); tries++;
  }
  if (WiFi.status() == WL_CONNECTED)
    Serial.println("\n[WiFi] Connected: " + WiFi.localIP().toString());
  else
    Serial.println("\n[WiFi] Connection FAILED!");

  // MQTT
  mqtt.setServer(MQTT_BROKER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(4096);
  reconnectMQTT();

  // RFID
  SPI.begin(RFID_SCK_PIN, RFID_MISO_PIN, RFID_MOSI_PIN, RFID_SS_PIN);
  rfid.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);
  Serial.println("[RFID] Firmware: 0x" +
    String(rfid.PCD_ReadRegister(rfid.VersionReg), HEX));

  // Coin Acceptor
  pinMode(COIN_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), coinISR, FALLING);
  delay(2000);
  noInterrupts();
  pulseCount    = 0;
  lastPulseTime = 0;
  interrupts();
  Serial.println("[Coin] CH-926 ready on GPIO " + String(COIN_PIN));

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

    int pulses = pulseCount;
    pulseCount = 0;

    float value = getCoinValue(pulses);

    if (value > 0) {
      totalInserted += value;

      Serial.println("[Coin] Accepted: " + String(getCoinLabel(pulses)) +
                     " ($" + String(value, 1) + ")");
      Serial.println("[Coin] Inserted: $" + String(totalInserted, 2) +
                     " / Due: $" + String(totalDue, 2) +
                     " / Remaining: $" + String(max(0.0f, totalDue - totalInserted), 2));

      // Notify Backend of coin inserted (real-time tracking)
      publishCoinInserted(value, totalInserted);

      // Check if payment is complete
      if (totalInserted >= totalDue) {
        state = STATE_PAYMENT_COMPLETE;
        publishPaymentComplete();
        Serial.println("[Payment] Waiting for Backend confirmation...");
      }

    } else {
      Serial.println("[Coin] REJECTED — unknown coin (" + String(pulses) + " pulses)");
    }
  }
}
