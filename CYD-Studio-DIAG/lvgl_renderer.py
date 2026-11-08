"""LVGL 9.6 backend for CYD Studio. TFT_eSPI is used only as the LCD SPI transport.
Generated scene objects are retained and only their values are updated periodically.
"""
import re
import unicodedata
import json


def lcd_font_safe(s):
    text=str(s if s is not None else '')
    translate={'ł':'l','Ł':'L','←':'','→':'','↑':'','↓':'','◀':'','▶':'',
               '°':' deg','µ':'u','μ':'u','Ω':'Ohm','²':'^2','³':'^3',
               '×':'x','÷':'/','–':'-','—':'-','…':'...','✓':'OK',
               '✔':'OK','✗':'X','●':'*','★':'*','⚙':'SET','▣':'','⌘':''}
    text=''.join(translate.get(ch,ch) for ch in text)
    text=unicodedata.normalize('NFKD',text)
    text=''.join(ch for ch in text if not unicodedata.combining(ch))
    text=text.encode('ascii','ignore').decode('ascii')
    return ' '.join(text.split())


def q(s, n=80):
    return json.dumps(lcd_font_safe(s)[:n], ensure_ascii=True)


def rgb(s, fallback='0xFFFFFF'):
    if isinstance(s,str) and re.fullmatch('#[0-9a-fA-F]{6}',s):return '0x'+s[1:]
    return fallback


def num(w,key,default,minimum,maximum):
    try:
        v=float(w.get(key,default))
        if not (-1e14<v<1e14):return default
        return max(minimum,min(maximum,v))
    except (ValueError,TypeError,AttributeError):return default


def widget_expr(w,features,logic_ids,ui_ids):
    source=str(w.get('source','constant'))
    if source=='battery_percent' and features.get('battery'):return '(float)batteryPercent()'
    if source=='battery_voltage' and features.get('battery'):return 'batteryVolts()'
    if source=='wifi_rssi':return '(WiFi.status()==WL_CONNECTED?(float)WiFi.RSSI():NAN)' if str(features.get('wifi_mode','off')) in ('sta','ap_sta') else 'NAN'
    if source.startswith('logic:'):
        if source[6:] not in logic_ids:raise ValueError('Widget uses missing logic node '+source[6:])
        return 'logicValue'+str(logic_ids[source[6:]])
    if w.get('id') in ui_ids and w.get('type') in ('slider','switch','checkbox'):
        return f'uiValues[{ui_ids[w["id"]]}]'
    return f'{num(w,"level",0,-1000000,1000000):.6f}f'


GLUE=r'''
// CYD Studio · LVGL 9.6 renderer, TFT_eSPI only handles SPI panel transport.
// Allocate 24 rows (1/10 of a 320x240 screen) at run time, outside static .bss.
// LVGL recommends at least 1/10 of the display for PARTIAL rendering.
// Keep a 2-row emergency buffer only if the 24-row heap allocation fails.
static uint8_t cyd_lv_emergency_buf[320 * 2 * 2];
static uint8_t *cyd_lv_buf = nullptr;
static uint32_t cyd_lv_buf_bytes = 0;
static lv_display_t *cyd_lv_display = nullptr;
static lv_obj_t *cyd_widgets[64];
static lv_obj_t *cyd_labels[64];
static lv_obj_t *cyd_fills[64];
static lv_obj_t *cyd_knobs[64];
static lv_obj_t *cyd_scales[64];
static lv_chart_series_t *cyd_fft_series[64]={};
static uint8_t *cyd_wf_buffers[64]={};
static uint32_t cyd_rf_ui_seen[64]={};
static uint32_t cyd_fft_ui_seen[64]={};
static void cyd_release_rf_canvases(){
  for(int i=0;i<64;i++){
    if(cyd_wf_buffers[i]){lv_free(cyd_wf_buffers[i]);cyd_wf_buffers[i]=nullptr;}
  }
}

static int cyd_pressed_widget = -1;
static int cyd_rendered_scene = -1;
static uint32_t cyd_lv_last = 0;

static void cyd_flush(lv_display_t *disp,const lv_area_t *area,uint8_t *px){
  uint32_t w=(uint32_t)(area->x2-area->x1+1);
  uint32_t h=(uint32_t)(area->y2-area->y1+1);
#ifdef CYD_M5_DISPLAY
  // M5Unified + M5GFX owns the LCD SPI bus and power management.
  tft.pushImage(area->x1,area->y1,w,h,(const uint16_t*)px);
#else
  tft.startWrite();
  tft.setAddrWindow(area->x1,area->y1,w,h);
  tft.pushColors((uint16_t *)px,w*h,true);
  tft.endWrite();
#endif
  lv_display_flush_ready(disp);
}
static lv_obj_t* cyd_box(lv_obj_t *parent,int x,int y,int w,int h,uint32_t bg,int radius=0){
  lv_obj_t *o=lv_obj_create(parent); lv_obj_remove_style_all(o);
  lv_obj_set_pos(o,x,y); lv_obj_set_size(o,w,h);
  lv_obj_set_style_bg_opa(o,LV_OPA_COVER,0);
  lv_obj_set_style_bg_color(o,lv_color_hex(bg),0);
  lv_obj_set_style_radius(o,radius,0);
  lv_obj_remove_flag(o,LV_OBJ_FLAG_SCROLLABLE);
  return o;
}
// The Python generator converts unsupported Unicode symbols to ASCII before emission.
// Every text label occupies exactly one reserved row. Longer captions get an ellipsis.
// This prevents unintended wrapping over sliders, scales and other widgets.
static lv_obj_t* cyd_lbl(lv_obj_t *parent,const char *text,uint32_t fg){
  lv_obj_update_layout(parent);
  int32_t pw=lv_obj_get_width(parent),ph=lv_obj_get_height(parent);
  lv_obj_t *o=lv_label_create(parent);
  lv_obj_remove_style_all(o);
  lv_obj_set_style_text_color(o,lv_color_hex(fg),0);
  lv_obj_set_style_text_opa(o,LV_OPA_COVER,0);
  lv_obj_set_style_bg_opa(o,LV_OPA_TRANSP,0);
  lv_obj_remove_flag(o,LV_OBJ_FLAG_CLICKABLE);
  lv_obj_set_style_text_font(o,(ph<30 || pw<95)?&lv_font_montserrat_12:&lv_font_montserrat_14,0);
  lv_obj_set_style_text_align(o,LV_TEXT_ALIGN_CENTER,0);
  lv_obj_set_style_pad_all(o,0,0);
  lv_label_set_long_mode(o,LV_LABEL_LONG_DOT);
  lv_obj_set_style_text_letter_space(o,0,0);
  lv_obj_set_size(o,pw>10?pw-10:pw,(ph>=22)?19:(ph>=12?ph-2:ph));
  lv_label_set_text(o,(text && text[0])?text:"");
  lv_obj_align(o,LV_ALIGN_CENTER,0,0);
  lv_obj_move_foreground(o);
  return o;
}

// Visual presets use LVGL 9.6 native style properties, not screenshots.
// Flat legacy mode remains available to preserve existing low-memory projects.
// Small, retained axis labels.  The canvas and chart data are updated live;
// tick labels stay fixed and do not allocate on every refresh.
static lv_obj_t *cyd_axis_label(lv_obj_t *parent,const char*str,int x,int y,int w,uint32_t color){
  lv_obj_t *o=lv_label_create(parent);
  lv_label_set_long_mode(o,LV_LABEL_LONG_DOT);
  lv_obj_set_size(o,w,15);
  lv_label_set_text(o,str);
  lv_obj_set_pos(o,x,y);
  lv_obj_set_style_text_color(o,lv_color_hex(color),0);
  lv_obj_set_style_text_font(o,&lv_font_montserrat_12,0);
  lv_obj_set_style_text_opa(o,LV_OPA_COVER,0);
  return o;
}

static void cyd_style_panel(lv_obj_t *o,uint8_t skin,uint32_t accent,bool button){
  if(!o)return;
  if(skin==0){
    lv_obj_set_style_border_width(o,button?2:1,0);
    lv_obj_set_style_border_color(o,lv_color_hex(button?0x8cdfff:0x54748a),0);
    lv_obj_set_style_radius(o,button?7:5,0);
    if(button){
      lv_obj_set_style_outline_width(o,2,LV_STATE_PRESSED);
      lv_obj_set_style_outline_color(o,lv_color_hex(0xffe18a),LV_STATE_PRESSED);
      lv_obj_set_style_outline_opa(o,LV_OPA_COVER,LV_STATE_PRESSED);
    }
    return;
  }
  uint32_t top=(skin==2)?0x2c3943:0x1c354c;
  uint32_t bottom=(skin==2)?0x101b25:0x091625;
  if(button){top=accent;bottom=0x102f44;}
  lv_obj_set_style_bg_color(o,lv_color_hex(top),0);
  lv_obj_set_style_bg_grad_color(o,lv_color_hex(bottom),0);
  lv_obj_set_style_bg_grad_dir(o,LV_GRAD_DIR_VER,0);
  lv_obj_set_style_bg_opa(o,LV_OPA_COVER,0);
  lv_obj_set_style_radius(o,10,0);
  lv_obj_set_style_border_color(o,lv_color_hex((skin==2)?0x65818b:0x365f79),0);
  lv_obj_set_style_border_width(o,button?2:1,0);
  lv_obj_set_style_border_side(o,LV_BORDER_SIDE_FULL,0);
  lv_obj_set_style_outline_width(o,0,0);
  if(button){
    lv_obj_set_style_border_color(o,lv_color_hex(0x95dfff),LV_STATE_PRESSED);
    lv_obj_set_style_outline_color(o,lv_color_hex(0xffd76d),LV_STATE_PRESSED);
    lv_obj_set_style_outline_width(o,2,LV_STATE_PRESSED);
    lv_obj_set_style_outline_opa(o,LV_OPA_COVER,LV_STATE_PRESSED);
    lv_obj_set_style_bg_color(o,lv_color_hex(0x155474),LV_STATE_PRESSED);
  }
}
static void cyd_style_caption(lv_obj_t *parent,const char*caption,uint8_t skin,int reserve_right=0){
  if(!parent || !caption || !caption[0])return;
  if(lv_obj_get_height(parent)<28)return; // Two distinct rows for value and rail.
  lv_obj_t*o=lv_label_create(parent);
  lv_obj_set_style_text_color(o,lv_color_hex(skin==2?0xe5cda9:0xa5c3d9),0);
  lv_obj_set_style_text_font(o,&lv_font_montserrat_12,0);
  lv_obj_set_style_text_opa(o,LV_OPA_COVER,0);
  lv_label_set_long_mode(o,LV_LABEL_LONG_DOT);
  lv_obj_set_size(o,lv_obj_get_width(parent)>16+reserve_right?lv_obj_get_width(parent)-16-reserve_right:1,14);
  lv_label_set_text(o,caption);
  lv_obj_set_pos(o,8,3);
}


// Built-in LVGL 9 widgets only. These object pointers are retained by their parent.
static void cyd_widget_title(lv_obj_t *panel,const char *txt,uint8_t skin){
  cyd_style_caption(panel,txt,skin==0?1:skin);
}
static void cyd_setup_bar(lv_obj_t *bar,uint32_t accent){
  lv_bar_set_range(bar,0,1000);
  lv_obj_set_style_bg_opa(bar,LV_OPA_COVER,LV_PART_MAIN);
  lv_obj_set_style_bg_color(bar,lv_color_hex(0x31495c),LV_PART_MAIN);
  lv_obj_set_style_bg_color(bar,lv_color_hex(accent),LV_PART_INDICATOR);
  lv_obj_set_style_bg_opa(bar,(lv_opa_t)210,LV_PART_INDICATOR);
  lv_obj_set_style_radius(bar,7,LV_PART_MAIN);
  lv_obj_set_style_radius(bar,7,LV_PART_INDICATOR);
  lv_obj_set_style_border_width(bar,0,LV_PART_MAIN);
  lv_obj_set_style_pad_all(bar,0,LV_PART_MAIN);
}
static lv_obj_t* cyd_native_meter(lv_obj_t*parent,int x,int y,int w,int h,uint32_t accent){
  lv_obj_t *o=lv_bar_create(parent);
  lv_obj_set_pos(o,x,y);lv_obj_set_size(o,w,h);
  cyd_setup_bar(o,accent);
  return o;
}
static lv_obj_t* cyd_native_status(lv_obj_t *parent,int x,int y,uint32_t accent){
  lv_obj_t *o=lv_led_create(parent);
  lv_obj_set_pos(o,x,y);lv_obj_set_size(o,20,20);
  lv_led_set_color(o,lv_color_hex(accent));
  return o;
}

static void cyd_paint_text(lv_obj_t *o,float value,int precision,const char *unit){
  if(!o)return;
  if(!isfinite(value)) { lv_label_set_text(o,"N/A"); return; }
  String s=String(value,precision)+String(unit);
  if(strcmp(lv_label_get_text(o),s.c_str())!=0)lv_label_set_text(o,s.c_str());
}
static void cyd_paint_text_named(lv_obj_t *o,const char *name,float value,int precision,const char *unit){
  if(!o)return;
  String s=String(name?name:"")+String(" ");
  if(isfinite(value))s+=String(value,precision)+String(unit);else s+="N/A";
  if(strcmp(lv_label_get_text(o),s.c_str())!=0)lv_label_set_text(o,s.c_str());
}
static float cyd_fraction(float v,float vmin,float vmax){
  if(!isfinite(v)||vmax<=vmin)return 0;
  return constrain((v-vmin)/(vmax-vmin),0.0f,1.0f);
}
static void cyd_lv_init(){
  lv_init();
  lv_tick_set_cb([]()->uint32_t{return millis();});
  cyd_lv_display=lv_display_create(tft.width(),tft.height());
  lv_display_set_color_format(cyd_lv_display,LV_COLOR_FORMAT_RGB565);
  lv_display_set_default(cyd_lv_display);
  const uint32_t rows=24;
  const uint32_t needed=(uint32_t)tft.width()*rows*2U;
  cyd_lv_buf=(uint8_t*)heap_caps_malloc(needed,MALLOC_CAP_8BIT);
  if(cyd_lv_buf){cyd_lv_buf_bytes=needed;}
  else{
    cyd_lv_buf=cyd_lv_emergency_buf;
    cyd_lv_buf_bytes=sizeof(cyd_lv_emergency_buf);
    Serial.println("CYD WARNING: unable to allocate 24-row LVGL draw buffer");
  }
  lv_display_set_buffers(cyd_lv_display,cyd_lv_buf,nullptr,cyd_lv_buf_bytes,LV_DISPLAY_RENDER_MODE_PARTIAL);
  lv_display_set_flush_cb(cyd_lv_display,cyd_flush);
}
'''


RF_LVGL_UPDATE=r"""
// 96x48 RGB565 canvas. Write directly to its pixel buffer; invalidate exactly once.
// Pushing one pixel through lv_canvas_set_px() repeatedly causes thousands of redraws.
static void cyd_update_rf_heatmap(int idx){
  if(!cyd_fills[idx] || !cyd_wf_buffers[idx])return;
  if(cyd_rf_ui_seen[idx]==cydRFRevision)return;
  uint16_t *pixels=(uint16_t*)cyd_wf_buffers[idx];
  const uint8_t startRow=cydRFRow, completed=cydRFCompletedRows;
  for(int y=0;y<48;y++){
    const int row=y/2,src=(startRow+row)%24;
    const bool valid=row>=24-(int)completed;
    for(int x=0;x<96;x++){
      const int k=(x*(CYD_RF_BINS-1)+47)/95;
      float db=valid?cydRFWf[src][k]:-130.0f;
      float f=constrain((db+114.0f)/78.0f,0.0f,1.0f);
      // Dark indigo, blue, cyan, yellow, orange-red (RGB565).
      uint8_t r=(uint8_t)(255.0f*constrain((f-0.38f)*2.0f,0.0f,1.0f));
      uint8_t g=(uint8_t)(240.0f*constrain((f-0.10f)*2.1f,0.0f,1.0f)*(1.0f-constrain((f-0.78f)*2.5f,0.0f,1.0f)));
      uint8_t b=(uint8_t)(20.0f+210.0f*constrain(1.0f-f*1.25f,0.0f,1.0f));
      pixels[y*96+x]=(uint16_t)(((r&0xF8)<<8)|((g&0xFC)<<3)|(b>>3));
    }
  }
  cyd_rf_ui_seen[idx]=cydRFRevision;
  lv_obj_invalidate(cyd_fills[idx]);
  char title[80];
  snprintf(title,sizeof(title),"CC1101 %.2f..%.2f MHz  %.0f dBm",
           (double)CYD_RF_START,(double)CYD_RF_END,(double)cydRFLatest);
  lv_label_set_text(cyd_labels[idx],title);
}
"""

FFT_LVGL_UPDATE=r"""
// One chart refresh after updating all Y samples. No per-bin redraw.
static void cyd_update_fft_chart(int idx){
  if(!cyd_fills[idx] || !cyd_fft_series[idx])return;
  if(cyd_fft_ui_seen[idx]==cydFFTRevision)return;
  cyd_fft_ui_seen[idx]=cydFFTRevision;
  float maxv=0.5f;
  for(int k=1;k<32;k++)if(cydFFTBins[k]>maxv)maxv=cydFFTBins[k];
  int32_t values[32];
  for(int k=0;k<32;k++){
    float value=k?cydFFTBins[k]/maxv:0.0f;
    values[k]=(int32_t)(100.0f*constrain(value,0.0f,1.0f));
  }
  lv_chart_set_series_values(cyd_fills[idx],cyd_fft_series[idx],values,32);
  lv_chart_refresh(cyd_fills[idx]);
  char title[70];
  snprintf(title,sizeof(title),"FFT ADC   %.0f Hz",(double)cydFFTPeakHz);
  lv_label_set_text(cyd_labels[idx],title);
}
"""

ADC_WATERFALL_UPDATE=r"""
// ADC FFT waterfall (not a 433 MHz CC1101 radio scanner).
// A single 64x24 8-bit ring holds 24 spectral rows; canvas is RGB565.
static uint8_t cydADCHistory[24][64]={};
static uint8_t cydADCHead=0,cydADCRows=0;
static uint32_t cydADCComputedRevision=UINT32_MAX;
static void cyd_adc_store_fft_row(){
  if(cydADCComputedRevision==cydFFTRevision)return;
  cydADCComputedRevision=cydFFTRevision;
  float maximum=1.0f;
  for(int k=1;k<32;k++)maximum=fmaxf(maximum,cydFFTBins[k]);
  for(int x=0;x<64;x++){
    int bin=1+(x*30)/63;
    float v=constrain(cydFFTBins[bin]/maximum,0.0f,1.0f);
    // Gamma highlights weak spectral components.
    cydADCHistory[cydADCHead][x]=(uint8_t)roundf(255.0f*sqrtf(v));
  }
  cydADCHead=(cydADCHead+1)%24;
  if(cydADCRows<24)cydADCRows++;
}
static void cyd_update_adc_heatmap(int idx){
  if(!cyd_fills[idx] || !cyd_wf_buffers[idx])return;
  if(cyd_fft_ui_seen[idx]==cydFFTRevision)return;
  cyd_fft_ui_seen[idx]=cydFFTRevision;
  cyd_adc_store_fft_row();
  uint16_t *pixels=(uint16_t*)cyd_wf_buffers[idx];
  for(int y=0;y<48;y++){
    const int row=y/2,src=(cydADCHead+row)%24;
    const bool valid=row>=24-(int)cydADCRows;
    for(int x=0;x<96;x++){
      const int bin=(x*63+47)/95;
      float a=valid?(float)cydADCHistory[src][bin]/255.0f:0.0f;
      uint8_t r=(uint8_t)(255.0f*constrain((a-0.45f)*2.1f,0.0f,1.0f));
      uint8_t g=(uint8_t)(250.0f*constrain(a*1.9f,0.0f,1.0f));
      uint8_t b=(uint8_t)(18.0f+220.0f*constrain(1.0f-abs(a-0.35f)*2.5f,0.0f,1.0f));
      pixels[y*96+x]=(uint16_t)(((r&0xF8)<<8)|((g&0xFC)<<3)|(b>>3));
    }
  }
  lv_obj_invalidate(cyd_fills[idx]);
  char title[70];
  snprintf(title,sizeof(title),"ADC GPIO%d FFT  %.0f Hz",CYD_FFT_GPIO,(double)cydFFTPeakHz);
  lv_label_set_text(cyd_labels[idx],title);
}
"""

def generate_widgets(device, screen_w,screen_h):
    scenes=device.get('scenes',[]) or []
    feat=device.get('features',{}) or {}
    logic_ids={n.get('id'):i for i,n in enumerate((device.get('logic') or {}).get('nodes',[]))}
    controls=[w for s in scenes for w in (s.get('widgets') or []) if w.get('type') in ('slider','switch','checkbox') and w.get('source','constant')=='constant']
    ui_ids={w.get('id'):i for i,w in enumerate(controls)}
    build=['void drawScene(){','  if(cyd_rendered_scene==activeScene)return;','  cyd_rendered_scene=activeScene;','  lv_obj_clean(lv_screen_active());','  cyd_release_rf_canvases();','  memset(cyd_widgets,0,sizeof(cyd_widgets));','  memset(cyd_labels,0,sizeof(cyd_labels));','  memset(cyd_fills,0,sizeof(cyd_fills));','  memset(cyd_knobs,0,sizeof(cyd_knobs));','  memset(cyd_scales,0,sizeof(cyd_scales));','  memset(cyd_fft_series,0,sizeof(cyd_fft_series));','  switch(activeScene){']
    updates=['void lv_updateWidgets(){','  if(cyd_rendered_scene!=activeScene)drawScene();','  switch(activeScene){']
    for scene_num,scene in enumerate(scenes):
        bg=rgb(scene.get('bg','#101928'),'0x101928')
        build += [f'  case {scene_num}:{{','  lv_obj_t *screen=lv_screen_active();',f'  lv_obj_set_style_bg_color(screen,lv_color_hex({bg}),0);','  lv_obj_set_style_bg_opa(screen,LV_OPA_COVER,0);']
        updates += [f'  case {scene_num}:{{']
        for i,w in enumerate((scene.get('widgets') or [])[:64]):
            if not isinstance(w,dict):continue
            typ=str(w.get('type',''))
            x=int(num(w,'x',0,0,screen_w-1));y=int(num(w,'y',0,0,screen_h-1))
            ww=int(num(w,'w',80,1,screen_w-x));hh=int(num(w,'h',35,1,screen_h-y))
            bg=rgb(w.get('bg','#288fd5'),'0x288fd5');fg=rgb(w.get('fg','#ffffff'))
            label=q(w.get('text') or w.get('label') or ({"button":"BUTTON","bar":"BAR","progress":"PROGRESS","slider":"SLIDER","battery":"BATTERY","switch":"SWITCH","checkbox":"CHECK","led":"LED","gauge":"GAUGE","value":"VALUE","analog":"ANALOG","integer":"INTEGER","digital":"DIGITAL"}.get(typ, "")))
            source=str(w.get('source','constant'))
            expr=widget_expr(w,feat,logic_ids,ui_ids)
            prec=int(num(w,'precision',1,0,3));unit=q(str(w.get('unit',''))[:8])
            minv=num(w,'min',0,-1000000,1000000); maxv=num(w,'max',100,-1000000,1000000)
            threshold=num(w,'threshold',0.5,-1000000,1000000)
            width=ww
            skin={'legacy':0,'neo':1,'industrial':2}.get(w.get('visualStyle',device.get('uiTheme','neo')),1)
            # Use one base object per widget; live changes don't reconstruct the screen.
            if typ=='text':
                build += [f'    cyd_widgets[{i}]=cyd_box(screen,{x},{y},{ww},{hh},0,0);',f'    lv_obj_set_style_bg_opa(cyd_widgets[{i}],LV_OPA_TRANSP,0);',f'    cyd_labels[{i}]=cyd_lbl(cyd_widgets[{i}],{label},{bg});']
                if source!='constant':updates += [f'    cyd_paint_text(cyd_labels[{i}],(float)({expr}),{prec},{q("%" if source=="battery_percent" else " V" if source=="battery_voltage" else str(w.get("unit",""))[:8])});']
            elif typ=='line':
                build += [f'    static const lv_point_precise_t cyd_segment_{scene_num}_{i}[]={{ {{0,0}}, {{{ww-1},{hh-1}}} }};',
                          f'    cyd_widgets[{i}]=lv_line_create(screen);',
                          f'    lv_line_set_points(cyd_widgets[{i}],cyd_segment_{scene_num}_{i},2);',
                          f'    lv_obj_set_pos(cyd_widgets[{i}],{x},{y});',
                          f'    lv_obj_set_style_line_color(cyd_widgets[{i}],lv_color_hex({bg}),0);',
                          f'    lv_obj_set_style_line_width(cyd_widgets[{i}],2,0);']
            elif typ in ('rect','frame','circle'):
                radius= min(ww,hh)//2 if typ=='circle' else 0
                build += [f'    cyd_widgets[{i}]=cyd_box(screen,{x},{y},{ww},{hh},{bg},{radius});']
                if typ=='frame':build += [f'    lv_obj_set_style_bg_opa(cyd_widgets[{i}],LV_OPA_TRANSP,0);',f'    lv_obj_set_style_border_width(cyd_widgets[{i}],2,0);',f'    lv_obj_set_style_border_color(cyd_widgets[{i}],lv_color_hex({bg}),0);']
                if w.get('text'):
                    build += [f'    cyd_labels[{i}]=cyd_lbl(cyd_widgets[{i}],{label},{fg});',f'    lv_obj_move_foreground(cyd_labels[{i}]);']
            elif typ in ('button','custom','wifi','gyro','audio','mic','rfwave','rfsignal','rfrssi','icon'):
                bc={'wifi':'0x245d4d','gyro':'0x125a70','audio':'0x344e6f','mic':'0x344e6f','rfwave':'0x10273c','rfsignal':'0x10273c','rfrssi':'0x10273c','icon':'0x132c41'}.get(typ,bg)
                text={'wifi':'Wi-Fi','gyro':'GYRO','audio':'AUDIO','mic':'MIC','rfwave':'RF SIGNAL','rfsignal':'RF SIGNAL','rfrssi':'RSSI'}.get(typ,None)
                if typ=='button':
                    build += [f'    cyd_widgets[{i}]=lv_button_create(screen);',
                              f'    lv_obj_set_pos(cyd_widgets[{i}],{x},{y});',
                              f'    lv_obj_set_size(cyd_widgets[{i}],{ww},{hh});',
                              f'    lv_obj_set_style_bg_color(cyd_widgets[{i}],lv_color_hex({bc}),0);',
                              f'    lv_obj_set_style_pad_all(cyd_widgets[{i}],0,0);',
                              f'    lv_obj_set_style_shadow_width(cyd_widgets[{i}],0,0);']
                else:
                    build += [f'    cyd_widgets[{i}]=cyd_box(screen,{x},{y},{ww},{hh},{bc},8);']
                build += [f'    cyd_labels[{i}]=cyd_lbl(cyd_widgets[{i}],{q(text) if text else label},{fg});']
                if typ=='rfrssi':updates += [f'    cyd_paint_text(cyd_labels[{i}],(float)({expr}),0," dBm");']
                if typ=='icon':
                    symbol=str(w.get('iconName','wifi')).lower()
                    if symbol=='wifi':
                        build += [f'    lv_label_set_text(cyd_labels[{i}],"WIFI");']
                    elif symbol=='battery':
                        build += [f'    lv_label_set_text(cyd_labels[{i}],"BAT");']
                if typ in ('wifi','rfsignal','rfwave','gyro','audio','mic'):
                    # Native LVGL bar displays the value; previews and firmware use the same geometry.
                    build += [f'    cyd_style_caption(cyd_widgets[{i}],{label},{skin},55);']
                    if typ=='rfwave':
                        diameter=max(18,min(ww//3,hh-25))
                        build += [f'    cyd_fills[{i}]=lv_arc_create(cyd_widgets[{i}]);',
                                  f'    lv_obj_set_size(cyd_fills[{i}],{diameter},{diameter});',
                                  f'    lv_obj_set_pos(cyd_fills[{i}],8,{max(18,(hh-diameter)//2)});',
                                  f'    lv_arc_set_bg_angles(cyd_fills[{i}],0,270);',
                                  f'    lv_arc_set_rotation(cyd_fills[{i}],135);',
                                  f'    lv_arc_set_range(cyd_fills[{i}],0,1000);',
                                  f'    lv_obj_set_style_arc_color(cyd_fills[{i}],lv_color_hex({bg}),LV_PART_INDICATOR);',
                                  f'    lv_obj_set_style_arc_width(cyd_fills[{i}],5,LV_PART_MAIN);',
                                  f'    lv_obj_set_style_arc_width(cyd_fills[{i}],5,LV_PART_INDICATOR);',
                                  f'    lv_obj_remove_flag(cyd_fills[{i}],LV_OBJ_FLAG_CLICKABLE);',
                                  f'    lv_obj_set_pos(cyd_labels[{i}],{diameter+12},{max(23,hh//2-9)});',
                                  f'    lv_obj_set_width(cyd_labels[{i}],{max(1,ww-diameter-16)});']
                    else:
                        build += [f'    cyd_fills[{i}]=cyd_native_meter(cyd_widgets[{i}],8,{max(12,hh-15)},{max(2,ww-16)},{max(5,min(10,hh//5))},{bg});',
                                  f'    lv_obj_set_pos(cyd_labels[{i}],8,{max(2,hh//2-10)});',
                                  f'    lv_obj_set_size(cyd_labels[{i}],{max(1,ww-16)},16);']
                    updates += [f'    {{float v=(float)({expr});float f=cyd_fraction(v,{minv:.5f}f,{maxv:.5f}f);'+('lv_arc_set_value' if typ=='rfwave' else 'lv_bar_set_value')+f'(cyd_fills[{i}],(int)roundf(1000*f)'+(');' if typ=='rfwave' else ',LV_ANIM_OFF);')+f'cyd_paint_text(cyd_labels[{i}],v,{0 if typ in ("rfsignal","rfwave") else prec},{q(" dBm" if typ in ("rfwave","rfsignal") else str(w.get("unit",""))[:8])});}}']
                if typ=='gyro':
                    pass
            elif typ in ('bar','progress','slider','battery'):
                base='0x172b40' if typ=='slider' else '0x142537'
                # Top label and bottom rail never occupy the same pixel row.
                rail_height=max(2,min(9,hh//6)) if hh>=28 else 1
                rail_y=max(1,hh-rail_height-4) if hh>=28 else hh-1
                value_height=max(1,min(17,rail_y-5)) if hh>=28 else max(1,hh-4)
                build += [f'    cyd_widgets[{i}]=cyd_box(screen,{x},{y},{ww},{hh},{base},5);']
                if typ=='battery':
                    bh=max(2,min(10,hh//6))
                    by=max(1,hh-bh-4)
                    build += [f'    cyd_fills[{i}]=cyd_native_meter(cyd_widgets[{i}],9,{by},{max(2,ww-27)},{bh},{bg});',
                              f'    cyd_box(cyd_widgets[{i}],{max(0,ww-16)},{by+max(0,bh//3)},5,{max(3,bh//3)},0xb9dbe4,1);',
                              f'    cyd_labels[{i}]=cyd_lbl(cyd_widgets[{i}],"0%",0xeafffb);',
                              f'    lv_obj_set_pos(cyd_labels[{i}],{max(4,ww-58)},3);',
                              f'    lv_obj_set_size(cyd_labels[{i}],{max(3,min(52,ww-8))},16);',
                              f'    lv_obj_set_style_text_align(cyd_labels[{i}],LV_TEXT_ALIGN_RIGHT,0);',
                              f'    cyd_widget_title(cyd_widgets[{i}],{label},{skin});']
                    v_expr=expr if source.startswith('logic:') else '(float)batteryPercent()' if feat.get('battery') else expr
                    updates += [f'    {{ float pct=constrain((float)({v_expr}),0.0f,100.0f);',
                                f'      lv_bar_set_value(cyd_fills[{i}],(int)roundf(10*pct),LV_ANIM_OFF);',
                                f'      lv_obj_set_style_bg_color(cyd_fills[{i}],lv_color_hex(pct<20?0xef665c:0x48c981),LV_PART_INDICATOR);',
                                f'      cyd_paint_text(cyd_labels[{i}],pct,0,"%"); }}']
                else:
                    if typ=='slider':
                        build += [f'    cyd_fills[{i}]=lv_slider_create(cyd_widgets[{i}]);',
                                  f'    lv_obj_set_pos(cyd_fills[{i}],{min(13,max(2,ww//10))},{rail_y});',
                                  f'    lv_obj_set_size(cyd_fills[{i}],{max(6,ww-26)},{rail_height});',
                                  f'    lv_slider_set_range(cyd_fills[{i}],0,1000);',
                                  f'    lv_obj_set_style_bg_color(cyd_fills[{i}],lv_color_hex(0x30495b),LV_PART_MAIN);',
                                  f'    lv_obj_set_style_bg_color(cyd_fills[{i}],lv_color_hex({bg}),LV_PART_INDICATOR);',
                                  f'    lv_obj_set_style_bg_color(cyd_fills[{i}],lv_color_hex(0xf8ffff),LV_PART_KNOB);',
                                  f'    lv_obj_set_style_width(cyd_fills[{i}],{min(12,max(3,hh//3))},LV_PART_KNOB);',
                                  f'    lv_obj_set_style_height(cyd_fills[{i}],{min(12,max(3,hh//3))},LV_PART_KNOB);',
                                  f'    lv_obj_set_style_pad_all(cyd_fills[{i}],0,LV_PART_MAIN);',
                                  f'    lv_obj_set_style_radius(cyd_fills[{i}],5,LV_PART_MAIN);']
                    else:
                        build += [f'    cyd_fills[{i}]=lv_bar_create(cyd_widgets[{i}]);',
                                  f'    lv_obj_set_pos(cyd_fills[{i}],8,{rail_y});',
                                  f'    lv_obj_set_size(cyd_fills[{i}],{max(1,ww-16)},{rail_height});',
                                  f'    lv_bar_set_range(cyd_fills[{i}],0,1000);',
                                  f'    lv_obj_set_style_bg_color(cyd_fills[{i}],lv_color_hex(0x284052),LV_PART_MAIN);',
                                  f'    lv_obj_set_style_bg_color(cyd_fills[{i}],lv_color_hex({bg}),LV_PART_INDICATOR);',
                                  f'    lv_obj_set_style_bg_opa(cyd_fills[{i}],(lv_opa_t)210,LV_PART_INDICATOR);',
                                  f'    lv_obj_set_style_radius(cyd_fills[{i}],4,0);']
                    if typ=='bar':
                        build += [f'    cyd_labels[{i}]=cyd_lbl(cyd_widgets[{i}],{label},{fg});',
                                  f'    lv_obj_set_size(cyd_labels[{i}],{max(1,ww-12)},{value_height});',
                                  f'    lv_obj_set_pos(cyd_labels[{i}],6,3);',
                                  f'    lv_obj_move_foreground(cyd_labels[{i}]);']
                        if hh>=44 and ww<110:
                            # Narrow bar: title above, numeric value below, rail at bottom.
                            build += [f'    cyd_style_caption(cyd_widgets[{i}],{label},{skin});',
                                      f'    lv_obj_set_pos(cyd_labels[{i}],6,21);',
                                      f'    lv_obj_set_size(cyd_labels[{i}],{max(1,ww-12)},{max(1,min(17,rail_y-23))});']
                    if typ!='bar':
                        # Reserve the top row for a legible percentage/duty value; the native
                        # slider/rail occupies only the lower strip of the widget.
                        build += [f'    cyd_labels[{i}]=cyd_lbl(cyd_widgets[{i}],{label},{fg});',
                                  f'    lv_obj_set_pos(cyd_labels[{i}],{max(3,ww-59)},3);',
                                  f'    lv_obj_set_size(cyd_labels[{i}],{max(3,min(55,ww-7))},{value_height});',
                                  f'    lv_obj_set_style_text_align(cyd_labels[{i}],LV_TEXT_ALIGN_RIGHT,0);',
                                  f'    lv_obj_move_foreground(cyd_labels[{i}]);']
                        if hh>=28 and ww>=93:
                            build += [f'    cyd_style_caption(cyd_widgets[{i}],{label},{skin},60);']
                    elif hh>=42 and ww>=110:
                        build += [f'    cyd_style_caption(cyd_widgets[{i}],{label},{skin},60);', f'    lv_obj_set_pos(cyd_labels[{i}],{max(4,ww-62)},3);', f'    lv_obj_set_width(cyd_labels[{i}],{max(1,min(57,ww-8))});', f'    lv_obj_set_style_text_align(cyd_labels[{i}],LV_TEXT_ALIGN_RIGHT,0);']
                    build += [f'    lv_obj_set_style_bg_opa(cyd_labels[{i}],LV_OPA_TRANSP,0);',f'    lv_obj_move_foreground(cyd_labels[{i}]);']
                    value_call=f'lv_slider_set_value(cyd_fills[{i}],(int)roundf(1000*frac),LV_ANIM_OFF)' if typ=='slider' else f'lv_bar_set_value(cyd_fills[{i}],(int)roundf(1000*frac),LV_ANIM_OFF)'
                    updates += [f'    {{float v=(float)({expr});float frac=cyd_fraction(v,{minv:.5f}f,{maxv:.5f}f);{value_call};']
                    if typ=='bar':
                        if hh>=42:updates += [f'      cyd_paint_text(cyd_labels[{i}],v,{prec},{unit});']
                        else:updates += [f'      cyd_paint_text_named(cyd_labels[{i}],{label},v,{prec},{unit});']
                    if typ=='progress':
                        if hh>=28 and ww>=93:updates += [f'      cyd_paint_text(cyd_labels[{i}],frac*100.0f,0,"%");']
                        else:updates += [f'      cyd_paint_text_named(cyd_labels[{i}],{label},frac*100.0f,0,"%");']
                    if typ=='slider':
                        if hh>=28 and ww>=93:updates += [f'      cyd_paint_text(cyd_labels[{i}],v,{prec},{unit});']
                        else:updates += [f'      cyd_paint_text_named(cyd_labels[{i}],{label},v,{prec},{unit});']
                    updates += ['    }']
            elif typ in ('value','analog','integer','digital','led','switch','checkbox','gauge'):
                base={'gauge':'0x152738','switch':'0x203448','checkbox':'0x18314a','led':'0x394957','digital':'0x42506b'}.get(typ,'0x172b40')
                radius=min(ww,hh)//2 if typ=='led' else 7
                build += [f'    cyd_widgets[{i}]=cyd_box(screen,{x},{y},{ww},{hh},{base},{radius});',f'    cyd_labels[{i}]=cyd_lbl(cyd_widgets[{i}],{label},{fg});']
                if typ=='gauge' and (hh<94 or ww<96):
                    # Compact built-in bar instead of illegible 20px circular scale.
                    build += [f'    cyd_style_caption(cyd_widgets[{i}],{label},{skin},0);',
                              f'    cyd_fills[{i}]=cyd_native_meter(cyd_widgets[{i}],8,{max(13,hh-15)},{max(2,ww-16)},9,{bg});',
                              f'    lv_obj_set_size(cyd_labels[{i}],{max(1,ww-10)},17);',
                              f'    lv_obj_set_pos(cyd_labels[{i}],5,{max(1,hh//2-12)});']
                    updates += [f'    {{float v=(float)({expr});lv_bar_set_value(cyd_fills[{i}],(int)roundf(1000*cyd_fraction(v,{minv:.5f}f,{maxv:.5f}f)),LV_ANIM_OFF);cyd_paint_text(cyd_labels[{i}],v,{prec},{unit});}}']
                elif typ=='gauge':
                    # A real instrument: native LVGL round scale, major/minor ticks,
                    # numeric min/max labels and coloured arc. 5 ticks x 4 divisions.
                    diameter=max(24,min(ww-14,hh-66))
                    arcdiam=max(12,diameter-32)
                    label_count=5 if diameter>=140 else 3
                    labels=[format(minv+(maxv-minv)*j/(label_count-1), '.%df'% (prec if maxv-minv<20 else 0)) for j in range(label_count)]
                    labels_cpp=', '.join(q(t) for t in labels)+', nullptr'
                    build += [
                        f'    static const char *cyd_gauge_labels_{scene_num}_{i}[]={{ {labels_cpp} }};',
                        f'    cyd_scales[{i}]=lv_scale_create(cyd_widgets[{i}]);',
                        f'    lv_obj_set_size(cyd_scales[{i}],{diameter},{diameter});',
                        f'    lv_obj_set_pos(cyd_scales[{i}],{(ww-diameter)//2},19);',
                        f'    lv_scale_set_mode(cyd_scales[{i}],LV_SCALE_MODE_ROUND_INNER);',
                        f'    lv_scale_set_rotation(cyd_scales[{i}],135);',
                        f'    lv_scale_set_angle_range(cyd_scales[{i}],270);',
                        f'    lv_scale_set_range(cyd_scales[{i}],0,100);',
                        f'    lv_scale_set_total_tick_count(cyd_scales[{i}],21);',
                        f'    lv_scale_set_major_tick_every(cyd_scales[{i}],{20//(label_count-1)});',
                        f'    lv_scale_set_text_src(cyd_scales[{i}],cyd_gauge_labels_{scene_num}_{i});',
                        f"    lv_scale_set_label_show(cyd_scales[{i}],{'true' if diameter>=110 else 'false'});",
                        f'    lv_obj_set_style_line_color(cyd_scales[{i}],lv_color_hex(0x42617b),LV_PART_MAIN);',
                        f'    lv_obj_set_style_line_color(cyd_scales[{i}],lv_color_hex(0x8daecb),LV_PART_ITEMS);',
                        f'    lv_obj_set_style_line_color(cyd_scales[{i}],lv_color_hex(0xdef7ff),LV_PART_INDICATOR);',
                        f'    lv_obj_set_style_text_color(cyd_scales[{i}],lv_color_hex(0xf0f7ff),LV_PART_INDICATOR);',
                        f'    lv_obj_set_style_length(cyd_scales[{i}],4,LV_PART_ITEMS);',
                        f'    lv_obj_set_style_length(cyd_scales[{i}],9,LV_PART_INDICATOR);',
                        f'    lv_obj_set_style_bg_opa(cyd_scales[{i}],LV_OPA_TRANSP,0);',
                        f'    cyd_fills[{i}]=lv_arc_create(cyd_widgets[{i}]);',
                        f'    lv_obj_set_size(cyd_fills[{i}],{arcdiam},{arcdiam});',
                        f'    lv_obj_set_pos(cyd_fills[{i}],{(ww-arcdiam)//2},{19+(diameter-arcdiam)//2});',
                        f'    lv_arc_set_rotation(cyd_fills[{i}],135);',
                        f'    lv_arc_set_bg_angles(cyd_fills[{i}],0,270);',
                        f'    lv_arc_set_range(cyd_fills[{i}],0,100);',
                        f'    lv_obj_set_style_arc_width(cyd_fills[{i}],9,LV_PART_MAIN);',
                        f'    lv_obj_set_style_arc_width(cyd_fills[{i}],9,LV_PART_INDICATOR);',
                        f'    lv_obj_set_style_arc_color(cyd_fills[{i}],lv_color_hex(0x284357),LV_PART_MAIN);',
                        f'    lv_obj_set_style_arc_color(cyd_fills[{i}],lv_color_hex({bg}),LV_PART_INDICATOR);',
                        f'    lv_obj_remove_flag(cyd_fills[{i}],LV_OBJ_FLAG_CLICKABLE);',
                        f'    lv_obj_set_size(cyd_labels[{i}],{max(1,ww-10)},19);',
                        f'    lv_obj_set_pos(cyd_labels[{i}],5,{max(0,hh-23)});',
                        f'    lv_obj_set_style_text_color(cyd_labels[{i}],lv_color_hex(0xffffff),0);',
                        f'    lv_obj_set_style_text_font(cyd_labels[{i}],&lv_font_montserrat_14,0);',
                        f'    lv_obj_move_foreground(cyd_labels[{i}]);'
                    ]
                    if diameter<110:
                        build += [f'    cyd_axis_label(cyd_widgets[{i}],{q(format(minv,".0f"))},8,{max(20,hh-44)},47,0xeef7ff);',
                                  f'    cyd_axis_label(cyd_widgets[{i}],{q(format(maxv,".0f"))},{max(1,ww-52)},{max(20,hh-44)},47,0xeef7ff);']
                    updates += [f'    {{float v=(float)({expr});lv_arc_set_value(cyd_fills[{i}],(int)roundf(100*cyd_fraction(v,{minv:.5f}f,{maxv:.5f}f)));cyd_paint_text(cyd_labels[{i}],v,{prec},{unit});}}']
                elif typ=='led':
                    compact=hh<58
                    if compact:
                        build += [f'    cyd_fills[{i}]=cyd_native_status(cyd_widgets[{i}],5,{max(1,(hh-20)//2)}, {bg});',
                                  f'    lv_obj_set_pos(cyd_labels[{i}],30,{max(0,(hh-16)//2)});',
                                  f'    lv_obj_set_size(cyd_labels[{i}],{max(1,ww-34)},16);',
                                  f'    lv_obj_set_style_text_align(cyd_labels[{i}],LV_TEXT_ALIGN_LEFT,0);']
                    else:
                        build += [f'    cyd_widget_title(cyd_widgets[{i}],{label},{skin});',
                                  f'    cyd_fills[{i}]=cyd_native_status(cyd_widgets[{i}],{max(0,(ww-20)//2)},{max(20,(hh-20)//2)}, {bg});',
                                  f'    lv_obj_set_size(cyd_labels[{i}],{max(1,ww-8)},16);',
                                  f'    lv_obj_set_pos(cyd_labels[{i}],4,{max(0,hh-19)});']
                    if compact:
                        updates += [f'    {{bool on=(float)({expr})>={threshold:.5f}f;if(on)lv_led_on(cyd_fills[{i}]);else lv_led_off(cyd_fills[{i}]);lv_label_set_text(cyd_labels[{i}],on?{q(lcd_font_safe(w.get("text") or "LED")+" ON")}:{q(lcd_font_safe(w.get("text") or "LED")+" OFF")});}}']
                    else:
                        updates += [f'    {{bool on=(float)({expr})>={threshold:.5f}f;if(on)lv_led_on(cyd_fills[{i}]);else lv_led_off(cyd_fills[{i}]);lv_label_set_text(cyd_labels[{i}],on?"ON":"OFF");}}']
                elif typ in ('switch','checkbox'):
                    # Two distinct layouts avoid value overlays on 40px high widgets.
                    compact=hh<58 or ww<105
                    toggle_w=max(24,min(54,ww//2)) if typ=='switch' else 22
                    toggle_x=5 if compact else max(6,(ww-toggle_w)//2)
                    toggle_y=max(1,(hh-22)//2) if compact else max(19,(hh-22)//2)
                    if not compact:build += [f'    cyd_widget_title(cyd_widgets[{i}],{label},{skin});']
                    build += [f'    cyd_fills[{i}]={"lv_switch_create" if typ=="switch" else "lv_checkbox_create"}(cyd_widgets[{i}]);',
                              f'    lv_obj_set_pos(cyd_fills[{i}],{toggle_x},{toggle_y});']
                    if typ=='switch':build += [f'    lv_obj_set_size(cyd_fills[{i}],{toggle_w},22);',
                                              f'    lv_obj_set_style_bg_color(cyd_fills[{i}],lv_color_hex({bg}),LV_PART_INDICATOR);']
                    else:build += [f'    lv_checkbox_set_text(cyd_fills[{i}],"");']
                    build += [f'    lv_obj_add_flag(cyd_fills[{i}],LV_OBJ_FLAG_EVENT_BUBBLE);']
                    if compact:
                        build += [f'    lv_obj_set_pos(cyd_labels[{i}],{min(ww-1,toggle_x+toggle_w+5)},{max(0,(hh-16)//2)});',
                                  f'    lv_obj_set_size(cyd_labels[{i}],{max(1,ww-toggle_x-toggle_w-8)},16);',
                                  f'    lv_obj_set_style_text_align(cyd_labels[{i}],LV_TEXT_ALIGN_LEFT,0);']
                        updates += [f'    {{bool on=(float)({expr})>={threshold:.5f}f;if(on)lv_obj_add_state(cyd_fills[{i}],LV_STATE_CHECKED);else lv_obj_remove_state(cyd_fills[{i}],LV_STATE_CHECKED);lv_label_set_text(cyd_labels[{i}],on?{q(lcd_font_safe(w.get("text") or typ.upper())+" ON")}:{q(lcd_font_safe(w.get("text") or typ.upper())+" OFF")});}}']
                    else:
                        build += [f'    lv_obj_set_size(cyd_labels[{i}],{max(1,ww-8)},16);',
                                  f'    lv_obj_set_pos(cyd_labels[{i}],4,{max(0,hh-18)});']
                        updates += [f'    {{bool on=(float)({expr})>={threshold:.5f}f;if(on)lv_obj_add_state(cyd_fills[{i}],LV_STATE_CHECKED);else lv_obj_remove_state(cyd_fills[{i}],LV_STATE_CHECKED);lv_label_set_text(cyd_labels[{i}],on?"ON":"OFF");}}']
                elif typ=='digital':
                    updates += [f'    {{bool on=(float)({expr})>={threshold:.5f}f;lv_label_set_text(cyd_labels[{i}],on?"ON":"OFF");lv_obj_set_style_text_color(cyd_labels[{i}],lv_color_hex(on?0x70f5ae:0xff9d87),0);}}']
                else:updates += [f'    cyd_paint_text(cyd_labels[{i}],(float)({expr}),{0 if typ=="integer" else prec},{unit});']
            elif typ=='waterfall':
                adc_mode=w.get('waterfallMode')=='adc_fft'
                # A 96x48 RGB565 LVGL canvas, 9216B, refreshed once per completed sweep.
                build += [
                    f'    cyd_widgets[{i}]=cyd_box(screen,{x},{y},{ww},{hh},0x081426,6);',
                    f'    cyd_labels[{i}]=cyd_lbl(cyd_widgets[{i}],"{"ADC GPIO35 FFT" if adc_mode else "CC1101 RSSI"}",{fg});',
                    f'    lv_obj_set_size(cyd_labels[{i}],{max(1,ww-6)},18);',
                    f'    lv_obj_set_pos(cyd_labels[{i}],3,1);',
                    f'    cyd_wf_buffers[{i}]=(uint8_t*)lv_malloc(96*48*2);',
                    f'    if(cyd_wf_buffers[{i}]){{',
                    f'      cyd_fills[{i}]=lv_canvas_create(cyd_widgets[{i}]);',
                    f'      lv_canvas_set_buffer(cyd_fills[{i}],cyd_wf_buffers[{i}],96,48,LV_COLOR_FORMAT_RGB565);',
                    f'      lv_obj_set_pos(cyd_fills[{i}],3,20);',
                    f'      lv_obj_set_size(cyd_fills[{i}],{max(1,ww-6)},{max(1,hh-42)});',
                    f'      lv_image_set_inner_align(cyd_fills[{i}],LV_IMAGE_ALIGN_STRETCH);',
                    f'      lv_image_set_antialias(cyd_fills[{i}],false);',
                    f'      {"cyd_fft_ui_seen" if adc_mode else "cyd_rf_ui_seen"}[{i}]=UINT32_MAX;',
                    f'    }}else lv_label_set_text(cyd_labels[{i}],"WATERFALL: LOW MEMORY");'
                ]
                if adc_mode:
                    build += [
                        f'    cyd_axis_label(cyd_widgets[{i}],"0 Hz",4,{hh-18},70,0xbadcf0);',
                        f'    cyd_axis_label(cyd_widgets[{i}],(String((int)(CYD_FFT_RATE/2))+" Hz").c_str(),{max(3,ww-76)},{hh-18},75,0xbadcf0);'
                    ]
                else:
                    build += [
                        f'    cyd_axis_label(cyd_widgets[{i}],(String(CYD_RF_START,2)+" MHz").c_str(),4,{hh-18},96,0xbadcf0);',
                        f'    cyd_axis_label(cyd_widgets[{i}],(String(CYD_RF_END,2)+" MHz").c_str(),{max(3,ww-101)},{hh-18},101,0xbadcf0);'
                    ]
                updates += [f'    {"cyd_update_adc_heatmap" if adc_mode else "cyd_update_rf_heatmap"}({i});']
            elif typ=='spectrum':
                # Draw 31 usable positive-frequency FFT bins with a native LVGL BAR chart.
                build += [
                    f'    cyd_widgets[{i}]=cyd_box(screen,{x},{y},{ww},{hh},0x081426,6);',
                    f'    cyd_labels[{i}]=cyd_lbl(cyd_widgets[{i}],"ADC FFT",{fg});',
                    f'    lv_obj_set_size(cyd_labels[{i}],{max(1,ww-6)},18);',
                    f'    lv_obj_set_pos(cyd_labels[{i}],3,1);',
                    f'    cyd_fills[{i}]=lv_chart_create(cyd_widgets[{i}]);',
                    f'    lv_obj_set_pos(cyd_fills[{i}],30,23);',
                    f'    lv_obj_set_size(cyd_fills[{i}],{max(1,ww-35)},{max(1,hh-45)});',
                    f'    lv_chart_set_div_line_count(cyd_fills[{i}],5,5);',
                    f'    lv_chart_set_type(cyd_fills[{i}],LV_CHART_TYPE_BAR);',
                    f'    lv_chart_set_point_count(cyd_fills[{i}],32);',
                    f'    lv_chart_set_axis_range(cyd_fills[{i}],LV_CHART_AXIS_PRIMARY_Y,0,100);',
                    f'    lv_obj_set_style_pad_all(cyd_fills[{i}],2,0);',
                    f'    cyd_fft_series[{i}]=lv_chart_add_series(cyd_fills[{i}],lv_color_hex({bg}),LV_CHART_AXIS_PRIMARY_Y);',
                    f'    cyd_fft_ui_seen[{i}]=UINT32_MAX;'
                ]
                build += [
                    f'    cyd_axis_label(cyd_widgets[{i}],"100",2,24,28,0xbadcf0);',
                    f'    cyd_axis_label(cyd_widgets[{i}],"0",11,{hh-34},22,0xbadcf0);',
                    f'    cyd_axis_label(cyd_widgets[{i}],"0 Hz",30,{hh-17},64,0xbadcf0);',
                    f'    cyd_axis_label(cyd_widgets[{i}],(String((int)(CYD_FFT_RATE/2))+" Hz").c_str(),{max(32,ww-78)},{hh-17},75,0xbadcf0);'
                ]
                updates += [f'    cyd_update_fft_chart({i});']
            elif typ=='draw':
                # Native LVGL lv_line path objects; const point arrays live in flash, not DRAM.
                pts=w.get('paths',[])
                build += [f'    cyd_widgets[{i}]=cyd_box(screen,{x},{y},{ww},{hh},0,0);',f'    lv_obj_set_style_bg_opa(cyd_widgets[{i}],LV_OPA_TRANSP,0);']
                for pathno,path in enumerate(pts[:16] if isinstance(pts,list) else []):
                    if not isinstance(path,list) or len(path)<2:continue
                    step=max(1,(len(path)+127)//128)
                    sampled=path[::step]
                    if sampled[-1] != path[-1]:sampled.append(path[-1])
                    cpp_pts=[]
                    for pair in sampled:
                        if not isinstance(pair,(list,tuple)) or len(pair)!=2:continue
                        try:px=int(float(pair[0]))-x;py=int(float(pair[1]))-y
                        except (ValueError,TypeError):continue
                        cpp_pts.append('{%d,%d}'%(max(-1000,min(1000,px)),max(-1000,min(1000,py))))
                    if len(cpp_pts)<2:continue
                    ident=f'{scene_num}_{i}_{pathno}'
                    build += [f'    static const lv_point_precise_t cyd_pts_{ident}[]={{'+','.join(cpp_pts)+'};',
                              f'    lv_obj_t* cyd_stroke_{ident}=lv_line_create(cyd_widgets[{i}]);',
                              f'    lv_line_set_points(cyd_stroke_{ident},cyd_pts_{ident},{len(cpp_pts)});',
                              f'    lv_obj_set_style_line_color(cyd_stroke_{ident},lv_color_hex({bg}),0);',
                              f'    lv_obj_set_style_line_width(cyd_stroke_{ident},2,0);']
            else:
                build += [f'    cyd_widgets[{i}]=cyd_box(screen,{x},{y},{ww},{hh},{bg},6);',f'    cyd_labels[{i}]=cyd_lbl(cyd_widgets[{i}],{label},{fg});']
            if skin and typ in ('button','custom','wifi','gyro','audio','mic','rfwave','rfsignal','rfrssi','icon','bar','progress','slider','battery','value','analog','integer','digital','led','switch','checkbox','gauge','waterfall','spectrum'):
                build += [f'    cyd_style_panel(cyd_widgets[{i}],{skin},{bg},{"true" if typ=="button" else "false"});']
                if typ in ('value','analog','integer','digital','rfrssi') and hh>=42 and w.get('text'):
                    build += [f'    cyd_style_caption(cyd_widgets[{i}],{label},{skin});']
                    if True:build += [f'    lv_obj_set_width(cyd_labels[{i}],{max(1,ww-16)});',f'    lv_obj_set_pos(cyd_labels[{i}],8,{max(16,hh-25)});',f'    lv_obj_set_style_text_align(cyd_labels[{i}],LV_TEXT_ALIGN_CENTER,0);']
                if typ=='slider':
                    build += [
                        f'    cyd_style_caption(cyd_widgets[{i}],{label},{skin},{max(40,(ww*42)//100)});',
                        f'    lv_obj_set_width(cyd_labels[{i}],{max(1,(ww*42)//100)});',
                        f'    lv_obj_set_pos(cyd_labels[{i}],{max(8,(ww*57)//100)},3);',
                        f'    lv_obj_set_size(cyd_labels[{i}],{max(1,(ww*42)//100)},16);',
                        f'    lv_obj_set_style_text_align(cyd_labels[{i}],LV_TEXT_ALIGN_RIGHT,0);'
                    ]
                if typ in ('value','analog','integer','digital','rfrssi'):
                    build += [f'    lv_obj_set_style_text_color(cyd_labels[{i}],lv_color_hex({fg}),0);']
                if typ=='gauge' and hh>=94 and ww>=96:
                    # Keep the native round scale visible in every visual theme.
                    build += [f'    cyd_style_caption(cyd_widgets[{i}],{label},{skin});']
                if typ=='spectrum':
                    build += [f'    lv_obj_set_style_bg_opa(cyd_fills[{i}],LV_OPA_TRANSP,0);',f'    lv_obj_set_style_border_width(cyd_fills[{i}],0,0);']
        build += ['    break;','  }']
        updates += ['    break;','  }']
    build += ['  default:activeScene=0;cyd_rendered_scene=-1;break;','  }','  lv_updateWidgets();','}']
    updates += ['  default:break;','  }','}']
    # build calls update; forward declare.
    needs_rf=any(w.get('type')=='waterfall' and w.get('waterfallMode')!='adc_fft' for sc in scenes for w in sc.get('widgets',[]))
    needs_fft=any(w.get('type')=='spectrum' for sc in scenes for w in sc.get('widgets',[]))
    needs_adc_wf=any(w.get('type')=='waterfall' and w.get('waterfallMode')=='adc_fft' for sc in scenes for w in sc.get('widgets',[]))
    helpers=[]
    if needs_rf:helpers.append(RF_LVGL_UPDATE)
    if needs_fft:helpers.append(FFT_LVGL_UPDATE)
    if needs_adc_wf:helpers.append(ADC_WATERFALL_UPDATE)
    return '\n'.join(helpers+['void lv_updateWidgets();']+build+updates)+'\n'


def convert(code, device, prof, rotation):
    if not prof.get('screen'):return code
    if prof.get('m5display'):
        native_w,native_h=prof['size']
        screen_w,screen_h=(native_h,native_w) if rotation%2 else (native_w,native_h)
    else:
        screen_w,screen_h=((240,135) if rotation%2 else (135,240)) if prof.get('cardputer_adv') else ((320,240) if rotation%2 else (240,320))
    begin=code.find('void drawScene(){')
    if begin<0:raise RuntimeError('LVGL renderer: existing screen drawing function not found')
    # Replace the complete balanced function, also on displays without a touch controller.
    opening=code.index('{',begin)
    depth=0
    finish=-1
    for i in range(opening,len(code)):
        if code[i]=='{':depth+=1
        elif code[i]=='}':
            depth-=1
            if depth==0:
                finish=i+1
                break
    if finish<0:raise RuntimeError('LVGL renderer: unbalanced scene function')
    code=code[:begin]+GLUE+'\n'+generate_widgets(device,screen_w,screen_h)+'\n'+code[finish:]
    code=code.replace('#include <TFT_eSPI.h>','#include <TFT_eSPI.h>\n#include <lvgl.h>\n#include <esp_heap_caps.h>')
    if prof.get('m5display'):
        code=code.replace('#include <M5Unified.h>','#include <M5Unified.h>\n#include <lvgl.h>\n#include <esp_heap_caps.h>')
    needle=('  tft.setColorDepth(16);tft.setRotation(SCREEN_ROTATION);tft.fillScreen(TFT_BLACK);' if prof.get('m5display') else '  tft.init();tft.setRotation(SCREEN_ROTATION);tft.fillScreen(TFT_BLACK);')
    if needle not in code:raise RuntimeError('LVGL renderer: setup display init not found')
    code=code.replace(needle,needle+'\n  cyd_lv_init();')
    # Control value changes update existing LVGL objects, without teardown and LCD clearing.
    code=re.sub(r'(uiValues\[[^\]]+\]=[^;]+;)drawScene\(\);',r'\1lv_updateWidgets();',code)
    code=code.replace('if(millis()-lastRefresh>250){lastRefresh=millis();drawScene();}', 'if(millis()-lastRefresh>80){lastRefresh=millis();lv_updateWidgets();}')
    needle='  pollBacklight();'
    code=code.replace(needle,needle+'\n  if(millis()-cyd_lv_last>=5){cyd_lv_last=millis();lv_timer_handler();}')
    return code