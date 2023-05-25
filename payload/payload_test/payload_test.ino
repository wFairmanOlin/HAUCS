
#include <Adafruit_LPS2X.h>

#define SENSOR_ID 1
#define TEST 0
#define MTU 64

#define PTHRESH 5
#define TRIGGER_INTERVAL 2000
#define SAMPLE_INTERVAL 1000
#define MAX_SAMPLES 6

Adafruit_LPS28 lps;
Adafruit_Sensor *lps_temp, *lps_pressure;

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("payload is alive");
  digitalWrite(LEDB, LOW);
  

  //// LPS298 ////
  if (!lps.begin_I2C()) {
    Serial.println("Failed to find LPS2X chip");
    for (int i = 0; i < 100; i ++)
    {
      digitalWrite(LED_BUILTIN, LOW);
      delay(50);
      digitalWrite(LED_BUILTIN, HIGH);
      delay(50);
      }
  }
  else
    Serial.println("LPS2X Found!");

}

void loop() {

  lps_temp = lps.getTemperatureSensor();
  lps_pressure = lps.getPressureSensor();
  sensors_event_t psr;
  sensors_event_t tmp;
  lps_temp->getEvent(&tmp);
  lps_pressure->getEvent(&psr);
  float pressure = psr.pressure;
  float temperature = tmp.temperature;
  
  int DO = 0;
  for (int i = 0; i < 10; i ++){
    DO += analogRead(A0);
  }
  
  DO = DO / 10;
  Serial.print("do "); Serial.print(DO);
  Serial.print(" p "); Serial.print(pressure);
  Serial.print(" t "); Serial.println(temperature);
  delay(100);

}
