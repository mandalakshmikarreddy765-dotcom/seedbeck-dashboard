#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

const char* ssid = "Wokwi-GUEST";
const char* password = "";

// Paste YOUR exact Beeceptor URL here:
const char* serverUrl = "https://seedbeck-server.free.beeceptor.com/api/data";

LiquidCrystal_I2C lcd(0x27, 16, 2);

const float S_EST_MIN_THRESHOLD = 0.025f;
const float R_INT_MAX_THRESHOLD = 3.500f;

inline bool is_anomaly(float s_est, float r_int, float delta_t) {
    if (s_est < S_EST_MIN_THRESHOLD || r_int > R_INT_MAX_THRESHOLD || delta_t < 10.0f) {
        return true; 
    }
    return false;
}

#define PIN_TEMP_HOT   34
#define PIN_TEMP_COLD  35
#define PIN_POT_LOAD   32

void setup() {
  Serial.begin(115200);
  pinMode(PIN_TEMP_HOT, INPUT);
  pinMode(PIN_TEMP_COLD, INPUT);
  pinMode(PIN_POT_LOAD, INPUT);

  lcd.init();
  lcd.backlight();
  
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Web Wi-Fi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to Cloud Web Gateway!");
}

void loop() {
  int rawHot = analogRead(PIN_TEMP_HOT);
  int rawCold = analogRead(PIN_TEMP_COLD);
  int rawPot = analogRead(PIN_POT_LOAD);

  float t_hot = map(rawHot, 0, 4095, 20, 100);
  float t_cold = map(rawCold, 0, 4095, 10, 80);
  float delta_t = t_hot - t_cold;
  float v_oc = (delta_t > 0) ? (delta_t * 35.0f) : 0.0f;
  float r_int = (rawPot / 4095.0f) * 5.5f + 0.5f;
  float s_est = (delta_t > 1.0f) ? (v_oc / delta_t) / 1000.0f : 0.0f;

  bool anomaly = is_anomaly(s_est, r_int, delta_t);

  // Update LCD
  lcd.setCursor(0, 0);
  lcd.print("dT:"); lcd.print((int)delta_t); lcd.print("C R:"); lcd.print(r_int, 1); lcd.print("  ");
  lcd.setCursor(0, 1);
  lcd.print(anomaly ? "!! FAULT DETECTED!!" : "STATUS: HEALTHY ");

  // Send POST request over Wi-Fi
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");

    String jsonPayload = "{\"delta_t\":" + String(delta_t, 1) + 
                         ",\"r_int\":" + String(r_int, 2) + 
                         ",\"s_est\":" + String(s_est, 4) + 
                         ",\"anomaly\":" + String(anomaly ? "true" : "false") + "}";

    int httpCode = http.POST(jsonPayload);
    Serial.print("Web Response Code: ");
    Serial.println(httpCode);
    http.end();
  }

  delay(2000);
}
