#include <Arduino.h>
#include <bluefruit.h>
#include <Wire.h>

#define BATT A6
#define SENSOR_ID 4
#define MTU 12

#define SAMPLE_INTERVAL 1000

#define DO_ADDR 0x09
#define LPS_ADDR 0x5D
#define LPS_WHOAMI 0x0F
#define LPS_CTRL_REG2 0x11
#define LPS_PRES_OUT_XL 0x28
#define LPS_TEMP_OUT_L 0x2B

//Payload Service
BLEService payloadService = BLEService("B1EC");
BLECharacteristic human = BLECharacteristic("CCCC");
BLECharacteristic ptxChar = BLECharacteristic("BBBB");
BLECharacteristic prxChar = BLECharacteristic("AAAA");
BLEDis bledis;    // DIS (Device Information Service) helper class instance

bool isConnect = false;

uint8_t rx_buffer[MTU];
uint8_t tx_buffer[MTU];
char human_buffer[32] = "hello world";

union Data {
  int i;
  float f;
  uint8_t bytes[4];
};

Data pressure, temperature, DO, initPressure;
unsigned long sampleTimer = 0;

void setup() {
  Serial.begin(9600);
  Wire.begin();
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
  Bluefruit.begin();
  Bluefruit.Periph.setConnectCallback(connect_callback);
  Bluefruit.Periph.setDisconnectCallback(disconnect_callback);
  Bluefruit.setTxPower(8);    // Check bluefruit.h for supported values
  Bluefruit.Periph.setConnInterval(9, 24);

  // Configure and Start the Device Information Service
  Serial.println("Configuring the Device Information Service");
  bledis.setManufacturer("HAUCS");
  bledis.setModel("DO Sensor");
  bledis.begin();
  payloadService.begin();
  human.setProperties(CHR_PROPS_READ | CHR_PROPS_NOTIFY);
  human.setPermission(SECMODE_OPEN, SECMODE_OPEN);
  human.setFixedLen(32);
  human.begin();
  ptxChar.setProperties(CHR_PROPS_READ | CHR_PROPS_WRITE | CHR_PROPS_NOTIFY);
  ptxChar.setPermission(SECMODE_OPEN, SECMODE_OPEN);
  ptxChar.setFixedLen(MTU);
  ptxChar.setCccdWriteCallback(cccd_callback);
  ptxChar.begin();
  prxChar.setProperties(CHR_PROPS_READ | CHR_PROPS_WRITE);
  prxChar.setPermission(SECMODE_OPEN, SECMODE_OPEN);
  prxChar.setFixedLen(MTU);
  prxChar.setWriteCallback(rxReceived);
  prxChar.begin();


  startAdv();
  Serial.println("BLE Advertising!");
}

void loop() {
  isConnect = Bluefruit.connected();

  if (isConnect){
    if ( (millis() - sampleTimer) > SAMPLE_INTERVAL) {
      sampleTimer = millis();
      pollSensors();
      int idx = 1;
      tx_buffer[0] = SENSOR_ID;
      for (int i = 0; i < 4; i ++) {
        tx_buffer[idx++] = pressure.bytes[i];
      }
      for (int i = 0; i < 4; i ++) {
        tx_buffer[idx++] = temperature.bytes[i];
      }
      for (int i = 0; i < 2; i ++) {
        tx_buffer[idx++] = DO.bytes[i];
      }
      Serial.print("sending ");
      int msgLen = 12;
      Serial.println(msgLen);
      ptxChar.notify(tx_buffer, msgLen);
      
      //CAN DELETE
      if (initPressure.f == 0){
        initPressure.f = pressure.f;
      }
      float depth = (pressure.f - initPressure.f) * 39.37 * 0.010227;
      float fahrenheit = temperature.f * 9 / 5 + 32;
      sprintf(human_buffer, "%.2fin %.2fF %.2imV   ", depth, fahrenheit, DO.i);
      human.notify(human_buffer, 32);
    }
  }
}

void startAdv(void) {
  // Advertising packet
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();

  // Include bleuart 128-bit uuid
  Bluefruit.Advertising.addService(payloadService);

  // Secondary Scan Response packet (optional)
  // Since there is no room for 'Name' in Advertising packet
  Bluefruit.ScanResponse.addName();

  /* Start Advertising
     - Enable auto advertising if disconnected
     - Interval:  fast mode = 20 ms, slow mode = 152.5 ms
     - Timeout for fast mode is 30 seconds
     - Start(timeout) with timeout = 0 will advertise forever (until connected)

     For recommended advertising interval
     https://developer.apple.com/library/content/qa/qa1931/_index.html
  */
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 2056);    // in unit of 0.625 ms
  Bluefruit.Advertising.setFastTimeout(30);      // number of seconds in fast mode
  Bluefruit.Advertising.start(0);                // 0 = Don't stop advertising after n seconds
}

void pollSensors() {
  float temp_p, temp_t;
  readLPS(&temperature.f, &pressure.f);
//  pressure.f = temp_p;
//  temperature.f = temp_t; 
  DO.i = readDO();
  Serial.print("p "); Serial.print(pressure.f);
  Serial.print(" t "); Serial.print(temperature.f);
  Serial.print(" do "); Serial.println(DO.i);
}
/*
   Called when data is written to the prx characteristic
*/
void rxReceived(uint16_t conn_hdl, BLECharacteristic* chr, uint8_t* data, uint16_t len) {

  int rx_len = len;
  Serial.println(rx_len);

  if (rx_len > 0) {
    memcpy(&rx_buffer, data, len);
  }

  if (rx_buffer[0] > 0) {
    Serial.print("command received: ");
  }

  Serial.write(rx_buffer, rx_len);
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


void readLPS(float *t, float *p) {
  int32_t pressure = 0;
  int16_t temperature = 0;
  //enable oneshot measurement
  Wire.beginTransmission(LPS_ADDR);
  Wire.write(LPS_CTRL_REG2);
  Wire.write(0x01);
  Wire.endTransmission(true);
  //wait for measurement
  uint8_t ctrl_reg2 = 0x01;
  while (ctrl_reg2 == 0x01) {
    Wire.beginTransmission(LPS_ADDR);
    Wire.write(LPS_CTRL_REG2);
    Wire.endTransmission(false);
    Wire.requestFrom(LPS_ADDR, 1, true);
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

void connect_callback(uint16_t conn_handle)
{
  // Get the reference to current connection
  BLEConnection* connection = Bluefruit.Connection(conn_handle);

  char central_name[32] = { 0 };
  connection->getPeerName(central_name, sizeof(central_name));

  Serial.print("Connected to ");
  Serial.println(central_name);
}

/**
 * Callback invoked when a connection is dropped
 * @param conn_handle connection where this event happens
 * @param reason is a BLE_HCI_STATUS_CODE which can be found in ble_hci.h
 */
void disconnect_callback(uint16_t conn_handle, uint8_t reason)
{
  (void) conn_handle;
  (void) reason;

  Serial.print("Disconnected, reason = 0x"); Serial.println(reason, HEX);
  Serial.println("Advertising!");
}



void cccd_callback(uint16_t conn_hdl, BLECharacteristic* chr, uint16_t cccd_value)
{
    // Display the raw request packet
    Serial.print("CCCD Updated: ");
    //Serial.printBuffer(request->data, request->len);
    Serial.print(cccd_value);
    Serial.println("");

    // Check the characteristic this CCCD update is associated with in case
    // this handler is used for multiple CCCD records.
    if (chr->uuid == ptxChar.uuid) {
        if (chr->notifyEnabled(conn_hdl)) {
            Serial.println("payload 'Notify' enabled");
        } else {
            Serial.println("payload 'Notify' disabled");
        }
    }
}
