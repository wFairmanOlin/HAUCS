#include <Wire.h>
//#include <WIRE_MOD.h>
#define I2C_ADDR 0x09
#define LED_RED 9
#define LED_GREEN 10
#define DO A1

#define SAMPLE_MS 100

int do_val = 0;
uint8_t data[10];
volatile bool receive_flag = false;
volatile bool request_flag = false;

unsigned long led_counter = millis();
unsigned long sample_counter = millis();

void setup() {
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(DO, INPUT);
  Wire.begin(I2C_ADDR);
  Wire.setTimeout(0);
  Wire.onRequest(requestEvent);
  Wire.onReceive(receiveEvent);
  
  for (int i = 0; i < 5; i++){
    digitalWrite(LED_RED, 0);
    digitalWrite(LED_GREEN, 0);
    delay(50);
    digitalWrite(LED_RED, 1);
    digitalWrite(LED_GREEN, 1);
    delay(50);
  }
 }

void loop() {
    //handle sampling
    delay(10);
    int temp_do = analogRead(DO);
    if (temp_do > 2)
    {
      do_val = (9 * do_val + temp_do)/10;
    }
    if ( (millis() - sample_counter) >  SAMPLE_MS)
    {
      data[0] = do_val & 0xFF;
      data[1] = (do_val >> 8) & 0xFF;
    }

    //handle messaging
    if (receive_flag){
      led_counter = millis();
      receive_flag = false;
      digitalWrite(LED_GREEN, 0);
    }
    if (request_flag){
      led_counter = millis();
      request_flag = false;
      digitalWrite(LED_RED, 0);
    }
    
    if ((millis() - led_counter) > 50)
    {
      digitalWrite(LED_GREEN, 1); 
      digitalWrite(LED_RED, 1);
    }
}

void requestEvent() {
  request_flag = true;
//  Wire.write(data[0]);
  Wire.write(&data[0],2);
}

void receiveEvent(int howMany) {
  receive_flag = true;
  while (Wire.available()){
    Wire.read();
  }
}
