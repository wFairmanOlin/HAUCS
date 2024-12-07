#include "BLEDevice.h"
#include "TinyGPS++.h"
#include<Arduino.h>
#include <RH_RF95.h>
#include <RHReliableDatagram.h>

#define MTU 12
#define PRESSURE_OFFSET 9

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
uint8_t payload_data[(MTU - 2) * 2];
int pdata_idx = 0; 

//// System Variables ////

union Data {
  int i;
  float f;
  uint8_t bytes[4];
};

union Data initPressure, initDO, lat, lng, deg;

int payloadID = 0;
bool newData = false;     //new data received
bool sendData = false;    //data should forward over LoRa
bool sentData = false;    //controls white LED
bool underwater = false;
bool sendGPS = false;
unsigned long dataTimer = 0;
uint8_t lora_buffer[128];
unsigned long gpsTimer = 0;

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


//Use Serial 2 on ESP32 for GPS
TinyGPSPlus gps;

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

void setup() {
  Serial.begin(115200);
  digitalWrite(LED, HIGH);
  Serial.println("Topside is alive");

  //// reset initial values ////
  initPressure.f = 0;
  initDO.f = 0;

  //// BLE ////
  BLEDevice::init("");
  startScan();
  
  //// GPS ////
  Serial2.begin(9600, SERIAL_8N1, 16, 17);

  //// LORA ////
  pinMode(LED, OUTPUT);
  pinMode(RFM95_RST, OUTPUT);
  digitalWrite(RFM95_RST, HIGH);
  delay(100);
  
  if (!manager.init())
    Serial.println("init failed");
    
  manager.setTimeout(5000);
  driver.setSpreadingFactor(12);
  driver.setSignalBandwidth(125000);
  driver.setFrequency(RF95_FREQ);
  driver.setTxPower(23, false);
}

void loop() {

  //// BLE ////
  // doConnect is true then we have scanned for and found the desired Payload
  if (doConnect == true) {
    if (connectToServer()) {
      doConnect = false;
      connected = true;
      Serial.println("Connected to Payload");
    } //connectToServer 
    else
      Serial.println("Failed to connect to Payload");
  }
  // attempt a rescan every 5 seconds
  else if (!connected){
    if ((millis() - scanTimer) > 5000){
      scanTimer = millis();
      startScan();
    }
  }

  //// GPS ////
  while (Serial2.available()) {
   gps.encode(Serial2.read());
  }

  //// SEND DATA IF BUFFER FILLED ////
  if (pdata_idx >= sizeof(payload_data)){
    sendData = true;
    pdata_idx = 0;
  }
  // otherwise collect data
  else{
    //// DATA ////
    if (newData) {
      newData = false;
      
      //handle startup case
      if (initPressure.f == 0){
        payloadID = ptx_buffer[0];
        memcpy(&initPressure, &ptx_buffer[1], 4);
        memcpy(&initDO, &ptx_buffer[9], 2);
      }
      //handle normal case
      else{
        Data currentPressure;
        memcpy(&currentPressure, &ptx_buffer[1], 4);
        //only sample if payload is underwater
        if (currentPressure.f > (initPressure.f + PRESSURE_OFFSET)){
          //reset data timer if just entered water
          if (!underwater){
            underwater = true;
            dataTimer = millis();
          }
          //record sample every 5 seconds
          if ( (millis() - dataTimer) > 5000){
            Serial.println("recording");
            dataTimer = millis();
            memcpy(&payload_data[pdata_idx], &ptx_buffer[1], 10); 
            pdata_idx += 10;
          }// data timer
        }//underwater
        else{
          //handle first instance out of water
          if (underwater){
            digitalWrite(LED, 0);
          }
          underwater = false;
        }//not underwater;
      }//not startup
    }//new data
  }//data buff not full

  //throw out incomplete data
  if (((millis() - dataTimer) > 15000) && (pdata_idx != 0)){
    dataTimer = millis();
    Serial.println("stale data ... cleared pdata");
    pdata_idx = 0;
  }
  
  if (sendData){
    sendData = false;
    Serial.println("sending data over LoRa ...");
    sendLora();
  } 

  if (sendGPS){
    if (millis() - gpsTimer > 5000){
      gpsTimer = millis();
      if (gps.location.isValid()){
        displayGPSInfo();
        sendGPSLora();
      }
    }
  }
  
  //Send Data on button press
  if (digitalRead(0) == 0){
    digitalWrite(LED, HIGH);
    delay(500);
    digitalWrite(LED, LOW);
    sendGPS = !sendGPS;
    Serial.print("send gps ");
    Serial.println(sendGPS);
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
    lora_buffer[loraIdx++] = payloadID;
    lora_buffer[loraIdx++] = sizeof(payload_data) + 1 + 14;
    for (int i = 0; i < 4; i ++)
      lora_buffer[loraIdx++] = lat.bytes[i];
    for (int i = 0; i < 4; i ++)
      lora_buffer[loraIdx++] = lng.bytes[i];
    for (int i = 0; i < 4; i ++)
      lora_buffer[loraIdx++] = initPressure.bytes[i];
    for (int i = 0; i < 2; i ++)
      lora_buffer[loraIdx++] = initDO.bytes[i];

    memcpy(&lora_buffer[loraIdx], &payload_data[0], sizeof(payload_data));
    loraIdx += sizeof(payload_data);

    if (manager.sendtoWait(lora_buffer, loraIdx, SERVER_ADDRESS)){
      Serial.println("LoRa Message Acknowledged");
      for (int i = 0; i < 10; i++){
        digitalWrite(LED, !digitalRead(LED));
        delay(100);
      }
      digitalWrite(LED, 1);
    }
    else
      Serial.println("LoRa Message Not Received");
}

void sendGPSLora(){

    lat.f = gps.location.lat();
    lng.f = gps.location.lng();

    int loraIdx = 0;
    
    lora_buffer[loraIdx++] = 44;
    for (int i = 0; i < 4; i ++)
      lora_buffer[loraIdx++] = lat.bytes[i];
    for (int i = 0; i < 4; i ++)
      lora_buffer[loraIdx++] = lng.bytes[i];

    Serial.print("LoRa Message: ");
    for (int i = 0; i < loraIdx; i++){
      Serial.print(lora_buffer[i], HEX);
      Serial.print(" ");
    }
    Serial.println();
    if (manager.sendtoWait(lora_buffer, loraIdx, SERVER_ADDRESS)){
      Serial.println("LoRa Message Acknowledged");
      for (int i = 0; i < 10; i++){
        digitalWrite(LED, !digitalRead(LED));
        delay(100);
      }
    }
    else
      Serial.println("LoRa Message Not Received");
}

/*
 * Called when payload updates the PTX characteristic
 */
static void notifyCallback(
  BLERemoteCharacteristic* pBLERemoteCharacteristic,
  uint8_t* pData, size_t length, bool isNotify) {
    
  for (int i = 0; i < length; i++){
    ptx_buffer[i] = *(pData + i);
  }
  newData = true;
}

/**
 * Setup Scan
 */
void startScan(){
    BLEScan* pBLEScan = BLEDevice::getScan();
    pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
    pBLEScan->setInterval(1349);
    pBLEScan->setWindow(449);
    pBLEScan->setActiveScan(true);
    pBLEScan->start(1, false);
}

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
