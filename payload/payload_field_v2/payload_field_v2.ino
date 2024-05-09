#include <ArduinoBLE.h>
#include <Adafruit_LPS2X.h>

#define SENSOR_ID 3
#define MTU 64

#define PTHRESH 10
#define P_BUF_SIZE 30
#define TRIGGER_INTERVAL 1000
#define SAMPLE_INTERVAL 10000
#define MAX_SAMPLES 6

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
bool underwater = true;

union Data {
  int i;
  float f;
  uint8_t bytes[4];
};

float p_buf[P_BUF_SIZE];
union Data pressure, temperature, DO;
float *p_buf_start = p_buf;
float avg_amb_p = 0;
unsigned long triggerTimer = 0;
unsigned long sampleTimer = 0;
int numSamples = 0;
int sampleLimit = MAX_SAMPLES;

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("payload is alive");
  digitalWrite(LEDB, LOW);
  

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

  for (int i = 0; i < P_BUF_SIZE; i++){
    pollSensors();
    p_buf[i] = pressure.f;
    delay(50);
  }
  
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
    
  //// PRESSURE DETECTION ////
  if ( (millis() - triggerTimer) > TRIGGER_INTERVAL ){

    //// calcualte average ambient buffer ////
    avg_amb_p = 0;
    for (int i = 0; i < P_BUF_SIZE; i++){
      avg_amb_p += p_buf[i];
    }
    avg_amb_p /= P_BUF_SIZE;
    
    triggerTimer = millis();
    Serial.print("new sample - ");
    pollSensors();

    //// detect if underwater ////
    if ( (pressure.f - avg_amb_p) > PTHRESH){
      Serial.println("tripped pressure threshold");
      if (!getSample) {
        underwater = true;
        getSample = true;
        sampleTimer = millis();
        sampleLimit = MAX_SAMPLES;
      }
    }
    //// must be out of water ////
    else {
      if (underwater){
        Serial.println("detected out of water");
        underwater = false;
      }
      Serial.println(pressure.f - avg_amb_p); 
      memmove( p_buf_start, (p_buf_start + 1) , (P_BUF_SIZE - 1)*4 );
      p_buf[P_BUF_SIZE - 1] = pressure.f;
    }
  }

  if (getSample) {

    // stop sampling if reached limit or out of water
    if ((numSamples >= sampleLimit)){
      getSample = false;
      // only send if data is collected
      if (numSamples > 0)
        sendSample = true;
    }
    // take a sample at every timed interval
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
      int msgLen = numSamples * 10 + 2;
      Serial.println(msgLen);
      tx_buffer[0] = SENSOR_ID;
      tx_buffer[1] = msgLen;
      ptxChar.writeValue(tx_buffer, msgLen);
      sendSample = false;
      numSamples = 0;
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
    delay(100);
    temp_DO += analogRead(A0);
  }
  
  DO.i = temp_DO / 10;
  Serial.print("do "); Serial.println(DO.i);
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
