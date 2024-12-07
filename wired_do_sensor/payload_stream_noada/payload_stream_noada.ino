#include <Arduino.h>
#include <Wire.h>

#define DO_ADDR 0x09
#define LPS_ADDR 0x5D
#define LPS_WHOAMI 0x0F
#define LPS_CTRL_REG2 0x11
#define LPS_PRES_OUT_XL 0x28
#define LPS_TEMP_OUT_L 0x2B

float temperature, pressure;

void setup() {
  Serial.begin(9600);
  Wire.begin();
}

void loop() {

  int DO = readDO();
  readLPS(&temperature, &pressure);
  
  Serial.print("do "); Serial.print(DO);
  Serial.print(" p "); Serial.print(pressure);
  Serial.print(" t "); Serial.println(temperature);
  delay(100);

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

void readLPS(float *t, float *p){
  int32_t pressure = 0;
  int16_t temperature = 0;
  //enable oneshot measurement
  Wire.beginTransmission(LPS_ADDR);
  Wire.write(LPS_CTRL_REG2);
  Wire.write(0x01);
  Wire.endTransmission(true);
  //wait for measurement
  uint8_t ctrl_reg2 = 0x01;
  while (ctrl_reg2 == 0x01){
    Wire.beginTransmission(LPS_ADDR);
    Wire.write(LPS_CTRL_REG2);
    Wire.endTransmission(false);
    Wire.requestFrom(LPS_ADDR,1, true);
    ctrl_reg2 = Wire.read();
  }
  //store measurments
  Wire.beginTransmission(LPS_ADDR);
  Wire.write(LPS_PRES_OUT_XL);
  Wire.endTransmission(false);
  Wire.requestFrom(LPS_ADDR, 5, true);
  pressure = Wire.read() | (Wire.read() << 8) | (Wire.read() << 16);
  temperature = Wire.read() | (Wire.read() << 8);

  *p = pressure / 4096.0; 
  *t = temperature / 100.0;
}
