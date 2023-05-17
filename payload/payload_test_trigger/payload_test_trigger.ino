/*
  The code will upload the sensor data to the topside when the pressure difference changes by 10 millibars
*/
#include <ArduinoBLE.h>
#include <Adafruit_LPS2X.h>
#include <Wire.h>
#define DO_PIN A0

Adafruit_LPS28 lps;
Adafruit_Sensor *lps_temp, *lps_pressure;

float previous_pressure_difference = 0;

/*
 * Start Sequence
 */
void setup() {
  Serial.begin(115200);
  delay(1000);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.println("Adafruit LPS2X test!");

  if (!lps.begin_I2C()) {
    Serial.println("Failed to find LPS2X chip");
    for (int i = 0; i < 100; i ++)
    {
      digitalWrite(LED_BUILTIN, LOW); delay(50);
      digitalWrite(LED_BUILTIN, HIGH);delay(50);
    }
    while (1) ; // infinite loop
  }
  Serial.println("LPS2X Found!");
  
  lps_temp = lps.getTemperatureSensor();
  lps_pressure = lps.getPressureSensor();
}

void loop() {
  sensors_event_t pressure;
  sensors_event_t temp;
  lps_temp->getEvent(&temp);
  lps_pressure->getEvent(&pressure);
  float psr = pressure.pressure;
  float tem = temp.temperature;

//  Serial.print("temp ");
//  Serial.print(tem);
//  Serial.print(" pres ");
//  Serial.println(psr);
//  delay(100);

  // Calculate pressure difference
  float pressure_difference = psr - 1013.25; // 1013.25 is the atmospheric pressure at sea level

  // Check if pressure difference has changed by 10 millibars
  if (abs(pressure_difference - previous_pressure_difference) >= 10) {
    Serial.println("Pressure difference has changed by 10 millibars");
    // Upload sensor data
    Serial.println("Uploading sensor data...");
    Serial.print("temp ");
    Serial.print(tem);
    Serial.print(" pres ");
    Serial.println(psr);

    // Update previous pressure difference
    previous_pressure_difference = pressure_difference;
  }
}
