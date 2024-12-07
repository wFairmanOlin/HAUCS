#include <Arduino.h>
#include <Adafruit_LPS2X.h>
#include <Wire.h>

#define MV_PER_LSB   (0.0732421875F)
#define DO_ADDR 0x09

Adafruit_LPS28 lps;
Adafruit_Sensor *lps_temp, *lps_pressure;
  
void setup() {
  Serial.begin(9600);
  Serial.println("warming up");
  Serial.println("starting in ...");
  delay(1000);
  Serial.println("3");
  delay(1000);
  Serial.println("2");
  delay(1000);
  Serial.println("1");
  delay(1000);
//  digitalWrite(LEDB, LOW);
  
  //// LPS29X ////
  if (!lps.begin_I2C()) {
    Serial.println("Failed to find LPS2X chip");
    for (int i = 0; i < 100; i ++)
    {
//      digitalWrite(LED_BUILTIN, LOW);
      delay(50);
//      digitalWrite(LED_BUILTIN, HIGH);
      delay(50);
      }
  }
}

void loop() {

//  lps_temp = lps.getTemperatureSensor();
  lps_pressure = lps.getPressureSensor();
  sensors_event_t psr;
//  sensors_event_t tmp;
//  lps_temp->getEvent(&tmp);
  lps_pressure->getEvent(&psr);
  float pressure = psr.pressure;
//  float temperature = tmp.temperature;

//  int DO = readDO();
//  Serial.print("do "); Serial.print(DO);
  Serial.print(" p "); Serial.println(pressure);
//  Serial.print(" t "); Serial.println(temperature);
  delay(500);

}



int readDO() {
  uint16_t val = 0;
  Wire.beginTransmission(DO_ADDR);
  Wire.write(0x01);
  Wire.endTransmission();
  delay(10);
  Wire.requestFrom(DO_ADDR, 0x01);
  delay(10);
  if (Wire.available())
    val = Wire.read();
  Wire.beginTransmission(DO_ADDR);
  Wire.write(0x02);
  Wire.endTransmission();
  delay(10);
  Wire.requestFrom(DO_ADDR, 0x01);
  if (Wire.available())
    val = val | (Wire.read() << 8);
  return val;
}

//void readLPS(){
//  int32_t pressure = 0;
//  int16_t temperature = 0;
//  //enable oneshot measurement
//  Wire.beginTransmission(LPS_ADDR);
//  Wire.write(LPS_CTRL_REG2);
//  Wire.write(0x01);
//  Wire.endTransmission();
//  //wait for measurment
//  uint8_t ctrl_reg2 = 0x01;
//  while (ctrl_reg2 == 0x01){
//    Wire.beginTransmission(LPS_ADDR);
//    Wire.requestFrom(LPS_CTRL_REG2,1);
//    ctrl_reg2 = Wire.read();
//    Serial.println(ctrl_reg2);
//    Wire.endTransmission();
//  }
//  //store measurments
//  Wire.beginTransmission(LPS_ADDR);
//  Wire.requestFrom(LPS_PRES_OUT_XL, 5);
//  pressure = Wire.read() | (Wire.read() << 8) | (Wire.read() << 16);
//  temperature = Wire.read() | (Wire.read() << 8);
//  Wire.endTransmission();
//
////  pressure /= 4096;
////  temperature /= 100;
//  Serial.print(" p "); Serial.print(pressure);
//  Serial.print(" t "); Serial.println(temperature);
//}
