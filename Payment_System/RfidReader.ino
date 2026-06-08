/**
 * NEOSHOP ESP32 — Step 1: RFID + Invoice Only
 * =============================================
 * فقط: قراءة RFID + استقبال الفاتورة
 * بدون: OLED, Coin, Bill, Payment
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MFRC522.h>
#include <ArduinoJson.h>

// ─── Config ───────────────────────────────────────────────────────────────────
const char* WIFI_SSID   = "Coolnet_2130";
const char* WIFI_PASS   = "Bl@100200300";
const char* MQTT_BROKER = "192.168.56.141";
const int   MQTT_PORT   = 1883;
const char* MQTT_USER   = "neoshop";
const char* MQTT_PASS_S = "neoshop_mqtt_pass";
const char* DEVICE_ID   = "ESP32-PAYMENT-01";

// ─── Topics ───────────────────────────────────────────────────────────────────
const char* TOPIC_PAYMENT_REQUEST = "payment/request";
const char* TOPIC_PAYMENT_STATUS  = "payment/status";

// ─── RFID Pins ────────────────────────────────────────────────────────────────
#define RFID_SS_PIN   5
#define RFID_RST_PIN  27
#define RFID_SCK_PIN  18
#define RFID_MISO_PIN 19
#define RFID_MOSI_PIN 23

// ─── Objects ──────────────────────────────────────────────────────────────────
WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);
MFRC522      rfid(RFID_SS_PIN, RFID_RST_PIN);

// ─── State ────────────────────────────────────────────────────────────────────
bool waitingForInvoice  = false;
unsigned long rfidTimestamp     = 0;
unsigned long lastRFIDCheck     = 0;
unsigned long lastMQTTReconnect = 0;
const int RFID_TIMEOUT_MS = 10000;

// ─────────────────────────────────────────────────────────────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];

  Serial.println("[MQTT] Received [" + String(topic) + "]: " + msg);

  StaticJsonDocument<4096> doc;
  if (deserializeJson(doc, msg)) {
    Serial.println("[MQTT] JSON parse error");
    return;
  }

  String event = doc["event"] | "";

  if (String(topic) == TOPIC_PAYMENT_STATUS) {

    if (event == "invoice_ready") {
      // ── طباعة الفاتورة كاملة ──────────────────────────────────────────
      Serial.println("════════════════════════════════════");
      Serial.println("[Invoice] ✅ INVOICE RECEIVED!");
      Serial.println("[Invoice] Code:    " + String(doc["invoice_code"] | ""));
      Serial.println("[Invoice] Session: " + String((int)(doc["session_id"] | 0)));
      Serial.println("[Invoice] Total:   $" + String((float)(doc["total_amount"] | 0.0), 2));
      Serial.println("[Invoice] RFID:    " + String(doc["cart_rfid"] | ""));
      Serial.println("[Invoice] Items:");

      JsonArray items = doc["items"].as<JsonArray>();
      for (JsonObject item : items) {
        Serial.println("  - " +
          String(item["product_name"] | "") +
          " x" + String((int)(item["quantity"] | 0)) +
          " = $" + String((float)(item["subtotal"] | 0.0), 2));
      }
      Serial.println("════════════════════════════════════");
      Serial.println("[System] Ready to scan next card...");

      waitingForInvoice = false;

    } else if (event == "no_invoice") {
      Serial.println("[MQTT] ❌ No invoice — finish shopping first");
      waitingForInvoice = false;
    }
  }
}

// ─────────────────────────────────────────────────────────────────────────────
void reconnectMQTT() {
  if (mqtt.connected()) return;
  Serial.print("[MQTT] Connecting...");
  String clientId = String(DEVICE_ID) + "-" + String(random(0xffff), HEX);
  if (mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS_S)) {
    Serial.println(" Connected!");
    mqtt.subscribe(TOPIC_PAYMENT_STATUS, 1);
    Serial.println("[MQTT] Subscribed to payment/status");
  } else {
    Serial.println(" Failed! rc=" + String(mqtt.state()));
  }
}

// ─────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n[NEOSHOP] Starting — RFID + Invoice Test");

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
    Serial.println("\n[WiFi] FAILED!");

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

  Serial.println("[NEOSHOP] Ready ✅ — bring RFID card close");
}

// ─────────────────────────────────────────────────────────────────────────────
void loop() {
  // MQTT reconnect
  if (!mqtt.connected()) {
    unsigned long now = millis();
    if (now - lastMQTTReconnect > 5000) {
      lastMQTTReconnect = now;
      reconnectMQTT();
    }
  }
  mqtt.loop();

  // RFID timeout
  if (waitingForInvoice && millis() - rfidTimestamp > RFID_TIMEOUT_MS) {
    Serial.println("[RFID] ⏱ Timeout — ready to scan again");
    waitingForInvoice = false;
  }

  // RFID read
  if (!waitingForInvoice && millis() - lastRFIDCheck > 500) {
    lastRFIDCheck = millis();

    byte bufferATQA[2];
    byte bufferSize = sizeof(bufferATQA);
    MFRC522::StatusCode status = rfid.PICC_RequestA(bufferATQA, &bufferSize);

    if (status == MFRC522::STATUS_OK || status == MFRC522::STATUS_COLLISION) {
      if (rfid.PICC_ReadCardSerial()) {

        // قراءة UID
        String uid = "";
        for (byte i = 0; i < rfid.uid.size; i++) {
          if (rfid.uid.uidByte[i] < 0x10) uid += "0";
          uid += String(rfid.uid.uidByte[i], HEX);
          if (i < rfid.uid.size - 1) uid += ":";
        }
        uid.toUpperCase();
        rfid.PICC_HaltA();
        rfid.PCD_StopCrypto1();

        Serial.println("[RFID] Card detected: " + uid);

        // إرسال payment_request
        StaticJsonDocument<256> doc;
        doc["cart_rfid"] = uid;
        doc["event"]     = "payment_request";
        doc["device_id"] = DEVICE_ID;
        String payload;
        serializeJson(doc, payload);
        mqtt.publish(TOPIC_PAYMENT_REQUEST, payload.c_str(), false);
        Serial.println("[MQTT] Payment request sent for RFID: " + uid);

        waitingForInvoice = true;
        rfidTimestamp     = millis();
      }
    }
  }
}