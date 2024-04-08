//#include "BLEScan.h"
#include "TinyGPS++.h"
//#include "heltec.h"
#include<Arduino.h>
#include <RH_RF95.h>
#include <RHReliableDatagram.h>
#define MTU 64

//// BLE Code ////
//BLE Source Code: https://github.com/espressif/arduino-esp32/blob/master/libraries/BLE/examples/BLE_client/BLE_client.ino

//static boolean doScan = false;
unsigned long scanTimer = 0;


int ptxLen = 0;
 
//// System Variables ////

union Data {
  int i;
  float f;
  uint8_t bytes[4];
};

union Data lat, lng, deg;

int payloadID = 0;
bool requestData = false; //new data requested
bool newData = false;     //new data received
bool sendData = true;    //data should forward over LoRa
uint8_t lora_buffer[128];
unsigned long blinkTimer = 0;

//for HELTEC LORA
#define CLIENT_ADDRESS 11
#define SERVER_ADDRESS 1

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
unsigned long gpsTimer = 0;

void setup() {
  Serial.begin(115200);
  delay(2000);
  digitalWrite(LED, HIGH);
  Serial.println("Topside is alive");

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

  //// GPS ////
  
  //read new NMEA messages from GPS
  while (Serial2.available()) {
   gps.encode(Serial2.read());
  }

  if ((millis() - scanTimer) > 5000){
    scanTimer = millis();
    if (gps.location.isValid())
      sendLora();
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
      for (int i = 0; i < 20; i++){
        digitalWrite(LED, !digitalRead(LED));
        delay(100);
      }
    }
    else
      Serial.println("LoRa Message Not Received");
}
