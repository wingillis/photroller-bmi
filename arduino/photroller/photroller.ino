#include "sinusoid.h"

uint16_t table_idx1 = 0;
uint16_t table_idx2 = 0;
uint32_t start_time1 = 0;
uint32_t start_time2 = 0;
float sample_hold1
float sample_hold2

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
    
void setup() {
  
  Serial.begin(115200);
  SerialUSB.begin(2000000);
  // while(!SerialUSB); // wait until we get a connect up in here
   if (SerialUSB.available() >= 36) {
    SerialUSB.println('Data received...');
    read_init_values();
    SerialUSB.println(init_parameters.freq1);
    SerialUSB.println(init_parameters.freq2);
    SerialUSB.println(init_parameters.amp1);
    SerialUSB.println(init_parameters.amp2);
    SerialUSB.println(init_parameters.offset1);
    SerialUSB.println(init_parameters.offset2);
  }
  else {
    SerialUSB.println('Waiting for initialization data');
    delay(1000);
    return;
  }

  // loop 1 will run sinusoid 1, loop 2 sinusoid 2, loop 3 reading in data...

  sample_hold1 = (1 / (MAX_SAMPLES * init_parameters.freq1)) * 1e6;
  sample_hold2 = (1 / (MAX_SAMPLES * init_parameters.freq2)) * 1e6;  
  
  Scheduler.startLoop(loop2);
  
}

void loop() {

  // Serial.println(SINE_TABLE[table_idx]);

  // wait for command to be send over standard USB port specifying freqs..., then start the loop

  // so 
  // 1) read in frequencies, offsets, and amplitudes
  // 2) generate sinusoids continuously
  // 3) read in adc data and pipe out to dedicated USB port
  // 4) python program will stop everything


//  SerialUSB.println(SINE_TABLE[table_idx]);
//  
  table_idx1++;

  if (table_idx1 == MAX_SAMPLES) {
    table_idx1 = 0;
  }

  start_time = micros();
  while(micros() - start_time < sample_hold1);

  // by default pipe out to DAC0

}

void loop2() {

  table_idx2++;

  if (table_idx2 == MAX_SAMPLES) {
    table_idx2 = 0;
  }

  start_time = micros();
  while(micros() - start_time < sample_hold2);

  // by default pipe out to DAC1
   
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
    byte b[8];
    float val;
  } amp1;
  
  for (i=0; i<8; i++) {
    amp1.b[i] = SerialUSB.read();
  };
  
  // amplitude is passed as a float 0-5, convert to uint16_t
  
  uint16_t amp1_dig  = (amp1.val / 5) * 65535;
  
  union {
    byte b[8];
    float val;
  } amp2;
  
  for (i=0; i<8; i++) {
    amp2.b[i] = SerialUSB.read();
  };
  
  uint16_t amp2_dig = (amp2.val / 5) * 65535;
  
  union {
    byte b[8];
    float val;
  } offset1;
  
  for (i=0; i<8; i++) {
    offset1.b[i] = SerialUSB.read();
  };
  
  uint16_t offset1_dig = (offset1.val / 5) * 65535;
  
  
  union {
    byte b[8];
    float val;
  } offset2;
  
  for (i=0; i<8; i++) {
    offset2.b[i] = SerialUSB.read();
  };
  
  uint16_t offset2_dig = (offset2.val / 5) * 65535;

  init_parameters.freq1 = freq1.val;
  init_parameters.freq2 = freq2.val;
  init_parameters.amp1 = amp1.val;
  init_parameters.amp2 = amp2.val;
  init_parameters.offset1 = offset1.val;
  init_parameters.offset2 = offset2.val;

}

