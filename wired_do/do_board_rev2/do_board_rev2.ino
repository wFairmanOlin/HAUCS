
#include <WIRE_MOD.h>
#include <avr/sleep.h>
#define I2C_ADDR 0x09
#define LED_RED 9
#define LED_GREEN 10
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

int counter = 0;

void setup() {
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(DO, INPUT);
  Wire.begin(I2C_ADDR);
  Wire.onRequest(requestEvent);
  Wire.onReceive(receiveEvent);
  data[0] = 0x02;
  
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
    do_val = analogRead(DO);

    data[1] = do_val & 0xFF;
    data[2] = (do_val >> 8) & 0xFF;
    
    delay(10);

    if (msg_flag){
      counter = 0;
      msg_flag = false;
      digitalWrite(LED_GREEN, 0);
      delay(20);
    }
    else{
      digitalWrite(LED_GREEN, 1);
      digitalWrite(LED_RED, 1);
    }

    if(counter > 200){
      //go to sleep
      set_sleep_mode (SLEEP_MODE_PWR_DOWN);
      sleep_enable();
      digitalWrite(LED_GREEN, LOW);
      digitalWrite(LED_RED, LOW);
      sleep_cpu();
      //wake up
      sleep_disable();
      counter = 0;
      TWCR = bit(TWEN) | bit(TWIE) | bit(TWEA) | bit(TWINT);// release I2C
      Wire.begin(I2C_ADDR);
      counter = 0;
    }
    counter ++;
}

void requestEvent() {
  Wire.write(data[reg_addr]);
}

void receiveEvent(int howMany) {
  msg_flag = true; 
  msg_size = howMany;

  if (howMany == 1)
      reg_addr = Wire.read();
      
  if (reg_addr > 9)
    reg_addr = 9;

  
}
