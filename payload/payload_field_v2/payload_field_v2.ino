#include <ArduinoBLE.h>
#include <Adafruit_LPS2X.h>

#define SENSOR_ID 2
#define TEST 0
#define MTU 64

#define PTHRESH 10
#define TRIGGER_INTERVAL 2000
#define SAMPLE_INTERVAL 2000
#define MAX_SAMPLES 3

Adafruit_LPS28 lps;
Adafruit_Sensor *lps_temp, *lps_pressure;

//Payload Service
BLEService payloadService("B1EC");
BLECharacteristic ptxChar("BBBB", BLERead | BLENotify, MTU, 0);
BLECharacteristic prxChar("AAAA", BLERead | BLEWrite, MTU, 0);
bool connected = false;

uint8_t rx_buffer[MTU];
uint8_t tx_buffer[MTU];

bool getSample = false;
bool sendSample = false;

union Data {
  int i;
  float f;
  uint8_t bytes[4];
};

union Data pressure, temperature, DO;
float prev_pressure;
unsigned long triggerTimer = 0;
unsigned long sampleTimer = 0;
unsigned long testTimer = 0;
int numSamples = 0;
int sampleLimit = MAX_SAMPLES;

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("payload is alive");

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

  //// BLE ////
  if (!BLE.begin()){
    Serial.println("Starting BLE failed");
  }
  else
    Serial.println("Started BLE!");
    
  BLE.setLocalName("DO Sensor");
  BLE.setAdvertisedService(payloadService);
  payloadService.addCharacteristic(prxChar);
  payloadService.addCharacteristic(ptxChar);
  BLE.addService(payloadService);
  prxChar.setEventHandler(BLEWritten, rxReceived);
  BLE.advertise();
  Serial.println("BLE Advertising!");

  // set initial values
  pollSensors();
  prev_pressure = pressure.f;
}

void loop() {

  //// BLE ////
  BLEDevice central = BLE.central();
  //true if BLE client is connected
  if (central) {
    if (!connected){
      connected = true;
      Serial.print("Connected to central: ");
      // print the central's BT address:
      Serial.println(central.address());
      digitalWrite(LED_BUILTIN, LOW);
      
    }
  }
  else {
    if (connected){
      connected = false;
      digitalWrite(LED_BUILTIN, HIGH);
      Serial.println("Disconnected from central");
    }
  }

  //// TEST ////
  if (TEST == 1){
    if ( (millis() - testTimer) > 10000){
      testTimer = millis();
      Serial.println("Test Trigger");
      getSample = true;
      sampleLimit = MAX_SAMPLES;
    }
  }
  //// PRESSURE DETECTION ////
  if ( (millis() - triggerTimer) > TRIGGER_INTERVAL ){
    triggerTimer = millis();
    Serial.print("new sample - ");
    pollSensors();
    
    if ( (pressure.f - prev_pressure) > PTHRESH){
      Serial.println("tripped pressure threshold");
      if (!getSample) {
        getSample = true;
        sampleLimit = MAX_SAMPLES;
      }
    }
    else
      Serial.println(pressure.f - prev_pressure);

    prev_pressure = pressure.f;
  }

  if (getSample) {

    if (numSamples >= sampleLimit){
      getSample = false;
      sendSample = true;
      numSamples = 0;
    }
    else if ( (millis() - sampleTimer) > SAMPLE_INTERVAL){
      Serial.println("sampling ...");
      sampleTimer = millis();
      pollSensors();
      int idx = numSamples * 10 + 2;
      for (int i = 0; i < 4; i ++){
        tx_buffer[idx++] = pressure.bytes[i];
      }
      for (int i = 0; i < 4; i ++){
        tx_buffer[idx++] = temperature.bytes[i];
      }
      for (int i = 0; i < 2; i ++){
        tx_buffer[idx++] = DO.bytes[i];
      }
      numSamples ++;
    }
  }

  if (sendSample) {
    if (connected) {
      Serial.print("sending ");
      int msgLen = sampleLimit * 10 + 2;
      Serial.println(msgLen);
      tx_buffer[0] = SENSOR_ID;
      tx_buffer[1] = msgLen;
      ptxChar.writeValue(tx_buffer, msgLen);
      sendSample = false;
    }
  }
}


void pollSensors(){

  lps_temp = lps.getTemperatureSensor();
  lps_pressure = lps.getPressureSensor();
  sensors_event_t psr;
  sensors_event_t tmp;
  lps_temp->getEvent(&tmp);
  lps_pressure->getEvent(&psr);
  pressure.f = psr.pressure;
  temperature.f = tmp.temperature;
  
  int temp_DO = 0;
  for (int i = 0; i < 10; i ++){
    temp_DO += analogRead(A0);
  }
  
  DO.i = temp_DO / 10;
  
}
/*
 * Called when data is written to the prx characteristic
 */
void rxReceived(BLEDevice central, BLECharacteristic characteristic) {

  int rx_len = prxChar.valueLength();
  Serial.println(rx_len);

  if (rx_len > 0){
    prxChar.readValue(rx_buffer, rx_len);
  }

  if (rx_buffer[0] > 0){
    getSample = true;
    sampleLimit = rx_buffer[0];
  }

  Serial.write(rx_buffer, rx_len);
}
