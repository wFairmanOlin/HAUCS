#include "BLEDevice.h"
//#include "BLEScan.h"
#include "TinyGPS++.h"
//#include "heltec.h"
#include<Arduino.h>


//// BLE Code ////
//BLE Source Code: https://github.com/espressif/arduino-esp32/blob/master/libraries/BLE/examples/BLE_client/BLE_client.ino

static BLEUUID serviceUUID("B1EC");
// The characteristics of the remote service we are interested in.
static BLEUUID    prxUUID("AAAA");
static BLEUUID    ptxUUID("BBBB");
static boolean doConnect = false;
static boolean connected = false;
static boolean doScan = false;
unsigned long scanTimer = 0;
static BLERemoteCharacteristic* prxChar;
static BLERemoteCharacteristic* ptxChar;
static BLEAdvertisedDevice* myDevice;

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
      doScan = true;
    }
  }
};

/*
 * Called when Payload connects or disconnects
 */
class MyClientCallback : public BLEClientCallbacks {
  void onConnect(BLEClient* pclient) {
  }

  void onDisconnect(BLEClient* pclient) {
    connected = false;
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
    pClient->setMTU(64); //set client to request maximum MTU from server (default is 23 otherwise)
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

    connected = true;
    return true;
}
 
/*
 * Called when payload updates the RX characteristic
 */
static void notifyCallback(
  BLERemoteCharacteristic* pBLERemoteCharacteristic,
  uint8_t* pData,
  size_t length,
  bool isNotify) {
    Serial.print("Notify callback for characteristic ");
    Serial.print(pBLERemoteCharacteristic->getUUID().toString().c_str());
    Serial.print(" of data length ");
    Serial.println(length);
    Serial.print("data: ");
    Serial.write(pData, length);
    Serial.println();
}

//Use Serial 2 on ESP32 for GPS
TinyGPSPlus gps;
unsigned long gpsTimer = 0;

void setup() {
  Serial.begin(115200);
  delay(2000);
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

  //// GPS ////
  Serial2.begin(9600, SERIAL_8N1, 16, 17);

}

void loop() {

  //// BLE ////
  
  // doConnect is true then we have scanned for and found the desired Payload
  if (doConnect == true) {
    if (connectToServer()) {
      Serial.println("Connected to Payload");
    } else {
      Serial.println("Failed to connect to Payload");
    }
    doConnect = false;
  }
  // attempt a rescan every 5 seconds
  else if (doScan){
    if ((millis() - scanTimer) > 5000){
      scanTimer = millis();
      BLEDevice::getScan()->start(0);
    }
  }

  //// GPS ////
  
  //read new NMEA messages from GPS
  while (Serial2.available()) {
   gps.encode(Serial2.read());
  }

  if ((millis() - gpsTimer) > 5000){
    displayGPSInfo();
  }
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
  {
    Serial.print(F("INVALID"));
  }

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
  {
    Serial.print(F("INVALID"));
  }

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
  {
    Serial.print(F("INVALID"));
  }

  Serial.println();
}
