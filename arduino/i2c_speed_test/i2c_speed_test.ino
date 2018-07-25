#include <Wire.h>

uint32_t start_time;
byte lsb;
byte msb;
#define DAC_ADDR 0x0C
#define ADC_ADDR 0x48

void setup() {
  SerialUSB.begin(2000000);
  Wire.begin();
  Wire.setClock(1000000L);
}

void loop() {

  uint16_t hi = 60000;
  uint16_t lo = 0;

  byte lsb = (hi & 0x00FF);
  byte msb = (hi & 0xFF00) >> 8;

  start_time = micros();
  
  Wire.beginTransmission(DAC_ADDR);

  // DAC address, 48?
  
  Wire.write(49);
  Wire.write(msb);
  
  if (lsb >= 0) {
    Wire.write(lsb);
  }
  
  Wire.endTransmission();
  SerialUSB.println(micros() - start_time);

  lsb = (lo & 0x00FF);
  msb = (lo & 0xFF00) >> 8;

  Wire.beginTransmission(DAC_ADDR);
  
  Wire.write(49);
  Wire.write(msb);
  
  if (lsb >= 0) {
    Wire.write(lsb);
  }
  
  Wire.endTransmission();

  SerialUSB.println(micros() - start_time);
  delay(1000);
  
}
