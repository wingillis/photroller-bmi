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
  float amp1;
  float amp2;
  float offset1;
  float offset2;
};

parameters init_parameters;

unsigned long next_update1 = 0;
unsigned long next_update2 = 0;
    
void setup() {

  Serial.begin(115200);
  
  while(Serial.available() < 1) {
  }
  
//  Serial.println("Data received...");
  read_init_values();

  // LUDICROUS SPEED!
  Wire.begin();
  Wire.setClock(1000000L);
  
//  Serial.println(init_parameters.freq1);
//  Serial.println(init_parameters.freq2);
//  Serial.println(init_parameters.amp1);
//  Serial.println(init_parameters.amp2);
//  Serial.println(init_parameters.offset1);
//  Serial.println(init_parameters.offset2);

  // loop 1 will run sinusoid 1, loop 2 sinusoid 2, loop 3 reading in data...

  max_samples = sizeof(SINE_TABLE) / 2 - 1;
  sample_hold1 = (1e6 / ((max_samples + 1) * init_parameters.freq1));
  sample_hold2 = (1e6 / ((max_samples + 1) * init_parameters.freq2)); 
  
//  Serial.println(sample_hold1);
//  Serial.println(sample_hold2);

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
    sample_hold1 = (1e6 / ((max_samples + 1) * init_parameters.freq1));
    sample_hold2 = (1e6 / ((max_samples + 1) * init_parameters.freq2));
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

  Serial.readBytes(freq1.b, 2);
//  Serial.println(freq1.val);
  
  union {
    byte b[2];
    uint16_t val;
  } freq2;
  
  Serial.readBytes(freq2.b, 2);
//  Serial.println(freq2.val);
  
  union {
    byte b[4];
    float val;
  } amp1;
  
  Serial.readBytes(amp1.b, 4);
//  Serial.println(amp1.val);
  
  // amplitude is passed as a float 0-5, convert to uint16_t
  
//  uint16_t amp1_dig  = (amp1.val / 5) * 65535;
  
  union {
    byte b[4];
    float val;
  } amp2;
  
  Serial.readBytes(amp2.b, 4);
//  Serial.println(amp2.val);
  
//  uint16_t amp2_dig = (amp2.val / 5) * 65535;
  
  union {
    byte b[4];
    float val;
  } offset1;
  
  Serial.readBytes(offset1.b, 4);
//  Serial.println(offset1.val);
  
//  uint16_t offset1_dig = (offset1.val / 5) * 65535;
  
  
  union {
    byte b[4];
    float val;
  } offset2;

  Serial.readBytes(offset2.b, 4);
//  Serial.println(offset2.val);
  
//  uint16_t offset2_dig = (offset2.val / 5) * 65535;

  init_parameters.freq1 = freq1.val;
  init_parameters.freq2 = freq2.val;
//  init_parameters.amp1 = amp1_dig;
//  init_parameters.amp2 = amp2_dig;
//  init_parameters.offset1 = offset1_dig;
//  init_parameters.offset2 = offset2_dig;
  init_parameters.amp1 = amp1.val;
  init_parameters.amp2 = amp2.val;
  init_parameters.offset1 = offset1.val;
  init_parameters.offset2 = offset2.val;

}

uint16_t shape_sine(uint16_t val, float offset, float amp) {
  float new_amp = (float) val * (amp - offset) / 5.0;
  return (uint16_t) new_amp + (offset / 5 * 65535);
}

void write_sine1() {
  uint16_t val = shape_sine(SINE_TABLE[table_idx1], init_parameters.offset1, init_parameters.amp1);
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
  uint16_t val = shape_sine(SINE_TABLE[table_idx2], init_parameters.offset2, init_parameters.amp2);
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
