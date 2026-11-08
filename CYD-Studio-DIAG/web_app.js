(()=>{
'use strict';
const $=id=>document.getElementById(id),cv=$('canvas'),ctx=cv.getContext('2d');
const palettes=['#2381b1','#9b66de','#e59645','#329c76','#c45d89'];
const presets={
 cyd28:{label:'CYD 2.8 R · 1 USB',screen:true,wifi:true,bt:true,desc:'ILI9341 · XPT2046',connectors:[
   ['P1 · UART / ZASILANIE',[['1','VIN · zasilanie'],['2','GPIO1 · TX0 (USB UART)'],['3','GPIO3 · RX0 (USB UART)'],['4','GND']]],
   ['P3 · GPIO',[['1','GND'],['2','GPIO35 · wejście ADC1, tylko INPUT'],['3','GPIO22 · I2C SCL / CN1'],['4','GPIO21 · zajęty przez BL LCD']]],
   ['CN1 · GPIO / I2C',[['1','GND'],['2','GPIO22 · I2C SCL / P3'],['3','GPIO27 · I2C SDA'],['4','3.3 V']]],
   ['P4 · GŁOŚNIK',[['A','wyjście wzmacniacza audio'],['B','wyjście wzmacniacza audio'],['GPIO','26 · wejście wzmacniacza DAC2']]],
   ['LCD · SPI',[['SCLK','GPIO14'],['MOSI','GPIO13'],['MISO','GPIO12'],['CS','GPIO15'],['DC','GPIO2'],['BL','GPIO21']]],
   ['DOTYK · XPT2046',[['CLK','GPIO25'],['MOSI','GPIO32'],['MISO','GPIO39 (INPUT)'],['CS','GPIO33'],['IRQ','GPIO36 (INPUT)']]],
   ['microSD',[['SCLK','GPIO18'],['MOSI','GPIO23'],['MISO','GPIO19'],['CS','GPIO5']]],
   ['INNE',[['RGB','GPIO4/16/17 (aktywne LOW)'],['LDR','GPIO34 · wejście ADC1'],['BOOT','GPIO0'],['RESET','EN']]]]},
 cyd24:{label:'CYD 2.4 R',screen:true,wifi:true,bt:true,desc:'ILI9341 · XPT2046',connectors:[
  ['LCD SPI',[['MOSI','GPIO13'],['MISO','GPIO12'],['SCLK','GPIO14'],['CS','GPIO15'],['DC','GPIO2'],['BL','GPIO27']]],
  ['DOTYK SPI (sprawdź rewizję)',[['CLK','GPIO14'],['MOSI','GPIO13'],['MISO','GPIO12'],['CS','GPIO33'],['IRQ','GPIO36']]],
  ['microSD',[['CS','GPIO5'],['SCLK','GPIO18'],['MOSI','GPIO23'],['MISO','GPIO19']]],
  ['ZŁĄCZA',[['GPIO','Zależą od rewizji CYD 2.4'],['UWAGA','GPIO27 użyte przez BL · nie używaj jako I2C SDA']]]]},
 cyd28t:{label:'CYD 2.8 T',screen:true,wifi:true,bt:true,desc:'LCD · dotyk wymaga identyfikacji',connectors:[
  ['LCD SPI',[['SCLK','GPIO14'],['MOSI','GPIO13'],['CS','GPIO15'],['DC','GPIO2'],['BL','GPIO21']]],
  ['DOTYK',[['UWAGA','Wariant T może mieć inny sterownik dotyku; generator nie aktywuje dotyku do jego weryfikacji']]],
  ['microSD',[['CS','GPIO5'],['SCLK','GPIO18'],['MOSI','GPIO23'],['MISO','GPIO19']]],
  ['P1 / P3 / CN1 / P4',[['UWAGA','Sprawdź faktyczne oznaczenia na PCB przed podłączeniem']]]]},
 atom:{label:'M5 ATOM Lite',screen:false,wifi:true,bt:true,desc:'ESP32 · node bez LCD',connectors:[
  ['GROVE 4 PIN',[['1','GND'],['2','5V'],['3','GPIO26'],['4','GPIO32']]],
  ['GROVE I2C',[['SCL','GPIO21'],['SDA','GPIO25']]],
  ['PINS',[['I/O','GPIO19,21,22,23,25,33'],['RGB','GPIO27'],['BUTTON','GPIO39'],['IR','GPIO12']]],
  ['USB',[['ZASILANIE','USB-C 5V'],['PROGRAMOWANIE','USB UART']]]]},
 cardputeradv:{label:'M5Stack Cardputer ADV',screen:true,wifi:true,bt:false,desc:'Stamp-S3A · ST7789V2 240×135 · TCA8418 · ES8311 · BMI270',connectors:[
  ['GROVE HY2.0-4P',[['BLACK','GND'],['RED','5 V'],['YELLOW','GPIO2'],['WHITE','GPIO1']]],
  ['EXT 14-pin',[['1','GPIO3 / RESET'],['2','5 VIN'],['3','GPIO4 / INT'],['4','GND'],['5','GPIO6 / BUSY'],['6','5 V OUT'],['7','GPIO40 / SPI SCK'],['8','GPIO8 / I2C SDA'],['9','GPIO14 / MOSI'],['10','GPIO9 / I2C SCL'],['11','GPIO39 / SPI MISO'],['12','GPIO13 / UART TX'],['13','GPIO5 / CS'],['14','GPIO15 / UART RX']]],
  ['LCD · ST7789V2',[['BL','GPIO38'],['RST','GPIO33'],['DC','GPIO34'],['MOSI','GPIO35'],['SCK','GPIO36'],['CS','GPIO37']]],
  ['KLAWIATURA 56 klawiszy · TCA8418',[['SDA','GPIO8'],['SCL','GPIO9'],['INT','GPIO11']]],
  ['AUDIO · ES8311 + NS4150B',[['I2C SDA','GPIO8'],['I2C SCL','GPIO9'],['I2S BCLK','GPIO41'],['I2S DOUT','GPIO46'],['I2S LRCK','GPIO43'],['I2S DIN','GPIO42'],['OUT','1 W speaker + jack 3.5 mm']]],
  ['6D IMU · BMI270',[['SDA','GPIO8'],['SCL','GPIO9']]],
  ['microSD',[['CS','GPIO12'],['MOSI','GPIO14'],['SCLK','GPIO40'],['MISO','GPIO39']]],
  ['IR / AKUMULATOR',[['IR TX','GPIO44'],['Battery ADC','GPIO10'],['Battery','1750 mAh Li-ion']]],
  ['UWAGA',[['Firmware','Podgląd ST7789 LVGL jest eksperymentalny'],['Peryferia','Klawiatura / audio / IMU wymagają osobnych bibliotek sterowników']]]]},
 s3:{label:'ESP32-S3 DevKit',screen:false,wifi:true,bt:false,desc:'Wi‑Fi + BLE · bez Classic',connectors:[
  ['INTERFEJSY',[['GPIO','GPIO0..48 zależnie od modułu'],['I2C','przypisywane piny'],['SPI','przypisywane piny'],['I2S','przypisywane piny'],['UART','TX/RX'],['USB','GPIO19/20 · USB natywne']]],
  ['WAŻNE',[['BLE','TAK'],['Bluetooth Classic','NIE'],['ADC','ESP32-S3: ADC1 i ADC2'],['GPIO','sprawdź zajęte piny Flash/PSRAM na module']]]]},
 esp32:{label:'ESP32 DevKit',screen:false,wifi:true,bt:true,desc:'ESP32 · node bez LCD',connectors:[
  ['PERYFERIA',[['GPIO','GPIO0..39; GPIO34–39 tylko wejścia'],['ADC','ADC1 / ADC2'],['DAC','GPIO25 / GPIO26'],['PWM','LEDC'],['I2C','dowolne odpowiednie GPIO'],['SPI','VSPI / HSPI'],['UART','3 kontrolery'],['CAN','TWAI · zewnętrzny transceiver']]],
  ['RADIO',[['Wi‑Fi','2.4 GHz'],['BT Classic','TAK'],['BLE','TAK']]]]} };
// Pinouts: github.com/witnessmenow/ESP32-Cheap-Yellow-Display and BruceDevices/firmware.
presets.cyd28usb={...presets.cyd28,label:'CYD 2.8 R · 2 USB',desc:'ST7789 · BGR · touch XPT2046'};
presets.cardputeradv={label:'M5Stack Cardputer ADV',screen:true,wifi:true,bt:false,desc:'ESP32-S3 · ST7789 240x135 · keyboard',connectors:[['LCD',[['SCK','GPIO36'],['MOSI','GPIO35'],['CS','GPIO37'],['DC','GPIO34'],['RST','GPIO33'],['BL','GPIO38']]],['GROVE',[['IO1','GPIO2'],['IO2','GPIO1']]]]};
presets.coreink={label:'M5Stack CoreInk',screen:false,wifi:true,bt:true,desc:'ESP32-PICO-D4 · E-Ink 200×200; sterownik E-Ink poza edytorem TFT',connectors:[
 ['E-INK 200×200',[['BUSY','GPIO4'],['RST','GPIO0'],['DC','GPIO15'],['CS','GPIO9'],['SCK','GPIO18'],['MOSI','GPIO23']]],
 ['BUTTONS',[['UP','GPIO37'],['CENTER','GPIO38'],['DOWN','GPIO39'],['USER','GPIO5']]],
 ['ON BOARD',[['LED','GPIO10'],['BUZZER','GPIO2'],['PWR HOLD','GPIO12'],['RTC SDA','GPIO21'],['RTC SCL','GPIO22']]],
 ['GROVE CUSTOM',[['IO1','GPIO32'],['IO2','GPIO33']]]
]};
presets.stamplc={label:'M5Stack StamPLC',screen:false,wifi:true,bt:false,desc:'ESP32-S3 · 4 relays · 8 opto inputs · CAN / RS485 · ST7789 1.14 (renderer w przygotowaniu)',connectors:[
 ['CAN',[['TX','GPIO42'],['RX','GPIO43']]],
 ['RS485',[['TX','GPIO0 / BOOT'],['RX','GPIO39'],['DIR','GPIO46']]],
 ['AW9523B I2C',[['SDA','GPIO13'],['SCL','GPIO15'],['INT','GPIO14'],['RESET','GPIO3 HIGH at boot'],['ADDR','0x59']]],
 ['RELAY OUTPUTS',[['RLY1–RLY4','AW9523 P0_0–P0_3'],['WARNING','Expander outputs, not native ESP32 GPIO']]],
 ['OPTO INPUTS',[['IN1–IN8','AW9523 P0_4–P0_7 + P1_4–P1_7']]],
 ['GROVE A',[['IO1','GPIO2'],['IO2','GPIO1']]],['GROVE C',[['IO1','GPIO5'],['IO2','GPIO4']]],
 ['STAMPLC BUS',[['SDA/SCL','GPIO13 / GPIO15'],['SCK/MOSI/MISO/CS','GPIO7 / GPIO8 / GPIO9 / GPIO11']]]
]};


// Verified GPIO mapping: M5Stack official pin maps, November 2026.
presets.atoms3lite={label:'M5 ATOM S3 Lite',screen:false,wifi:true,bt:false,desc:'ESP32-S3 · bez LCD, GPIO2/1 Grove',connectors:[
 ['GROVE CUSTOM',[['GND','GND'],['5V','5 V'],['YELLOW','GPIO2'],['WHITE','GPIO1']]],
 ['PINS',[['EXT','GPIO5/6/7/8/38/39 (sprawdź obudowę)'],['USB','USB-C natywny · CDC'],['RADIO','Wi-Fi + BLE, bez BT Classic']]] ]};
presets.atommatrix={label:'M5 ATOM Matrix',screen:false,wifi:true,bt:true,desc:'ESP32-PICO-D4 · RGB LED 5×5 + MPU6886',connectors:[
 ['GROVE CUSTOM',[['YELLOW','GPIO26'],['WHITE','GPIO32']]],
 ['INTERNAL',[['RGB LED 5×5','GPIO27'],['MPU6886 SCL/SDA','GPIO21 / GPIO25'],['BUTTON','GPIO39'],['IR TX','GPIO12']]],
 ['EXTERNAL',[['GPIO','GPIO19 / GPIO21 / GPIO22 / GPIO23 / GPIO25 / GPIO33']]] ]};
presets.stamps3={label:'M5 StampS3',screen:false,wifi:true,bt:false,desc:'ESP32-S3 · miniaturowy moduł bez LCD',connectors:[
 ['ZASILANIE',[['3V3','3.3V'],['GND','GND'],['USB','Natywne USB ESP32-S3']]],
 ['GPIO',[['UWAGA','Pinout zależy od płytki bazowej / wersji StampS3'],['KONFIGURACJA','GPIO1..48 po weryfikacji schematu bazy']]] ]};
presets.atoms3={label:'M5 ATOM S3',screen:true,wifi:true,bt:false,desc:'ESP32-S3 · GC9107 128×128 · MPU6886; M5Unified',connectors:[
 ['LCD GC9107',[['MOSI','GPIO21'],['SCK','GPIO17'],['CS','GPIO15'],['DC','GPIO33'],['RST','GPIO34'],['BL','GPIO16']]],
 ['GROVE CUSTOM',[['YELLOW','GPIO2'],['WHITE','GPIO1']]],
 ['MPU6886',[['SDA','GPIO38'],['SCL','GPIO39']]],['PINS',[['GPIO','5,6,7,8,38,39']]] ]};
presets.cores3={label:'M5Stack CoreS3',screen:true,wifi:true,bt:false,desc:'ESP32-S3 · ILI9342C/E 320×240 · pojemnościowy dotyk; M5Unified',connectors:[
 ['LCD',[['MOSI','GPIO37'],['SCK','GPIO36'],['CS','GPIO3'],['DC','GPIO35'],['RST','AW9523 P1_1']]],
 ['PORT A',[['SDA','GPIO2'],['SCL','GPIO1']]],['PORT B',[['IO1','GPIO9'],['IO2','GPIO8']]],['PORT C',[['TX','GPIO17'],['RX','GPIO18']]],
 ['I2C INTERNAL',[['SDA','GPIO12'],['SCL','GPIO11']]],['TOUCH',[['CONTROL','M5Unified (brak XPT2046)']]] ]};
presets.core2={label:'M5Stack Core2',screen:true,wifi:true,bt:true,desc:'ESP32 · ILI9342C 320×240 + FT6336U; M5Unified',connectors:[
 ['PORT A',[['SDA','GPIO32'],['SCL','GPIO33']]],['PORT B',[['IO1','GPIO26'],['IO2','GPIO36']]],['PORT C',[['TX','GPIO14'],['RX','GPIO13']]],
 ['I2C INTERNAL',[['SDA','GPIO21'],['SCL','GPIO22']]],['TOUCH',[['IC','FT6336U / M5Unified']]],['LCD',[['DISPLAY','320×240 / M5Unified']]] ]};
presets.m5basic={label:'M5Stack Basic',screen:true,wifi:true,bt:true,desc:'ESP32 · ILI9342C 320×240 · przyciski A/B/C; M5Unified',connectors:[
 ['PORT A',[['SDA','GPIO21'],['SCL','GPIO22']]],['PORT B',[['IO1','GPIO26'],['IO2','GPIO36']]],['PORT C',[['TX','GPIO17'],['RX','GPIO16']]],
 ['LCD',[['MOSI','GPIO23'],['SCK','GPIO18'],['CS','GPIO14'],['DC','GPIO27'],['RST','GPIO33'],['BL','GPIO32']]],
 ['BUTTONS',[['A','GPIO39'],['B','GPIO38'],['C','GPIO37']]] ]};
presets.stickcplus2={label:'M5StickC Plus2',screen:true,wifi:true,bt:true,desc:'ESP32-PICO-V3-02 · ST7789V2 135×240; M5Unified',connectors:[
 ['GROVE CUSTOM',[['YELLOW','GPIO32'],['WHITE','GPIO33']]],
 ['LCD ST7789V2',[['MOSI','GPIO15'],['SCK','GPIO13'],['DC','GPIO14'],['RST','GPIO12'],['CS','GPIO5'],['BL','GPIO27']]],
 ['IMU / RTC',[['SDA','GPIO21'],['SCL','GPIO22']]],['BUTTONS',[['A','GPIO37'],['B','GPIO39'],['C','GPIO35']]],
 ['POWER',[['HOLD','GPIO4 · sterowane przez M5Unified']]] ]};

const groups=[
 ['Łączność','Wi‑Fi STA','Wbudowane','gotowe'],['Łączność','Hotspot SoftAP','Wbudowane','gotowe'],['Łączność','Wi‑Fi AP+STA','Wbudowane','gotowe'],['Łączność','Bluetooth BLE','Wbudowane','gotowe'],['Łączność','Bluetooth Classic','ESP32 klasyczny','gotowe'],['Łączność','ESP‑NOW','Wbudowane','katalog'],['Łączność','OTA','Wi‑Fi','katalog'],
 ['Komunikacja','UART / Serial','Wbudowane','katalog'],['Komunikacja','I2C','Wbudowane','gotowe'],['Komunikacja','SPI / microSD','Wbudowane / karta','katalog'],['Komunikacja','I2S audio','Wbudowane + moduł','gotowe'],['Komunikacja','TWAI / CAN','Transceiver 3.3 V','katalog'],['Komunikacja','RS485 / Modbus','Transceiver 3.3 V','katalog'],
 ['Inputs','GPIO digital','Wbudowane','katalog'],['Inputs','ADC','Wbudowane','gotowe'],['Inputs','DAC','ESP32 klasyczny','gotowe'],['Inputs','PWM LEDC','Wbudowane','katalog'],['Inputs','PCNT / RMT','Zależnie od MCU','katalog'],
 ['Sprzęt','LCD TFT','Tylko płytka z LCD','gotowe'],['Sprzęt','Dotyk XPT2046','CYD R','gotowe'],['Sprzęt','Żyroskop MPU6050','Moduł zewnętrzny','gotowe'],['Sprzęt','Mikrofon I2S','Moduł zewnętrzny','gotowe'],['Sprzęt','Bateria ADC','Dzielnik zewnętrzny','gotowe'],['Sprzęt','CC1101 / LoRa','Moduł SPI','katalog'],['RF','RSSI · Wi-Fi STA','Built-in Wi-Fi client','gotowe'],['RF','RSSI · BLE / LoRa / CC1101','Driver / paired receiver','katalog'],['RF','RSSI · ESP-NOW / nRF24 / Zigbee','Module/API measurement','katalog']];
let seq=0;const uid=()=>`u${Date.now().toString(36)}${(seq++).toString(36)}`;
function W(type,text,x,y,w,h,bg,to=''){
 const rf=['rfwave','rfsignal','rfrssi','waterfall','spectrum'].includes(type);
 return {id:uid(),type,text,x,y,w,h,bg,fg:'#ffffff',visualStyle:'neo',to,level:rf?-67:65,min:rf?-110:0,max:rf?-30:100,unit:rf?' dBm':type==='analog'?' V':'',precision:rf?0:1,threshold:.5,source:rf?'wifi_rssi':type==='battery'?'battery_percent':'constant',radioType:'wifi',paths:[]};
}
function newScenes(){const labels=['DIAGNOSTYKA','WIBRACJE','MIKROFON','433 MHz','USTAWIENIA'];const scenes=[{id:'menu',name:'MENU',bg:'#101d32',widgets:[W('text','DIAG / CYD',14,10,212,29,'#55d8ff')]}];labels.forEach((v,i)=>scenes[0].widgets.push(W('button',v,25,47+i*50,190,41,palettes[i],'screen'+(i+1))));labels.forEach((v,i)=>scenes.push({id:'screen'+(i+1),name:v,bg:'#0d1b2e',widgets:[W('text',v,10,14,220,33,'#ffffff'),W(['gyro','bar','audio','wifi','battery'][i],['WIBRACJE','78','MIKROFON','WIFI','BAT'][i],23,89,194,85,palettes[i]),W('button','MENU',48,263,144,43,palettes[i],'menu')]}));return scenes}
// The RF screen is an editable example; each radio driver supplies its own RSSI through a data source.
const _newScenesOriginal=newScenes;
newScenes=function(){
 const pages=_newScenesOriginal();const rf=pages.find(p=>p.id==='screen4');
 if(rf){rf.widgets=rf.widgets.filter(w=>w.type!=='wifi');
  rf.widgets.splice(1,0,W('rfwave','433 MHz',20,76,200,76,'#38baf2'),W('rfsignal','CC1101',20,160,200,66,'#56d6a3'));
  rf.widgets[1].radioType='cc1101';rf.widgets[1].source='constant';rf.widgets[2].radioType='cc1101';rf.widgets[2].source='constant';
 }
 return pages;
};
function newCardputerScenes(){
 const n=(type,text,x,y,w,h,bg)=>({id:uid(),type,text,x,y,w,h,bg,fg:'#ffffff',source:'constant',level:0,min:0,max:100,precision:0,unit:'',paths:[]});
 return [{id:'menu',name:'CARDPUTER ADV',bg:'#08182d',widgets:[
  n('text','CARDPUTER ADV',8,5,224,22,'#57d3fb'),
  n('text','GROVE G2 / G1',10,30,214,20,'#a6c5e2'),
  n('value','Battery ADC · GPIO10',10,57,108,52,'#34d7b7'),
  n('button','PERIPHERALS',124,57,106,52,'#248fd5')]}];
}

function newM5Scenes(profile){
 const wide=['core2','cores3','m5basic'].includes(profile), tiny=profile==='atoms3';
 const w=wide?320:tiny?128:135, h=wide?240:tiny?128:240;
 const wgt=(type,text,x,y,ww,hh,bg,to)=>({...W(type,text,x,y,ww,hh,bg,to),fg:'#f5fbff'});
 return [{id:'menu',name:'M5 MAIN',bg:'#0b192b',widgets:[
  wgt('text',presets[profile].label.toUpperCase(),6,4,w-12,tiny?21:27,'#8fdefd'),
  wgt('button','MENU',8,tiny?37:44,w-16,tiny?32:43,'#247dc5','menu'),
  wgt('progress','TEST 65%',8,tiny?79:102,w-16,tiny?31:44,'#29bda7')]}];
}
function defaultGrove(profile){if(profile==='atoms3lite'||profile==='atoms3'||profile==='stamps3')return {A:{io1:2,io2:1},B:{io1:-1,io2:-1},C:{io1:-1,io2:-1}};if(profile==='cores3')return {A:{io1:2,io2:1},B:{io1:9,io2:8},C:{io1:17,io2:18}};if(profile==='core2')return {A:{io1:32,io2:33},B:{io1:26,io2:36},C:{io1:14,io2:13}};if(profile==='m5basic')return {A:{io1:21,io2:22},B:{io1:26,io2:36},C:{io1:17,io2:16}};if(profile==='stickcplus2')return {A:{io1:32,io2:33},B:{io1:-1,io2:-1},C:{io1:-1,io2:-1}};if(profile==='atommatrix')return {A:{io1:26,io2:32},B:{io1:-1,io2:-1},C:{io1:-1,io2:-1}};if(profile==='coreink')return {A:{io1:32,io2:33},B:{io1:-1,io2:-1},C:{io1:-1,io2:-1}};if(profile==='stamplc')return {A:{io1:2,io2:1},B:{io1:-1,io2:-1},C:{io1:5,io2:4}};if(profile==='cardputeradv')return {A:{io1:2,io2:1},B:{io1:-1,io2:-1},C:{io1:-1,io2:-1}};const atom=profile==='atom',s3=profile==='s3',c24=profile==='cyd24';return {A:{io1:atom?25:s3?8:c24?-1:27,io2:atom?21:s3?9:c24?-1:22},B:{io1:atom?26:s3?4:35,io2:atom?32:s3?5:-1},C:{io1:-1,io2:-1}}}
function getGrove(d=current()){if(!d.grove)d.grove=defaultGrove(d.profile);return d.grove}
function newDev(profile,name){return {id:uid(),profile,name,uiTheme:'neo',lcd:{driver:profile==='cyd28usb'?'st7789':'ili9341_2',order:profile==='cyd28usb'?'bgr':'rgb',inversion:'off'},grove:defaultGrove(profile),githubLibraries:[],rotation:profile==='cardputeradv'||['core2','cores3','m5basic'].includes(profile)?1:0,scenes:profile==='cardputeradv'?newCardputerScenes():['core2','cores3','m5basic','stickcplus2','atoms3'].includes(profile)?newM5Scenes(profile):(presets[profile].screen?newScenes():[]),currentScene:'menu',features:{wifi_mode:profile==='cyd28'?'ap':'off',sta_ssid:'CYD-DIAG',sta_password:'cyd12345',ap_ssid:'CYD-DIAG',ap_password:'cyd12345',ble:false,bt_classic:false,gyro:false,battery:false,battery_v_min:3.2,battery_v_max:4.2,battery_smooth:20,backlight_brightness:85,backlight_timeout_s:profile==='cyd28t'||profile==='cardputeradv'?0:60,backlight_dim:0,audio_rx:false,audio_tx:false,audio_dest:'192.168.4.1',audio_port:3333},pins:{i2c_sda:profile==='atoms3'?38:profile==='cores3'?12:profile==='core2'?21:profile==='m5basic'?21:profile==='stickcplus2'?21:profile==='atommatrix'?25:profile==='atoms3lite'||profile==='stamps3'?2:profile==='coreink'?21:profile==='stamplc'?13:profile==='cardputeradv'?8:profile==='atom'?25:profile==='s3'?8:27,i2c_scl:profile==='atoms3'?39:profile==='cores3'?11:profile==='core2'?22:profile==='m5basic'?22:profile==='stickcplus2'?22:profile==='atommatrix'?21:profile==='atoms3lite'||profile==='stamps3'?1:profile==='coreink'?22:profile==='stamplc'?15:profile==='cardputeradv'?9:profile==='atom'?21:profile==='s3'?9:22,battery_adc:profile==='atoms3'||profile==='cores3'||profile==='atoms3lite'||profile==='stamps3'?4:profile==='coreink'?35:profile==='stamplc'?4:profile==='cardputeradv'?10:profile==='atom'?33:profile==='s3'?4:35,battery_divider:2,mic_bclk:19,mic_ws:22,mic_din:23},touch:{xmin:200,xmax:3900,ymin:200,ymax:3900,swap:false,flipX:false,flipY:false,autoCal:true,orientationVersion:4},logic:{nodes:[],edges:[]},libraries:[],custom:{includes:'',setup:'',loop:''}}}
const initial={version:3,currentDevice:null,devices:[]};initial.devices.push(newDev('cyd28','CYD MAIN'));initial.currentDevice=initial.devices[0].id;initial.devices[0].features.audio_rx=true;const atomDemo=newDev('atom','ATOM MICROPHONE');atomDemo.features.wifi_mode='sta';atomDemo.features.audio_tx=true;initial.devices.push(atomDemo);
let project;try{let p=JSON.parse(localStorage.getItem('cyd_diag_project_v2'));project=p&&Array.isArray(p.devices)&&p.devices.length?p:initial}catch{project=initial}
// v2.31: drop the mistakenly installed mirrored X+Y default from the CYD 2.8 R preset.
// Explicit custom single-axis mappings and touch calibration values are never overwritten.
if((project.version||2)<3){
 for(const d of project.devices||[]){
  if(d.profile==='cyd28'){
   if(d.touch && d.touch.swap===false && d.touch.flipX===true && d.touch.flipY===true && d.touch.autoCal===true){d.touch.flipX=false;d.touch.flipY=false;}
   d.lcd=d.lcd||{};
   if(!d.lcd.inversion||d.lcd.inversion==='off')d.lcd.inversion='on';
  }
 }
 project.version=3;
 try{localStorage.setItem('cyd_diag_project_v2',JSON.stringify(project));}catch{}
}
// Migrate the old CYD 2.8 R single-USB stock profile saved by earlier versions.
// Only modify the known-bad uncustomized defaults; keep custom calibration untouched.
for(const d of project.devices){
 if(d.profile!=='cyd28')continue;
 d.touch=d.touch||{};
 if(Number(d.touch.orientationVersion||0)<4){
   if(!d.touch.swap&&!d.touch.flipX&&!d.touch.flipY){d.touch.flipX=true;d.touch.flipY=true;}
   d.touch.orientationVersion=4;
 }
 d.lcd=d.lcd||{};
 if(d.lcd.driver==='ili9341_2'&&d.lcd.inversion==='on'&&d.lcd.order==='bgr'){
   d.lcd.inversion='off';d.lcd.order='rgb';
 }
}
for(const dev of project.devices||[]){for(const sc of dev.scenes||[]){for(const w of sc.widgets||[]){if(typeof w.text==='string')w.text=w.text.replace(/^\s*[←◀▣⌘]\s*/,'');}}}
let tab='screen',sel=null,preview=false,previewPressed=null,pen=false,drag=null,hist=[],buildJob=null,pollHandle=0,demoVoltage=3.85,demoTimer=null;
const current=()=>project.devices.find(d=>d.id===project.currentDevice)||project.devices[0];
const scene=()=>current().scenes.find(s=>s.id===current().currentScene)||current().scenes[0];
const screenSize=()=>{const d=current(),r=Number(d.rotation||0)%2;if(d.profile==='atoms3')return {w:128,h:128};if(d.profile==='stickcplus2')return r?{w:240,h:135}:{w:135,h:240};if(['core2','cores3','m5basic'].includes(d.profile))return r?{w:320,h:240}:{w:240,h:320};return current().profile==='cardputeradv'?(Number(current().rotation||0)%2?{w:240,h:135}:{w:135,h:240}):(Number(current().rotation||0)%2?{w:320,h:240}:{w:240,h:320})};
const screenW=()=>screenSize().w,screenH=()=>screenSize().h;
function resizeStage(){const {w,h}=screenSize();if(cv.width!==w||cv.height!==h){cv.width=w;cv.height=h}cv.classList.toggle('landscape',w>h);cv.parentElement.dataset.size=`${w} × ${h}`;cv.parentElement.style.setProperty('--lcdsize',`"${presets[current().profile].label} · ${w} × ${h}"`)}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp=(a,min,max)=>Math.min(max,Math.max(min,a));
const batteryLimits=d=>[Number(d.features.battery_v_min??3.2),Number(d.features.battery_v_max??4.2)];
function batteryPreviewPct(){const [vmin,vmax]=batteryLimits(current());return clamp(Math.round((demoVoltage-vmin)*100/Math.max(.01,vmax-vmin)),0,100)}
function stopDemo(){if(demoTimer){clearInterval(demoTimer);demoTimer=null}const b=$('mapDemo');if(b)b.textContent='▶ Symuluj ładowanie'}

function toast(s){$('toast').textContent=s;$('toast').classList.add('show');setTimeout(()=>$('toast').classList.remove('show'),2600)}
function save(){try{localStorage.setItem('cyd_diag_project_v2',JSON.stringify(project))}catch{toast('Browser storage unavailable or full. Export your project to JSON.')}scheduleLint()}
function mark(){hist.push(JSON.stringify(project));if(hist.length>80)hist.shift();$('undo').disabled=false}
function refreshNav(){let d=current();$('devlist').innerHTML=project.devices.map(v=>`<button class="device-item ${v.id===d.id?'active':''}" data-dev="${esc(v.id)}"><span class="badge-round">${presets[v.profile].screen?'▣':'◉'}</span><span><strong>${esc(v.name)}</strong><span class="device-desc">${esc(presets[v.profile].label)}</span></span></button>`).join('');$('sceneList').innerHTML=d.scenes.length?d.scenes.map((s,i)=>`<button class="${s.id===d.currentScene?'active':''}" data-sc="${esc(s.id)}">${i===0?'⌂ ':i+' · '}${esc(s.name)}</button>`).join(''):'<p class="hint">Edytor LCD nie jest aktywny dla tej płytki; dostępne są GPIO i logika urządzenia.</p>';$('sceneHint').textContent=d.scenes.length?'Dotknij nazwę ekranu — możesz zmieniać każdy osobno.':'Wybierz PERYFERIA, GPIO i LOGIKA dla modułu.';$('screenTitle').textContent=scene()?.name||'Urządzenie bez ekranu';$('buildDevice').textContent=d.name+' · '+presets[d.profile].label; if($('screenRotation'))$('screenRotation').value=String(d.rotation||0);resizeStage();
 const ctxDev=$('contextDevice'),ctxLoc=$('contextLocation');if(ctxDev){ctxDev.textContent=d.name;ctxLoc.textContent=({screen:'Screens',logic:'Block Logic',hardware:'Peripherals',pins:'GPIO & Ports',grove:'Grove Ports',libs:'Libraries & Code',build:'Build & Flash'})[tab]+' / '+(scene()?.name||presets[d.profile].label)}
 if(d.scenes.length){$('sceneName').value=scene().name;$('sceneBg').value=scene().bg}
 $('stage').style.display=d.scenes.length?'grid':'none';$('tools').style.display=d.scenes.length?'flex':'none';$('editHint').textContent=d.scenes.length?(pen?'Tryb pędzla: rysuj palcem po ekranie.':'Wybierz element, przesuń go palcem lub kliknij TEST.'):'To urządzenie nie ma własnego LCD — steruje czujnikami lub wysyła dane.';
 if(!d.scenes.length){$('inspector').innerHTML='<div class="inspector-empty">Wybierz PERYFERIA, aby ustawić moduł ESP32.</div>'}
}
// Tree structure mirrors devices, screens, graphics, logic, libraries and generated files.
const treeOpen=new Set(['project','devices','outputs']);let treeInitialized=false;
function treeFolder(key,label,content,count='',icon='📁',filter=''){
 if(filter && !label.toLowerCase().includes(filter) && !content)return '';
 const open=filter ? ' open' : (treeOpen.has(key)?' open':'');
 return `<details data-tree-key="${esc(key)}"${open}><summary><span class="tree-icon">${icon}</span><span>${esc(label)}</span>${count!==''?`<span class="tree-counter">${esc(count)}</span>`:''}</summary><div class="tree-children">${content||'<div class="tree-empty">No items</div>'}</div></details>`;
}
function treeItem(label,icon,action,attrs={},filter='',force=false,selected=false,tag=''){
 if(filter && !force && !String(label).toLowerCase().includes(filter))return '';
 let a=Object.entries(attrs).map(([k,v])=>` data-${k}="${esc(v)}"`).join('');
 return `<button class="tree-leaf ${selected?'active':''}" data-tree-action="${action}"${a} title="${esc(label)}"><span class="tree-icon">${icon}</span><span>${esc(label)}</span>${tag?`<span class="tree-tag">${esc(tag)}</span>`:''}</button>`;
}
function libraryList(d){
 const external=[];
 if(presets[d.profile].screen){external.push('LVGL 9.6.0 · UI rendering');external.push('bodmer/TFT_eSPI @ ^2.5.43 · LCD SPI driver');if(d.profile==='cyd28'||d.profile==='cyd24')external.push('XPT2046_Touchscreen (GitHub)')}
 const f=d.features||{};
 const internal=['Arduino.h'];
 if(presets[d.profile].screen)internal.push('SPI.h');
 if(f.wifi_mode&&f.wifi_mode!=='off')internal.push('WiFi.h');
 if(f.audio_rx||f.audio_tx)internal.push('WiFiUdp.h');
 if(f.audio_tx)internal.push('driver/i2s.h');
 if(f.gyro)internal.push('Wire.h');
 if(f.bt_classic)internal.push('BluetoothSerial.h');
 if(f.ble)internal.push('BLEDevice.h');
 return {external,internal,custom:Array.isArray(d.libraries)?d.libraries:[]};
}
function renderExplorer(){
 const root=$('projectTree');if(!root)return;
 const q=($('explorerSearch').value||'').trim().toLowerCase();
 const selected=current();
 if(!treeInitialized){for(const key of ['device:','scenes:'])treeOpen.add(key+selected.id);treeInitialized=true;}
 let devices='';
 for(const d of project.devices){
   const all=q && (d.name+' '+presets[d.profile].label).toLowerCase().includes(q);
   const term=all?'':q;
   const f=d.features||{};
   const scenes=d.scenes||[];
   let screenItems='';
   for(const sc of scenes){
     screenItems+=treeItem(sc.name,'▣','screen',{'device-id':d.id,'scene-id':sc.id},term,false,d.id===selected.id&&d.currentScene===sc.id&&tab==='screen');
   }
   const screens=treeFolder('scenes:'+d.id,'Screens',screenItems,scenes.length,'🖥️',term);
   const blocks=(d.logic?.nodes||[]).length;
   const controls=[
     treeItem('Block diagram','🧩','tab',{'device-id':d.id,'tab':'logic'},term,false,d.id===selected.id&&tab==='logic',String(blocks)),
     treeItem('Grove Port A/B/C','🔌','tab',{'device-id':d.id,'tab':'grove'},term,false,d.id===selected.id&&tab==='grove'),
     treeItem('GPIO & connectors','🔌','tab',{'device-id':d.id,'tab':'pins'},term,false,d.id===selected.id&&tab==='pins'),
     treeItem('Peripherals / Wi-Fi / BT','📡','tab',{'device-id':d.id,'tab':'hardware'},term,false,d.id===selected.id&&tab==='hardware')
   ].join('');
   const signals=treeFolder('logic:'+d.id,'Logic & hardware',controls,blocks,'🧩',term);
   const lib=libraryList(d);
   const libUser=lib.custom.map(x=>treeItem(x,'📦','library',{'device-id':d.id},term)).join('');
   const libAutomatic=lib.external.map(x=>treeItem(x,'📚','library',{'device-id':d.id},term)).join('');
   const libIncluded=lib.internal.map(x=>treeItem(x,'⚙','library',{'device-id':d.id},term)).join('');
   const libraries=treeFolder('libs:'+d.id,'Libraries',
     treeFolder('deps:'+d.id,'PlatformIO dependencies',libAutomatic,lib.external.length,'📦',term)+
     treeFolder('arduino:'+d.id,'ESP32 framework',libIncluded,lib.internal.length,'⚙️',term)+
     treeFolder('userlibs:'+d.id,'User libraries',libUser||treeItem('＋ Add a library','＋','library',{'device-id':d.id},term),lib.custom.length,'📚',term),
     lib.external.length+lib.custom.length,'📚',term);
   let drawn=[];for(const sc of scenes)for(const w of (sc.widgets||[]))if(w.type==='draw'||w.type==='custom'||w.type==='rect'||w.type==='circle'||w.type==='frame'||w.type==='line')drawn.push({sc,w});
   const assets=treeFolder('graphics:'+d.id,'Graphics & custom widgets',drawn.map(({sc,w})=>treeItem(`${sc.name}: ${w.text||w.type}`,'🎨','widget',{'device-id':d.id,'scene-id':sc.id,'widget-id':w.id},term)).join(''),drawn.length,'🎨',term);
   const radioWidgets=scenes.flatMap(sc=>(sc.widgets||[]).filter(w=>['rfwave','rfsignal','rfrssi','waterfall','spectrum'].includes(w.type)).map(w=>({sc,w})));
   const radioFolder=treeFolder('rfwidgets:'+d.id,'Radio indicators',
     [['rfwave','＋ RF Waves'],['rfsignal','＋ Signal Bars'],['rfrssi','＋ RSSI dBm']].map(([type,name])=>treeItem(name,'📡','radio-add',{'device-id':d.id,'widget-type':type},term)).join('')+
     radioWidgets.map(({sc,w})=>treeItem(sc.name+': '+(w.radioType||'Wi-Fi').toUpperCase()+' '+w.type,'◉','widget',{'device-id':d.id,'scene-id':sc.id,'widget-id':w.id},term)).join(''),radioWidgets.length,'📶',term);
   const usercode=treeItem('User includes / setup / loop','⌘','library',{'device-id':d.id},term);
   const content=treeItem('Device settings','🔧','tab',{'device-id':d.id,'tab':'hardware'},term,false,d.id===selected.id&&tab==='hardware')+screens+signals+radioFolder+libraries+assets+usercode;
   devices+=treeFolder('device:'+d.id,d.name,content,presets[d.profile].label,presets[d.profile].screen?'▣':'◉',q);
 }
 const files=treeFolder('output:src','src',treeItem('main.cpp','📄','build',{},q),'','📁',q)+
   treeItem('platformio.ini','📄','build',{},q)+treeItem('project.json','📄','export',{},q)+treeItem('Screen SVG / PNG','🎨','screen-export',{},q)+treeItem('Project ZIP','📦','export',{},q)+treeItem('firmware.bin (after Build)','💾','build',{},q);
 const output=treeFolder('outputs','Generated PlatformIO files',files,'on Build','📂',q);
 const rootTree=treeFolder('project','CYD Studio Project',treeFolder('devices','Devices',devices,project.devices.length,'📁',q)+output,'','📂',q);
 root.innerHTML=rootTree||'<div class="tree-empty">No matching project items</div>';
}
$('explorerSearch').addEventListener('input',renderExplorer);
$('projectTree').addEventListener('toggle',e=>{
 if(e.target.matches?.('details[data-tree-key]')){
  const key=e.target.dataset.treeKey;
  if(e.target.open)treeOpen.add(key);else treeOpen.delete(key);
 }
},true);
$('projectTree').addEventListener('click',e=>{
 const b=e.target.closest('button[data-tree-action]');if(!b)return;
 const act=b.dataset.treeAction,id=b.dataset.deviceId;
 if(id && project.devices.some(x=>x.id===id))project.currentDevice=id;
 sel=null;preview=false;pen=false;
 if(act==='radio-add'){
   if(!presets[current().profile].screen){toast('Select a device with an LCD');return}
   selectTab('screen');const btn=$('tools').querySelector('[data-add="'+b.dataset.widgetType+'"]');if(btn)btn.click();return;
 }
 if(act==='export'){$('exportZip').click();return;}
 if(act==='screen-export'){selectTab('screen');return;}
 if(act==='screen'||act==='widget'){
   const sc=current().scenes.find(x=>x.id===b.dataset.sceneId);if(sc)current().currentScene=sc.id;
   if(act==='widget')sel=b.dataset.widgetId;
   // selectTab clears selection, so restore after tab has changed.
   selectTab('screen');if(act==='widget'){sel=b.dataset.widgetId;renderCanvas();inspector()}
 }else if(act==='tab'){selectTab(b.dataset.tab)}
 else if(act==='library') {selectTab('libs');$('libraries').focus()}
 else if(act==='build'){selectTab('build');toast('Generate BIN to create/update PlatformIO files.')}
});
$('explorerNewDevice').onclick=()=>{$('addDeviceBox').open=true;$('newName').focus();$('addDeviceBox').scrollIntoView({block:'nearest',behavior:'smooth'})};
$('explorerNewScreen').onclick=()=>{
 const d=current();if(!presets[d.profile].screen)return toast('This board has no display. Select a CYD first.');
 mark();const n=d.scenes.length+1,id='screen_'+uid();
 d.scenes.push({id,name:'SCREEN '+n,bg:'#0d1b2e',widgets:[W('text','SCREEN '+n,10,14,screenW()-20,33,'#ffffff'),W('button','MENU',Math.round((screenW()-144)/2),screenH()-57,144,43,'#2679b0','menu')]});
 d.currentScene=id;sel=null;selectTab('screen');toast('Screen added. You can now edit it.');
};
$('explorerAddLibrary').onclick=()=>{selectTab('libs');$('libraries').focus();toast('Enter PlatformIO library, then click Save component & libraries.')};
const SENSOR_ICON_NAMES=['wifi','bluetooth','radio','antenna','can','temperature','pressure','gyro','microphone','battery','voltage','water','light','gps','speed','nfc','vibration','sensor','signal','waves'];
function drawSensorSymbol(cx,cy,r,name,color){
 const stroke=(fn)=>{ctx.beginPath();fn();ctx.stroke()},line=(x1,y1,x2,y2)=>stroke(()=>{ctx.moveTo(x1,y1);ctx.lineTo(x2,y2)});
 ctx.save();ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=Math.max(1.7,r*.12);ctx.lineCap='round';ctx.lineJoin='round';
 if(['wifi','radio','signal','waves','nfc'].includes(name)){
   ctx.beginPath();ctx.arc(cx,cy+r*.60,r*.10,0,7);ctx.fill();
   for(let k=1;k<=3;k++)stroke(()=>ctx.arc(cx,cy+r*.60,r*k*.35,-Math.PI*.83,-Math.PI*.17));
 }else if(name==='bluetooth'){
   line(cx,cy-r,cx,cy+r);line(cx,cy-r,cx+r*.65,cy-r*.4);line(cx+r*.65,cy-r*.4,cx-r*.55,cy+r*.6);line(cx-r*.55,cy-r*.6,cx+r*.65,cy+r*.4);line(cx+r*.65,cy+r*.4,cx,cy+r);
 }else if(name==='temperature'){
   stroke(()=>{ctx.roundRect(cx-r*.23,cy-r,r*.46,r*1.46,r*.2)});ctx.beginPath();ctx.arc(cx,cy+r*.67,r*.34,0,7);ctx.fill();line(cx,cy, cx,cy+r*.6);
 }else if(['gyro','vibration','sensor'].includes(name)){
   stroke(()=>ctx.arc(cx,cy,r*.78,0,7));stroke(()=>ctx.arc(cx,cy,r*.35,0,7));line(cx-r*.96,cy,cx-r*.43,cy);line(cx+r*.43,cy,cx+r*.96,cy);
 }else if(name==='microphone'){
   stroke(()=>ctx.roundRect(cx-r*.35,cy-r,r*.7,r*1.25,r*.34));stroke(()=>ctx.arc(cx,cy,r*.7,0,Math.PI));line(cx,cy+r*.7,cx,cy+r);line(cx-r*.46,cy+r,cx+r*.46,cy+r);
 }else if(name==='battery'){
   stroke(()=>ctx.roundRect(cx-r*.9,cy-r*.5,r*1.55,r,r*.12));ctx.fillRect(cx+r*.66,cy-r*.2,r*.25,r*.4);ctx.fillRect(cx-r*.58,cy-r*.24,r*.75,r*.48);
 }else if(name==='voltage'){
   stroke(()=>{ctx.moveTo(cx+r*.08,cy-r);ctx.lineTo(cx-r*.55,cy+r*.1);ctx.lineTo(cx+r*.05,cy+r*.1);ctx.lineTo(cx-r*.09,cy+r);ctx.lineTo(cx+r*.58,cy-r*.23);ctx.lineTo(cx,cy-r*.23)});
 }else if(name==='can'){
   stroke(()=>ctx.roundRect(cx-r*.94,cy-r*.64,r*1.88,r*1.28,r*.18));ctx.font=`bold ${Math.max(9,r*.68)}px system-ui`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('CAN',cx,cy);
 }else if(['pressure','speed'].includes(name)){
   stroke(()=>ctx.arc(cx,cy,r*.86,Math.PI,2*Math.PI));line(cx,cy,cx+r*.51,cy-r*.57);ctx.beginPath();ctx.arc(cx,cy,r*.11,0,7);ctx.fill();
 }else if(['gps','antenna'].includes(name)){
   line(cx,cy+r, cx,cy-r*.7);line(cx-r*.7,cy+r, cx+r*.7,cy+r);stroke(()=>ctx.arc(cx,cy-r*.7,r*.2,0,7));
 }else if(name==='water'){
   stroke(()=>{ctx.moveTo(cx,cy-r);ctx.bezierCurveTo(cx+r*1.4,cy+r*.3,cx+r*.6,cy+r, cx,cy+r);ctx.bezierCurveTo(cx-r*.7,cy+r,cx-r*1.3,cy+r*.2,cx,cy-r)})
 }else if(name==='light'){
   stroke(()=>ctx.arc(cx,cy-r*.2,r*.55,0,7));line(cx-r*.33,cy+r*.5,cx+r*.33,cy+r*.5);line(cx-r*.2,cy+r*.78,cx+r*.2,cy+r*.78);
 }
 ctx.restore();
}
function hexColor(x){return /^#[0-9a-f]{6}$/i.test(x||'')?x:'#ffffff'}
function drawText(text,x,y,w,h,fg,size=12){ctx.fillStyle=fg;ctx.font=`bold ${size}px system-ui,sans-serif`;ctx.textAlign='center';ctx.textBaseline='middle';let st=String(text||'');while(ctx.measureText(st).width>w-6&&st.length>3)st=st.slice(0,-2)+'…';ctx.fillText(st,x+w/2,y+h/2)}
function rounded(x,y,w,h,r,fill){ctx.fillStyle=fill;ctx.beginPath();ctx.roundRect(x,y,w,h,Math.min(r,w/2,h/2));ctx.fill()}
function widgetSignal(w){if(w.source==='wifi_rssi')return -67;if(w.source==='battery_percent')return batteryPreviewPct();if(w.source==='battery_voltage')return demoVoltage;if((w.source||'').startsWith('logic:')){const data=liveReadings[w.source.slice(6)];if(data&&Number.isFinite(data.value))return data.value}return Number(w.level??0)}
function widgetFraction(w){const min=Number(w.min??0),max=Number(w.max??100);return clamp((widgetSignal(w)-min)/Math.max(0.000001,max-min),0,1)}
function fmtWidget(w){const val=widgetSignal(w),precision=Number(w.precision??1);return ((w.type==='integer'||w.type==='digital')?String(Math.round(val)):val.toFixed(Math.max(0,Math.min(3,precision))))+(w.unit||'')}

// CYD Studio Visual 2.27 — native Canvas design preview for the same LVGL styling
// generated by lvgl_renderer.py. No external editor assets are required.
function visualPanel(x,y,w,h,accent,skin,isButton=false){
 const industrial=skin==='industrial',fgTop=industrial?'#2c3943':'#1c354c',fgBottom=industrial?'#101b25':'#091625';
 ctx.save();const g=ctx.createLinearGradient(0,y,0,y+h);
 if(isButton){g.addColorStop(0,accent);g.addColorStop(1,'#102f44');}
 else{g.addColorStop(0,fgTop);g.addColorStop(1,fgBottom)}
 rounded(x,y,w,h,Math.min(10,h/4),g);ctx.strokeStyle=industrial?'#65818b':'#365f79';ctx.lineWidth=1;
 ctx.beginPath();ctx.roundRect(x+.5,y+.5,Math.max(1,w-1),Math.max(1,h-1),Math.min(10,h/4));ctx.stroke();
 // No decorative stripe: LVGL native panel doesn't add one.
 ctx.restore();
}
function visualCaption(txt,x,y,w,color='#a5c3d9',sz=10){
 ctx.save();ctx.font=`500 ${sz}px system-ui,sans-serif`;ctx.textAlign='left';ctx.textBaseline='top';ctx.fillStyle=color;
 let t=String(txt||'');while(ctx.measureText(t).width>w-2&&t.length>3)t=t.slice(0,-2)+'…';ctx.fillText(t,x,y);ctx.restore();
}
function visualBar(x,y,w,h,value,accent){
 rounded(x,y,w,h,Math.min(h/2,8),'#31495c');
 const filled=Math.max(0,w*clamp(value,0,1));if(filled){const grad=ctx.createLinearGradient(x,y,x+w,y);grad.addColorStop(0,accent);grad.addColorStop(1,'#8bf4db');rounded(x,y,filled,h,Math.min(h/2,8),grad)}
}
function drawVisualProWidget(w){
 const type=w.type,skin=w.visualStyle||current().uiTheme||'neo';
 if(skin==='legacy'||['text','rect','frame','circle','line','custom','draw'].includes(type))return false;
 const x=w.x,y=w.y,ww=w.w,hh=w.h,accent=hexColor(w.bg),fg=hexColor(w.fg),v=widgetSignal(w),frac=widgetFraction(w);
 visualPanel(x,y,ww,hh,accent,skin,type==='button');
 const caption=(v='',sz=12)=>visualCaption(v,x+8,y+3,ww-16,skin==='industrial'?'#e5cda9':'#a5c3d9',sz);
 if(type==='button'){drawText(w.text||'BUTTON',x+7,y+5,ww-14,hh-10,'#ffffff',14);return true}
 if(['value','analog','integer','digital','rfrssi'].includes(type)){
  if(hh>37)caption(w.text||type.toUpperCase());
  const txt=type==='digital'?(v>=Number(w.threshold??.5)?'ON':'OFF'):type==='rfrssi'?`${Math.round(v)} dBm`:fmtWidget(w);
  const ty=hh>37?y+18:y+2, th=hh>37?hh-20:hh-4;
  drawText(txt,x+7,ty,ww-14,th,type==='digital'?(v>=Number(w.threshold??.5)?'#70f5ae':'#ff9d87'):accent,Math.min(24,Math.max(12,Math.round(th*.64))));return true;
 }
 if(['bar','progress'].includes(type)){
  // Separate typography and indicator rows; never draw a rail under a number.
  const rh=hh>=28?Math.max(3,Math.min(9,hh*.16)):1,railY=y+hh-rh-4;
  if(hh>=48){visualCaption(w.text||type.toUpperCase(),x+8,y+3,ww-16);drawText(`${Math.round(frac*100)}%`,x+5,y+19,ww-10,Math.max(12,railY-y-21),'#eafaff',12)}
  else{visualCaption(w.text||type.toUpperCase(),x+8,y+3,Math.max(1,ww*.55-8));drawText(`${Math.round(frac*100)}%`,x+ww*.58,y+2,ww*.40,17,'#eafaff',11)}
  if(hh>=28)visualBar(x+8,railY,ww-16,rh,frac,accent);
  return true;
 }
 if(type==='slider'){
  visualCaption(w.text||'SLIDER',x+8,y+3,Math.max(1,ww*.56-10));
  drawText(fmtWidget(w),x+ww*.58,y+2,ww*.38,18,fg,12);
  const by=y+hh*.75;
  visualBar(x+13,by-4,ww-26,8,frac,accent);
  ctx.fillStyle='#ffffff';ctx.beginPath();ctx.arc(x+13+(ww-26)*frac,by,Math.min(10,hh*.16),0,2*Math.PI);ctx.fill();ctx.strokeStyle=accent;ctx.lineWidth=2;ctx.stroke();return true;
 }
 if(type==='gauge'){
  caption(w.text||'GAUGE');const diameter=Math.max(24,Math.min(ww-14,hh-66));const cx=x+ww/2,cy=y+19+diameter/2,r=diameter/2,angle=t=>Math.PI*.75+Math.PI*1.5*t;
  ctx.save();ctx.lineCap='butt';
  for(let j=0;j<21;j++){const a=angle(j/20),major=j%5===0;ctx.strokeStyle=major?'#def7ff':'#8daecb';ctx.lineWidth=major?2:1;ctx.beginPath();ctx.moveTo(cx+Math.cos(a)*(r-(major?13:7)),cy+Math.sin(a)*(r-(major?13:7)));ctx.lineTo(cx+Math.cos(a)*r,cy+Math.sin(a)*r);ctx.stroke()}
  const nlab=diameter>=140?5:3;
  if(diameter>=110)for(let j=0;j<nlab;j++){const a=angle(j/(nlab-1)),v=Number(w.min??0)+(Number(w.max??100)-Number(w.min??0))*j/(nlab-1);ctx.fillStyle='#eaf9ff';ctx.font='10px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(v.toFixed(Number(w.precision??1)),cx+Math.cos(a)*(r-25),cy+Math.sin(a)*(r-25))}
  else {visualCaption(Number(w.min??0).toFixed(0),x+9,y+hh-44,47,'#eef7ff',10);visualCaption(Number(w.max??100).toFixed(0),x+ww-52,y+hh-44,47,'#eef7ff',10)}
  const ar=Math.max(5,(diameter-32)/2-5);ctx.lineWidth=9;ctx.strokeStyle='#284357';ctx.beginPath();ctx.arc(cx,cy,ar,Math.PI*.75,Math.PI*2.25);ctx.stroke();ctx.strokeStyle=accent;ctx.beginPath();ctx.arc(cx,cy,ar,Math.PI*.75,angle(frac));ctx.stroke();ctx.restore();
  drawText(fmtWidget(w),x,y+hh-29,ww,24,'#ffffff',14);caption(w.text||'GAUGE');return true;
 }
 if(type==='battery'){
  const pct=clamp(w.source?.startsWith('logic:')?v:batteryPreviewPct(),0,100);
  visualCaption(w.text||'BATTERY',x+8,y+3,Math.max(5,ww-70));
  drawText(`${Math.round(pct)}%`,x+ww-55,y+1,48,18,'#ffffff',12);
  const bx=x+9,by=y+hh-17,bw=ww-27,bh=9;
  ctx.strokeStyle='#adcbd6';ctx.lineWidth=2;ctx.strokeRect(bx,by,bw,bh);ctx.fillStyle='#adcbd6';ctx.fillRect(bx+bw+2,by+bh*.3,4,bh*.4);
  visualBar(bx+2,by+2,bw-4,Math.max(2,bh-4),pct/100,pct<20?'#f77f63':'#36dca7');return true;
 }
 if(['led','switch','checkbox'].includes(type)){
  const on=v>=Number(w.threshold??.5);caption(w.text||type.toUpperCase());
  if(type==='led'){
   const cx=x+ww/2,cy=y+hh*.48,r=Math.max(5,Math.min(ww,hh)*.17);
   ctx.beginPath();ctx.arc(cx,cy,r,0,7);ctx.fillStyle=on?accent:'#3a4a5a';ctx.fill();ctx.strokeStyle='#2b5061';ctx.lineWidth=1;ctx.stroke();
  }else if(type==='switch'){
   const bw=Math.min(67,ww-18),cx=x+(ww-bw)/2,cy=y+hh*.42+2;
   rounded(cx,cy-12,bw,24,12,on?accent:'#456173');rounded(cx+(on?bw-24:2),cy-10,20,20,10,'#eafffb');
  }else{ctx.strokeStyle=on?accent:'#7194a9';ctx.lineWidth=2;ctx.strokeRect(x+12,y+hh*.39,18,18);if(on){ctx.strokeStyle='#ffffff';ctx.lineWidth=2.5;ctx.beginPath();ctx.moveTo(x+15,y+hh*.49);ctx.lineTo(x+20,y+hh*.55);ctx.lineTo(x+29,y+hh*.38);ctx.stroke()}}
  if(type!=='led')drawText(on?'ON':'OFF',x+5,y+hh-19,ww-10,17,fg,12);else drawText(on?'ON':'OFF',x+5,y+hh-19,ww-10,17,fg,12);
  return true;
 }
 if(type==='waterfall'||type==='spectrum'){
  const pad=7,head=Math.min(20,Math.round(hh*.21)),ch=hh-head-13;
  caption(type==='waterfall'?(w.waterfallMode==='adc_fft'?'ADC35  /  FFT WATERFALL':'CC1101  /  WATERFALL'):'ADC  /  FFT SPECTRUM',9);
  if(type==='waterfall'){
   const ncol=55,nrow=24;
   for(let row=0;row<nrow;row++)for(let col=0;col<ncol;col++){
    const peak=Math.exp(-Math.pow((col-13-(row%6)*.7)/3.6,2))+.8*Math.exp(-Math.pow((col-37+(row%5)*.5)/4.2,2))+.09*Math.abs(Math.sin(row*.31+col*.7));
    const strength=clamp(peak,0,1);
    let rr=0,gg=0,bb=0;
    if(strength<.35){const q=strength/.35;rr=7;gg=15+85*q;bb=38+130*q}
    else if(strength<.70){const q=(strength-.35)/.35;rr=7+120*q;gg=100+145*q;bb=168-75*q}
    else{const q=(strength-.70)/.30;rr=127+128*q;gg=245-70*q;bb=93-70*q}
    ctx.fillStyle=`rgb(${Math.round(rr)},${Math.round(gg)},${Math.round(bb)})`;
    ctx.fillRect(x+pad+col*(ww-2*pad)/ncol,y+head+row*ch/nrow,Math.ceil((ww-2*pad)/ncol),Math.ceil(ch/nrow));
   }
  }else{
   ctx.strokeStyle='#244156';ctx.lineWidth=1;for(let r=1;r<=3;r++){const yy=y+head+r*ch/4;ctx.beginPath();ctx.moveTo(x+pad,yy);ctx.lineTo(x+ww-pad,yy);ctx.stroke()}
   for(let col=0;col<32;col++){
    const peak=.06+Math.exp(-Math.pow((col-9)/2.8,2))*.9+.55*Math.exp(-Math.pow((col-23)/3,2));
    const bh=clamp(peak,0,1)*ch*.92;
    ctx.fillStyle=col<18?accent:'#67bffc';ctx.fillRect(x+pad+col*(ww-2*pad)/32,y+head+ch-bh,Math.max(1,(ww-2*pad)/32-1),bh);
   }
  }
  visualCaption(type==='spectrum'?'0 Hz                                     2 kHz':w.waterfallMode==='adc_fft'?'0 Hz                                  2 kHz':'RF SWEEP',x+pad,y+hh-11,ww-2*pad,'#89afc7',9);return true;
 }
 if(['wifi','gyro','audio','mic','icon','rfwave','rfsignal'].includes(type)){
  caption(w.text||type.toUpperCase());
  if(type==='icon'){drawSensorSymbol(x+ww/2,y+hh*.61,Math.min(ww,hh)*.23,w.iconName||'wifi',accent);return true}
  if(type==='rfwave'){
   const diameter=Math.max(18,Math.min(Math.floor(ww/3),hh-25));
   const cx=x+8+diameter/2,cy=y+Math.max(18,Math.floor((hh-diameter)/2))+diameter/2;
   const a=.75*Math.PI,b=(.75+1.5*frac)*Math.PI;
   ctx.lineWidth=5;ctx.strokeStyle='#284357';ctx.beginPath();ctx.arc(cx,cy,diameter/2-4,a,2.25*Math.PI);ctx.stroke();
   ctx.strokeStyle=accent;ctx.beginPath();ctx.arc(cx,cy,diameter/2-4,a,b);ctx.stroke();
   drawText(`${Math.round(v)} dBm`,x+diameter+12,y+Math.max(23,hh/2-9),Math.max(12,ww-diameter-16),17,fg,12);
  }else{
   const val=type==='rfsignal'?`${Math.round(v)} dBm`:fmtWidget(w);
   drawText(val,x+8,y+Math.max(17,hh/3),ww-16,19,fg,12);
   visualBar(x+8,y+Math.max(22,Math.floor(hh*2/3)),ww-16,Math.max(6,Math.min(13,Math.floor(hh/5))),frac,accent);
  }
  return true;
 }
 return false;
}

function renderCanvas(){const d=current();if(!d.scenes.length)return;resizeStage();const s=scene();ctx.clearRect(0,0,screenW(),screenH());ctx.fillStyle=hexColor(s.bg);ctx.fillRect(0,0,screenW(),screenH());
  for(const w of s.widgets){const {x,y,w:ww,h:hh}=w;const bg=hexColor(w.bg),fg=hexColor(w.fg);
    if(drawVisualProWidget(w)){}
    else if(w.type==='button'){rounded(x,y,ww,hh,8,bg);drawText(w.text,x,y,ww,hh,fg,12)}
    else if(w.type==='text'){drawText(w.source==='battery_voltage'?demoVoltage.toFixed(2)+' V':w.source==='battery_percent'?batteryPreviewPct()+'%':w.text,x,y,ww,hh,bg,17)}
    else if(w.type==='rect'){ctx.fillStyle=bg;ctx.fillRect(x,y,ww,hh)}
    else if(w.type==='frame'){ctx.strokeStyle=bg;ctx.lineWidth=2;ctx.strokeRect(x,y,ww,hh)}
    else if(w.type==='circle'){ctx.fillStyle=bg;ctx.beginPath();ctx.ellipse(x+ww/2,y+hh/2,Math.max(1,ww/2),Math.max(1,hh/2),0,0,Math.PI*2);ctx.fill()}
    else if(w.type==='line'){ctx.strokeStyle=bg;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+ww-1,y+hh-1);ctx.stroke()}
    else if(['bar','progress'].includes(w.type)){ctx.strokeStyle=fg;ctx.lineWidth=1;ctx.strokeRect(x,y,ww,hh);ctx.fillStyle=bg;ctx.fillRect(x+2,y+2,(ww-4)*widgetFraction(w),Math.max(0,hh-4));if(w.type==='progress')drawText(Math.round(widgetFraction(w)*100)+'%',x,y,ww,hh,fg,12)}
    else if(['value','analog','integer'].includes(w.type)){rounded(x,y,ww,hh,7,'#172b40');drawText(fmtWidget(w),x,y,ww,hh,bg,Math.min(23,Math.round(hh/2)));if(w.text&&hh>40){ctx.textAlign='left';ctx.font='10px sans-serif';ctx.fillStyle=fg;ctx.fillText(w.text,x+6,y+8)}}
    else if(['digital','led'].includes(w.type)){const on=widgetSignal(w)>=Number(w.threshold??.5);if(w.type==='led'){ctx.beginPath();ctx.arc(x+ww/2,y+hh/2,Math.min(ww,hh)*.34,0,Math.PI*2);ctx.fillStyle=on?bg:'#394957';ctx.fill();ctx.strokeStyle=fg;ctx.lineWidth=2;ctx.stroke();}else{rounded(x,y,ww,hh,8,on?bg:'#42506b');drawText(on?'ON':'OFF',x,y,ww,hh,'#ffffff',16)}}
    else if(w.type==='slider'){rounded(x,y,ww,hh,6,'#172b40');const sx=x+13,ex=x+ww-13,cy=y+hh*.59;ctx.fillStyle='#456179';ctx.fillRect(sx,cy-3,ex-sx,6);ctx.fillStyle=bg;ctx.fillRect(sx,cy-3,(ex-sx)*widgetFraction(w),6);ctx.beginPath();ctx.arc(sx+(ex-sx)*widgetFraction(w),cy,9,0,Math.PI*2);ctx.fillStyle=fg;ctx.fill();drawText(`${w.text||'SLIDER'}: ${fmtWidget(w)}`,x,y,ww,Math.min(27,hh/2),fg,11)}
    else if(w.type==='gauge'){rounded(x,y,ww,hh,8,'#152738');const cx=x+ww/2,cy=y+hh*.5-5,r=Math.max(22,Math.min(ww-12,hh-12)/2-6);const angle=t=>Math.PI*.75+Math.PI*1.5*t;for(let j=0;j<21;j++){const a=angle(j/20),major=j%5===0;ctx.strokeStyle=major?'#def7ff':'#8daecb';ctx.lineWidth=major?2:1;ctx.beginPath();ctx.moveTo(cx+Math.cos(a)*(r-(major?13:7)),cy+Math.sin(a)*(r-(major?13:7)));ctx.lineTo(cx+Math.cos(a)*r,cy+Math.sin(a)*r);ctx.stroke()}for(let j=0;j<5;j++){const a=angle(j/4),v=Number(w.min??0)+(Number(w.max??100)-Number(w.min??0))*j/4,txt=v.toFixed(Number(w.precision??1));ctx.fillStyle='#eaf9ff';ctx.font='10px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(txt,cx+Math.cos(a)*(r-25),cy+Math.sin(a)*(r-25))}const rad=r-19;ctx.lineWidth=7;ctx.strokeStyle='#284357';ctx.beginPath();ctx.arc(cx,cy,rad,Math.PI*.75,Math.PI*2.25);ctx.stroke();ctx.strokeStyle=bg;ctx.beginPath();ctx.arc(cx,cy,rad,Math.PI*.75,angle(widgetFraction(w)));ctx.stroke();drawText(fmtWidget(w),x,y+hh-31,ww,24,'#ffffff',14)}
    else if(w.type==='switch'){rounded(x,y,ww,hh,9,'#203448');const on=widgetSignal(w)>=Number(w.threshold??.5),px=on?x+ww-27:x+8;rounded(x+5,y+hh/2-13,ww-10,26,14,on?bg:'#485b6b');ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(px+10,y+hh/2,10,0,2*Math.PI);ctx.fill();drawText(w.text,x,y,ww,hh*.35,fg,11)}
    else if(w.type==='checkbox'){rounded(x,y,ww,hh,5,'#18314a');ctx.strokeStyle=fg;ctx.strokeRect(x+6,y+hh/2-9,18,18);if(widgetSignal(w)>=Number(w.threshold??.5)){ctx.fillStyle=bg;ctx.fillRect(x+9,y+hh/2-6,12,12)}ctx.textAlign='left';ctx.textBaseline='middle';ctx.fillStyle=fg;ctx.font='bold 12px sans-serif';ctx.fillText(w.text||'CHECK',x+32,y+hh/2)}
    else if(w.type==='battery'){ctx.strokeStyle=fg;ctx.lineWidth=2;ctx.strokeRect(x,y,ww-7,hh);ctx.fillStyle=fg;ctx.fillRect(x+ww-5,y+hh/3,5,hh/3);const pct=clamp(w.source?.startsWith('logic:')?widgetSignal(w):batteryPreviewPct(),0,100);ctx.fillStyle=pct<20?'#ef665c':'#48c981';ctx.fillRect(x+3,y+3,Math.max(0,(ww-13)*pct/100),hh-6);drawText(Math.round(pct)+'%',x,y,ww-7,hh,'#ffffff',12)}
    else if(w.type==='icon'){rounded(x,y,ww,hh,8,'#132c41');drawSensorSymbol(x+ww/2,y+hh/2,Math.min(ww,hh)*.35,w.iconName||'wifi',bg);}
    else if(w.type==='custom'){rounded(x,y,ww,hh,7,bg);drawText(w.text,x,y,ww,hh,fg,12)}
    else if(w.type==='wifi'){rounded(x,y,ww,hh,7,'#123448');drawSensorSymbol(x+ww*.22,y+hh*.50,Math.min(ww*.18,hh*.40),'wifi','#48e5be');drawText('Wi-Fi',x+ww*.40,y,ww*.58,hh,'#fff',13)}
    else if(w.type==='gyro'){rounded(x,y,ww,hh,7,'#125a70');drawSensorSymbol(x+ww*.22,y+hh*.5,Math.min(ww*.17,hh*.38),'gyro','#a2eefe');drawText('GYRO',x+ww*.36,y,ww*.64,hh,'#fff',14)}
    else if(['rfwave','rfsignal','rfrssi'].includes(w.type)){
      rounded(x,y,ww,hh,7,'#10273c');
      const radio=String(w.radioType||'wifi').toUpperCase(),raw=widgetSignal(w),valid=Number.isFinite(raw);
      const level=valid?widgetFraction(w):0;
      const signalColor=level<.25?'#fa777b':level<.55?'#efb957':bg;
      ctx.font='bold 10px system-ui,sans-serif';ctx.textAlign='left';ctx.textBaseline='top';ctx.fillStyle=fg;
      ctx.fillText(radio.slice(0,14),x+7,y+5);ctx.font='8px system-ui,sans-serif';ctx.textAlign='right';ctx.fillStyle='#8eacbf';ctx.fillText(w.source==='constant'?'DEMO':'PREVIEW',x+ww-5,y+5);
      if(w.type==='rfwave'){
        const cx=x+Math.min(35,ww*.22),cy=y+hh*.61,maxRadius=Math.max(4,Math.min(hh*.34,ww*.17));
        const phase=(Date.now()%1400)/1400;
        ctx.fillStyle=signalColor;ctx.beginPath();ctx.arc(cx,cy,3,0,Math.PI*2);ctx.fill();
        for(let i=0;i<3;i++){
          ctx.beginPath();ctx.strokeStyle=signalColor;ctx.globalAlpha=valid?(0.25+0.7*((i/3+phase)%1)):0.15;
          ctx.lineWidth=Math.max(1.5,maxRadius/13);
          ctx.arc(cx,cy,maxRadius*(i+1)/3,-Math.PI*.46,Math.PI*.46);ctx.stroke();
        }ctx.globalAlpha=1;
        const text=valid?Math.round(raw)+' dBm':'NO RSSI';
        drawText(text,x+ww*.40,y+hh*.26,ww*.56,hh*.57,fg,Math.min(15,hh*.20));
      }else if(w.type==='rfsignal'){
        const barHeight=hh*.50,bottom=y+hh*.76,spacing=Math.max(5,Math.min(17,(ww-19)/8));
        for(let i=0;i<5;i++){const bh=barHeight*(i+1)/5;ctx.fillStyle=valid&&level>i/5?signalColor:'#344e63';ctx.fillRect(x+8+i*spacing,bottom-bh,Math.max(4,spacing-3),bh)}
        ctx.fillStyle=fg;ctx.font='bold 12px system-ui,sans-serif';ctx.textAlign='right';ctx.textBaseline='middle';ctx.fillText(valid?Math.round(raw)+' dBm':'N/A',x+ww-7,y+hh*.60);
      }else{
        const text=valid?Math.round(raw)+' dBm':'N/A';drawText(text,x+2,y+hh*.22,ww-4,hh*.69,signalColor,Math.max(12,Math.min(23,hh*.40)));
      }
    }
    else if(w.type==='waterfall'||w.type==='spectrum'){
      rounded(x,y,ww,hh,5,'#071321');const head=Math.min(21,hh*.18);
      ctx.textAlign='left';ctx.textBaseline='top';ctx.font='bold 10px system-ui';ctx.fillStyle='#98f0ce';
      ctx.fillText(w.type==='waterfall'?(w.waterfallMode==='adc_fft'?'ADC GPIO35 · FFT WATERFALL':'CC1101 · RSSI WATERFALL'):'ADC · FFT SPECTRUM',x+6,y+4);
      if(w.type==='waterfall'){
        for(let row=0;row<20;row++)for(let col=0;col<44;col++){
          const level=Math.max(0,Math.sin(col*.22+row*.06)**4+Math.sin(col*.6-row*.19)**10*.7);
          ctx.fillStyle=`hsl(${215-level*190},85%,${12+level*50}%)`;
          const xx=x+col*ww/44, yy=y+head+row*(hh-head-23)/20;
          ctx.fillRect(xx,yy,Math.ceil(ww/44),Math.ceil((hh-head-23)/20));
        }
        ctx.fillStyle='#a1bacd';ctx.font='9px system-ui';ctx.fillText(w.waterfallMode==='adc_fft'?'0 Hz':'433.3 MHz',x+4,y+hh-14);ctx.fillText(w.waterfallMode==='adc_fft'?'2000 Hz':'434.5 MHz',x+ww*.59,y+hh-14);
      }else{
        for(let bin=0;bin<30;bin++){
          const peak=Math.max(0,Math.exp(-(((bin-7)/3)**2))+Math.exp(-(((bin-19)/2.7)**2))*.65+(Math.sin(bin*3.1)**2)*.08);
          const bh=Math.min(hh-head-13,peak*(hh-head-13)*.84);
          ctx.fillStyle=bin<15?'#35d9a4':'#46a6f4';ctx.fillRect(x+bin*ww/30,y+hh-13-bh,Math.max(1,ww/30-1),bh);
        }
        ctx.fillStyle='#bddbec';ctx.font='9px system-ui';ctx.fillText('0 Hz',x+4,y+hh-11);ctx.fillText('Nyquist',x+ww*.69,y+hh-11);
      }
      ctx.fillStyle='#e5b960';ctx.font='8px system-ui';ctx.textAlign='right';ctx.fillText('PREVIEW',x+ww-4,y+hh-11);
    }
    else if(w.type==='audio'){rounded(x,y,ww,hh,7,'#344e6f');for(let j=0;j<15;j++){ctx.fillStyle=bg;let b=Math.abs(Math.sin(j*0.7))*hh*.56;ctx.fillRect(x+8+j*(ww-16)/15,y+(hh-b)/2,Math.max(2,(ww-16)/20),b)}drawText('AUDIO',x,y,ww,hh,'#fff',11)}
    else if(w.type==='draw'){ctx.strokeStyle=bg;ctx.lineWidth=2.5;ctx.lineCap='round';for(const path of w.paths||[]){ctx.beginPath();path.forEach((p,i)=>{if(i===0)ctx.moveTo(p[0],p[1]);else ctx.lineTo(p[0],p[1])});ctx.stroke()}}
    if(!preview&&!pen&&['battery','bar','progress','value','integer','analog','digital','led','slider','gauge','switch','checkbox','text','rfwave','rfsignal','rfrssi','waterfall','spectrum'].includes(w.type)){
      ctx.beginPath();ctx.arc(x+ww-5,y+hh-5,5,0,Math.PI*2);ctx.fillStyle=w.source?.startsWith('logic:')?'#32e7a9':'#54c9ff';ctx.fill();ctx.lineWidth=1.4;ctx.strokeStyle='#132132';ctx.stroke();
    }
    if(preview&&previewPressed===w.id){ctx.strokeStyle='#ffe09a';ctx.lineWidth=2.5;ctx.strokeRect(x+1.5,y+1.5,ww-3,hh-3)}
    if(sel===w.id&&!preview&&!pen){ctx.setLineDash([4,4]);ctx.lineWidth=1.5;ctx.strokeStyle='#ffffff';ctx.strokeRect(x,y,ww,hh);ctx.setLineDash([])}
  }
}
function rerender(){refreshImportedBlocks();refreshNav();renderExplorer();if(tab==='screen'){$('visualTheme').value=current().uiTheme||'neo';renderCanvas();inspector()}if(tab==='hardware')renderFeatures();if(tab==='pins')renderPins();if(tab==='grove')renderGrove();if(tab==='libs')renderLibs();if(tab==='build')renderBuild();if(tab==='logic')renderLogic();save()}
function selectTab(next){if(next==='mapping')next='logic';stopDemo();tab=next;document.querySelectorAll('[id^="tab_"]').forEach(n=>n.classList.add('hide'));$('tab_'+next).classList.remove('hide');document.querySelectorAll('#tabs button').forEach(n=>n.classList.toggle('active',n.dataset.tab===next));sel=null;rerender()}
$('tabs').addEventListener('click',e=>{let b=e.target.closest('[data-tab]');if(b)selectTab(b.dataset.tab)});
$('devlist').addEventListener('click',e=>{const b=e.target.closest('[data-dev]');if(!b)return;stopDemo();project.currentDevice=b.dataset.dev;sel=null;pen=false;preview=false;rerender()});
$('sceneList').addEventListener('click',e=>{const b=e.target.closest('[data-sc]');if(!b)return;current().currentScene=b.dataset.sc;sel=null;preview=false;pen=false;selectTab('screen')});
$('addDevice').addEventListener('click',()=>{mark();const p=$('newProfile').value,d=newDev(p,$('newName').value||presets[p].label);project.devices.push(d);project.currentDevice=d.id;sel=null;pen=false;preview=false;$('addDeviceBox').open=false;selectTab(presets[p].screen?'screen':'hardware');toast('Urządzenie dodane')});
function widgetCoords(e){const r=cv.getBoundingClientRect();return{x:clamp(Math.round((e.clientX-r.left)*screenW()/r.width),0,screenW()-1),y:clamp(Math.round((e.clientY-r.top)*screenH()/r.height),0,screenH()-1)}}
function hit(pt){
 const items=[...scene().widgets].reverse(),within=w=>pt.x>=w.x&&pt.x<w.x+w.w&&pt.y>=w.y&&pt.y<w.y+w.h;
 // Decorative layers may overlap the user-supplied design. They must not block
 // controls when the device preview is being used to test interactions.
 if(preview){const control=items.find(w=>['button','slider','switch','checkbox'].includes(w.type)&&within(w));if(control)return control;}
 return items.find(w=>w.type!=='draw'&&within(w));
}
function onDown(e){if(!current().scenes.length)return;const pt=widgetCoords(e),h=hit(pt);if(preview){if(h?.type==='button'&&h.to){current().currentScene=h.to;sel=null;rerender()}else if(h?.type==='button'){toast('Kliknięto: '+(h.text||'BUTTON'));previewPressed=h.id;renderCanvas();setTimeout(()=>{if(previewPressed===h.id){previewPressed=null;renderCanvas()}},220)}else if(h?.type==='slider'&&(!h.source||h.source==='constant')){mark();const fraction=clamp((pt.x-h.x-13)/Math.max(1,h.w-26),0,1);h.level=+(Number(h.min??0)+(Number(h.max??100)-Number(h.min??0))*fraction).toFixed(2);drag={type:'test-slider',id:h.id,pointer:e.pointerId};cv.setPointerCapture(e.pointerId);renderCanvas();save()}else if(h&&['switch','checkbox'].includes(h.type)&&(!h.source||h.source==='constant')){mark();h.level=widgetSignal(h)>=Number(h.threshold??.5)?0:1;renderCanvas();save()}return}
 if(h&&['battery','bar','progress','value','integer','analog','digital','led','slider','gauge','switch','checkbox','text','rfwave','rfsignal','rfrssi','waterfall','spectrum'].includes(h.type)&&Math.hypot(pt.x-(h.x+h.w-5),pt.y-(h.y+h.h-5))<11){connectScreenPort(h);return}e.preventDefault();cv.setPointerCapture(e.pointerId);if(pen){let brush=scene().widgets.findLast(w=>w.type==='draw'&&w.bg===penColor());if(!brush){mark();brush=W('draw','',0,0,screenW(),screenH(),penColor());scene().widgets.push(brush)}else mark();brush.paths.push([[pt.x,pt.y]]);drag={type:'draw',id:brush.id,pointer:e.pointerId};renderCanvas();return}
 sel=h?.id||null;if(h)drag={type:'move',id:h.id,pointer:e.pointerId,sx:pt.x,sy:pt.y,bx:h.x,by:h.y,changed:false};else drag=null;inspector();renderCanvas()}
function onMove(e){if(!drag||drag.pointer!==e.pointerId)return;const pt=widgetCoords(e),w=scene().widgets.find(w=>w.id===drag.id);if(!w)return;
 if(drag.type==='test-slider'){const f=clamp((pt.x-w.x-13)/Math.max(1,w.w-26),0,1);w.level=+(Number(w.min??0)+(Number(w.max??100)-Number(w.min??0))*f).toFixed(2);renderCanvas();save();return}
 if(drag.type==='draw'){const path=w.paths[w.paths.length-1];if(path.length<600)path.push([pt.x,pt.y]);renderCanvas();return}
 const x=clamp(drag.bx+pt.x-drag.sx,0,screenW()-w.w),y=clamp(drag.by+pt.y-drag.sy,0,screenH()-w.h);if(x===w.x&&y===w.y)return;if(!drag.changed){mark();drag.changed=true}w.x=x;w.y=y;renderCanvas()}
function onUp(e){if(!drag||drag.pointer!==e.pointerId)return;drag=null;rerender()}
cv.addEventListener('pointerdown',onDown);cv.addEventListener('pointermove',onMove);cv.addEventListener('pointerup',onUp);cv.addEventListener('pointercancel',onUp);
function penColor(){return $('sceneBg').dataset.pen||'#4cdaff'}
$('pen').addEventListener('click',()=>{preview=false;pen=!pen;sel=null;$('pen').classList.toggle('active',pen);$('testMode').classList.remove('active');$('editMode').classList.toggle('active',!pen);rerender();if(pen)toast('Rysuj palcem bezpośrednio po ekranie')});
$('tools').addEventListener('click',e=>{const b=e.target.closest('[data-add]');if(!b)return;const type=b.dataset.add;mark();pen=false;preview=false;$('pen').classList.remove('active');const sizes={icon:[58,58],text:[205,34],circle:[64,64],line:[140,55],battery:[135,50],bar:[170,32],progress:[170,32],led:[65,65],digital:[135,50],integer:[150,55],analog:[150,55],value:[150,55],slider:[185,61],gauge:[150,125],switch:[130,53],checkbox:[130,44],rfwave:[175,75],rfsignal:[175,70],rfrssi:[145,58],waterfall:[205,135],spectrum:[205,130]};const [rw,rh]=sizes[type]||[170,49];const w=Math.min(rw,screenW()-10),h=Math.min(rh,screenH()-10);
 const label={icon:'★',button:'BUTTON',text:'LABEL',gyro:'GYRO',wifi:'WiFi',audio:'AUDIO',battery:'BAT',custom:'CUSTOM',value:'VALUE',integer:'INTEGER',analog:'VOLTAGE',digital:'DIGITAL',led:'LED',slider:'SLIDER',gauge:'GAUGE',progress:'PROGRESS',switch:'SWITCH',checkbox:'CHECK',rfwave:'WiFi',rfsignal:'WiFi',rfrssi:'WiFi',waterfall:'CC1101',spectrum:'FFT AUDIO'}[type]||'';const ob=W(type,label,Math.round((screenW()-w)/2),clamp(35+scene().widgets.length*19,5,screenH()-h),w,h,type==='led'?'#37c87d':'#378fdb');ob.visualStyle=current().uiTheme||'neo';if(type==='icon')ob.iconName='wifi';scene().widgets.push(ob);sel=ob.id;rerender();toast('Widget added. Drag it on the LCD.')});
$('editMode').addEventListener('click',()=>{preview=false;pen=false;$('pen').classList.remove('active');$('editMode').classList.add('active');$('testMode').classList.remove('active');rerender()});
$('testMode').addEventListener('click',()=>{preview=true;pen=false;sel=null;$('pen').classList.remove('active');$('editMode').classList.remove('active');$('testMode').classList.add('active');rerender()});
$('png').addEventListener('click',()=>{renderCanvas();const a=document.createElement('a');a.download=current().name+'_'+scene().name+'.png';a.href=cv.toDataURL('image/png');a.click();toast(`PNG exported: ${screenW()}×${screenH()}`)});
$('exportSvg').addEventListener('click',async()=>{try{const r=await fetch('/api/svg',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project,device_id:current().id,scene_id:scene().id})});if(!r.ok)throw Error((await r.json()).error||'SVG export failed');downloadBlob(await r.blob(),`${current().name}_${scene().name}.svg`);toast('Screen SVG exported')}catch(e){toast('Start the local server: '+e.message)}});
$('visualTheme').addEventListener('change',e=>{if(!current().scenes.length)return;mark();const skin=e.target.value;current().uiTheme=skin;for(const w of scene().widgets)w.visualStyle=skin;renderCanvas();inspector();save();toast('Styl LVGL: '+e.target.selectedOptions[0].textContent)});
$('screenRotation').addEventListener('change',e=>{const d=current(),old=Number(d.rotation||0),next=Number(e.target.value);if(old===next)return;mark();const ow=old%2?320:240,oh=old%2?240:320,nw=next%2?320:240,nh=next%2?240:320;if((old%2)!==(next%2))for(const sc of d.scenes){for(const w of sc.widgets){w.x=Math.round(w.x*nw/ow);w.y=Math.round(w.y*nh/oh);w.w=Math.max(1,Math.min(nw-w.x,Math.round(w.w*nw/ow)));w.h=Math.max(1,Math.min(nh-w.y,Math.round(w.h*nh/oh)));if(w.type==='draw')for(const path of w.paths||[])for(const pt of path){pt[0]=Math.round(pt[0]*nw/ow);pt[1]=Math.round(pt[1]*nh/oh)}}}d.rotation=next;sel=null;rerender();toast('LCD orientation: '+(next%2?'Landscape · 320×240':'Portrait · 240×320'))});
$('sceneName').addEventListener('change',e=>{if(!current().scenes.length)return;mark();scene().name=e.target.value||scene().name;rerender()});$('sceneBg').addEventListener('input',e=>{if(!current().scenes.length)return;scene().bg=e.target.value;renderCanvas();save()});
function inspector(){
 const d=current();$('inspectorTitle').textContent=sel?'Widget settings':'Nothing selected';if(!d.scenes.length)return;
 const w=scene().widgets.find(w=>w.id===sel);if(!w||preview){$('inspector').innerHTML='<div class="inspector-empty">'+(preview?'TEST mode: tap a button, slider or switch.':'Select a widget to edit style, range and data binding.')+'</div>';return}
 const dest=d.scenes.map(s=>`<option value="${esc(s.id)}" ${w.to===s.id?'selected':''}>${esc(s.name)}</option>`).join('');
 const isRF=['rfwave','rfsignal','rfrssi','waterfall','spectrum'].includes(w.type);
 const bound=['battery','bar','progress','value','integer','analog','digital','led','slider','gauge','switch','checkbox','text', 'rfwave','rfsignal','rfrssi','waterfall','spectrum'].includes(w.type);
 const showRange=['bar','progress','value','integer','analog','digital','led','slider','gauge','switch','checkbox','rfwave','rfsignal','rfrssi','waterfall','spectrum'].includes(w.type);
 const options=[['constant',isRF?'Demo / constant RSSI':'Constant / touch value'],...(isRF&&w.radioType==='wifi'?[['wifi_rssi','Wi-Fi STA RSSI (automatic)']]:[]),['battery_percent','Battery level (%)'],['battery_voltage','Battery voltage (V)'],...ensureLogic().nodes.map(n=>['logic:'+n.id,'Block · '+(BLOCKS[n.type]?.label||n.type)+' · '+n.id.slice(-5)])];
 const radioField=isRF?`<div class="field"><label>Radio / protocol</label><select id="wradioType">${[['wifi','Wi-Fi STA'],['ble','Bluetooth LE'],['bt','Bluetooth Classic'],['espnow','ESP-NOW'],['lora','LoRa'],['cc1101','CC1101'],['nrf24','nRF24L01'],['zigbee','Zigbee / Thread'],['rf433','433 MHz RF'],['rf868','868 MHz RF'],['rf915','915 MHz RF'],['custom','Other / Custom']].map(([v,n])=>`<option value="${v}" ${w.radioType===v?'selected':''}>${n}</option>`).join('')}</select><div class="hint">Automatic RSSI is available for connected Wi-Fi STA. For other radios, connect an RSSI output from a sensor/driver block, or use Demo.</div></div>`:'';
 const sourceField=bound?`<div class="field"><label>Data source</label><select id="wsource">${options.map(([v,t])=>`<option value="${esc(v)}" ${w.source===v?'selected':''}>${esc(t)}</option>`).join('')}</select></div>`:'';
 const rangeFields=showRange?`<div class="two"><div class="field"><label>Minimum</label><input id="wmin" type="number" step="any" value="${Number(w.min??0)}"></div><div class="field"><label>Maximum</label><input id="wmax" type="number" step="any" value="${Number(w.max??100)}"></div></div><div class="two"><div class="field"><label>Value (when constant)</label><input id="wlevel" type="number" step="any" value="${Number(w.level??65)}"></div><div class="field"><label>Unit (e.g. V, A, °C)</label><input id="wunit" value="${esc(w.unit||'')}"></div></div><div class="two"><div class="field"><label>Decimals (0–3)</label><input id="wprecision" type="number" min="0" max="3" value="${Number(w.precision??1)}"></div><div class="field"><label>ON threshold (LED / Digital)</label><input id="wthreshold" type="number" step="any" value="${Number(w.threshold??0.5)}"></div></div>`:'';
 $('inspector').innerHTML=`<div class="stack"><div class="chiprow"><strong>${esc(w.type.toUpperCase())}</strong><button id="delWidget" class="red" style="margin-left:auto">Delete</button></div><div class="field"><label>Text</label><input id="wtext" maxlength="60" value="${esc(w.text)}"></div><div class="field"><label>Wizualny styl LVGL (preview + firmware)</label><select id="wvisualStyle"><option value="neo" ${((w.visualStyle||d.uiTheme||"neo")==="neo")?"selected":""}>NEON PRO</option><option value="industrial" ${((w.visualStyle||d.uiTheme||"neo")==="industrial")?"selected":""}>INDUSTRIAL</option><option value="legacy" ${((w.visualStyle||d.uiTheme||"neo")==="legacy")?"selected":""}>KLASYCZNY</option></select></div><div class="two"><div class="field"><label>Primary color</label><input id="wbg" type="color" value="${hexColor(w.bg)}"></div><div class="field"><label>Text / outline</label><input id="wfg" type="color" value="${hexColor(w.fg)}"></div></div><div class="two"><div class="field"><label>X</label><input id="wx" type="number" value="${w.x}"></div><div class="field"><label>Y</label><input id="wy" type="number" value="${w.y}"></div><div class="field"><label>Width</label><input id="ww" type="number" value="${w.w}"></div><div class="field"><label>Height</label><input id="wh" type="number" value="${w.h}"></div></div>${w.type==='button'?`<div class="field"><label>Navigate to screen</label><select id="wto"><option value="">None</option>${dest}</select></div>`:''}${radioField}${sourceField}${rangeFields}${w.type==='icon'?`<div class="field"><label>Sensor icon (offline vector; CYD-compatible)</label><select id="wiconName">${SENSOR_ICON_NAMES.map(n=>`<option ${w.iconName===n?'selected':''}>${n}</option>`).join('')}</select><p class="hint">Vector symbols: Wi-Fi, Bluetooth, CC1101 radio, M5 sensors, CAN, IMU and more. Can be drawn directly on the LCD.</p></div>`:''}${bound?'<button id="connectWidget" class="primary wide">● Connect input port → Blocks</button>':''}<div class="hint">Link a block to a widget through Data source. Slider and Switch can be controlled by touch when their source is Constant.</div></div>`;
 $('wvisualStyle').onchange=e=>{mark();w.visualStyle=e.target.value;renderCanvas();save()};
 if(w.type==='icon'){$('wiconName').onchange=e=>{mark();w.iconName=e.target.value;save();renderCanvas()}}
 if(bound)$('connectWidget').onclick=()=>connectScreenPort(w);if(isRF){$('wradioType').addEventListener('change',e=>{mark();w.radioType=e.target.value;w.text=e.target.selectedOptions[0].textContent.replace(' STA','');if(w.radioType!=='wifi'&&w.source==='wifi_rssi')w.source='constant';w.unit=' dBm';save();rerender()})}
 $('delWidget').onclick=()=>{mark();scene().widgets=scene().widgets.filter(o=>o.id!==sel);sel=null;rerender()};
 for(const [id,key] of [['wtext','text'],['wbg','bg'],['wfg','fg'],['wx','x'],['wy','y'],['ww','w'],['wh','h'],['wto','to'],['wlevel','level'],['wmin','min'],['wmax','max'],['wunit','unit'],['wprecision','precision'],['wthreshold','threshold'],['wsource','source']]){
  const el=$(id);if(!el)continue;el.addEventListener('focus',()=>mark(),{once:true});el.addEventListener('input',()=>{let v=el.value;if(['x','y','w','h','level','min','max','precision','threshold'].includes(key)){v=Number(v);if(!Number.isFinite(v))return;if(key==='x')v=clamp(Math.round(v),0,screenW()-w.w);else if(key==='y')v=clamp(Math.round(v),0,screenH()-w.h);else if(key==='w')v=clamp(Math.round(v),1,screenW()-w.x);else if(key==='h')v=clamp(Math.round(v),1,screenH()-w.y);else if(key==='precision')v=clamp(Math.round(v),0,3)}w[key]=v;renderCanvas();save()});el.addEventListener('change',()=>{renderCanvas();save()});
 }
}
function htmlField(name,label,val,type='text',note=''){return `<div class="field"><label for="${name}">${label}</label><input id="${name}" type="${type}" value="${esc(val)}" ${type==='number'?'step="any"':''}>${note?`<div class="hint">${note}</div>`:''}</div>`}
function onField(name,obj,key,callback){const n=$(name);if(!n)return;n.addEventListener('change',e=>{mark();obj[key]=n.type==='checkbox'?n.checked:n.type==='number'?+n.value:n.value;save();if(callback)callback()})}
function renderFeatures(){const d=current(),f=d.features,p=d.pins;const bluetoothClassic=presets[d.profile].bt,old=d.profile==='cyd28'||d.profile==='cyd24'||d.profile==='cyd28t'||d.profile==='atom'||d.profile==='esp32';
 $('features').innerHTML=`<div class="tile"><h3>Wi‑Fi / Hotspot (SoftAP)</h3><select id="wifi_mode"><option value="off">Wyłączone</option><option value="ap">Hotspot · CYD tworzy sieć</option><option value="sta">STA · łączy się z routerem</option><option value="ap_sta">AP + STA · oba tryby</option></select><div class="two">${htmlField('ap_ssid','Nazwa hotspotu',f.ap_ssid)}${htmlField('ap_password','Hasło hotspotu',f.ap_password)}</div><div class="two">${htmlField('sta_ssid','Wi‑Fi do połączenia',f.sta_ssid)}${htmlField('sta_password','Hasło Wi‑Fi',f.sta_password)}</div><div class="hint">Hasła trafią do firmware urządzenia — używaj osobnej sieci testowej.</div></div>
 <div class="tile"><h3>Bluetooth</h3><label class="toggle"><input id="ble" type="checkbox" ${f.ble?'checked':''}> BLE · reklamowany stos BLE</label><label class="toggle"><input id="bt_classic" type="checkbox" ${f.bt_classic?'checked':''} ${!bluetoothClassic?'disabled':''}> Bluetooth Classic (SPP) ${!bluetoothClassic?'— brak w S3':''}</label></div>
 <div class="tile"><h3>Żyroskop / IMU (MPU6050)</h3><label class="toggle"><input id="gyro" type="checkbox" ${f.gyro?'checked':''}> Aktywuj czujnik I2C</label><div class="two">${htmlField('i2c_sda','I2C SDA · GPIO',p.i2c_sda,'number')}${htmlField('i2c_scl','I2C SCL · GPIO',p.i2c_scl,'number')}</div><div class="hint">Czujnik zewnętrzny; adres I2C 0x68. Wartości będą widoczne na komponencie GYRO.</div></div>
 <div class="tile"><h3>Bateria</h3><label class="toggle"><input id="battery" type="checkbox" ${f.battery?'checked':''}> Odczyt napięcia przez ADC</label><div class="two">${htmlField('battery_adc','ADC · GPIO',p.battery_adc,'number')}${htmlField('battery_divider','Mnożnik dzielnika',p.battery_divider,'number')}</div><div class="card-note">CYD nie ma tu potwierdzonego wbudowanego pomiaru baterii. Potrzebny jest dzielnik napięcia i wejście ADC1; nie podłączaj baterii bezpośrednio do GPIO.</div></div>
 <div class="tile"><h3>Mikrofon i dźwięk przez Wi‑Fi</h3><label class="toggle"><input id="audio_rx" type="checkbox" ${f.audio_rx?'checked':''}> Odbieraj audio na CYD (DAC GPIO26)</label><label class="toggle"><input id="audio_tx" type="checkbox" ${f.audio_tx?'checked':''}> Nadaj z mikrofonu I2S (ATOM / ESP32)</label><div class="three">${htmlField('mic_bclk','BCLK',p.mic_bclk,'number')}${htmlField('mic_ws','WS',p.mic_ws,'number')}${htmlField('mic_din','DIN',p.mic_din,'number')}</div><div class="two">${htmlField('audio_dest','Adres IP CYD',f.audio_dest)}${htmlField('audio_port','Port UDP',f.audio_port,'number')}</div><div class="hint">Prototyp: 8 kHz / mono / PCM8 UDP. Odbiornik wymaga Wi‑Fi, a nadajnik mikrofonu I2S. Na CYD audio idzie na istniejące wyjście wzmacniacza GPIO26.</div></div>${['cyd28','cyd28usb','cyd28t','cyd24'].includes(d.profile)?`<div class="tile"><h3>LCD — kolory i sterownik (CYD)</h3><div class="field"><label>Panel</label><select id="lcdDriver"><option value="ili9341_2">ILI9341_2 (CYD R)</option><option value="ili9341">ILI9341</option><option value="st7789">ST7789 (część 2USB)</option></select></div><div class="two"><div class="field"><label>Kolory</label><select id="lcdOrder"><option value="bgr">BGR</option><option value="rgb">RGB</option></select></div><div class="field"><label>Inwersja</label><select id="lcdInversion"><option value="on">ON</option><option value="off">OFF</option></select></div></div><div class="hint">Jeżeli LCD ma brązowe/nieprawidłowe kolory, przestaw BGR/RGB lub inwersję i wygeneruj nowy BIN. Dla 2USB możliwy ST7789.</div></div>`:''}${['cyd28','cyd28usb','cyd28t','cyd24'].includes(d.profile)?`<div class="tile"><h3>Kalibracja dotyku XPT2046 — 5 punktów</h3><div class="hint"><b>W firmware:</b> przy pierwszym uruchomieniu dotknij 5 celowników. Macierz korekcji zapisuje się w oddzielnej partycji NVS <code>touchcal</code> (12 KB), niezależnej od firmware. Aby powtórzyć, przytrzymaj ekran 2 s podczas startu. Zmiana orientacji LCD uruchomi kalibrację ponownie. Ustawienia odbicia poniżej służą wyłącznie starszym generatorom.</div><div class="field"><label>Orientacja dotyku względem LCD</label><select id="touchPreset"><option value="none">Normalny</option><option value="mirror-x">Odbicie X (lewo/prawo)</option><option value="mirror-y">Odbicie Y (góra/dół)</option><option value="mirror-xy">Odbicie X + Y (180°)</option><option value="swap">Zamień X/Y</option><option value="swap-mirror-x">Zamień X/Y + odbicie X</option><option value="swap-mirror-y">Zamień X/Y + odbicie Y</option><option value="swap-mirror-xy">Zamień X/Y + odbicie X/Y</option><option value="custom">Ustawienia własne</option></select><button id="resetTouch231" type="button" class="wide">Przywróć ustawienia dotyku CYD 2.8 R · 1 USB</button></div><div class="two">${htmlField('xmin','Raw X min',d.touch.xmin,'number')}${htmlField('xmax','Raw X max',d.touch.xmax,'number')}${htmlField('ymin','Raw Y min',d.touch.ymin,'number')}${htmlField('ymax','Raw Y max',d.touch.ymax,'number')}</div><label class="toggle"><input id="swap" type="checkbox" ${d.touch.swap?'checked':''}> Zamień osie X / Y</label><label class="toggle"><input id="flipX" type="checkbox" ${d.touch.flipX?'checked':''}> Odwróć X</label><label class="toggle"><input id="flipY" type="checkbox" ${d.touch.flipY?'checked':''}> Odwróć Y</label><div class="hint">Przyciski i dotyk korzystają z tych samych współrzędnych 240×320. Kalibracja może się różnić między rewizjami.</div></div>`:''}`;
 d.lcd=d.lcd||{driver:d.profile==='cyd28usb'?'st7789':'ili9341_2',order:d.profile==='cyd28usb'?'bgr':'rgb',inversion:'off'};
 for(const [id,k,def] of [['lcdDriver','driver','ili9341_2'],['lcdOrder','order','rgb'],['lcdInversion','inversion','off']]){const el=$(id);if(el){el.value=d.lcd[k]||def;onField(id,d.lcd,k)}}
 $('wifi_mode').value=f.wifi_mode||'off';onField('wifi_mode',f,'wifi_mode');for(const key of ['ap_ssid','ap_password','sta_ssid','sta_password','ble','bt_classic','gyro','battery','audio_rx','audio_tx','audio_dest','audio_port'])onField(key,f,key);for(const key of ['i2c_sda','i2c_scl','battery_adc','battery_divider','mic_bclk','mic_ws','mic_din'])onField(key,p,key);for(const key of ['xmin','xmax','ymin','ymax','swap','flipX','flipY'])onField(key,d.touch,key,()=>{if(key==='swap'||key==='flipX'||key==='flipY')renderFeatures()});
 const resetTouch=$('resetTouch231');if(resetTouch)resetTouch.onclick=()=>{mark();Object.assign(d.touch,{swap:false,flipX:d.profile==='cyd28',flipY:d.profile==='cyd28',xmin:200,xmax:3900,ymin:200,ymax:3900,orientationVersion:4});save();renderFeatures();toast('CYD 2.8 R · 1 USB: X/Y skorygowane. Wygeneruj BIN.');};
 const touchPreset=$('touchPreset');if(touchPreset){const states=['none','mirror-x','mirror-y','mirror-xy','swap','swap-mirror-x','swap-mirror-y','swap-mirror-xy'];const bits=Number(!!d.touch.swap)*4+Number(!!d.touch.flipX)+Number(!!d.touch.flipY)*2;touchPreset.value=states[bits];touchPreset.onchange=()=>{const v=touchPreset.value;if(v==='custom')return;mark();d.touch.swap=v.startsWith('swap');d.touch.flipX=v.includes('mirror-x')||v.includes('mirror-xy');d.touch.flipY=v.includes('mirror-y')||v.includes('mirror-xy');save();renderFeatures();toast('Dotyk: '+v+'. Wygeneruj nowy BIN.');};}
 
 $('catalog').innerHTML=groups.filter(row=>!(d.profile==='s3'&&row[1]==='Bluetooth Classic')).map(([cat,name,req,st])=>`<div class="tile" style="margin:0"><b>${esc(name)}</b><br><span class="hint">${esc(cat)} · ${esc(req)}</span><br><span class="pill ${st==='gotowe'?'good':'warn'}">${st==='gotowe'?'generator':'katalog / własny kod'}</span></div>`).join('')}
function renderPins(){const d=current(),p=presets[d.profile];$('pinmap').innerHTML='<div class="notice"><b>'+esc(p.label)+'</b> · '+esc(p.desc)+'<br>Pozycje na złączach dotyczą referencyjnych wersji; u klonów mogą występować zmiany.</div>'+p.connectors.map(([title,pins])=>`<div class="port"><h3>${esc(title)}</h3>${pins.map(([pin,desc])=>`<div class="pin-row"><strong>${esc(pin)}</strong><span>${esc(desc)}</span></div>`).join('')}</div>`).join('')+(d.profile==='cyd28'?'<div class="card-note">GPIO35, 36 i 39: tylko wejścia; GPIO21 współdzielony z podświetleniem. P3 i CN1 mają wspólne GPIO22.</div>':'')}
function renderGrove(){
 const d=current(),ports=getGrove(d),pairs=[['A','I²C / red · SCL, SDA'],['B','GPIO / ADC · black'],['C','UART / blue · RX, TX']];
 $('grovePorts').innerHTML=pairs.map(([name,info])=>`<div class="grove-port"><strong>PORT ${name} <span class="pill">${info}</span></strong><div class="grove-layout"><span class="grove-pin signal">${name==='A'?'SDA':'IO1'}</span><label>GPIO<input type="number" min="-1" max="48" data-grove-port="${name}" data-grove-line="io1" value="${Number(ports[name].io1)}"></label><span class="hint">${name==='A'?'I²C SDA':'-1 = not wired'}</span><span class="grove-pin signal">${name==='A'?'SCL':'IO2'}</span><label>GPIO<input type="number" min="-1" max="48" data-grove-port="${name}" data-grove-line="io2" value="${Number(ports[name].io2)}"></label><span class="hint">${name==='A'?'I²C SCL':'-1 = not wired'}</span></div><p class="hint">GND / 5V power pins are physical connector pins; set a separate safe power supply.</p></div>`).join('');
 $('grovePorts').querySelectorAll('[data-grove-port]').forEach(el=>el.onchange=()=>{const v=Number(el.value),max=d.profile==='s3'?48:39;if(!Number.isInteger(v)||v < -1||v>max){toast('GPIO must be -1 (unwired) or 0–'+max);renderGrove();return}mark();ports[el.dataset.grovePort][el.dataset.groveLine]=v;if(el.dataset.grovePort==='A'){if(el.dataset.groveLine==='io1')d.pins.i2c_sda=v;else d.pins.i2c_scl=v;}save();toast('Grove pin map saved. Rebuild firmware to apply.')});
}
const M5_DEVICES=[
 'Core Basic','Core Gray','Core GO','Core FIRE','Core2','Core2 v1.1','CoreS3','CoreS3SE','Tough','CoreInk','M5Paper','M5PaperS3','M5PaperColor','M5Station','M5StickC','M5StickC Plus','M5StickC Plus2','M5StickS3','ATOM Lite','ATOM Matrix','ATOM Echo','ATOM PSRAM','ATOM U','ATOM S3','ATOM S3Lite','ATOM S3R','ATOM S3RExt','ATOM S3RCam','ATOM S3U','STAMP PICO','STAMP S3','STAMP S3A','STAMP S3Bat','STAMP S3Mini','STAMP PLC','STAMP C3','STAMP C3U','STAMP C5','STAMP C6','M5Dial','M5DinMeter','M5Capsule','Cardputer','Cardputer ADV','M5VAMeter','M5AirQ','M5NanoC6','M5UnitC6L','M5PowerHub','M5StopWatch','M5StackChan','M5ChainCaptain','M5DualKey','M5Tab5','M5StampP4'
];
// Offline seed displayed immediately. Full list is loaded from GitHub via localhost.
const M5_SEED=[{"name": "M5Unified", "full_name": "m5stack/M5Unified", "url": "https://github.com/m5stack/M5Unified", "description": "Unified controller API", "category": "Core / Graphics", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5GFX", "full_name": "m5stack/M5GFX", "url": "https://github.com/m5stack/M5GFX", "description": "Graphics drivers", "category": "Core / Graphics", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5UnitUnified", "full_name": "m5stack/M5UnitUnified", "url": "https://github.com/m5stack/M5UnitUnified", "description": "Unified Unit sensor APIs", "category": "Core / Graphics", "interface": "I2C", "archived": false, "library_candidate": true}, {"name": "M5Family", "full_name": "m5stack/M5Family", "url": "https://github.com/m5stack/M5Family", "description": "M5Stack library dependency index", "category": "Core / Graphics", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-NFC", "full_name": "m5stack/M5Unit-NFC", "url": "https://github.com/m5stack/M5Unit-NFC", "description": "NFC", "category": "Unit", "interface": "I2C", "archived": false, "library_candidate": true}, {"name": "M5Unit-RFID", "full_name": "m5stack/M5Unit-RFID", "url": "https://github.com/m5stack/M5Unit-RFID", "description": "RFID", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Module-QRCode", "full_name": "m5stack/M5Module-QRCode", "url": "https://github.com/m5stack/M5Module-QRCode", "description": "QR reader", "category": "Module", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Chain", "full_name": "m5stack/M5Chain", "url": "https://github.com/m5stack/M5Chain", "description": "Chain series controller libraries", "category": "Other", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-EXTIO2", "full_name": "m5stack/M5Unit-EXTIO2", "url": "https://github.com/m5stack/M5Unit-EXTIO2", "description": "I/O expander", "category": "Unit", "interface": "I2C", "archived": false, "library_candidate": true}, {"name": "M5Unit-Sonic", "full_name": "m5stack/M5Unit-Sonic", "url": "https://github.com/m5stack/M5Unit-Sonic", "description": "Ultrasonic distance", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-RELAY", "full_name": "m5stack/M5Unit-RELAY", "url": "https://github.com/m5stack/M5Unit-RELAY", "description": "Relay controls", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-ENV", "full_name": "m5stack/M5Unit-ENV", "url": "https://github.com/m5stack/M5Unit-ENV", "description": "Temperature / humidity / pressure", "category": "Unit", "interface": "I2C", "archived": false, "library_candidate": true}, {"name": "M5Unit-ACSSR", "full_name": "m5stack/M5Unit-ACSSR", "url": "https://github.com/m5stack/M5Unit-ACSSR", "description": "AC solid-state relay", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-KMeter", "full_name": "m5stack/M5Unit-KMeter", "url": "https://github.com/m5stack/M5Unit-KMeter", "description": "Thermocouple temperature", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-Encoder", "full_name": "m5stack/M5Unit-Encoder", "url": "https://github.com/m5stack/M5Unit-Encoder", "description": "Rotary encoder", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-MQTT", "full_name": "m5stack/M5Unit-MQTT", "url": "https://github.com/m5stack/M5Unit-MQTT", "description": "MQTT communication", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-DDS", "full_name": "m5stack/M5Unit-DDS", "url": "https://github.com/m5stack/M5Unit-DDS", "description": "Signal generator", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-UHF-RFID", "full_name": "m5stack/M5Unit-UHF-RFID", "url": "https://github.com/m5stack/M5Unit-UHF-RFID", "description": "UHF RFID", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-PoESP32", "full_name": "m5stack/M5Unit-PoESP32", "url": "https://github.com/m5stack/M5Unit-PoESP32", "description": "PoE controller", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-RTC", "full_name": "m5stack/M5Unit-RTC", "url": "https://github.com/m5stack/M5Unit-RTC", "description": "Real-time clock", "category": "Unit", "interface": "I2C", "archived": false, "library_candidate": true}, {"name": "M5-DLight", "full_name": "m5stack/M5-DLight", "url": "https://github.com/m5stack/M5-DLight", "description": "Ambient light sensor", "category": "Unit", "interface": "I2C", "archived": false, "library_candidate": true}, {"name": "M5-RoverC", "full_name": "m5stack/M5-RoverC", "url": "https://github.com/m5stack/M5-RoverC", "description": "Motor / Rover control", "category": "Other", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5-ADS1115", "full_name": "m5stack/M5-ADS1115", "url": "https://github.com/m5stack/M5-ADS1115", "description": "16-bit ADC", "category": "Unit", "interface": "I2C", "archived": false, "library_candidate": true}, {"name": "M5-ADS1100", "full_name": "m5stack/M5-ADS1100", "url": "https://github.com/m5stack/M5-ADS1100", "description": "16-bit ADC", "category": "Unit", "interface": "I2C", "archived": false, "library_candidate": true}, {"name": "M5-FPC1020A", "full_name": "m5stack/M5-FPC1020A", "url": "https://github.com/m5stack/M5-FPC1020A", "description": "Fingerprint sensor", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5_EzData", "full_name": "m5stack/M5_EzData", "url": "https://github.com/m5stack/M5_EzData", "description": "EzData client", "category": "Other", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5-Ethernet", "full_name": "m5stack/M5-Ethernet", "url": "https://github.com/m5stack/M5-Ethernet", "description": "Ethernet", "category": "Other", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-GLASS", "full_name": "m5stack/M5Unit-GLASS", "url": "https://github.com/m5stack/M5Unit-GLASS", "description": "Glass display", "category": "Unit", "interface": "", "archived": false, "library_candidate": true}, {"name": "M5Unit-IMU", "full_name": "m5stack/M5Unit-IMU", "url": "https://github.com/m5stack/M5Unit-IMU", "description": "IMU gyroscope / accelerometer", "category": "Unit", "interface": "I2C", "archived": false, "library_candidate": true}, {"name": "M5Unit-RollerCAN-Internal-FW", "full_name": "m5stack/M5Unit-RollerCAN-Internal-FW", "url": "https://github.com/m5stack/M5Unit-RollerCAN-Internal-FW", "description": "RollerCAN device firmware (not an Arduino library)", "category": "Firmware", "interface": "CAN", "archived": false, "library_candidate": false}, {"name": "M5Unit-Roller485-Internal-FW", "full_name": "m5stack/M5Unit-Roller485-Internal-FW", "url": "https://github.com/m5stack/M5Unit-Roller485-Internal-FW", "description": "Roller485 device firmware (not an Arduino library)", "category": "Firmware", "interface": "RS485", "archived": false, "library_candidate": false}];
let m5Inventory=M5_SEED, m5InventorySource='Offline shortlist', m5InventoryComplete=false,
    m5Loaded=false, m5Loading=false, m5Shown=36, m5FetchError='';
const m5AllowUrl=url=>/^https:\/\/github\.com\/m5stack\/[a-z0-9_.-]+$/i.test(url||'');
function renderM5Catalog(){
 const q=($('m5Search')?.value||'').trim().toLowerCase();
 const kind=$('m5Category')?.value||'all';
 $('m5Devices').innerHTML=M5_DEVICES.filter(n=>n.toLowerCase().includes(q)).map(n=>`<span class="m5-device-chip">${esc(n)}</span>`).join('')||'<span class="hint">No controller matches</span>';
 let matches=m5Inventory.filter(r=>(kind==='all'||(kind==='Libraries'?r.library_candidate:r.category===kind))&&
 [r.name,r.full_name,r.description,r.category,r.interface].join(' ').toLowerCase().includes(q));
 matches.sort((a,b)=>a.name.localeCompare(b.name,undefined,{sensitivity:'base'}));
 const shown=matches.slice(0,m5Shown);
 $('m5Status').textContent=`${m5InventorySource}: ${m5Inventory.length} repositories · ${matches.length} matches · ${shown.length} shown`+
 (!m5InventoryComplete?' · partial/offline':' · full inventory')+(m5FetchError?' · '+m5FetchError:'');
 $('m5Catalog').innerHTML=shown.map(r=>{const url=m5AllowUrl(r.url)?r.url:'';
 const dep=(r.library_candidate&&!r.archived);
 return `<div class="m5-repo"><b>${esc(r.name)}</b><div class="m5-meta"><span>${esc(r.category||'Other')}</span>${r.interface?`<span>Verified bus: ${esc(r.interface)}</span>`:''}${r.archived?'<span>Archived</span>':''}${!dep?'<span>Check repo type</span>':''}</div>
 <div class="repo-desc">${esc(r.description||'No description on GitHub')}</div>
 <div class="bar">${dep?`<button data-m5-add="${esc(url)}" title="Add repository dependency">＋ Library</button>`:''}<button data-m5-block="${esc(url)}" title="Inspect driver and create a custom block">▣ Block</button><a href="${esc(url)}" target="_blank" rel="noopener noreferrer">GitHub</a></div></div>`}).join('')||'<div class="notice">No matching repositories.</div>';
 $('m5More').classList.toggle('hide',shown.length===matches.length);
 $('m5More').textContent=`Show more (+${Math.min(36,matches.length-shown.length)})`;
}
async function loadM5Catalogue(force=false){
 if(m5Loading||(!force&&m5Loaded))return;
 m5Loading=true;$('m5Refresh').disabled=true;
 m5InventorySource='Loading official GitHub inventory';renderM5Catalog();
 try{const data=await api('/api/m5stack/catalog'+(force?'?refresh=1':''));
 if(!Array.isArray(data.items)||!data.items.length)throw Error('Empty catalogue');
 m5Inventory=data.items.filter(x=>x&&m5AllowUrl(x.url));
 m5InventorySource=data.source||'GitHub';m5InventoryComplete=!!data.complete;m5FetchError=data.error||'';m5Loaded=true;
 }catch(e){m5InventorySource='Offline shortlist';m5FetchError=e.message;m5Loaded=true;}
 m5Loading=false;$('m5Refresh').disabled=false;renderM5Catalog();
}
function registerGitHubBlock(lib){
 if(!lib||!lib.id)return;
 const existing=(current().githubLibraries||[]).find(x=>x.id===lib.id);
 if(existing)Object.assign(existing,lib);else{current().githubLibraries=current().githubLibraries||[];current().githubLibraries.push(lib)}
 BLOCKS.github={cat:'GitHub libraries',color:'#deae69',label:'GitHub · Custom Library',inputs:['IN1','IN2','IN3','IN4','IN5','IN6','IN7','IN8'],props:{library_id:[lib.id,'GitHub library','text']}};
 save();renderLogic();renderExplorer();
}
function refreshImportedBlocks(){const libs=current().githubLibraries||[];if(libs.length){BLOCKS.github={cat:'GitHub libraries',color:'#deae69',label:'GitHub · Library',inputs:['IN1','IN2','IN3','IN4','IN5','IN6','IN7','IN8'],props:{library_id:[libs[0].id,'GitHub library','text']}}}else delete BLOCKS.github}
$('m5Search').oninput=()=>{m5Shown=36;renderM5Catalog()};
$('m5Category').onchange=()=>{m5Shown=36;renderM5Catalog()};
$('m5More').onclick=()=>{m5Shown+=36;renderM5Catalog()};
$('m5Refresh').onclick=()=>loadM5Catalogue(true);
$('m5Catalog').onclick=async e=>{
 const add=e.target.closest('[data-m5-add]'),blk=e.target.closest('[data-m5-block]');
 const url=(add||blk)?.dataset[add?'m5Add':'m5Block'];
 if(!url||!m5AllowUrl(url))return;
 if(add){const repo=url+'.git';const d=current();d.libraries=d.libraries||[];
 if(!d.libraries.includes(repo)){mark();d.libraries.push(repo);save();} $('libraries').value=d.libraries.join('\n');
 toast('Library added to project. Check compatible Arduino API before building.');return;}
 $('githubUrl').value=url;const display=$('githubResults');display.textContent='Inspecting '+url+'…';
 try{const result=await api('/api/github/inspect',{url});registerGitHubBlock(result.library);
 display.textContent=(result.library.ready?'API manifest ready':'Custom template ONLY: C++ driver code needed')+' · '+result.library.repo;
 toast(result.library.ready?'Ready block imported':'Custom block imported — configure its C++ API');}
 catch(err){display.textContent='Unable to inspect: '+err.message;toast(err.message)}
};
$('groveExample').onclick=()=>{
 const d=current();if(!presets[d.profile].screen){toast('Select a CYD with a display first.');return}
 const mapping=getGrove(d);if(mapping.B.io1!==35){toast('Map Grove Port B / IO1 to GPIO35 before adding this example.');return}
 mark();const screen=d.scenes.find(s=>s.id==='screen5')||scene();d.currentScene=screen.id;
 let battery=screen.widgets.find(w=>w.type==='battery');if(!battery){battery=W('battery','BATTERY',55,75,135,51,'#35d58c');screen.widgets.push(battery)}
 const g=ensureLogic(),make=(type,x,y,props={})=>{const n={id:uid(),type,x,y,props:{}};for(const [k,def] of Object.entries(BLOCKS[type].props))n.props[k]=props[k]??def[0];g.nodes.push(n);return n};
 const a=make('groveanalog',20,165,{port:'B',line:'io1',mul:2}),m=make('map',245,165,{inMin:3.2,inMax:4.2,outMin:0,outMax:100}),c=make('clamp',470,165,{min:0,max:100}),out=make('screenout',695,165,{widgetId:battery.id});
 g.edges.push({from:a.id,to:m.id,input:0},{from:m.id,to:c.id,input:0},{from:c.id,to:out.id,input:0});battery.source='logic:'+out.id;
 d.features.battery=true;logicSelected=out.id;save();selectTab('logic');renderLogic();toast('Wired example added. The battery input is connected to GPIO35 through a 2:1 divider.');
};
$('githubImport').onclick=async()=>{const url=$('githubUrl').value.trim();if(!url)return;const node=$('githubResults');node.textContent='Inspecting public GitHub repository…';try{const result=await api('/api/github/inspect',{url});registerGitHubBlock(result.library);node.textContent=(result.library.ready?'Template recognized':'Imported as editable custom template')+' · '+result.library.repo+' · select GitHub block in Block Logic';toast('GitHub repository added');}catch(e){node.textContent='Import failed: '+e.message;toast(e.message)}};
function renderLibs(){const d=current();renderM5Catalog();loadM5Catalogue();$('libraries').value=(d.libraries||[]).join('\n');$('customIncludes').value=d.custom?.includes||'';$('customSetup').value=d.custom?.setup||'';$('customLoop').value=d.custom?.loop||''}
$('saveCustom').addEventListener('click',()=>{mark();let d=current();d.libraries=$('libraries').value.split('\n').map(s=>s.trim()).filter(Boolean);d.custom={includes:$('customIncludes').value,setup:$('customSetup').value,loop:$('customLoop').value};rerender();toast('Libraries and components saved')});
function renderBuild(){$('buildDevice').textContent=current().name+' · '+presets[current().profile].label}
async function api(path,body=null){const opt=body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{};let r;try{r=await fetch(path,opt)}catch(e){throw Error('Brak połączenia z lokalnym serwerem CYD Studio. Uruchom URUCHOM_CYD_STUDIO.bat i nie zamykaj okna. ('+e.message+')')}let j;try{j=await r.json()}catch(e){throw Error('Serwer odpowiedział nieprawidłowo. Sprawdź wersję otwartej strony CYD Studio.')}if(!r.ok)throw Error(j.error||'Błąd serwera HTTP '+r.status);return j}
async function status(){try{const r=await api('/api/status');$('status').textContent=r.pio?'● PlatformIO gotowe':'● Brak PlatformIO';$('status').className=r.pio?'ok':'no';}catch{$('status').textContent='● Edytor offline · uruchom serwer';$('status').className='no'}}
async function ports(){try{let r=await api('/api/ports');$('ports').innerHTML='<option value="">Wybierz port USB</option>'+r.ports.map(o=>`<option value="${esc(o.port)}">${esc(o.port)} · ${esc(o.description)}</option>`).join('');toast(r.ports.length?'Wykryto porty COM: '+r.ports.length:'Brak portów COM. Sprawdź Menedżer urządzeń Windows / kabel USB. '+(r.errors||[]).join(' | '))}catch(e){toast(e.message)}}
async function runJob(kind){
 const id=current().id,what=kind==='build'?'Build BIN':kind==='check'?'Check C++ while firmware runs':'Flash firmware';
 const body={project,device_id:id};
 if(kind==='flash'){
  const port=$('manualPort').value.trim()||$('ports').value;
  if(!port){toast('Podaj COM, np. COM4');return}
  body.port=port;await disconnectSerial();
 }
 buildJob=null;
 resetBuildProgress(what);$('log').textContent=what+'…\n';
 setJobButtons(true,kind);
 try{
  const r=await api('/api/'+kind,body);
  $('buildInfo').textContent='Projekt PlatformIO: '+r.project_path;
  buildJob=r.job_id;await poll(r.job_id,kind);
 }catch(e){$('log').textContent='BŁĄD: '+e.message;renderErrorLinks($('log').textContent);toast(e.message);setJobButtons(false,kind)}
}
function setJobButtons(active,kind){
 for(const id of ['build','flash','checkCpp','checkCppDock'])$(id).disabled=active;
 $('stopBuild').disabled=!active||kind==='flash';
 if(active)$('downloadBin').disabled=true;
}
function resetBuildProgress(label){$('compileProgress').value=0;$('buildPct').textContent='0%';$('buildPhase').textContent=label;$('progressDetail').textContent='Czekam na komunikaty PlatformIO…'}
function showBuildProgress(j){
 const pct=Math.max(0,Math.min(100,Number(j.progress)||0));
 $('compileProgress').value=pct;$('buildPct').textContent=pct+'%';$('buildPhase').textContent=j.phase||'Pracuję…';
 $('progressDetail').textContent=j.state==='cancelled'?'Kompilacja zatrzymana.':j.state==='failed'?'Zatrzymano. Szczegóły w logu.':j.state==='success'?'Operacja zakończona pomyślnie.':j.accurate?'Dokładny postęp zapisu z ESP32.':'Postęp orientacyjny według etapu kompilacji.';
}
// Error navigator: GCC line numbers → generated main.cpp; config errors → settings / block.
let errorFlashTimer=0;
function markErrorElement(el){
 if(!el)return;
 el.scrollIntoView({block:'center',behavior:'smooth'});
 el.classList.add('cyd-error-focus');clearTimeout(errorFlashTimer);
 errorFlashTimer=setTimeout(()=>el.classList.remove('cyd-error-focus'),6500);
}
function closestErrorLine(text){
 const lines=String(text||'').split('\n');
 return lines.find(x=>/src[\\/]main\.cpp:\d+(?::\d+)?/.test(x)&&/error:/.test(x))
 ||lines.find(x=>/src[\\/]main\.cpp:\d+(?::\d+)?/.test(x))
 ||lines.find(x=>/overflowed by \d+ bytes|dram0_0_seg|error:|błąd:/i.test(x))
 ||lines[lines.length-1]||'';
}
async function navigateBuildError(message){
 const value=String(message||'');
 const match=value.match(/(?:src[\\/]main\.cpp|main\.cpp):(\d+)(?::(\d+))?/);
 if(match){
  try{
   const out=await api('/api/source',{project,device_id:current().id});
   const lines=out.code.split('\n');
   const line=Number(match[1]);
   const start=Math.max(0,line-11),end=Math.min(lines.length,line+10);
   const markup=lines.slice(start,end).map((x,i)=>{
    const n=start+i+1;
    return `<div class="source-row ${n===line?'source-fail':''}"><span class="source-number">${n}</span>${esc(x)}</div>`;
   }).join('');
   let d=$('sourceErrorWindow');
   if(!d){d=document.createElement('div');d.id='sourceErrorWindow';d.className='source-error-window';document.body.appendChild(d)}
   d.innerHTML=`<div class="source-error-card"><div class="bar" style="justify-content:space-between"><strong>main.cpp · wiersz ${line}</strong><button id="sourceErrorClose">✕ Zamknij</button></div><div class="hint">${esc(value)}</div><div class="source-content">${markup}</div></div>`;
   d.querySelector('#sourceErrorClose').onclick=()=>d.remove();
   d.addEventListener('click',e=>{if(e.target===d)d.remove()},{once:true});
   markErrorElement(d.querySelector('.source-fail'));return;
  }catch(e){toast('Nie mogę otworzyć źródła: '+e.message)}
 }
 if(/wifi|ssid|hasł|bluetooth|ble|audio|i2c|grove|bater|battery|mikrofon/i.test(value)){
  selectTab('hardware');
  const target=/wifi|ssid|hasł/i.test(value)?'wifi_mode':/bluetooth/i.test(value)?'bt_classic':/ble/i.test(value)?'ble':/audio|mikrofon/i.test(value)?'audio_rx':/i2c/i.test(value)?'i2c_sda':'battery';
  markErrorElement($(target)||$('tab_hardware'));return;
 }
 if(/blok|block|adc|pin gpio|gpio\d+|screen widget/i.test(value)){
  selectTab('logic');
  const type=/adc/i.test(value)?'adc':/screen widget/i.test(value)?'screenout':null;
  const n=ensureLogic().nodes.find(n=>!type||n.type===type);
  if(n){logicSelected=n.id;renderLogic();markErrorElement([...document.querySelectorAll('#logicNodes [data-node]')].find(x=>x.dataset.node===n.id));}
  else markErrorElement($('logicBoard'));
  return;
 }
 selectTab('build');markErrorElement($('buildPhase'));
 if(/dram0|overflowed|will not fit|memory/i.test(value)){
  $('progressDetail').textContent='BRAK DRAM: nowy generator 2.28 oszczędza 17 664 bajty. Użyj ponownie Generate BIN (stary wygenerowany projekt nie ma poprawki).';
 }
}
function renderErrorLinks(log){
 const txt=String(log||'');const links=[];
 for(const line of txt.split('\n')){
  if(!/(?:error:|błąd:|fatal error:|overflowed by \d+ bytes|region `dram0_0_seg'|failed to fetch)/i.test(line))continue;
  const trimmed=line.trim();if(!trimmed||links.includes(trimmed))continue;
  links.push(trimmed);if(links.length>=8)break;
 }
 const root=$('errorNav');if(!root)return;
 root.innerHTML=links.map((line,i)=>`<button class="error-entry" data-error-index="${i}" title="Kliknij, aby przejść do błędu"><span>⚠</span> ${esc(line.slice(0,200))}</button>`).join('');
 root.querySelectorAll('[data-error-index]').forEach(button=>button.onclick=()=>navigateBuildError(links[Number(button.dataset.errorIndex)]));
}
$('log').addEventListener('click',()=>navigateBuildError(closestErrorLine($('log').textContent)));
$('generatorLint').addEventListener('click',()=>{if(/error|błąd/i.test($('generatorLint').textContent))navigateBuildError($('generatorLint').textContent)});

async function poll(jobid,kind){
 try{
  const j=await api('/api/job/'+jobid);
  const log=$('log'),next=j.log||'Job: '+j.state;
  if(kind==='check')$('codeDiagnostics').textContent=next.slice(-12000);
  if(log.textContent!==next){const follow=log.scrollTop+log.clientHeight>=log.scrollHeight-26;log.textContent=next;renderErrorLinks(next);if(follow)log.scrollTop=log.scrollHeight}
  showBuildProgress(j);
  if(['success','failed','cancelled'].includes(j.state)){
   setJobButtons(false,kind);
   if(j.state==='success'){
    toast(kind==='build'?'BIN ready':kind==='check'?'C++ syntax and libraries OK':'Flash complete');
    if(kind==='build'&&j.ready){$('downloadBin').disabled=false;$('downloadBin').onclick=()=>window.location.href='/api/bin/'+jobid}
   }else if(j.state==='cancelled')toast('Kompilacja została zatrzymana.');
   else toast('Błąd. Zobacz log PlatformIO.');
   return;
  }
  setTimeout(()=>poll(jobid,kind),400);
 }catch(e){setJobButtons(false,kind);$('buildPhase').textContent='Błąd komunikacji';toast(e.message)}
}
$('stopBuild').onclick=async()=>{
 if(!buildJob)return;
 $('stopBuild').disabled=true;
 $('buildPhase').textContent='Zatrzymywanie PlatformIO…';
 try{await api('/api/cancel',{job_id:buildJob})}
 catch(e){toast('Nie udało się zatrzymać: '+e.message);$('stopBuild').disabled=false}
};
$('scanPorts').onclick=ports;$('build').onclick=()=>runJob('build');$('flash').onclick=()=>runJob('flash');$('checkCpp').onclick=()=>runJob('check');$('checkCppDock').onclick=()=>runJob('check');
$('undo').onclick=()=>{if(!hist.length)return;project=JSON.parse(hist.pop());sel=null;pen=false;preview=false;rerender();toast('Cofnięto zmianę');$('undo').disabled=!hist.length};
function downloadBlob(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),4000)}
function exportJson(){downloadBlob(new Blob([JSON.stringify({...project,format:'cyd-studio-project',schema_version:'1.0'},null,2)],{type:'application/json'}),'CYD_STUDIO_DIAG_PROJECT.json')}
$('save').onclick=exportJson;
$('exportZip').onclick=async()=>{
 const b=$('exportZip');b.disabled=true;b.textContent='Packaging…';
 try{const response=await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({project})});
   if(!response.ok){const result=await response.json();throw Error(result.error||'Export failed')}
   downloadBlob(await response.blob(),'CYD_Studio_Portable_Project.zip');toast('ZIP: JSON + SVG + C++ / PlatformIO')
 }catch(e){toast('Export failed: '+e.message)}finally{b.disabled=false;b.textContent='📦 Eksportuj Project ZIP'}
};
$('open').onclick=()=>$('importfile').click();
$('importfile').onchange=async e=>{
 const file=e.target.files[0];if(!file)return;
 try{
   let p;
   if(file.name.toLowerCase().endsWith('.zip')){
     const bytes=new Uint8Array(await file.arrayBuffer());
     if(bytes.length>2600000)throw Error('ZIP too large (2.6 MB max)');
     let binary='';for(let offset=0;offset<bytes.length;offset+=8192)binary+=String.fromCharCode(...bytes.subarray(offset,offset+8192));
     const r=await api('/api/import',{zip_base64:btoa(binary)});p=r.project;
   }else p=JSON.parse(await file.text());
   if(!Array.isArray(p.devices)||!p.devices.length){
     if(Array.isArray(p.scenes)&&p.scenes.length){const d=newDev('cyd28','IMPORTED CYD');d.scenes=p.scenes;d.currentScene=p.scenes[0].id;p={version:2,currentDevice:d.id,devices:[d]}}
     else throw Error('Unrecognized project format');
   }
   mark();project=p;project.currentDevice=project.devices[0].id;sel=null;selectTab('screen');save();toast('Portable project imported');
 }catch(err){toast('Import failed: '+err.message)}e.target.value='';
};
// Katalog 29 przykładów: nazwane projekty JSON z bezpiecznego lokalnego serwera.
let examplesCatalog=[];
async function showExamples(){
  const dlg=$('examplesDialog');
  if(!dlg.open)dlg.showModal();
  $('examplesSearch').value='';
  $('examplesList').textContent='Wczytuję katalog przykładów…';
  $('examplesCount').textContent='';
  try{
    const response=await fetch('/api/examples',{cache:'no-store'});
    const data=await response.json();
    if(!response.ok)throw Error(data.error||'Błąd katalogu');
    examplesCatalog=data.examples||[];
    renderExamples();
    $('examplesSearch').focus();
  }catch(error){$('examplesList').textContent='Nie można wczytać przykładów: '+error.message;}
}
function renderExamples(){
  const q=$('examplesSearch').value.trim().toLocaleLowerCase('pl');
  const examples=examplesCatalog.filter(e=>[e.id,e.title,e.description,e.category,e.profile].join(' ').toLocaleLowerCase('pl').includes(q));
  $('examplesCount').textContent=`${examples.length} z ${examplesCatalog.length} przykładów`;
  $('examplesList').innerHTML=examples.length?examples.map(e=>`<button type="button" role="listitem" class="example-entry" data-example-id="${esc(e.id)}"><span class="example-n">${esc(e.id)}</span><span class="example-main"><span class="example-title">${esc(e.title)}</span><span class="example-details">${esc(e.category)} · ${esc(e.description)}</span></span></button>`).join(''):'Brak przykładów spełniających kryteria.';
}
$('examplesSearch').addEventListener('input',renderExamples);
$('examplesClose').onclick=()=>$('examplesDialog').close();
$('examplesQuick').onclick=showExamples;
$('examplesFromFileMenu').onclick=showExamples;
$('examplesList').addEventListener('click',async event=>{
  const entry=event.target.closest('[data-example-id]');if(!entry)return;
  const id=entry.dataset.exampleId;
  const meta=examplesCatalog.find(e=>e.id===id);if(!meta)return;
  if(!window.confirm(`Wczytać „${meta.title}”? Bieżący projekt zostanie zastąpiony. Możesz go najpierw zapisać w menu PLIK.`))return;
  entry.disabled=true;
  try{
    const response=await fetch('/api/example/'+encodeURIComponent(id),{cache:'no-store'});
    const data=await response.json();if(!response.ok)throw Error(data.error||'Błąd ładowania');
    const loaded=data.project;
    if(!loaded||!Array.isArray(loaded.devices)||!loaded.devices.length)throw Error('Brak urządzeń w przykładzie');
    mark();project=loaded;
    if(!project.devices.some(d=>d.id===project.currentDevice))project.currentDevice=project.devices[0].id;
    sel=null;logicSelected=null;logicSource=null;pen=false;preview=false;
    $('examplesDialog').close();
    const dev=project.devices.find(d=>d.id===project.currentDevice)||project.devices[0];
    selectTab(presets[dev.profile]?.screen?'screen':'hardware');
    toast('Przykład wczytany: '+meta.title);
  }catch(error){toast('Błąd przykładu: '+error.message)}
  finally{entry.disabled=false;}
});
// The left-side FILE menu calls the same functions as existing exports and import.
const fileMenu=$('fileMenu'),fileMenuToggle=$('fileMenuToggle');
function setFileMenu(open){fileMenu.hidden=!open;fileMenuToggle.setAttribute('aria-expanded',open?'true':'false');}
fileMenuToggle.addEventListener('click',()=>setFileMenu(fileMenu.hidden));
document.addEventListener('pointerdown',e=>{if(!e.target.closest('.file-menu-wrap'))setFileMenu(false)});
fileMenu.addEventListener('click',e=>{if(e.target.closest('button'))setFileMenu(false)});
$('fileNewQuick').onclick=()=>$('newProject').click();
$('fileOpenQuick').onclick=()=>$('open').click();
$('fileSaveQuick').onclick=()=>$('save').click();
$('exportSvgFile').onclick=()=>$('exportSvg').click();
$('exportPngFile').onclick=()=>$('png').click();
$('newProject').onclick=()=>{
 if(!window.confirm('Nowy projekt zastąpi bieżący projekt w automatycznym zapisie. Zapisz go najpierw, jeśli chcesz go zachować. Kontynuować?'))return;
 mark();const d=newDev('cyd28','CYD MAIN');
 project={version:2,currentDevice:d.id,devices:[d]};sel=null;pen=false;preview=false;logicSelected=null;logicSource=null;
 selectTab('screen');toast('Utworzono nowy projekt. Poprzedni można przywrócić przez Undo.');
};
window.addEventListener('keydown',e=>{
 if(e.key!=='Delete' || e.repeat || e.ctrlKey || e.altKey || e.metaKey || e.shiftKey) return;
 if(tab!=='screen' || preview || !sel || !current().scenes.length) return;
 const focus=document.activeElement;
 if(focus && (['INPUT','TEXTAREA','SELECT'].includes(focus.tagName) || focus.isContentEditable || focus.closest('[contenteditable=true]')))return;
 const sc=scene();
 if(!sc.widgets.some(w=>w.id===sel))return;
 e.preventDefault();mark();sc.widgets=sc.widgets.filter(w=>w.id!==sel);sel=null;rerender();toast('Usunięto zaznaczony element (Undo przywraca)');
});
window.addEventListener('keydown',e=>{
 if(e.key==='Escape'){setFileMenu(false);return;}
 if(!(e.ctrlKey||e.metaKey)||e.altKey)return;
 const k=e.key.toLowerCase();
 if(k==='o'){e.preventDefault();$('open').click();}
 else if(k==='s'){e.preventDefault();$('save').click();}
 else if(k==='n'){e.preventDefault();$('newProject').click();}
 else if(k==='z'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('undo').click()}
});

// ------------------------------------------------------------
// Bloczki funkcyjne. Wzorowane organizacja na kategoriach Visuino.
// Dzialajace typy sa generowane do C++ w studio_server.py.
const BLOCK_SYMBOLS={adc:'⚡',digital:'⬡',battery:'▣',voltage:'V',constant:'π',timer:'◷',map:'⇄',clamp:'⊣',add:'+',subtract:'−',multiply:'×',divide:'÷',ema:'≈',schmitt:'⇋',serial:'≡',scope:'∿',screenout:'▣',canrx:'CAN',cc1101rssi:'RF',rfbin:'▥',fftpeak:'FFT',fftbin:'≋',pwm:'PWM',gpioout:'GPIO',brightness:'☀',edge_rise:'↑',edge_fall:'↓',toggle:'⏻',counter:'№',debounce:'◷',lerp:'⤳',select:'◇',average:'μ',integrate:'∫',derivative:'Δ',deadband:'⊠',triangle:'△',saw:'◩',pulse:'▂'};
const BLOCKS={
 adc:{cat:'Inputs',color:'#5ec7fc',label:'ADC · napięcie',inputs:[],props:{gpio:[35,'GPIO','number'],mul:[1,'Mnożnik','number']}},
 digital:{cat:'Inputs',color:'#5ec7fc',label:'GPIO IN',inputs:[],props:{gpio:[34,'GPIO','number']}},
 battery:{cat:'Inputs',color:'#5ec7fc',label:'Bateria %',inputs:[],props:{}},
 voltage:{cat:'Inputs',color:'#5ec7fc',label:'Bateria [V]',inputs:[],props:{}},
 constant:{cat:'Generator',color:'#a5e36c',label:'Stała',inputs:[],props:{value:[50,'Wartość','number']}},
 uiinput:{cat:'Touch / UI',color:'#44c4d9',label:'Screen control OUT',inputs:[],props:{widgetId:['','Screen widget','text']}},
 timer:{cat:'Generator',color:'#a5e36c',label:'Timer impulsowy',inputs:[],props:{period:[1000,'Okres [ms]','number'],pulse:[150,'Czas ON [ms]','number']}},
 map:{cat:'Math / Analog',color:'#b99af9',label:'MAP · Range / Scaling',inputs:['IN'],props:{inMin:[3.2,'Wejście MIN','number'],inMax:[4.2,'Wejście MAX','number'],outMin:[0,'Wyjście MIN','number'],outMax:[100,'Wyjście MAX','number']}},
 clamp:{cat:'Math / Analog',color:'#b99af9',label:'Ogranicz (Clamp)',inputs:['IN'],props:{min:[0,'MIN','number'],max:[100,'MAX','number']}},
 add:{cat:'Math / Analog',color:'#b99af9',label:'Dodawanie',inputs:['A','B'],props:{}},
 subtract:{cat:'Math / Analog',color:'#b99af9',label:'Odejmowanie',inputs:['A','B'],props:{}},
 multiply:{cat:'Math / Analog',color:'#b99af9',label:'Mnożenie',inputs:['A','B'],props:{}},
 divide:{cat:'Math / Analog',color:'#b99af9',label:'Dzielenie',inputs:['A','B'],props:{}},
 abs:{cat:'Math / Analog',color:'#b99af9',label:'Wartość bezwzględna',inputs:['IN'],props:{}},
 ema:{cat:'Filters',color:'#ffd073',label:'Filtr EMA',inputs:['IN'],props:{alpha:[0.2,'Szybkość 0–1','number']}},
 schmitt:{cat:'Filters',color:'#ffd073',label:'Histereza Schmitta',inputs:['IN'],props:{low:[3.55,'Wyłącz poniżej','number'],high:[3.7,'Włącz powyżej','number']}},
 greater:{cat:'Logic',color:'#f999af',label:'Większe od',inputs:['IN'],props:{threshold:[50,'Próg','number']}},
 not:{cat:'Logic',color:'#f999af',label:'NOT',inputs:['IN'],props:{}},
 and:{cat:'Logic',color:'#f999af',label:'AND',inputs:['A','B'],props:{}},
 or:{cat:'Logic',color:'#f999af',label:'OR',inputs:['A','B'],props:{}},
 pwm:{cat:'Outputs',color:'#50d8b6',label:'PWM wyjście',inputs:['IN %'],props:{gpio:[22,'GPIO PWM','number'],hz:[1000,'Częstotliwość Hz','number']}},
 gpioout:{cat:'Outputs',color:'#50d8b6',label:'GPIO OUT',inputs:['IN'],props:{gpio:[22,'GPIO','number']}},
 brightness:{cat:'Outputs',color:'#50d8b6',label:'Jasność LCD',inputs:['IN 0–100%'],props:{}},
 serial:{cat:'Instruments',color:'#ffac6b',label:'Serial Monitor',inputs:['IN'],props:{name:['SYGNAŁ','Nazwa','text'],ms:[200,'Co [ms]','number']}},
 scope:{cat:'Instruments',color:'#ffac6b',label:'Oscilloscope',inputs:['IN'],props:{name:['SCOPE','Channel','text'],ms:[40,'Every [ms]','number']}},
 screenout:{cat:'Screen I/O',color:'#36e5b0',label:'Screen widget · INPUT',inputs:['VALUE'],props:{widgetId:['','Target widget','text']}},
 groveanalog:{cat:'Grove I/O',color:'#5ec7fc',label:'Grove · Analog IN',inputs:[],props:{port:['B','Port A / B / C','text'],line:['io1','io1 / io2','text'],mul:[1,'Scaling','number']}},
 grovedigital:{cat:'Grove I/O',color:'#5ec7fc',label:'Grove · Digital IN',inputs:[],props:{port:['B','Port A / B / C','text'],line:['io1','io1 / io2','text']}},
 groveout:{cat:'Grove I/O',color:'#50d8b6',label:'Grove · Digital OUT',inputs:['IN'],props:{port:['B','Port A / B / C','text'],line:['io1','io1 / io2','text']}},
 min:{cat:'Math',color:'#b99af9',label:'Minimum',inputs:['A','B'],props:{}},
 max:{cat:'Math',color:'#b99af9',label:'Maximum',inputs:['A','B'],props:{}},
 power:{cat:'Math',color:'#b99af9',label:'Power A^B',inputs:['A','B'],props:{}},
 modulo:{cat:'Math',color:'#b99af9',label:'Modulo',inputs:['A','B'],props:{}},
 sqrt:{cat:'Math',color:'#b99af9',label:'Square root',inputs:['IN'],props:{}},
 round:{cat:'Math',color:'#b99af9',label:'Round',inputs:['IN'],props:{}},
 floor:{cat:'Math',color:'#b99af9',label:'Floor',inputs:['IN'],props:{}},
 ceil:{cat:'Math',color:'#b99af9',label:'Ceiling',inputs:['IN'],props:{}},
 sin:{cat:'Math',color:'#b99af9',label:'Sine (radians)',inputs:['IN'],props:{}},
 cos:{cat:'Math',color:'#b99af9',label:'Cosine (radians)',inputs:['IN'],props:{}},
 less:{cat:'Logic',color:'#f999af',label:'A < B',inputs:['A','B'],props:{}},
 equals:{cat:'Logic',color:'#f999af',label:'A = B',inputs:['A','B'],props:{tolerance:[0.001,'Tolerance','number']}},
 xor:{cat:'Logic',color:'#f999af',label:'XOR',inputs:['A','B'],props:{}},
 nand:{cat:'Logic',color:'#f999af',label:'NAND',inputs:['A','B'],props:{}},
 nor:{cat:'Logic',color:'#f999af',label:'NOR',inputs:['A','B'],props:{}},
 between:{cat:'Logic',color:'#f999af',label:'Between',inputs:['IN'],props:{low:[0,'Minimum','number'],high:[100,'Maximum','number']}},
 // 2.13 maths and logic blocks – each has a C++ generator branch.
 negate:{cat:'Math',color:'#b99af9',label:'Negate −X',inputs:['IN'],props:{}},
 square:{cat:'Math',color:'#b99af9',label:'Square X²',inputs:['IN'],props:{}},
 sign:{cat:'Math',color:'#b99af9',label:'Sign −1/0/+1',inputs:['IN'],props:{}},
 log:{cat:'Math',color:'#b99af9',label:'Natural Log',inputs:['IN'],props:{}},
 exp:{cat:'Math',color:'#b99af9',label:'Exponential',inputs:['IN'],props:{}},
 tan:{cat:'Math',color:'#b99af9',label:'Tangent',inputs:['IN'],props:{}},
 radians:{cat:'Math',color:'#b99af9',label:'Degrees → radians',inputs:['DEG'],props:{}},
 degrees:{cat:'Math',color:'#b99af9',label:'Radians → degrees',inputs:['RAD'],props:{}},
 average:{cat:'Math',color:'#b99af9',label:'Average A / B',inputs:['A','B'],props:{}},
 lerp:{cat:'Math',color:'#b99af9',label:'Lerp A → B',inputs:['A','B','T'],props:{}},
 quantize:{cat:'Math',color:'#b99af9',label:'Quantize to step',inputs:['IN'],props:{step:[0.1,'Step','number']}},
 deadband:{cat:'Math',color:'#b99af9',label:'Deadband',inputs:['IN'],props:{center:[0,'Center','number'],width:[0.1,'Half-width','number']}},
 select:{cat:'Logic',color:'#f999af',label:'Select A / B',inputs:['SEL','A','B'],props:{}},
 greater2:{cat:'Logic',color:'#f999af',label:'A > B',inputs:['A','B'],props:{}},
 gte:{cat:'Logic',color:'#f999af',label:'A ≥ B',inputs:['A','B'],props:{}},
 lte:{cat:'Logic',color:'#f999af',label:'A ≤ B',inputs:['A','B'],props:{}},
 neq:{cat:'Logic',color:'#f999af',label:'A ≠ B',inputs:['A','B'],props:{tolerance:[0.001,'Tolerance','number']}},
 edge_rise:{cat:'Logic / Events',color:'#f6a0c5',label:'Rising edge',inputs:['IN'],props:{}},
 edge_fall:{cat:'Logic / Events',color:'#f6a0c5',label:'Falling edge',inputs:['IN'],props:{}},
 toggle:{cat:'Logic / Events',color:'#f6a0c5',label:'Toggle flip-flop',inputs:['TRIGGER'],props:{}},
 counter:{cat:'Logic / Events',color:'#f6a0c5',label:'Pulse Counter',inputs:['PULSE','RESET'],props:{}},
 debounce:{cat:'Logic / Events',color:'#f6a0c5',label:'Debounce',inputs:['IN'],props:{ms:[60,'Stable [ms]','number']}},
 integrate:{cat:'Math / Time',color:'#f7cc7d',label:'Integrator',inputs:['IN'],props:{gain:[1,'Gain','number']}},
 derivative:{cat:'Math / Time',color:'#f7cc7d',label:'Derivative / s',inputs:['IN'],props:{}},
 pulse:{cat:'Generators',color:'#c9f28c',label:'Pulse train',inputs:[],props:{period:[200,'Period [ms]','number'],duty:[25,'Duty %','number']}},
 saw:{cat:'Generators',color:'#c9f28c',label:'Sawtooth 0–100',inputs:[],props:{period:[2000,'Period [ms]','number']}},
 triangle:{cat:'Generators',color:'#c9f28c',label:'Triangle 0–100',inputs:[],props:{period:[2000,'Period [ms]','number']}},
 canrx:{cat:'Vehicle / CAN',color:'#62dbff',label:'CAN RX · TWAI listen-only',inputs:[],props:{rx:[27,'CAN RX GPIO','number'],tx:[22,'CAN TX GPIO','number'],bitrate:[500,'Bitrate [kbps] (125/250/500/1000)','number'],byte:[0,'Data byte index 0–7','number']}},
 cc1101rssi:{cat:'Radio / CC1101',color:'#4de9a8',label:'CC1101 · RSSI scanner',inputs:[],props:{cs:[22,'CS GPIO','number'],gdo0:[27,'GDO0 GPIO','number'],sck:[18,'SPI SCK','number'],miso:[19,'SPI MISO','number'],mosi:[23,'SPI MOSI','number'],from:[433.3,'Start MHz','number'],to:[434.5,'End MHz','number'],bins:[48,'Spectrum bins (16–64)','number'],settle:[12,'Settle per bin [ms]','number']}},
 rfbin:{cat:'Radio / CC1101',color:'#4de9a8',label:'CC1101 · Spectrum bin',inputs:['INDEX'],props:{}},
 fftpeak:{cat:'Audio / FFT',color:'#fcb56c',label:'FFT peak · ADC Hz',inputs:[],props:{gpio:[35,'ADC GPIO','number'],sampleHz:[4000,'Sample rate (Hz)','number']}},
 fftbin:{cat:'Audio / FFT',color:'#fcb56c',label:'FFT magnitude bin',inputs:['INDEX'],props:{}}

};
function ensureLogic(d=current()){if(!d.logic||!Array.isArray(d.logic.nodes)||!Array.isArray(d.logic.edges))d.logic={nodes:[],edges:[]};return d.logic}
let logicSelected=null,logicSource=null,logicMove=null,serialPort=null,serialReader=null,serialLines=[],scopeValues=[],scopeChannels={},serialConnected=false;
let liveReadings=Object.create(null), traceOn=true, traceFocused=false, serialWriteQueue=Promise.resolve(), tracePacketCount=0;
let lintTimer=null,lintSeq=0;
function formatTrace(v){if(!Number.isFinite(v))return '?';return Math.abs(v)>=1000?v.toFixed(1):Math.abs(v)>=10?v.toFixed(2):v.toFixed(4)}
function updateTraceUI(){
 const now=Date.now();let fresh=0;
 for(const n of ensureLogic().nodes){const d=liveReadings[n.id];if(d && now-d.time<2200)fresh++}
 document.querySelectorAll('[data-live],[data-trace-wire]').forEach(el=>{
  const d=liveReadings[el.dataset.live||el.dataset.traceWire];
  el.textContent=d && now-d.time<2200?formatTrace(d.value):'—';
 });
 document.querySelectorAll('[data-input-live]').forEach(el=>{
  const edge=ensureLogic().edges.find(e=>e.to===el.dataset.inputLive&&e.input===Number(el.dataset.inputIndex));
  const v=edge?liveReadings[edge.from]:null;
  el.textContent=v&&now-v.time<2200?formatTrace(v.value):'—';
 });
 document.querySelectorAll('#logicNodes .logic-node').forEach(el=>{const d=liveReadings[el.dataset.node];el.classList.toggle('live-fresh',!!d && now-d.time<2200)});
 $('liveDetails').textContent=serialConnected
  ?`Live values from ${fresh}/${ensureLogic().nodes.length} blocks · ${tracePacketCount} trace packets received · ${$('baud').value} bps. Changes need reflashing.`
  :'Connect USB, select Blocks and watch live values on the wires. Trace packets are hidden from regular Serial Monitor.';
 $('liveState').textContent=serialConnected?(traceOn?'USB CONNECTED':'TRACE PAUSED'):'DISCONNECTED';
}
function writeDebugCommand(cmd){
 serialWriteQueue=serialWriteQueue.then(async()=>{
  if(!serialConnected || !serialPort?.writable)throw Error('Connect USB first.');
  const writer=serialPort.writable.getWriter();
  try{await writer.write(new TextEncoder().encode(cmd+'\n'))}finally{writer.releaseLock()}
 }).catch(e=>toast('USB command: '+e.message));
 return serialWriteQueue;
}
function scheduleLint(){
 if(lintTimer)clearTimeout(lintTimer);
 const generation=++lintSeq;
 lintTimer=setTimeout(async()=>{
  try{const r=await api('/api/validate',{project,device_id:current().id});if(generation!==lintSeq)return;
   $('generatorLint').textContent='Generator OK · '+r.lines+' lines generated.'+(r.auto_fft?' Automatyczne FFT: ADC GPIO'+(['s3','cardputeradv','stamplc','atoms3lite','stamps3','atoms3','cores3'].includes(current().profile)?'4':'35')+' / 4 kHz.':'')+' Check C++ for toolchain errors.';
   $('generatorLint').style.color='#78eab7';
  }catch(e){if(generation!==lintSeq)return;$('generatorLint').textContent='Generator error: '+e.message;$('generatorLint').style.color='#ff9c9c'}
 },800);
}

const nodeById=id=>ensureLogic().nodes.find(n=>n.id===id);
function connectScreenPort(widget){
 if(!widget||!current().scenes.length)return;
 let n=ensureLogic().nodes.find(n=>n.type==='screenout'&&n.props?.widgetId===widget.id);
 if(!n){addLogicNode('screenout');n=nodeById(logicSelected);n.props.widgetId=widget.id;}
 mark();widget.source='logic:'+n.id;logicSelected=n.id;save();selectTab('logic');renderLogic();toast('Screen input ready: connect a block OUT → green screen input.');
}
function addLogicNode(type,x,y){const b=BLOCKS[type];if(!b)return;mark();const compact=document.body.classList.contains('blocks-compact');const g=ensureLogic(),n={id:uid(),type,x:x??(35+Math.floor(g.nodes.length/3)*(compact?240:352)),y:y??(30+(g.nodes.length%3)*(compact?400:530)),props:{}};for(const [k,p] of Object.entries(b.props))n.props[k]=p[0];if(type==='cc1101rssi'&&['cyd28','cyd28usb'].includes(current().profile)){Object.assign(n.props,{sck:25,miso:39,mosi:32});}if(type==='screenout'){const w=current().scenes.flatMap(s=>s.widgets).find(w=>['battery','bar','progress','value','integer','analog','digital','led','slider','gauge','switch','checkbox','text','rfwave','rfsignal','rfrssi','waterfall','spectrum'].includes(w.type));if(w)n.props.widgetId=w.id}if(type==='uiinput'){const w=current().scenes.flatMap(s=>s.widgets).find(w=>['slider','switch','checkbox'].includes(w.type)&&w.source==='constant');if(w)n.props.widgetId=w.id}g.nodes.push(n);logicSelected=n.id;g.layoutVersion=2;save();renderLogic()}
function renderLogicWires(){
 const board=$('logicBoard'), root=board.getBoundingClientRect(), svg=$('logicWires'), g=ensureLogic();
 const center=el=>{if(!el)return null;const r=el.getBoundingClientRect();return {x:r.left-root.left+r.width/2,y:r.top-root.top+r.height/2}};
 const elFor=(id,selector)=>Array.from(board.querySelectorAll(selector)).find(el=>el.dataset.out===id||el.dataset.inNode===id);
 svg.innerHTML=g.edges.map((e,i)=>{
   const start=center(elFor(e.from,'[data-out]'));
   const dest=center(Array.from(board.querySelectorAll('[data-in-node]')).find(el=>el.dataset.inNode===e.to&&Number(el.dataset.inIndex)===e.input));
   if(!start||!dest)return '';
   const bend=Math.max(35,Math.abs(dest.x-start.x)*.44);
   return `<path class="logic-wire" data-edge="${i}" d="M${start.x} ${start.y} C${start.x+bend} ${start.y},${dest.x-bend} ${dest.y},${dest.x} ${dest.y}"/><text class="trace-wire-label" data-trace-wire="${esc(e.from)}" x="${(start.x+dest.x)/2}" y="${(start.y+dest.y)/2-12}">—</text>`;
 }).join('');
 updateTraceUI();
}
function nodeExpectedHeight(n){
 const el=[...$('logicNodes').querySelectorAll('.logic-node')].find(e=>e.dataset.node===n.id);
 if(el)return Math.ceil(el.getBoundingClientRect().height);
 const b=BLOCKS[n.type];const ins=b?.inputs.length||0,props=Object.keys(b?.props||{}).length;
 return document.body.classList.contains('blocks-compact')?85+ins*27+props*39:142+ins*38+props*48;
}
function arrangeLogicNodes(){
 const graph=ensureLogic(),nodes=graph.nodes; if(!nodes.length)return;
 const outgoing=new Map(nodes.map(n=>[n.id,[]]));
 const indeg=new Map(nodes.map(n=>[n.id,0]));const depth=new Map(nodes.map(n=>[n.id,0]));
 for(const e of graph.edges){if(!indeg.has(e.from)||!indeg.has(e.to))continue; outgoing.get(e.from).push(e.to);indeg.set(e.to,indeg.get(e.to)+1)}
 const queue=nodes.filter(n=>indeg.get(n.id)===0).map(n=>n.id);let count=0;
 while(queue.length){const id=queue.shift();count++;for(const target of outgoing.get(id)||[]){depth.set(target,Math.max(depth.get(target),depth.get(id)+1));indeg.set(target,indeg.get(target)-1);if(indeg.get(target)===0)queue.push(target)}}
 // Cycles still get a visible layout; generator validation independently rejects them.
 if(count<nodes.length)for(const n of nodes)if(indeg.get(n.id)>0)depth.set(n.id,Math.max(0,depth.get(n.id)));
 // Measure actual rendered cards (including wrapped labels and active fonts).
 const colHeights=new Map();let maxX=0,maxY=0;
 const visible=[...$('logicNodes').querySelectorAll('.logic-node')];
 const measuredWidths=visible.map(el=>Math.ceil(el.getBoundingClientRect().width));
 const stepX=Math.max(...measuredWidths,document.body.classList.contains('blocks-compact')?210:290)+35;
 for(const [index,n] of nodes.entries()){const col=graph.edges.length===0?index%3:Math.min(depth.get(n.id),6);const x=35+col*stepX,y=30+(colHeights.get(col)||0);
  n.x=x;n.y=y;colHeights.set(col,(colHeights.get(col)||0)+nodeExpectedHeight(n)+26);
  maxX=Math.max(maxX,x+stepX);maxY=Math.max(maxY,y+nodeExpectedHeight(n)+40)}
 $('logicBoard').style.width=Math.max(1800,maxX)+'px';$('logicBoard').style.height=Math.max(1300,maxY)+'px';
 graph.layoutVersion=2;
}
function renderSettingInput(n,key,def,inline=false){
 const value=n.props?.[key]??def[0],bind=inline?`data-inline-node="${esc(n.id)}" data-inline-prop="${esc(key)}"`:`data-logic-prop="${esc(key)}"`;
 if(key==='widgetId'){
  const widgets=current().scenes.flatMap(sc=>sc.widgets).filter(w=>n.type==='screenout'?['battery','bar','progress','value','integer','analog','digital','led','slider','gauge','switch','checkbox','text','rfwave','rfsignal','rfrssi','waterfall','spectrum'].includes(w.type):['slider','switch','checkbox'].includes(w.type)&&w.source==='constant');
  return `<select ${bind} aria-label="${esc(def[1])}"><option value="">Select widget</option>${widgets.map(w=>`<option value="${esc(w.id)}" ${w.id===value?'selected':''}>${esc(w.type+': '+(w.text||w.id))}</option>`).join('')}</select>`;
 }
 if(key==='library_id'){
  const libs=current().githubLibraries||[];return `<select ${bind} aria-label="${esc(def[1])}"><option value="">Select library</option>${libs.map(x=>`<option value="${esc(x.id)}" ${x.id===value?'selected':''}>${esc(x.repo||x.name||x.id)}</option>`).join('')}</select>`;
 }
 if(key==='duty')return `<span class="logic-duty-wrap"><input ${bind} aria-label="Duty, 0 to 100 percent" type="number" min="0" max="100" step="1" value="${esc(value)}"><span class="logic-duty-unit" aria-hidden="true">%</span></span>`;
 return `<input ${bind} aria-label="${esc(def[1])}" type="${esc(def[2]==='number'?'number':'text')}" value="${esc(value)}" ${def[2]==='number'?'step="any"':''}>`;
}
function updateNodeProperty(n,key,newValue){
 const b=BLOCKS[n.type],definition=b?.props[key];if(!definition)return false;
 const v=definition[2]==='number'?Number(newValue):String(newValue);
 if(definition[2]==='number'&&(String(newValue).trim()===''||!Number.isFinite(v))){toast('Enter a valid number');return false}
 const updated={...n.props,[key]:v};
 if(n.type==='schmitt'&&Number(updated.low)>=Number(updated.high)){toast('Schmitt: LOW must be smaller than HIGH');return false}
 if(n.type==='map'&&Number(updated.inMin)===Number(updated.inMax)){toast('MAP: input MIN and MAX must differ');return false}
 if(n.type==='clamp'&&Number(updated.min)>Number(updated.max)){toast('Clamp: MIN must be <= MAX');return false}
 if(n.type==='pulse'&&key==='duty'&&(v<0||v>100)){toast('Duty must be in 0–100%');return false}
 mark();const old=n.props[key];n.props[key]=v;
 if(n.type==='screenout'&&key==='widgetId')for(const sc of current().scenes)for(const w of sc.widgets){if(w.id===old&&w.source==='logic:'+n.id)w.source='constant';if(w.id===v)w.source='logic:'+n.id}
 save();return true;
}
function numberOfWires(g,nodeId,direction,inputIndex=0){
 return g.edges.reduce((sum,e)=>sum+(direction==='in'
   ? (e.to===nodeId && Number(e.input)===inputIndex)
   : (e.from===nodeId)?1:0),0);
}
function renderBoardStrip(){
 const d=current(),meta=presets[d.profile],box=$('logicBoardStrip');if(!box)return;
 const c=d.profile==='cardputeradv';
 const items=c?[
  ['GROVE G2 · INPUT','grovedigital','A','io1'],
  ['GROVE G1 · INPUT','grovedigital','A','io2'],
  ['GROVE G2 · OUTPUT','groveout','A','io1'],
  ['ADC BAT · GPIO10','adc','10',''],
  ['IR TX · GPIO44','gpioout','44','']
 ]:d.profile==='cyd28'?[['GROVE GPIO35 · ADC','adc','35',''],['GROVE GPIO35 · IN','digital','35','']]:d.profile==='s3'?[['ADC GPIO4','adc','4',''],['GPIO OUT 5','gpioout','5','']]:[];
 box.innerHTML=`<div class="board-strip-title">▣ BOARD: <strong>${esc(d.name)} · ${esc(meta.label)}</strong> <span class="board-strip-meta">GPIO / Grove → bloczki</span></div>`+
 `<div class="board-strip-items">`+items.map(([caption,type,port,line])=>`<button class="board-strip-add" data-board-type="${type}" data-board-pin="${port}" data-board-line="${line}">＋ ${esc(caption)}</button>`).join('')+
 (c?'<span class="board-strip-status">I²C G8/G9 · keyboard TCA8418 · BMI270 · ES8311 · SPI microSD (piny w GPIO & Ports)</span>':'')+'</div>';
}
$('logicBoardStrip').addEventListener('click',event=>{
 const el=event.target.closest('[data-board-type]');if(!el)return;
 addLogicNode(el.dataset.boardType);
 const n=ensureLogic().nodes.find(n=>n.id===logicSelected);if(!n)return;
 if(n.type.startsWith('grove')){n.props.port=el.dataset.boardPin;n.props.line=el.dataset.boardLine}
 else n.props.gpio=Number(el.dataset.boardPin);
 save();renderLogic();toast('Dodano bloczek '+el.textContent.trim());
});
function renderLogic(){
 renderBoardStrip();
 const g=ensureLogic(),q=($('logicSearch').value||'').trim().toLowerCase();
 const needsInitialAutoLayout=!g.layoutVersion && g.nodes.length>0;
 let previous='';$('logicPalette').innerHTML=Object.entries(BLOCKS).filter(([id,b])=>(b.label+' '+b.cat+' '+id).toLowerCase().includes(q)).map(([id,b])=>{const h=b.cat!==previous?`<div class="logic-category">${esc(b.cat)}</div>`:'';previous=b.cat;return h+`<button class="logic-palette-btn" data-block="${id}" style="--cat:${b.color}"><span class="logic-palette-icon" aria-hidden="true">${esc(BLOCK_SYMBOLS[id]||'◈')}</span>${esc(b.label)}<small>＋ Add block · IN ${b.inputs.length} / OUT 1</small></button>`}).join('')||'<p>No matching blocks</p>';
 $('logicNodes').innerHTML=g.nodes.map(n=>{
  const b=BLOCKS[n.type];if(!b)return '';
  const settings=Object.entries(b.props).map(([key,def])=>`<div class="logic-setting"><label title="${esc(key)}">${esc(key==='duty'?'Duty':def[1])}</label>${renderSettingInput(n,key,def,true)}</div>`).join('')||'<div class="logic-setting-note">No parameters · live values below</div>';
  const outputCount=numberOfWires(g,n.id,'out');
  return `<div class="logic-node ${logicSelected===n.id?'selected':''}" data-node="${esc(n.id)}" style="left:${n.x}px;top:${n.y}px;--cat:${b.color}"><div class="logic-node-head" data-grab="${esc(n.id)}"><span>${esc(b.label)}</span><span class="logic-node-symbol">${esc(BLOCK_SYMBOLS[n.type]||'◈')}</span></div>${b.inputs.map((name,i)=>{const inputCount=numberOfWires(g,n.id,'in',i);return `<div class="logic-pin logic-input ${inputCount?'logic-connected':''}"><b tabindex="0" role="button" aria-label="Input ${esc(name)}; ${inputCount} wires" class="logic-socket input-socket" title="IN ${esc(name)} · ${inputCount} connected wires" data-in-node="${esc(n.id)}" data-in-index="${i}" data-connected="${inputCount?1:0}"><span class="logic-count" data-count="${inputCount}">${inputCount}</span></b><span class="logic-pin-text">IN · ${esc(name)}</span><span class="logic-port-status">${inputCount?'LINKED':'EMPTY'}</span><span class="logic-input-reading" data-input-live="${esc(n.id)}" data-input-index="${i}">—</span></div>`}).join('')}<div class="logic-pin logic-output"><span class="logic-pin-text">OUT · VALUE</span><b tabindex="0" role="button" aria-label="Output; ${outputCount} wires" class="logic-socket output-socket ${logicSource===n.id?'chosen':''}" title="OUT · ${outputCount} connected wires" data-out="${esc(n.id)}" data-connected="${outputCount?1:0}"><span class="logic-count" data-count="${outputCount}">${outputCount}</span></b></div><div class="logic-node-settings"><div class="logic-node-settings-head">SETTINGS · EDIT HERE</div>${settings}</div><div class="logic-node-result">LIVE OUT: <span class="logic-live" data-live="${esc(n.id)}">—</span> · ${esc(n.id.slice(-7))}</div></div>`;
 }).join('');
 if(needsInitialAutoLayout){arrangeLogicNodes();save();renderLogic();return;}
 const cards=[...$('logicNodes').querySelectorAll('.logic-node')];const maxX=Math.max(1800,...cards.map(el=>el.offsetLeft+el.offsetWidth+45));const maxY=Math.max(1300,...cards.map(el=>el.offsetTop+el.offsetHeight+50));
 $('logicBoard').style.width=maxX+'px';$('logicBoard').style.height=maxY+'px';
 $('logicWires').setAttribute('width',maxX);$('logicWires').setAttribute('height',maxY);
 renderLogicWires();updateTraceUI();
 $('logicConnection').textContent=logicSource?`Connect: ${BLOCKS[nodeById(logicSource)?.type]?.label||'block'} → choose input`:'Click an output, then an input';
 const n=nodeById(logicSelected);if(!n){$('logicInspector').textContent='Select a block to edit its properties.';return}
 const b=BLOCKS[n.type];$('logicInspector').innerHTML=`<div class="bar" style="justify-content:space-between"><h3>Properties: ${esc(b.label)}</h3><button id="logicDelete" class="red">Delete block</button></div><div class="logic-props">${Object.entries(b.props).map(([key,def])=>`<div class="field"><label>${esc(key==='duty'?'Duty':def[1])}</label>${renderSettingInput(n,key,def)}</div>`).join('')||'<span class="hint">No editable parameters</span>'}</div><div class="hint">Edit settings directly on the block or here. OUT connects to multiple IN sockets. One IN has one source.</div>`;
}
const blockSizeControl=$('blockSize');
function setBlockSize(mode){
 const compact=mode!=='normal';document.body.classList.toggle('blocks-compact',compact);
 blockSizeControl.value=compact?'compact':'normal';
 try{localStorage.setItem('cyd_block_size',compact?'compact':'normal')}catch(e){}
 renderLogic();
}
blockSizeControl.onchange=()=>setBlockSize(blockSizeControl.value);
setBlockSize((()=>{try{return localStorage.getItem('cyd_block_size')||'compact'}catch(e){return 'compact'}})());
$('logicSearch').oninput=renderLogic;
$('logicPalette').onclick=e=>{const b=e.target.closest('[data-block]');if(b)addLogicNode(b.dataset.block)};
$('logicBoard').addEventListener('click',e=>{const out=e.target.closest('[data-out]'),input=e.target.closest('[data-in-node]'),wire=e.target.closest('[data-edge]'),node=e.target.closest('[data-node]');const g=ensureLogic();if(out){logicSource=out.dataset.out;renderLogic();return}if(input){if(!logicSource){toast('Select an output pin first');return}if(logicSource===input.dataset.inNode){toast('You cannot connect a block to itself');return}mark();g.edges=g.edges.filter(v=>!(v.to===input.dataset.inNode&&v.input===+input.dataset.inIndex));g.edges.push({from:logicSource,to:input.dataset.inNode,input:+input.dataset.inIndex});const target=nodeById(input.dataset.inNode);if(target?.type==='screenout'){const widget=current().scenes.flatMap(sc=>sc.widgets).find(w=>w.id===target.props.widgetId);if(widget)widget.source='logic:'+target.id;}logicSource=null;save();renderLogic();return}if(wire){mark();g.edges.splice(+wire.dataset.edge,1);save();renderLogic();return}if(e.target.closest('input,select,textarea,label'))return;if(node){logicSelected=node.dataset.node;renderLogic()}});
$('logicNodes').addEventListener('pointerdown',e=>{const h=e.target.closest('[data-grab]');if(!h)return;const n=nodeById(h.dataset.grab);if(!n)return;logicSelected=n.id;const scroll=$('logicBoard').getBoundingClientRect();logicMove={id:n.id,x:e.clientX,y:e.clientY,nx:n.x,ny:n.y,started:false};h.setPointerCapture(e.pointerId)});
$('logicNodes').addEventListener('pointermove',e=>{if(!logicMove)return;let n=nodeById(logicMove.id);if(!n)return;const dx=e.clientX-logicMove.x,dy=e.clientY-logicMove.y;if(Math.abs(dx)+Math.abs(dy)<2)return;if(!logicMove.started){mark();logicMove.started=true}n.x=clamp(Math.round(logicMove.nx+dx),0,7500);n.y=clamp(Math.round(logicMove.ny+dy),0,4000);const h=$('logicNodes').querySelector(`[data-node="${n.id}"]`);if(h){h.style.left=n.x+'px';h.style.top=n.y+'px';const board=$('logicBoard'),svg=$('logicWires');board.style.width=Math.max(board.offsetWidth,n.x+h.offsetWidth+50)+'px';board.style.height=Math.max(board.offsetHeight,n.y+h.offsetHeight+50)+'px';svg.setAttribute('width',board.offsetWidth);svg.setAttribute('height',board.offsetHeight)}renderLogicWires()});
$('logicNodes').addEventListener('pointerup',()=>{if(logicMove){logicMove=null;save();renderLogic()}});
$('logicNodes').addEventListener('focusin',e=>{const el=e.target.closest('[data-inline-node]');if(!el)return;logicSelected=el.dataset.inlineNode;document.querySelectorAll('#logicNodes .logic-node').forEach(card=>card.classList.toggle('selected',card.dataset.node===logicSelected))});
$('logicNodes').addEventListener('change',e=>{const el=e.target.closest('[data-inline-prop]');if(!el)return;const n=nodeById(el.dataset.inlineNode);if(!n)return;if(updateNodeProperty(n,el.dataset.inlineProp,el.value)){logicSelected=n.id;renderLogic()}else{renderLogic()}});
$('logicInspector').addEventListener('change',e=>{const el=e.target.closest('[data-logic-prop]');if(!el)return;const n=nodeById(logicSelected);if(!n)return;updateNodeProperty(n,el.dataset.logicProp,el.value);renderLogic()});
$('logicArrange').onclick=()=>{mark();arrangeLogicNodes();save();renderLogic();toast('Auto arranged blocks and wires')};
$('logicInspector').addEventListener('click',e=>{if(!e.target.closest('#logicDelete'))return;mark();const g=ensureLogic();g.nodes=g.nodes.filter(n=>n.id!==logicSelected);g.edges=g.edges.filter(x=>x.from!==logicSelected&&x.to!==logicSelected);for(const sc of current().scenes)for(const w of sc.widgets)if(w.source==='logic:'+logicSelected)w.source='constant';logicSelected=null;logicSource=null;save();renderLogic()});
// Monitor serialowy: odczyt asynchroniczny, bufor 500 wierszy, odświeżanie max ~10 Hz.
let meterNumber=null,meterChannel='',serialPaused=false,serialBytes=0,serialLineCount=0;
let serialReadTask=null,serialFlushTimer=null;
function serialFlush(){serialFlushTimer=null;$('serialMonitor').textContent=serialLines.join('\n');$('serialMonitor').scrollTop=$('serialMonitor').scrollHeight;$('serialCount').textContent=serialLineCount+' linii · '+serialBytes+' bajtów';drawScope();updateTraceUI()}
function scheduleSerialFlush(){if(serialFlushTimer===null)serialFlushTimer=setTimeout(serialFlush,100)}
function appendSerialLine(line){
 if(serialPaused)return;
 if(line.startsWith('@DBG|')){
  const m=/^@DBG\|([A-Za-z0-9_-]{1,100})\|([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)$/.exec(line);
  if(m){const v=Number(m[2]);if(Number.isFinite(v)){
   liveReadings[m[1]]={value:v,time:Date.now()};tracePacketCount++;
   const channel='BLOCK:'+m[1].slice(-7);
   if(!scopeChannels[channel]){scopeChannels[channel]=[];const opt=document.createElement('option');opt.value=channel;opt.textContent=channel;$('scopeChannel').append(opt)}
   const a=scopeChannels[channel];a.push(v);if(a.length>400)a.shift();
   if(logicSelected===m[1]){$('meterValue').textContent=formatTrace(v);$('meterLabel').textContent=BLOCKS[nodeById(m[1])?.type]?.label||m[1]}
  }}scheduleSerialFlush();return;
 }

 serialLines.push(line);if(serialLines.length>500)serialLines.shift();serialLineCount++;
 const m=line.match(/(?:^|[:=\s])(-?\d+(?:[.,]\d+)?)(?=\s|$)/);
 if(m){const v=Number(m[1].replace(',','.'));if(Number.isFinite(v)){
  let ch=(line.split(/[:=]/)[0]||'DANE').trim().slice(0,25);if(ch===line)ch='DANE';
  meterNumber=v;meterChannel=ch;$('meterValue').textContent=Number.isInteger(v)?String(v):v.toFixed(3);$('meterLabel').textContent=ch;
  if(!scopeChannels[ch]){scopeChannels[ch]=[];const opt=document.createElement('option');opt.value=ch;opt.textContent=ch;$('scopeChannel').append(opt)}
  const a=scopeChannels[ch];a.push(v);if(a.length>400)a.shift();scopeValues.push(v);if(scopeValues.length>400)scopeValues.shift();
 }}scheduleSerialFlush();
}
function drawScope(){const cv=$('scopeCanvas'),ctx=cv.getContext('2d'),w=cv.width,h=cv.height,ch=$('scopeChannel').value,a=(ch==='__latest'?scopeValues:scopeChannels[ch])||[];ctx.fillStyle='#081426';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#244358';ctx.lineWidth=1;for(let i=1;i<6;i++){ctx.beginPath();ctx.moveTo(0,i*h/6);ctx.lineTo(w,i*h/6);ctx.stroke()}for(let i=1;i<12;i++){ctx.beginPath();ctx.moveTo(i*w/12,0);ctx.lineTo(i*w/12,h);ctx.stroke()}if(a.length<2)return;let min=Math.min(...a),max=Math.max(...a);if(min===max){min-=1;max+=1}ctx.strokeStyle='#5cf5ba';ctx.lineWidth=2;ctx.beginPath();a.forEach((v,i)=>{let x=i/(a.length-1)*(w-8)+4,y=h-10-(v-min)/(max-min)*(h-20);if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y)});ctx.stroke();ctx.fillStyle='#bdcfe0';ctx.font='12px monospace';ctx.fillText(max.toFixed(2),5,12);ctx.fillText(min.toFixed(2),5,h-4)}
$('scopeChannel').onchange=drawScope;
$('traceToggle').onclick=()=>{traceOn=!traceOn;$('traceToggle').textContent=traceOn?'Trace: ON':'Trace: OFF';writeDebugCommand(traceOn?'@DBG ON':'@DBG OFF');updateTraceUI()};
$('traceRate').onchange=()=>writeDebugCommand('@DBG RATE '+Number($('traceRate').value));
$('traceFocus').onclick=()=>{const i=ensureLogic().nodes.findIndex(n=>n.id===logicSelected);if(i<0){toast('Select a block first.');return}traceFocused=true;writeDebugCommand('@DBG FOCUS '+i);toast('Focused on '+BLOCKS[ensureLogic().nodes[i].type].label)};
$('traceAll').onclick=()=>{traceFocused=false;writeDebugCommand('@DBG ALL');toast('Tracing all blocks')};

$('serialPause').onclick=()=>{serialPaused=!serialPaused;$('serialPause').classList.toggle('active',serialPaused);$('serialPause').textContent=serialPaused?'Wznów':'Pauza';$('serialStatus').textContent=serialPaused?'Wstrzymano wyświetlanie (odczyt portu trwa).':serialConnected?'Odczyt danych na żywo.':'Port rozłączony.'};
$('serialClear').onclick=()=>{if(serialFlushTimer!==null){clearTimeout(serialFlushTimer);serialFlushTimer=null}serialLines=[];scopeValues=[];scopeChannels={};serialBytes=0;serialLineCount=0;$('serialMonitor').textContent='';$('serialCount').textContent='0 lines · 0 bytes';$('meterValue').textContent='—';$('meterLabel').textContent='Awaiting data';$('scopeChannel').innerHTML='<option value="__latest">Latest value</option>';drawScope()};
async function serialReadLoop(port){let reader=null;const decoder=new TextDecoder();let pending='';try{reader=port.readable.getReader();serialReader=reader;
 while(serialConnected){const {value,done}=await reader.read();if(done)break;if(!value)continue;serialBytes+=value.byteLength;pending+=decoder.decode(value,{stream:true});let pos;
  while((pos=pending.indexOf('\n'))>=0){const line=pending.slice(0,pos).trim();pending=pending.slice(pos+1);if(line)appendSerialLine(line)}
  if(pending.length>2048)pending=pending.slice(-1024);scheduleSerialFlush();
 }
}catch(e){if(serialConnected)toast('USB: '+e.message)}finally{if(reader){try{reader.releaseLock()}catch{}}if(serialReader===reader)serialReader=null;serialConnected=false;$('serialStatus').textContent='Odczyt portu zatrzymany.';scheduleSerialFlush()}}
async function disconnectSerial(){serialConnected=false;
 if(serialReader){try{await serialReader.cancel()}catch{}}
 if(serialReadTask){try{await serialReadTask}catch{}serialReadTask=null}
 if(serialPort){try{await serialPort.close()}catch(e){console.warn('Zamknięcie portu USB:',e.message)}}
 serialPort=null;serialReader=null;$('serialStatus').textContent='Port disconnected.';updateTraceUI();
}
$('serialDisconnect').onclick=()=>{disconnectSerial()};
$('serialConnect').onclick=async()=>{
 if(!navigator.serial){toast('Monitor USB wymaga Chrome lub Edge na komputerze (http://localhost).');return}
 try{if(serialPort)await disconnectSerial();serialPort=await navigator.serial.requestPort();await serialPort.open({baudRate:Number($('baud').value)});serialConnected=true;
 serialPaused=false;$('serialPause').classList.remove('active');$('serialPause').textContent='Pauza';
 $('serialStatus').textContent='Połączono USB · '+$('baud').value+' bps. Monitor wyłączy się przed flashowaniem.';
 serialReadTask=serialReadLoop(serialPort);updateTraceUI();
 }catch(e){toast('USB: '+e.message);await disconnectSerial()}
};
function setDockOpen(open){
 document.body.classList.toggle('dock-open',!!open);
 $('instrumentDock').classList.toggle('dock-collapsed',!open);
 $('dockToggle').setAttribute('aria-expanded',open?'true':'false');
 $('dockToggle').querySelector('.dock-indicator').textContent=open?'▾':'▴';
 try{localStorage.setItem('cyd_diag_dock_v26',open?'open':'closed')}catch{}
 if(open)requestAnimationFrame(drawScope);
}
$('dockToggle').onclick=()=>setDockOpen(!document.body.classList.contains('dock-open'));
$('toggleExplorer').onclick=()=>document.body.classList.toggle('hide-explorer');
$('toggleInspector').onclick=()=>document.body.classList.toggle('hide-inspector');
$('hideProperties').onclick=()=>document.body.classList.add('hide-inspector');
$('shortcutBuild').onclick=()=>selectTab('build');
window.addEventListener('keydown',e=>{
 if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='b'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){
  e.preventDefault();document.body.classList.toggle('hide-explorer');
 }
});
if(window.innerWidth<800){document.body.classList.add('hide-explorer','hide-inspector')}
let restoreDockOpen=false;try{restoreDockOpen=localStorage.getItem('cyd_diag_dock_v26')==='open'}catch{}setDockOpen(restoreDockOpen);
function updateDockStatus(){const el=$('dockConnection');if(el){el.textContent=serialConnected?'● USB connected':'● USB offline';el.classList.toggle('connected',serialConnected)}}
const updateTraceUIOriginal=updateTraceUI;
updateTraceUI=function(){updateTraceUIOriginal();updateDockStatus()};

// DIAG GPT 2.16: user-initiated, local-only diagnostics. No telemetry leaves the browser.
const diagErrors=[], diagActions=[];
function diagRecordAction(type, info=''){
 diagActions.push({time:new Date().toISOString(),type,info:String(info).slice(0,250)});
 if(diagActions.length>200)diagActions.shift();
}
window.addEventListener('error',event=>{
 diagErrors.push({time:new Date().toISOString(),kind:'window.error',message:String(event.message||'Unknown error'),file:String(event.filename||''),line:event.lineno||0,column:event.colno||0});
 if(diagErrors.length>100)diagErrors.shift();
});
window.addEventListener('unhandledrejection',event=>{
 diagErrors.push({time:new Date().toISOString(),kind:'unhandledrejection',message:String(event.reason?.stack||event.reason||'Unknown rejection')});
 if(diagErrors.length>100)diagErrors.shift();
});
document.addEventListener('click',event=>{
 const btn=event.target.closest?.('button');if(btn && !btn.closest('#diagGPTWindow'))diagRecordAction('button', btn.id||btn.dataset?.tab||btn.dataset?.add||btn.textContent.trim().slice(0,65));
},{capture:true});
function diagScrub(value, secrets){
 if(Array.isArray(value))return value.map(x=>diagScrub(x,secrets));
 if(value&&typeof value==='object'){
  const dest={};
  for(const [key,val] of Object.entries(value)){
   if(/(?:password|passwd|secret|token|auth(?:orization)?|api[_-]?key|credential|private[_-]?key)/i.test(key)){
    if(typeof val==='string'&&val.length>0)secrets.add(val);
    dest[key]='[REDACTED]';
   }else dest[key]=diagScrub(val,secrets);
  }
  return dest;
 }
 return value;
}
function diagSafeText(raw, secrets){
 let output=String(raw??'');
 for(const secret of [...secrets].filter(v=>v&&v.length>=3).sort((a,b)=>b.length-a.length))output=output.split(secret).join('[REDACTED]');
 return output.replace(/((?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*)([^\s,;]+)/gi,'$1[REDACTED]');
}
function diagGenerate(){
 const mask=$('diagMaskSecrets').checked,includeProject=$('diagIncludeProject').checked,includeSerial=$('diagIncludeSerial').checked;
 const secrets=new Set();
 // Extract secret values from the original project even when the JSON section is excluded.
 if(mask)diagScrub(project,secrets);
 const d=current(),g=ensureLogic();
 const object={
  format:'CYD Studio DIAG GPT report v1',generated_at:new Date().toISOString(),app:'CYD Studio DIAG 2.42 (Mokxi export + random click tones)',
  session:{active_device:d.name,active_profile:d.profile,active_screen:scene()?.name||null,editor_tab:tab,
   screen_rotation:d.rotation||0,screen_size:screenSize(),selected_widget:sel?.id||null,selected_block:logicSelected||null,
   connected_usb:serialConnected,baud:Number($('baud').value),serial_paused:serialPaused,trace_enabled:traceOn,
   trace_focus:traceFocused,trace_packet_count:tracePacketCount,
   build_job_id:buildJob||null,build_phase:$('buildPhase').textContent,build_progress:$('buildPct').textContent,
   build_status:$('status').textContent,device_count:project.devices.length,
   block_type_count:Object.keys(BLOCKS).length},
  live_blocks:g.nodes.map(n=>({id:n.id,type:n.type,label:BLOCKS[n.type]?.label||n.type,
    properties:n.props,input_connections:g.edges.filter(e=>e.to===n.id).map(e=>({source:e.from,input:e.input,live_value:liveReadings[e.from]?.value??null,age_ms:liveReadings[e.from]?Date.now()-liveReadings[e.from].time:null})),
    output_connections:g.edges.filter(e=>e.from===n.id).map(e=>({target:e.to,input:e.input})),
    output_value:liveReadings[n.id]?.value??null,
    age_ms:liveReadings[n.id]?Date.now()-liveReadings[n.id].time:null})),
  active_graph_edges:g.edges,
  build_and_generator:{build_log:$('log').textContent,build_info:$('buildInfo').textContent,
   code_diagnostics:$('codeDiagnostics').textContent,generator_lint:$('generatorLint').textContent,
   build_phase:$('buildPhase').textContent,build_progress:$('buildPct').textContent,
   serial_status:$('serialStatus').textContent},
  browser_errors:diagErrors,session_actions:diagActions,
  availability:{hardware_usb_connected:serialConnected,serial_lines_in_memory:serialLines.length,
    serial_history_note:'Only last 500 displayed serial lines retained. Clearing monitor or pausing can discard older lines.',
    live_trace_note:'Only latest observed value per block; timestamps relative to generated_at.',
    no_automatic_transmission:true}
 };
 if(includeSerial){object.usb={serial_lines:serialLines,serial_line_count_total:serialLineCount,serial_bytes_total:serialBytes,
   latest_meter:{channel:meterChannel,value:meterNumber},sampled_scope_channels:scopeChannels,
   sampled_scope_latest:scopeValues,trace_last_values:Object.fromEntries(Object.entries(liveReadings).map(([id,v])=>[id,{value:v.value,age_ms:Date.now()-v.time}]))};}
 if(includeProject)object.project=mask?diagScrub(project,secrets):project;
 let report='CYD STUDIO DIAG GPT — FULL DIAGNOSTIC REPORT\n'+
 'Generated locally. Nothing was transmitted automatically.\n'+
 'Note: review custom C++ and logs for sensitive data before sharing.\n\n'+JSON.stringify(object,null,2);
 if(mask)report=diagSafeText(report,secrets);
 return report;
}
function diagRefresh(){
 const report=diagGenerate();$('diagReportPreview').value=report;
 $('diagReportInfo').textContent='Current snapshot · '+report.length.toLocaleString('en-GB')+' characters · '+
 ensureLogic().nodes.length+' blocks · '+ensureLogic().edges.length+' connections · '+
 serialLines.length+' retained USB lines · '+diagErrors.length+' browser errors.';
 return report;
}
function diagShow(open){
 $('diagGPTWindow').hidden=!open;
 if(open){diagRefresh();$('diagGPTRefresh').focus();}
}
$('openDiagGPT').onclick=()=>diagShow(true);
$('openDiagGPTDock').onclick=()=>diagShow(true);
$('diagGPTClose').onclick=()=>diagShow(false);
$('diagGPTRefresh').onclick=()=>{diagRefresh();$('diagCopyStatus').textContent='Updated'};
for(const name of ['diagIncludeProject','diagIncludeSerial','diagMaskSecrets'])$(name).onchange=diagRefresh;
$('diagGPTCopy').onclick=async()=>{
 const report=diagRefresh();
 try{
  if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(report);
  else{const el=$('diagReportPreview');el.focus();el.select();if(!document.execCommand('copy'))throw Error('Clipboard unavailable');}
  $('diagCopyStatus').textContent='Copied ✓';toast('Diagnostic report copied. Paste it into this chat.');
 }catch(e){$('diagCopyStatus').textContent='Copy failed';toast('Copy failed: '+e.message+' · select report text manually')}
};
$('diagGPTDownload').onclick=()=>{
 const report=diagRefresh(),stamp=new Date().toISOString().replace(/[:.]/g,'-');
 downloadBlob(new Blob([report],{type:'text/plain;charset=utf-8'}),'CYD-DIAG-GPT-'+stamp+'.txt');
 $('diagCopyStatus').textContent='Saved .txt';
};
function diagStandaloneWindow(){
 const win=window.open('','CYD_DIAG_GPT_POPOUT','width=900,height=650,resizable=yes,scrollbars=yes');
 if(!win){toast('Popup blocked. Allow popups for localhost.');return}
 // Static HTML is only a presentation shell; report inserted as textContent, never as markup.
 win.document.open();
 win.document.write('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>CYD Studio DIAG GPT</title><style>body{background:#091725;color:#bdf5dd;font:14px system-ui;margin:16px}pre{white-space:pre-wrap;word-break:break-word;background:#10243a;padding:15px;border-radius:10px;font:12px/1.5 Consolas,monospace}button{padding:10px;margin:5px;border-radius:7px;background:#176395;color:white;border:1px solid #68b8ef;cursor:pointer}</style></head><body><h2>CYD Studio — DIAG GPT</h2><p>Move this window to another monitor. Copy the report into ChatGPT.</p><button id="copy">Copy full report</button><button id="refresh">Refresh from editor</button><pre id="report"></pre></body></html>');
 win.document.close();
 const refresh=()=>{if(win.closed)return;win.document.getElementById('report').textContent=diagRefresh()};
 win.document.getElementById('refresh').onclick=refresh;
 win.document.getElementById('copy').onclick=async()=>{refresh();try{await win.navigator.clipboard.writeText(win.document.getElementById('report').textContent)}catch{const r=win.document.createRange();r.selectNodeContents(win.document.getElementById('report'));win.getSelection().removeAllRanges();win.getSelection().addRange(r)}};
 refresh();win.focus();
}
$('diagGPTPopout').onclick=diagStandaloneWindow;
// Drag only by the title bar; all regular form inputs remain usable.
let diagDrag=null;
$('diagGPTDrag').addEventListener('pointerdown',event=>{
 if(event.target.closest('button')||window.matchMedia('(max-width:640px)').matches)return;
 const el=$('diagGPTWindow'),rect=el.getBoundingClientRect();
 diagDrag={id:event.pointerId,dx:event.clientX-rect.left,dy:event.clientY-rect.top};
 event.currentTarget.setPointerCapture(event.pointerId);
});
$('diagGPTDrag').addEventListener('pointermove',event=>{
 if(!diagDrag||event.pointerId!==diagDrag.id)return;
 const el=$('diagGPTWindow'),x=Math.max(0,Math.min(window.innerWidth-95,event.clientX-diagDrag.dx)),
 y=Math.max(0,Math.min(window.innerHeight-65,event.clientY-diagDrag.dy));
 el.style.left=x+'px';el.style.top=y+'px';
});
for(const type of ['pointerup','pointercancel'])$('diagGPTDrag').addEventListener(type,()=>{diagDrag=null});
window.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('diagGPTWindow').hidden)diagShow(false)});

drawScope();
setInterval(()=>{if(tab==='screen' && !document.hidden && current().scenes.length && scene().widgets.some(w=>w.type==='rfwave'))renderCanvas()},250);
$('undo').disabled=true;selectTab('screen');status();scheduleLint();updateTraceUI();
})();