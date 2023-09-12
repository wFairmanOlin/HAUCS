#include "BLEDevice.h"
//#include "BLEScan.h"
#include "TinyGPS++.h"
//#include "heltec.h"
#include<Arduino.h>
#include <RH_RF95.h>
#include <RHReliableDatagram.h>
#define MTU 64

//// BLE Code ////
//BLE Source Code: https://github.com/espressif/arduino-esp32/blob/master/libraries/BLE/examples/BLE_client/BLE_client.ino

static BLEUUID serviceUUID("B1EC");
// The characteristics of the remote service we are interested in.
static BLEUUID    prxUUID("AAAA");
static BLEUUID    ptxUUID("BBBB");
static boolean doConnect = false;
static boolean connected = false;
//static boolean doScan = false;
unsigned long scanTimer = 0;
static BLERemoteCharacteristic* prxChar;
static BLERemoteCharacteristic* ptxChar;
static BLEAdvertisedDevice* myDevice;

uint8_t prx_buffer[MTU];
uint8_t ptx_buffer[MTU];
//uint8_t prev_ptx_buffer[MTU];


int ptxLen = 0;

//// System Variables ////

union Data {
  int i;
  float f;
  uint8_t bytes[4];
};

union Data initPressure, initDO, lat, lng, deg;

int payloadID = 0;
bool requestData = false; //new data requested
bool newData = false;     //new data received
bool sendData = true;    //data should forward over LoRa
uint8_t lora_buffer[128];
unsigned long blinkTimer = 0;

//for HELTEC LORA
#define CLIENT_ADDRESS 11
#define SERVER_ADDRESS 10

#define RFM95_CS 18
#define RFM95_RST 14
#define RFM95_INT 26
#define LED 25
#define BATT_PIN 37
#define RF95_FREQ 915.0

// Singleton instance of the radio driver
RH_RF95 driver(RFM95_CS, RFM95_INT);
// Class to manage message delivery and receipt
RHReliableDatagram manager(driver, CLIENT_ADDRESS);


/**
 * Scan for BLE servers and find the first one that advertises the service we are looking for.
 */
class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
 /**
   * Called for each advertising BLE server (payload).
   */
  void onResult(BLEAdvertisedDevice advertisedDevice) {
    Serial.print("BLE Advertised Device found: ");
    Serial.println(advertisedDevice.toString().c_str());

    // We have found a device, let us now see if it contains the service we are looking for.
    if (advertisedDevice.haveServiceUUID() && advertisedDevice.isAdvertisingService(serviceUUID)) {

      BLEDevice::getScan()->stop();
      myDevice = new BLEAdvertisedDevice(advertisedDevice);
      doConnect = true;
//      doScan = true;
    }
  }
};

/*
 * Called when Payload connects or disconnects
 */
class MyClientCallback : public BLEClientCallbacks {
  void onConnect(BLEClient* pclient) {
    digitalWrite(LED, LOW);
  }

  void onDisconnect(BLEClient* pclient) {
    connected = false;
    //turn on led on disconnect
    digitalWrite(LED, HIGH);
    Serial.println("Payload disconnected");
  }
};

/*
 * Called when trying to establish a connection with the payload.
 */
bool connectToServer() {
    Serial.print("Forming a connection to ");
    Serial.println(myDevice->getAddress().toString().c_str());
    
    BLEClient*  pClient  = BLEDevice::createClient();
    Serial.println(" - Created client");

    pClient->setClientCallbacks(new MyClientCallback());

    // Connect to the remove BLE Server.
    pClient->connect(myDevice);
    Serial.println("- Connected to Server");
    //this is set to 64 on the payload side
    pClient->setMTU(MTU); //set client to request maximum MTU from server (default is 23 otherwise)
    // Obtain a reference to the service we are after in the remote BLE server.
    BLERemoteService* pRemoteService = pClient->getService(serviceUUID);
    if (pRemoteService == nullptr) {
      Serial.print("Failed to find our service UUID: ");
      Serial.println(serviceUUID.toString().c_str());
      pClient->disconnect();
      return false;
    }
    Serial.println(" - Found our service");

    // Obtain a reference to the tx characteristic in the service of the payload.
    ptxChar = pRemoteService->getCharacteristic(ptxUUID);
    if (ptxChar == nullptr) {
      Serial.print("Failed to find our characteristic UUID: ");
      Serial.println(ptxUUID.toString().c_str());
      pClient->disconnect();
      return false;
    }
    Serial.println(" - Found our characteristic");

    if(ptxChar->canNotify())
      ptxChar->registerForNotify(notifyCallback);

      
    // Obtain a reference to the rx characteristic in the service of the payload.
    prxChar = pRemoteService->getCharacteristic(prxUUID);
    if (ptxChar == nullptr) {
      Serial.print("Failed to find our characteristic UUID: ");
      Serial.println(prxUUID.toString().c_str());
      pClient->disconnect();
      return false;
    }
    Serial.println(" - Found our characteristic");

    return true;
}
 
/*
 * Called when payload updates the PTX characteristic
 */
static void notifyCallback(
  BLERemoteCharacteristic* pBLERemoteCharacteristic,
  uint8_t* pData, size_t length, bool isNotify) {
    
    Serial.print("PTX char updated with message length ");
    Serial.println(length);
//    Serial.print("data: ");
    ptxLen = length;
    for (int i = 0; i < length; i++){
      ptx_buffer[i] = *(pData + i);
//      Serial.print(*(pData + i), HEX);
//      Serial.print(" ");
    }
//    Serial.println();
    newData = true;
}

//Use Serial 2 on ESP32 for GPS
TinyGPSPlus gps;
unsigned long gpsTimer = 0;

void setup() {
  Serial.begin(115200);
  delay(2000);
  digitalWrite(LED, HIGH);
  Serial.println("Topside is alive");

  //// BLE ////
  BLEDevice::init("");
  // Retrieve a Scanner and set the callback we want to use to be informed when we
  // have detected a new device.  Specify that we want active scanning and start the
  // scan to run for 5 seconds.
  BLEScan* pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setInterval(1349);
  pBLEScan->setWindow(449);
  pBLEScan->setActiveScan(true);
  pBLEScan->start(5, false);

  //request init data for payload
  requestData = true;
  initPressure.f = 0;
  initDO.f = 0;

  //// GPS ////
  Serial2.begin(9600, SERIAL_8N1, 16, 17);

  //// LORA ////
  pinMode(LED, OUTPUT);
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);
  delay(100);
  
  if (!manager.init())
    Serial.println("init failed");

  /*  MODEM CONFIG IMPORTANT!!!
   *   
   *  Bw125Cr45Sf128   -> Bw = 125 kHz, Cr = 4/5, Sf = 128chips/symbol, CRC on. Default medium range. 
   *  Bw500Cr45Sf128   -> Bw = 500 kHz, Cr = 4/5, Sf = 128chips/symbol, CRC on. Fast+short range. 
   *  Bw31_25Cr48Sf512 -> Bw = 31.25 kHz, Cr = 4/8, Sf = 512chips/symbol, CRC on. Slow+long range.
   *  Bw125Cr48Sf4096  -> Bw = 125 kHz, Cr = 4/8, Sf = 4096chips/symbol, low data rate, CRC on. Slow+long range.
   *  Bw125Cr45Sf2048  -> Bw = 125 kHz, Cr = 4/5, Sf = 2048chips/symbol, CRC on. Slow+long range.
   *  
   *  If data rate is slower, increase timeout below
   */
  manager.setTimeout(5000);
//  driver.setModemConfig(RH_RF95::Bw125Cr45Sf2048);
  driver.setSpreadingFactor(12);
  driver.setSignalBandwidth(125000);
  driver.setFrequency(RF95_FREQ);
  driver.setTxPower(23, false);
}

void loop() {

  //// BLE ////
  
  // doConnect is true then we have scanned for and found the desired Payload
  if (doConnect == true) {
//    doConnect = false;
    if (connectToServer()) {
      doConnect = false;
      connected = true;
      Serial.println("Connected to Payload");
      //ignore if we are already asking for data
      if (!requestData){
        //check if characterisitic has been updated when disconnected
        bool dataUpdated = false;
        std::string value = ptxChar->readValue();
        ptxLen = value.length();
        for (int i = 0; i < ptxLen; i++){
          if (ptx_buffer[i] != value[i])
            dataUpdated = true;
          ptx_buffer[i] = value[i];
        }
        if (dataUpdated){
          Serial.println("Found Data after Disconnect!");
          sendLora();
        }
        else
          Serial.println("Data is the same!");
      }//!requestData
    } //connectToServer 
    else
      Serial.println("Failed to connect to Payload");
  }
  // attempt a rescan every 5 seconds
  else if (!connected){
    
    if ((millis() - scanTimer) > 5000){
      scanTimer = millis();
      BLEScan* pBLEScan = BLEDevice::getScan();
      pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
      pBLEScan->setInterval(1349);
      pBLEScan->setWindow(449);
      pBLEScan->setActiveScan(true);
      pBLEScan->start(1, false);
    }
  }

  //// GPS ////
  
  //read new NMEA messages from GPS
  while (Serial2.available()) {
   gps.encode(Serial2.read());
  }

  if ((millis() - gpsTimer) > 5000){
    gpsTimer = millis();
    displayGPSInfo();
  }

  //// DATA ////
  if (newData) {
    newData = false;
    if (sendData){
      Serial.println("sending data over LoRa ...");
      sendLora();
    }
    else{
      sendData = true;
      if (ptxLen > 11){
        Serial.println("updating initial pressure & DO");
        for (int i = 0; i < 4; i ++) {
          initPressure.bytes[i] = ptx_buffer[i + 2];
        }
        for (int i = 0; i < 2; i ++)
          initDO.bytes[i] = ptx_buffer[i + 10];
      Serial.print("init Pressure: "); Serial.println(initPressure.f);
      Serial.print("      init DO: "); Serial.println(initDO.i);
      }
    }
  }

  if (requestData) {
    if (connected){
      requestData = false;
      sendData = false;
      prxChar->writeValue(0x01, 1);
      Serial.println("data requested from payload");
    }
  }

  //Send Data on button press
  if (digitalRead(0) == 0){
    if (connected){
      Serial.println("Requesting Data");
      prxChar->writeValue(0x03, 1);
      delay(500);
    }
  }
}

/*
 * Called to send LoRa Data Messages
 */
 void sendLora(){

    lat.f = gps.location.lat();
    lng.f = gps.location.lng();
    deg.f = gps.course.deg();

    int loraIdx = 0;
    if (ptxLen > 0){
      lora_buffer[loraIdx++] = ptx_buffer[0];
      lora_buffer[loraIdx++] = ptx_buffer[1] + 20;
      for (int i = 0; i < 4; i ++)
        lora_buffer[loraIdx++] = lat.bytes[i];
      for (int i = 0; i < 4; i ++)
        lora_buffer[loraIdx++] = lng.bytes[i];
      for (int i = 0; i < 4; i ++)
        lora_buffer[loraIdx++] = deg.bytes[i];
      for (int i = 0; i < 4; i ++)
        lora_buffer[loraIdx++] = initPressure.bytes[i];
      for (int i = 0; i < 2; i ++)
        lora_buffer[loraIdx++] = initDO.bytes[i];
    }

    for (int i = 2; i < ptxLen; i ++){
      lora_buffer[loraIdx++] = ptx_buffer[i];
    }

    //Print Message eligibly
    Serial.println("LoRa Message");
    Serial.print("init pressure: "); Serial.println(initPressure.f);
    Serial.print("      init DO: "); Serial.println(initDO.i);
  
    int idx = 2;
    while (idx < ptxLen){
      union Data tempP, tempDO, tempT;
      tempDO.i = 0;
      for (int i = 0; i < 4; i++)
        tempP.bytes[i] = ptx_buffer[idx++];
      for (int i = 0; i < 4; i++)
        tempT.bytes[i] = ptx_buffer[idx++];
      for (int i = 0; i < 2; i++)
        tempDO.bytes[i] = ptx_buffer[idx++];

     Serial.print("     pressure: "); Serial.println(tempP.f);
     Serial.print("  temperature: "); Serial.println(tempT.f);
     Serial.print("           DO: "); Serial.println(tempDO.i);
    }
    
//    Serial.print("LoRa Message: ");
//    for (int i = 0; i < loraIdx; i++){
//      Serial.print(lora_buffer[i], HEX);
//      Serial.print(" ");
//    }
    
    Serial.println();
    if (manager.sendtoWait(lora_buffer, loraIdx, SERVER_ADDRESS)){
      Serial.println("LoRa Message Acknowledged");
      for (int i = 0; i < 50; i++){
        digitalWrite(LED, !digitalRead(LED));
        delay(100);
      }
    }
    else
      Serial.println("LoRa Message Not Received");
}
 
/*
 * Display basic GPS info. Copied form TinyGps++ example.
 */
void displayGPSInfo()
{
  Serial.print(F("Location: ")); 
  if (gps.location.isValid())
  {
    Serial.print(gps.location.lat(), 6);
    Serial.print(F(","));
    Serial.print(gps.location.lng(), 6);
  }
  else
    Serial.print(F("INVALID"));

  Serial.print(F(" Course: ")); 
  if (gps.course.isValid())
    Serial.print(gps.course.deg());
  else
    Serial.print(F("INVALID"));

  Serial.print(F(" Speed: ")); 
  if (gps.speed.isValid())
    Serial.print(gps.speed.mph());
  else
    Serial.print(F("INVALID"));

  Serial.print(F(" NSATS: ")); 
  
  Serial.print(gps.satellites.value());
    
  Serial.print(F("  Date/Time: "));
  if (gps.date.isValid())
  {
    Serial.print(gps.date.month());
    Serial.print(F("/"));
    Serial.print(gps.date.day());
    Serial.print(F("/"));
    Serial.print(gps.date.year());
  }
  else
    Serial.print(F("INVALID"));

  Serial.print(F(" "));
  if (gps.time.isValid())
  {
    if (gps.time.hour() < 10) Serial.print(F("0"));
    Serial.print(gps.time.hour());
    Serial.print(F(":"));
    if (gps.time.minute() < 10) Serial.print(F("0"));
    Serial.print(gps.time.minute());
    Serial.print(F(":"));
    if (gps.time.second() < 10) Serial.print(F("0"));
    Serial.print(gps.time.second());
    Serial.print(F("."));
    if (gps.time.centisecond() < 10) Serial.print(F("0"));
    Serial.print(gps.time.centisecond());
  }
  else
    Serial.print(F("INVALID"));

  Serial.println();
}
