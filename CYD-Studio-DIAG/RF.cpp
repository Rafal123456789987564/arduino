#include <Arduino.h>
#include <esp_arduino_version.h>
#include <RadioLib.h>
#include <SPI.h>
#include <TFT_eSPI.h>
#include <SPI.h>
#include <XPT2046_Touchscreen.h>


// Automatycznie wygenerowany projekt CYD Studio.
// Screen orientation: rotation=0  dimensions=240x320
static uint32_t lastRefresh=0;
TFT_eSPI tft = TFT_eSPI();
void drawCydSensorIcon(int cx,int cy,int r,const char*name,uint16_t fg){
  tft.drawCircle(cx,cy,r,fg);
  if(strcmp(name,"wifi")==0||strcmp(name,"radio")==0||strcmp(name,"signal")==0||strcmp(name,"waves")==0||strcmp(name,"nfc")==0){
    tft.fillCircle(cx,cy+r/2,2,fg);
    for(int layer=1;layer<=3;layer++){
      float radius=(float)r*layer/3.0f;
      for(int seg=0;seg<15;seg++){
        float a=-2.8f+(1.8f*seg/14.0f),b=-2.8f+(1.8f*(seg+1)/14.0f);
        tft.drawLine(cx+(int)(radius*cosf(a)),cy+r/2+(int)(radius*sinf(a)),cx+(int)(radius*cosf(b)),cy+r/2+(int)(radius*sinf(b)),fg);
      }
    }
  }else if(strcmp(name,"can")==0){
    tft.drawCentreString("CAN",cx,cy-8,2);
  }else if(strcmp(name,"temperature")==0){
    tft.drawRoundRect(cx-r/4,cy-r/2,r/2,r,4,fg);tft.fillCircle(cx,cy+r/2,r/4,fg);
  }else if(strcmp(name,"battery")==0){
    tft.drawRect(cx-r*3/4,cy-r/3,r*3/2,r*2/3,fg);tft.fillRect(cx+r*3/4,cy-r/6,r/6,r/3,fg);
    tft.fillRect(cx-r/2,cy-r/6,r*2/3,r/3,fg);
  }else if(strcmp(name,"gyro")==0||strcmp(name,"vibration")==0||strcmp(name,"sensor")==0){
    tft.drawCircle(cx,cy,r/2,fg);tft.fillCircle(cx,cy,2,fg);tft.drawLine(cx-r,cy,cx-r/2,cy,fg);
    tft.drawLine(cx+r/2,cy,cx+r,cy,fg);
  }else if(strcmp(name,"microphone")==0){
    tft.drawRoundRect(cx-r/3,cy-r*2/3,r*2/3,r,6,fg);tft.drawLine(cx,cy+r/3,cx,cy+r,fg);
    tft.drawLine(cx-r/2,cy+r,cx+r/2,cy+r,fg);
  }else if(strcmp(name,"voltage")==0){
    tft.drawLine(cx+r/4,cy-r,cx-r/2,cy,fg);tft.drawLine(cx-r/2,cy,cx+r/5,cy,fg);
    tft.drawLine(cx+r/5,cy,cx-r/4,cy+r,fg);
  }else if(strcmp(name,"pressure")==0||strcmp(name,"speed")==0){
    tft.drawLine(cx,cy,cx+r/2,cy-r/2,fg);tft.fillCircle(cx,cy,3,fg);
  }else if(strcmp(name,"water")==0){
    tft.fillCircle(cx,cy+r/4,r/3,fg);tft.drawLine(cx-r/3,cy+r/4,cx,cy-r/2,fg);
    tft.drawLine(cx,cy-r/2,cx+r/3,cy+r/4,fg);
  }else if(strcmp(name,"light")==0){
    tft.drawCircle(cx,cy-r/5,r/2,fg);tft.drawLine(cx-r/4,cy+r/2,cx+r/4,cy+r/2,fg);
  }else if(strcmp(name,"bluetooth")==0){
    tft.drawLine(cx,cy-r,cx,cy+r,fg);tft.drawLine(cx,cy-r,cx+r/2,cy-r/2,fg);
    tft.drawLine(cx+r/2,cy-r/2,cx-r/2,cy+r/2,fg);
    tft.drawLine(cx-r/2,cy-r/2,cx+r/2,cy+r/2,fg);tft.drawLine(cx+r/2,cy+r/2,cx,cy+r,fg);
  }else{
    tft.drawLine(cx,cy-r,cx,cy+r,fg);tft.drawLine(cx-r,cy+r,cx+r,cy+r,fg);
  }
}
// CC1101 scans *receiver RSSI* across frequencies. No RF IQ sampling or RF FFT.
static const int CYD_RF_BINS=48;
static const float CYD_RF_START=433.300000f,CYD_RF_END=434.500000f;
static const uint32_t CYD_RF_SETTLE=12UL;
static float cydRFBins[64]={};
static float cydRFWf[24][64]={};
static uint8_t cydRFRow=0;
static uint8_t cydRFCursor=0;
static float cydRFLatest=-130.0f;
static bool cydRFReady=false;
static uint32_t cydRFLastTune=0;
static SPIClass cydRFBus(HSPI);
static CC1101 cydRadio=new Module(22,27,RADIOLIB_NC,RADIOLIB_NC,cydRFBus,SPISettings(2000000,MSBFIRST,SPI_MODE0));
void initCydRF(){
  cydRFBus.begin(18,19,23,22);
  // RadioLib 7.8.1 CC1101 frequency units: MHz (float).
  cydRFReady=(cydRadio.begin()==RADIOLIB_ERR_NONE);
  if(cydRFReady){
    cydRFReady=(cydRadio.setFrequency(CYD_RF_START)==RADIOLIB_ERR_NONE);
    if(cydRFReady)cydRFReady=(cydRadio.receiveDirectAsync()==RADIOLIB_ERR_NONE);
  }
  cydRFLastTune=millis();
  Serial.println(cydRFReady?"CC1101: RSSI scan online":"CC1101: start failed; check SPI, wiring and power");
}
void pollCydRF(){
  if(!cydRFReady || (uint32_t)(millis()-cydRFLastTune)<CYD_RF_SETTLE)return;
  cydRFLatest=cydRadio.getRSSI();
  cydRFBins[cydRFCursor]=cydRFLatest;
  cydRFWf[cydRFRow][cydRFCursor]=cydRFLatest;
  if(++cydRFCursor>=CYD_RF_BINS){cydRFCursor=0;cydRFRow=(cydRFRow+1)%24;}
  const float MHz=CYD_RF_START+(CYD_RF_END-CYD_RF_START)*cydRFCursor/(CYD_RF_BINS-1);
  cydRFReady=(cydRadio.setFrequency(MHz)==RADIOLIB_ERR_NONE);
  if(cydRFReady)cydRFReady=(cydRadio.receiveDirectAsync()==RADIOLIB_ERR_NONE);
  cydRFLastTune=millis();
}
\nvoid drawCydRF(int x,int y,int w,int h){
  if(!cydRFReady){tft.setTextColor(TFT_ORANGE,TFT_BLACK);tft.drawCentreString("CC1101 offline",x+w/2,y+h/2,2);return;}
  const int head=17,bar=34;
  tft.fillRect(x,y,w,h,TFT_BLACK);
  tft.setTextColor(TFT_CYAN,TFT_BLACK);
  tft.drawString("CC1101 RSSI waterfall",x+2,y+1,1);
  const int histH=max(1,h-head-bar),histY=y+head;
  for(int row=0;row<24;row++){
    int rr=(cydRFRow+row)%24;
    for(int col=0;col<CYD_RF_BINS;col++){
      float v=cydRFWf[rr][col];
      uint8_t level=(uint8_t)constrain((v+110.0f)*255.0f/80.0f,0.0f,255.0f);
      uint16_t color=tft.color565(level,level/2,255-level);
      int x0=x+(col*w)/CYD_RF_BINS, x1=x+((col+1)*w)/CYD_RF_BINS;
      int y0=histY+(row*histH)/24,y1=histY+((row+1)*histH)/24;
      tft.fillRect(x0,y0,max(1,x1-x0),max(1,y1-y0),color);
    }
  }
  for(int col=0;col<CYD_RF_BINS;col++){
    float v=cydRFBins[col];
    int a=(int)constrain((v+115.0f)*bar/85.0f,0.0f,(float)bar);
    int x0=x+(col*w)/CYD_RF_BINS,x1=x+((col+1)*w)/CYD_RF_BINS;
    tft.fillRect(x0,y+h-a,max(1,x1-x0),a,TFT_GREEN);
  }
}

static const int SCREEN_ROTATION=0;
uint16_t C565(uint32_t rgb){return tft.color565((rgb>>16)&255,(rgb>>8)&255,rgb&255);}
static const int BACKLIGHT_PIN = 21;
SPIClass touchBus(VSPI);
XPT2046_Touchscreen touch(33,36);
static const int TOUCH_X_MIN=200, TOUCH_X_MAX=3900;
static const int TOUCH_Y_MIN=200, TOUCH_Y_MAX=3900;
static const bool TOUCH_SWAP=false, TOUCH_FLIP_X=false, TOUCH_FLIP_Y=false;
static int activeScene=0;
static bool touchWasDown=false;
static float uiValues[1]={0.0f};
static int activeSlider=-1;
extern float logicValue0;
static const uint8_t BL_CHANNEL=7;
static const uint8_t BL_NORMAL=85, BL_IDLE=0;
static const uint32_t BL_TIMEOUT_MS=60UL * 1000UL;
static uint32_t lastTouchMs=0;
static bool backlightDimmed=false;
void setBacklight(uint8_t percent){
  uint32_t duty=constrain((int)percent,0,100)*255/100;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(BACKLIGHT_PIN,duty);
#else
  ledcWrite(BL_CHANNEL,duty);
#endif
}
void initBacklight(){
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(BACKLIGHT_PIN,1000,8);
#else
  ledcSetup(BL_CHANNEL,1000,8);
  ledcAttachPin(BACKLIGHT_PIN,BL_CHANNEL);
#endif
  setBacklight(BL_NORMAL);
  lastTouchMs=millis();
}
void wakeBacklight(){
  lastTouchMs=millis();
  backlightDimmed=false;
  setBacklight(BL_NORMAL);
}
void pollBacklight(){
  if(BL_TIMEOUT_MS && !backlightDimmed && millis()-lastTouchMs>=BL_TIMEOUT_MS){
    backlightDimmed=true;
    setBacklight(BL_IDLE);
  }
}
namespace WiFi { static const int fake=0; }
void drawState(int x,int y,int w,int h,const char *name,bool ok){
  tft.fillRoundRect(x,y,w,h,7,ok?TFT_DARKGREEN:TFT_MAROON);
  tft.setTextColor(TFT_WHITE,ok?TFT_DARKGREEN:TFT_MAROON);
  tft.drawCentreString(name,x+w/2,y+h/2-8,2);
}
void drawBattery(int x,int y,int w,int h){
  tft.drawRoundRect(x,y,w-7,h,3,TFT_WHITE);
  tft.fillRect(x+w-5,y+h/3,5,h/3,TFT_WHITE);
  tft.setTextColor(TFT_WHITE,TFT_BLACK);tft.drawCentreString("BAT ?",x+w/2,y+h/2-8,2);
}
void drawGyro(int x,int y,int w,int h){drawState(x,y,w,h,"GYRO OFF",false);}
void drawAudio(int x,int y,int w,int h){drawState(x,y,w,h,"MIC OFF",false);}
void drawScene(){
  switch(activeScene){
  case 0: {
    tft.fillScreen(C565(0x101D32));
    tft.setTextColor(C565(0xFFFFFF),C565(0x101D32));
    tft.drawCentreString("DIAG / CYD",120,16,2);
    tft.fillRoundRect(25,47,190,41,8,C565(0x2381B1));
    tft.setTextColor(C565(0xFFFFFF),C565(0x2381B1));
    tft.drawCentreString("DIAGNOSTYKA",120,59,2);
    tft.fillRoundRect(25,97,190,41,8,C565(0x9B66DE));
    tft.setTextColor(C565(0xFFFFFF),C565(0x9B66DE));
    tft.drawCentreString("WIBRACJE",120,109,2);
    tft.fillRoundRect(25,147,190,41,8,C565(0xE59645));
    tft.setTextColor(C565(0xFFFFFF),C565(0xE59645));
    tft.drawCentreString("MIKROFON",120,159,2);
    tft.fillRoundRect(25,197,190,41,8,C565(0x329C76));
    tft.setTextColor(C565(0xFFFFFF),C565(0x329C76));
    tft.drawCentreString("433 MHz",120,209,2);
    tft.fillRoundRect(25,247,190,41,8,C565(0xC45D89));
    tft.setTextColor(C565(0xFFFFFF),C565(0xC45D89));
    tft.drawCentreString("USTAWIENIA",120,259,2);
    drawBattery(63,90,130,50);
    drawCydRF(0,0,240,120);
    break;
  }
  case 1: {
    tft.fillScreen(C565(0x0D1B2E));
    tft.setTextColor(C565(0xFFFFFF),C565(0x0D1B2E));
    tft.drawCentreString("DIAGNOSTYKA",120,22,2);
    drawGyro(23,89,194,85);
    tft.fillRoundRect(48,263,144,43,8,C565(0x2381B1));
    tft.setTextColor(C565(0xFFFFFF),C565(0x2381B1));
    tft.drawCentreString("? MENU",120,276,2);
    break;
  }
  case 2: {
    tft.fillScreen(C565(0x0D1B2E));
    tft.setTextColor(C565(0xFFFFFF),C565(0x0D1B2E));
    tft.drawCentreString("WIBRACJE",120,22,2);
    {
    float v=(float)(65.000000f);
    float frac=constrain((v-(0.000000f))/max(0.000001f,(100.000000f)),0.0f,1.0f);
    tft.drawRect(23,89,194,85,C565(0xFFFFFF));
    tft.fillRect(25,91,(int)((194-4)*frac),max(0,85-4),C565(0x9B66DE));
    }
    tft.fillRoundRect(48,263,144,43,8,C565(0x9B66DE));
    tft.setTextColor(C565(0xFFFFFF),C565(0x9B66DE));
    tft.drawCentreString("? MENU",120,276,2);
    break;
  }
  case 3: {
    tft.fillScreen(C565(0x0D1B2E));
    tft.setTextColor(C565(0xFFFFFF),C565(0x0D1B2E));
    tft.drawCentreString("MIKROFON",120,22,2);
    drawAudio(23,89,194,85);
    tft.fillRoundRect(48,263,144,43,8,C565(0xE59645));
    tft.setTextColor(C565(0xFFFFFF),C565(0xE59645));
    tft.drawCentreString("? MENU",120,276,2);
    break;
  }
  case 4: {
    tft.fillScreen(C565(0x0D1B2E));
    tft.setTextColor(C565(0xFFFFFF),C565(0x0D1B2E));
    tft.drawCentreString("433 MHz",120,22,2);
    tft.fillRoundRect(23,89,194,85,6,C565(0x123448));
    drawCydSensorIcon(65,131,31,"wifi",C565(0x329C76));
    tft.setTextColor(TFT_WHITE,C565(0x123448));tft.drawCentreString("Wi-Fi",158,123,2);
    tft.fillRoundRect(48,263,144,43,8,C565(0x329C76));
    tft.setTextColor(C565(0xFFFFFF),C565(0x329C76));
    tft.drawCentreString("? MENU",120,276,2);
    break;
  }
  case 5: {
    tft.fillScreen(C565(0x0D1B2E));
    tft.setTextColor(C565(0xFFFFFF),C565(0x0D1B2E));
    tft.drawCentreString("USTAWIENIA",120,22,2);
    drawBattery(23,89,194,85);
    tft.fillRoundRect(48,263,144,43,8,C565(0xC45D89));
    tft.setTextColor(C565(0xFFFFFF),C565(0xC45D89));
    tft.drawCentreString("? MENU",120,276,2);
    break;
  }
  default:activeScene=0;break;
  }
}
void onTouch(int x,int y){
  switch(activeScene){
    case 0:
      if(x>=25 && x<215 && y>=47 && y<88){activeScene=1;drawScene();return;}
      if(x>=25 && x<215 && y>=97 && y<138){activeScene=2;drawScene();return;}
      if(x>=25 && x<215 && y>=147 && y<188){activeScene=3;drawScene();return;}
      if(x>=25 && x<215 && y>=197 && y<238){activeScene=4;drawScene();return;}
      if(x>=25 && x<215 && y>=247 && y<288){activeScene=5;drawScene();return;}
      break;
    case 1:
      if(x>=48 && x<192 && y>=263 && y<306){activeScene=0;drawScene();return;}
      break;
    case 2:
      if(x>=48 && x<192 && y>=263 && y<306){activeScene=0;drawScene();return;}
      break;
    case 3:
      if(x>=48 && x<192 && y>=263 && y<306){activeScene=0;drawScene();return;}
      break;
    case 4:
      if(x>=48 && x<192 && y>=263 && y<306){activeScene=0;drawScene();return;}
      break;
    case 5:
      if(x>=48 && x<192 && y>=263 && y<306){activeScene=0;drawScene();return;}
      break;
  }
}
void moveSlider(int x){
  switch(activeSlider){
    default:break;
  }
}
void pollTouch(){
  bool pressed=touch.touched();
  if(pressed){
    if(!touchWasDown){
      bool wasDimmed=backlightDimmed;
      wakeBacklight();
      if(wasDimmed){touchWasDown=true;return;} // first touch only wakes LCD
    }
    static uint32_t lastSlideRefresh=0;
    if(!touchWasDown || (activeSlider>=0 && millis()-lastSlideRefresh>=35UL)){
      TS_Point p=touch.getPoint();
      int a=TOUCH_SWAP?p.y:p.x;
      int b=TOUCH_SWAP?p.x:p.y;
      int x0=constrain((int)map(a,TOUCH_X_MIN,TOUCH_X_MAX,0,239),0,239);
      int y0=constrain((int)map(b,TOUCH_Y_MIN,TOUCH_Y_MAX,0,319),0,319);
      if(TOUCH_FLIP_X)x0=239-x0;
      if(TOUCH_FLIP_Y)y0=319-y0;
      int x=x0,y=y0;
      if(SCREEN_ROTATION==1){x=319-y0;y=x0;}
      else if(SCREEN_ROTATION==2){x=239-x0;y=319-y0;}
      else if(SCREEN_ROTATION==3){x=y0;y=239-x0;}
      if(!touchWasDown)onTouch(x,y);
      else if(activeSlider>=0){moveSlider(x);lastSlideRefresh=millis();}
    }
  }else{activeSlider=-1;}
  touchWasDown=pressed;
}
// CYD Studio: compiled visual logic
float logicValue0=0.0f;
static bool debugTraceEnabled=true;
static uint16_t debugTraceRateMs=100;
static uint32_t debugTraceLast=0;
static uint16_t debugTraceCursor=0;
static int16_t debugTraceFocus=-1;
static char debugCommand[48];
static uint8_t debugCommandLen=0;
void emitDebugTrace(uint16_t idx){
  switch(idx){
    case 0: Serial.print("@DBG|");Serial.print("rad");Serial.print("|");Serial.println(logicValue0,4);break;
    default:break;
  }
}
void pollDebugCommands(){
  uint8_t processed=0;
  while(Serial.available() && processed++<48){
    const char c=(char)Serial.read();
    if(c=='\n' || c=='\r'){
      debugCommand[debugCommandLen]=0;
      if(strcmp(debugCommand,"@DBG ON")==0)debugTraceEnabled=true;
      else if(strcmp(debugCommand,"@DBG OFF")==0)debugTraceEnabled=false;
      else if(strcmp(debugCommand,"@DBG ALL")==0)debugTraceFocus=-1;
      else if(strncmp(debugCommand,"@DBG RATE ",10)==0){
        long r=atol(debugCommand+10);if(r>=50 && r<=5000)debugTraceRateMs=(uint16_t)r;
      }else if(strncmp(debugCommand,"@DBG FOCUS ",11)==0){
        long i=atol(debugCommand+11);if(i>=0 && i<1)debugTraceFocus=(int16_t)i;
      }
      debugCommandLen=0;
    }else if(debugCommandLen<sizeof(debugCommand)-1 && c>=32 && c<=126){
      debugCommand[debugCommandLen++]=c;
    }else{debugCommandLen=0;}
  }
}
void pollDebugTrace(){
  if(!debugTraceEnabled || (uint32_t)(millis()-debugTraceLast)<debugTraceRateMs)return;
  debugTraceLast=millis();
  if(debugTraceFocus>=0){emitDebugTrace((uint16_t)debugTraceFocus);return;}
  // At most six tagged samples per interval: safe at 115200 baud for typical graphs.
  for(uint8_t k=0;k<6 && k<1;k++){
    emitDebugTrace(debugTraceCursor);
    if(++debugTraceCursor>=1)debugTraceCursor=0;
  }
}
void pollLogic(){
  static uint32_t lastLogicTick = 0;
  if((uint32_t)(millis()-lastLogicTick)<20) return; // maks. 50 Hz, bez delay()
  lastLogicTick=millis();
  logicValue0=cydRFReady?cydRFLatest:-130.0f;
  pollDebugTrace();
}
void setup(){
  Serial.begin(115200);
  initBacklight();
  tft.init();tft.setRotation(SCREEN_ROTATION);tft.fillScreen(TFT_BLACK);
  touchBus.begin(25,39,32,33);touch.begin(touchBus);touch.setRotation(0);
  initCydRF();


  drawScene();
}
void loop(){
  pollTouch();
  pollBacklight();
  pollCydRF();
  pollDebugCommands();
  pollLogic();
  if(millis()-lastRefresh>250){lastRefresh=millis();drawScene();}

}