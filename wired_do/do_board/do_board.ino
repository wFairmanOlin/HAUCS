
#include <WIRE_MOD.h>
#define I2C_ADDR 0x09
#define LED A0
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
  pinMode(LED, OUTPUT);
  pinMode(DO, INPUT);
  Wire.begin(I2C_ADDR);
  Wire.onRequest(requestEvent);
  Wire.onReceive(receiveEvent);
  data[0] = 0x02;
  
  for (int i = 0; i < 5; i++){
    digitalWrite(LED, 0);
    delay(50);
    digitalWrite(LED, 1);
    delay(50);
  }
 }

void loop() {
    do_val = analogRead(DO);

    data[1] = do_val & 0xFF;
    data[2] = (do_val >> 8) & 0xFF;
    
    delay(10);

    if (msg_flag){
      msg_flag = false;
      digitalWrite(LED, 1);
    }
    else{
      digitalWrite(LED, 0);
    }
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
