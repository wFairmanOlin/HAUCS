
#include <WIRE_MOD.h>
#include <avr/sleep.h>
#include <avr/wdt.h>

#define I2C_ADDR 0x09
#define LED_GREEN 10
#define LED_RED 9
#define DO A1

union Data {
  float f;
  uint8_t bytes[4];
};

union Data do_voltage;

int do_val = 0;
uint8_t data[10];
volatile bool msg_flag = false;
volatile int reg_addr = 0;
volatile int msg_size = 0;

void setup() {
  wdt_reset();
  wdt_enable(WDTO_4S);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(DO, INPUT);


  Wire.begin(I2C_ADDR);
  Wire.onRequest(requestEvent);
  Wire.onReceive(receiveEvent);
  data[0] = 0x02;
  
  for (int i = 0; i < 4; i++){
    digitalWrite(LED_GREEN, 1);
    digitalWrite(LED_RED, 1);
    delay(50);
    digitalWrite(LED_GREEN, 0);
    digitalWrite(LED_RED, 0);
    delay(50);
  }
 }

void loop() {
    do_val = analogRead(DO);

    data[1] = do_val & 0xFF;
    data[2] = (do_val >> 8) & 0xFF;
    
    if (msg_flag){
      msg_flag = false;
      digitalWrite(LED_GREEN, 1);
      delay(20);
    }
    else{
      digitalWrite(LED_GREEN, 0);
    }
    delay(10);
}

void requestEvent() {
  wdt_reset();
  Wire.write(data[reg_addr]);
}

void receiveEvent(int howMany) {
  wdt_reset();
  msg_flag = true; 
  msg_size = howMany;

  if (howMany == 1)
      reg_addr = Wire.read();
      
  if (reg_addr > 9)
    reg_addr = 9;  
}
