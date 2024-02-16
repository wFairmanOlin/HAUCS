#include <Wire.h>
#define I2C_ADDR 0x09

int counter = 0;
uint8_t data[10];
volatile bool msg_flag = false;
volatile int reg_addr = 0;
volatile int msg_size = 0;

void setup() {
  Serial.begin(9600);
  Wire1.begin(I2C_ADDR);
  Wire1.onRequest(requestEvent);
  Wire1.onReceive(receiveEvent);
  data[0] = 0x02;
  }

void loop() {
    data[1] = counter & 0xFF;
    data[2] = (counter >> 8) & 0xFF;
    delay(100);
    counter++;

    if (msg_flag){
      msg_flag = false;
      Serial.print("Received Command: ");
      Serial.print(msg_size);
      Serial.print(" "); Serial.println(reg_addr);
    }
    
}

void requestEvent() {
  Serial.print("request event: ");
  Wire1.write(data[reg_addr]);
}

void receiveEvent(int howMany) {
  msg_flag = true; 
  msg_size = howMany;

  if (howMany == 1)
    reg_addr = Wire1.read();

  if (reg_addr > 9)
    reg_addr = 9;
}
