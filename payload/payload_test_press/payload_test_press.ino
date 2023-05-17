#include <ArduinoBLE.h>
#include <Adafruit_LPS2X.h>
#define DO_PIN A0

Adafruit_LPS28 lps;
Adafruit_Sensor *lps_temp, *lps_pressure;


/////////////// Payload Service /////////////////////////////
BLEService payloadService("4fafc201-1fb5-459e-8fcc-c5c9c331914b");

BLEByteCharacteristic cmdChar("000C", BLERead | BLEWrite | BLENotify);
BLEByteCharacteristic calChar("CA11", BLERead | BLEWrite);
BLEByteCharacteristic sensChar("5E00", BLERead | BLEWrite);
BLECharacteristic payloadChar1("0001", BLERead | BLENotify | BLEWrite, 31, 0);
BLECharacteristic payloadChar2("0002", BLERead | BLENotify | BLEWrite, 31, 0);
BLECharacteristic payloadChar3("0003", BLERead | BLENotify | BLEWrite, 31, 0);

bool centralChk = false;
bool disconnectChk = false;

long previousMillis = 0;  // last time the battery level was checked, in ms
float psr;
float tem;
int initial_DO = -1;

//////////////// SAMPLING PARAMETERS ///////////////////////
int numSamples = 3;
unsigned long firstSampleDelay = 30000; //30 second initial delay
unsigned long samplingTimeMax = 10000; //10 second duration
/////////////// SAMPLING VARIABLES ////////////////////////
unsigned long samplingTime = 0;
int sampleState = 0;
char sdata[30]; int sid = 0;

///////////////////////////////////////////////////////////

/*
 * Start Sequence
 */
void setup() {
  Serial.begin(9600);
  delay(1000);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.println("Adafruit LPS2X test!");

  if (!lps.begin_I2C()) {
    Serial.println("Failed to find LPS2X chip");
    for (int i = 0; i < 100; i ++)
    {
      digitalWrite(LED_BUILTIN, LOW); delay(50);
      digitalWrite(LED_BUILTIN, HIGH);delay(50);
    }
  }
  Serial.println("LPS2X Found!");

  //Initial DO
  initial_DO = analogRead(DO_PIN);
  
  lps_temp = lps.getTemperatureSensor();
  lps_pressure = lps.getPressureSensor();
  
  if (!BLE.begin()) {
    Serial.println("starting BLE failed!");
    delay(1000);
    while (1);
  }
  Serial.println("starting BLE:");

  BLE.setLocalName("sensorMonitor");
  BLE.setAdvertisedService(payloadService); // add the service UUID
  payloadService.addCharacteristic(cmdChar);
  payloadService.addCharacteristic(payloadChar1);
  payloadService.addCharacteristic(payloadChar2);
  payloadService.addCharacteristic(payloadChar3);
  payloadService.addCharacteristic(calChar);
  payloadService.addCharacteristic(sensChar);
      
  BLE.addService(payloadService); // Add the battery service
  cmdChar.setEventHandler(BLEWritten, cmdCharWritten);
  calChar.writeValue(0);
  calChar.setEventHandler(BLEWritten, calCharWritten);
  cmdChar.writeValue(0); // set initial value for this characteristic
  sensChar.setEventHandler(BLEWritten, sensCharWritten);

  int registers[3][32] = {};
  
  // start advertising
  BLE.advertise();
  Serial.println("Bluetooth® device active, waiting for connections...");
}


void updateSensorData(int sampleState) {
  // update sensor data
  // ...
}

BLEByteCharacteristic triggerChar("000D", BLERead | BLEWrite | BLENotify);

void cmdCharWritten(BLEDevice central, BLECharacteristic characteristic) {
  // central wrote new value to characteristic, update LED
  Serial.print("Characteristic event, written");
  //handle sampling request
  if (cmdChar.value() == 1){
    cmdChar.writeValue(0);
    sampleState = 1; 
    samplingTime = millis();
  }
  else if (triggerChar.value() == 1){
    // send sensor data to topside
    updateSensorData(sampleState);
  }
}

void calCharWritten(BLEDevice central, BLECharacteristic characteristic) {
  // central wrote new value to characteristic, update LED
  Serial.print("Characteristic event, written");
  //handle calibration request
  if (calChar.value() == 1){
    calChar.writeValue(0);
  }
}

void sensCharWritten(BLEDevice central, BLECharacteristic characteristic) {
  // central wrote new value to characteristic, update LED
  Serial.print("Characteristic event, written");
  //handle sensor data request
  if (sensChar.value() == 1){
    // send sensor data to topside
    updateSensorData(sampleState);
  }
}


void loop() {
  // wait for a Bluetooth® Low Energy central
  BLEDevice central = BLE.central();
  // if a central is connected to the peripheral:
  if (central) {
    if (centralChk == false)
    {
      Serial.print("Connected to central: ");
      // print the central's BT address:
      Serial.println(central.address());
      digitalWrite(LED_BUILTIN, LOW);
    }
    centralChk = true;
    disconnectChk = false;

  }
  else
  {
    // when the central disconnects, turn off the LED:
    if (disconnectChk == false)
    {
      Serial.print("Disconnected from central: ");
      Serial.println(central.address());
      centralChk = false;
      digitalWrite(LED_BUILTIN, HIGH);
    }
    disconnectChk = true;
  }
  
  ////////////////// Handle Sampling //////////////////
  if ((sampleState <= numSamples) && (sampleState > 0)) {
    if (sampleState == 1){
      if((millis() - samplingTime) > firstSampleDelay){
        samplingTime = millis();
        updateSensorData(sampleState);
        sampleState += 1;
      }
    }
    else{
      if((millis() - samplingTime) > samplingTimeMax){
        samplingTime = millis();
        updateSensorData(sampleState); 
        sampleState += 1;
        }
    }
    }
  
  // check for trigger from topside
  if (triggerChar.value() == 1){
    // send sensor data to topside
    updateSensorData(sampleState);
    // ...
  }
  
  // check for commands from topside
  if (cmdChar.value() == 1){
    cmdCharWritten(central, cmdChar);
    // handle command
    // ...
  }
  
  // check for calibration requests from topside
  if (calChar.value() == 1){
    calCharWritten(central, calChar);
    // handle calibration request
    // ...
  }

  // check for sensor data requests from topside
  if (sensChar.value() == 1){
    sensCharWritten(central, sensChar);
    // handle sensor data request
    // ...
  }
}
