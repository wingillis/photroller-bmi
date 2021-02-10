#include "sinusoid.h"
#include <Wire.h>

#define DAC_ADDR 0x0C
//#define ADC_ADDR 0x48

volatile uint16_t table_idx1 = 0;
volatile uint16_t table_idx2 = 0;
uint32_t max_samples;
unsigned long sample_hold1;
unsigned long sample_hold2;

struct parameters
{
  uint16_t freq1;
  uint16_t freq2;
  uint16_t amp1;
  uint16_t amp2;
  uint16_t offset1;
  uint16_t offset2;
};

parameters init_parameters;

unsigned long next_update1 = 0;
unsigned long next_update2 = 0;
    
void setup() {

  SerialUSB.begin(2000000);
  
  while(SerialUSB.available() < 1) {
    SerialUSB.println("Waiting for initialization data");
    SerialUSB.println(SerialUSB.available());
    delay(1000);
  }
  
  SerialUSB.println("Data received...");
  read_init_values();

  // LUDICROUS SPEED!
  Wire.begin();
  Wire.setClock(1000000L);
  
  SerialUSB.println(init_parameters.freq1);
  SerialUSB.println(init_parameters.freq2);
  SerialUSB.println(init_parameters.amp1);
  SerialUSB.println(init_parameters.amp2);
  SerialUSB.println(init_parameters.offset1);
  SerialUSB.println(init_parameters.offset2);

  // loop 1 will run sinusoid 1, loop 2 sinusoid 2, loop 3 reading in data...

  max_samples = sizeof(SINE_TABLE) / 2 - 1;
  sample_hold1 = (1.0 / (max_samples * init_parameters.freq1)) * 1e6;
  sample_hold2 = (1.0 / (max_samples * init_parameters.freq2)) * 1e6; 
  
  SerialUSB.println(sample_hold1);
  SerialUSB.println(sample_hold2);

  next_update1 = micros() + sample_hold1;
  next_update2 = micros() + sample_hold2;
  
}

void loop() {
  if (micros() > next_update1) {
    next_update1 = micros() + sample_hold1;
    write_sine1();
  }

  if (micros() > next_update2) {
    next_update2 = micros() + sample_hold2;
    write_sine2();
  }

  if (Serial.available() > 0) {
    read_init_values();
    sample_hold1 = (1.0 / (max_samples * init_parameters.freq1)) * 1e6;
    sample_hold2 = (1.0 / (max_samples * init_parameters.freq2)) * 1e6;
    next_update1 = micros() + sample_hold1;
    next_update2 = micros() + sample_hold2;
  }
}

void read_init_values() {

  // read in everything, pack into a struct to pass back to the main function
  
  // set frequencies

  int i = 0;

  union {
    byte b[2];
    uint16_t val;
  } freq1;
  
  for (i=0; i<2; i++) {
    freq1.b[i] = SerialUSB.read();
  };
  
  union {
    byte b[2];
    uint16_t val;
  } freq2;
  
  for (i=0; i<2; i++) {
    freq2.b[i] = SerialUSB.read();
  }
  
  union {
    byte b[4];
    float val;
  } amp1;
  
  for (i=0; i<4; i++) {
    amp1.b[i] = SerialUSB.read();
  };
  
  // amplitude is passed as a float 0-5, convert to uint16_t
  
  uint16_t amp1_dig  = (amp1.val / 5) * 65535;
  
  union {
    byte b[4];
    float val;
  } amp2;
  
  for (i=0; i<4; i++) {
    amp2.b[i] = SerialUSB.read();
  };
  
  uint16_t amp2_dig = (amp2.val / 5) * 65535;
  
  union {
    byte b[4];
    float val;
  } offset1;
  
  for (i=0; i<4; i++) {
    offset1.b[i] = SerialUSB.read();
  };
  
  uint16_t offset1_dig = (offset1.val / 5) * 65535;
  
  
  union {
    byte b[4];
    float val;
  } offset2;
  
  for (i=0; i<4; i++) {
    offset2.b[i] = SerialUSB.read();
  };
  
  uint16_t offset2_dig = (offset2.val / 5) * 65535;

  init_parameters.freq1 = freq1.val;
  init_parameters.freq2 = freq2.val;
  init_parameters.amp1 = amp1_dig;
  init_parameters.amp2 = amp2_dig;
  init_parameters.offset1 = offset1_dig;
  init_parameters.offset2 = offset2_dig;

}

uint16_t shape_sine(uint16_t val, uint16_t offset, uint16_t amp) {
  uint16_t new_amp = val * (amp - offset) / 65535;
  return new_amp + offset;
}

void write_sine1() {
  uint16_t val = shape_sine(SINE_TABLE[table_idx1]);
  byte lsb = (val / 2 & 0x00FF);
  byte msb = (val / 2 & 0xFF00) >> 8;

  Wire.beginTransmission(DAC_ADDR);

  // DAC address, 48?
  
  Wire.write(0x31);
  Wire.write(msb);
  Wire.write(lsb);
  
  Wire.endTransmission();

  table_idx1++;

  if (table_idx1 == max_samples) {
    table_idx1 = 0;
  }
  
}

void write_sine2() {
  uint16_t val = shape_sine(SINE_TABLE[table_idx2]);
  byte lsb = (val / 2 & 0x00FF);
  byte msb = (val / 2 & 0xFF00) >> 8;

  Wire.beginTransmission(DAC_ADDR);

  // DAC address, 48?
  
  Wire.write(0x32);
  Wire.write(msb);
  Wire.write(lsb);
  
  Wire.endTransmission();

  table_idx2++;

  if (table_idx2 == max_samples) {
    table_idx2 = 0;
  }
  
}
