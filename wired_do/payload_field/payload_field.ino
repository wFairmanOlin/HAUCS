#include <Arduino.h>
#include <bluefruit.h>
#include <Wire.h>

#define SENSOR_ID 4
#define MTU 20

#define PTHRESH 10
#define TRIGGER_INTERVAL 1000
#define SAMPLE_INTERVAL 5000

#define DO_ADDR 0x09
#define LPS_ADDR 0x5D
#define LPS_WHOAMI 0x0F
#define LPS_CTRL_REG2 0x11
#define LPS_PRES_OUT_XL 0x28
#define LPS_TEMP_OUT_L 0x2B

//Payload Service
BLEService payloadService = BLEService("B1EC");
BLECharacteristic ptxChar = BLECharacteristic("BBBB");
BLECharacteristic prxChar = BLECharacteristic("AAAA");
BLEDis bledis;    // DIS (Device Information Service) helper class instance

bool connected = false;

uint8_t rx_buffer[MTU];
uint8_t tx_buffer[MTU];

bool getSample = false;
bool sendSample = false;
bool underwater = true;

union Data {
  int i;
  float f;
  uint8_t bytes[4];
};

union Data pressure, temperature, DO;
float avg_amb_p = 0;
unsigned long triggerTimer = 0;
unsigned long sampleTimer = 0;

void setup() {
  Serial.begin(9600);
  Wire.begin();
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
  Bluefruit.begin();
  Bluefruit.Periph.setConnectCallback(connect_callback);
  Bluefruit.Periph.setDisconnectCallback(disconnect_callback);
  Bluefruit.setTxPower(4);    // Check bluefruit.h for supported values
  Bluefruit.Periph.setConnInterval(9, 24);

  // Configure and Start the Device Information Service
  Serial.println("Configuring the Device Information Service");
  bledis.setManufacturer("HAUCS");
  bledis.setModel("DO Sensor");
  bledis.begin();

  payloadService.begin();
  ptxChar.setProperties(CHR_PROPS_READ | CHR_PROPS_WRITE | CHR_PROPS_NOTIFY);
  ptxChar.setPermission(SECMODE_OPEN, SECMODE_OPEN);
  ptxChar.setMaxLen(MTU);
  ptxChar.begin();
  prxChar.setProperties(CHR_PROPS_READ | CHR_PROPS_WRITE);
  prxChar.setPermission(SECMODE_OPEN, SECMODE_OPEN);
  prxChar.setMaxLen(MTU);
  prxChar.setWriteCallback(rxReceived);
  prxChar.begin();


  startAdv();
  Serial.println("BLE Advertising!");
  pollSensors();
  avg_amb_p = pressure.f;
}

void loop() {
  connected = Bluefruit.connected();

  //// PRESSURE DETECTION ////
  if ( (millis() - triggerTimer) > TRIGGER_INTERVAL ) {

    Serial.print("avg_amb: "); Serial.println(avg_amb_p);

    triggerTimer = millis();
    Serial.print("new sample - ");
    pollSensors();

    //// detect if underwater ////
    if ( (pressure.f - avg_amb_p) > PTHRESH) {
      Serial.println("tripped pressure threshold");
      if (!underwater) {
        underwater = true;
        sampleTimer = millis();
      }
    }
    //// must be out of water ////
    else {
      if (underwater) {
        Serial.println("left water");
        underwater = false;
      }
    }
  }

  // take a sample at every timed interval
  if (underwater){
    if ( (millis() - sampleTimer) > SAMPLE_INTERVAL) {
      Serial.println("sampling ...");
      sendSample = true;
      sampleTimer = millis();
      pollSensors();
      int idx = 0;
      for (int i = 0; i < 4; i ++) {
        tx_buffer[idx++] = pressure.bytes[i];
      }
      for (int i = 0; i < 4; i ++) {
        tx_buffer[idx++] = temperature.bytes[i];
      }
      for (int i = 0; i < 2; i ++) {
        tx_buffer[idx++] = DO.bytes[i];
      }
    }
  }

  if (getSample){
    getSample = false;
    sendSample = true;
    sampleTimer = millis();
    pollSensors();
    int idx = 0;
    for (int i = 0; i < 4; i ++) {
      tx_buffer[idx++] = pressure.bytes[i];
    }
    for (int i = 0; i < 4; i ++) {
      tx_buffer[idx++] = temperature.bytes[i];
    }
    for (int i = 0; i < 2; i ++) {
      tx_buffer[idx++] = DO.bytes[i];
    }
  }

  if (sendSample) {
    Serial.print("sending ");
    int msgLen = 10;
    Serial.println(msgLen);
    ptxChar.notify(tx_buffer, msgLen);
    sendSample = false;
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
  Bluefruit.Advertising.setInterval(32, 244);    // in unit of 0.625 ms
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
    getSample = true;
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
  Serial.println("starting sample");
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
