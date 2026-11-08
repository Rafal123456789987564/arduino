#!/usr/bin/env python3
"""CYD Studio: localhost-only visual editor, PlatformIO project compiler and USB flasher.
No third-party Python packages needed. All build/flash requests originate on localhost.
"""
from __future__ import annotations

import base64
from lvgl_renderer import convert as convert_lvgl
import io
import json
import math
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
import unicodedata
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
import zipfile
from xml.sax.saxutils import escape as xml_escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'projekty_PIO'
OUTPUT.mkdir(exist_ok=True)
JOBS = {}
RUNNING_PROCS = {}
LOCK = threading.Lock()
MAX_BODY = 4_000_000

PROFILES = {
 'cyd28': {'board':'esp32dev','screen':True,'touch':True,'bl':21, 'touchpins':(25,39,32,33,36)},
 'cyd28usb': {'board':'esp32dev','screen':True,'touch':True,'bl':21, 'touchpins':(25,39,32,33,36)},
 'cyd24': {'board':'esp32dev','screen':True,'touch':True,'bl':27, 'touchpins':(14,12,13,33,36)},
 'cyd28t':{'board':'esp32dev','screen':True,'touch':False,'bl':21, 'touchpins':None},
 'atom':  {'board':'m5stack-atom','screen':False,'touch':False},
 's3':    {'board':'esp32-s3-devkitc-1','screen':False,'touch':False},
 'cardputeradv': {'board':'esp32-s3-devkitc-1','screen':True,'touch':False, 'bl':38, 'cardputer_adv':True},
 'esp32': {'board':'esp32dev','screen':False,'touch':False},
 'coreink': {'board':'m5stack-coreink','screen':False,'touch':False},
 'stamplc': {'board':'esp32-s3-devkitc-1','screen':False,'touch':False},
 'atoms3lite': {'board':'esp32-s3-devkitc-1','screen':False,'touch':False},
 'atommatrix': {'board':'m5stack-atom','screen':False,'touch':False},
 'stamps3': {'board':'esp32-s3-devkitc-1','screen':False,'touch':False},
 # M5Unified detects the M5GFX panel and configures display transport/power.
 'atoms3': {'board':'esp32-s3-devkitc-1','screen':True,'touch':False,'m5display':True,'size':(128,128)},
 'cores3': {'board':'esp32-s3-devkitc-1','screen':True,'touch':True,'native_touch':True,'m5display':True,'size':(240,320)},
 'core2': {'board':'esp32dev','screen':True,'touch':True,'native_touch':True,'m5display':True,'size':(240,320)},
 'm5basic': {'board':'esp32dev','screen':True,'touch':False,'m5display':True,'size':(240,320)},
 'stickcplus2': {'board':'esp32dev','screen':True,'touch':False,'m5display':True,'size':(135,240)},
}
S3_PROFILES = {'s3','cardputeradv','stamplc','atoms3lite','stamps3','atoms3','cores3'}
M5_DISPLAY_PROFILES = {'atoms3','cores3','core2','m5basic','stickcplus2'}


def find_pio():
    for cmd in ('pio', 'platformio'):
        full = shutil.which(cmd)
        if full: return full
    home = Path.home()
    paths = [home / '.platformio/penv/Scripts/platformio.exe', home / '.platformio/penv/bin/platformio',
             home / '.platformio/penv/Scripts/pio.exe', home / '.platformio/penv/bin/pio']
    return str(next((p for p in paths if p.is_file()), ''))




def detect_serial_ports():
    """Get COM devices even if PlatformIO's JSON command is unavailable.

    The result is informational. Only a user-selected port is used for flashing.
    """
    ports = {}
    errors = []
    def add(port, description=''):
        port = str(port or '').strip()
        if not port:
            return
        if os.name == 'nt':
            if not re.fullmatch(r'COM[0-9]{1,3}', port, re.I):
                return
            port = port.upper()
        if port not in ports or (description and not ports[port]):
            ports[port] = str(description or '').strip()

    # Windows registry works without pyserial or a working PlatformIO CLI.
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DEVICEMAP\SERIALCOMM') as key:
                idx = 0
                while True:
                    try:
                        _, name, _ = winreg.EnumValue(key, idx)
                    except OSError:
                        break
                    add(name, 'Windows COM device')
                    idx += 1
        except Exception as e:
            errors.append('Windows registry: '+str(e))

    try:
        from serial.tools import list_ports
        for item in list_ports.comports():
            add(item.device, item.description)
    except ImportError:
        pass
    except Exception as e:
        errors.append('pyserial: '+str(e))

    pio = find_pio()
    if pio:
        try:
            proc = subprocess.run([pio,'device','list','--json-output'],
                                  timeout=12,capture_output=True,text=True,
                                  encoding='utf-8',errors='replace')
            if proc.returncode == 0:
                raw=json.loads(proc.stdout)
                if isinstance(raw,list):
                    for item in raw:
                        if isinstance(item,dict):
                            add(item.get('port'),item.get('description'))
            else:
                errors.append('PlatformIO device list failed: '+proc.stderr[-250:])
        except Exception as e:
            errors.append('PlatformIO port scan: '+str(e))
    return {'ports':[{'port':k,'description':v} for k,v in sorted(ports.items())],
            'errors':errors}



# Public GitHub repositories only; no arbitrary remote URL requests.
GITHUB_REPO_RE = re.compile(r'^https://github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9_.-]{1,100})(?:\.git)?/?(?:#([A-Za-z0-9._/-]{1,100}))?$', re.I)
HEADER_RE = re.compile(r'^[A-Za-z0-9_./+-]{1,100}\.h(?:pp)?$')


def github_url(url):
    """Normalize GitHub repository URL, optional #tag / #commit for reproducibility."""
    if not isinstance(url,str):raise ValueError('Enter a public GitHub repository URL.')
    m=GITHUB_RE_RE = GITHUB_REPO_RE.fullmatch(url.strip())
    if not m:raise ValueError('Expected https://github.com/OWNER/REPOSITORY (optional #tag).')
    owner,repo,ref=m.groups()
    if repo.endswith('.git'):repo=repo[:-4]
    if repo.startswith('.') or repo in ('..','.') or owner.endswith('-'):
        raise ValueError('Invalid GitHub repository URL.')
    normalized=f'https://github.com/{owner}/{repo}.git'
    if ref: normalized+='#'+ref
    return owner,repo,ref,normalized


def get_github_json(url, max_bytes=60000):
    # URL is constructed from validated path segments; no redirects to external hosts.
    req=urllib.request.Request(url, headers={'User-Agent':'CYD-Studio-DIAG/2.18','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=7) as response:
        if urllib.parse.urlsplit(response.geturl()).hostname not in ('api.github.com','raw.githubusercontent.com'):
            raise ValueError('Unexpected GitHub redirect.')
        data=response.read(max_bytes+1)
        if len(data)>max_bytes:raise ValueError('GitHub metadata is too large.')
        return json.loads(data)



# GitHub organisation inventory: all PUBLIC repositories, not a claim that all products
# are supported or that every repository is an Arduino/PlatformIO library.
M5STACK_CATALOG_CACHE = ROOT / 'm5stack_catalog_cache.json'
M5STACK_CATALOG_SEED = ROOT / 'm5stack_offline_catalog.json'
M5STACK_CATALOG_LOCK = threading.Lock()
M5STACK_REFRESH_SECONDS = 24 * 3600


def classify_m5_repo(item):
    """Repository category, not a guarantee of a physical port or supported driver."""
    name = str(item.get('name') or '')
    low = name.lower()
    if low.endswith(('-firmware', '-internal-fw', '-fw')) or 'internal-fw' in low:
        return 'Firmware'
    if low.startswith(('m5unit-', 'm5unit_')):
        return 'Unit'
    if low.startswith(('m5module-', 'm5module_')):
        return 'Module'
    if low.startswith(('m5hat-', 'm5hat_')):
        return 'HAT'
    if low.startswith(('m5base-', 'm5base_')):
        return 'Base'
    if low in ('m5unified', 'm5gfx', 'm5unitunified', 'm5family'):
        return 'Core / Graphics'
    if 'camera' in low or 'sensor' in low:
        return 'Sensors / Camera'
    return 'Other'


def m5_library_candidate(row):
    if row.get('archived') or row.get('category') == 'Firmware':
        return False
    name = str(row.get('name', '')).lower()
    if 'internal-fw' in name or any(x in name for x in ('-firmware', '-bootloader')):
        return False
    return name.startswith(('m5unit-', 'm5module-', 'm5hat-', 'm5base-')) or name in (
        'm5unified', 'm5gfx', 'm5unitunified', 'm5family', 'm5-ads1115',
        'm5-ads1100', 'm5-dlight', 'm5-ethernet', 'm5chain', 'm5-roverc', 'm5_ezdata', 'm5-fpc1020a')


def clean_m5_repo(info):
    name = str(info.get('name') or '')[:120]
    owner = (info.get('owner') or {}).get('login', '') if isinstance(info.get('owner'), dict) else ''
    fullname = str(info.get('full_name') or '')
    if owner.lower() != 'm5stack' or not re.fullmatch(r'm5stack/[A-Za-z0-9_.-]{1,120}', fullname, re.I):
        raise ValueError('Non-M5Stack repository in GitHub organisation listing.')
    row = {'name':name, 'full_name':fullname,
           'url':'https://github.com/'+fullname,
           'description':str(info.get('description') or '')[:260],
           'category':classify_m5_repo(info),
           'interface':'',  # Never guess hardware pinouts from a repository name.
           'archived':bool(info.get('archived')),
           'updated_at':str(info.get('updated_at') or '')[:40],
           'language':str(info.get('language') or '')[:50],
           'offline_seed':False}
    row['library_candidate']=m5_library_candidate(row)
    return row


def read_m5_fallback():
    try:
        obj=json.loads(M5STACK_CATALOG_CACHE.read_text(encoding='utf-8'))
        if isinstance(obj,dict) and isinstance(obj.get('items'),list) and obj['items']:
            return {'source':'cached GitHub inventory', 'items':obj['items'],
                    'complete':bool(obj.get('complete',False)),
                    'updated_at':obj.get('updated_at'), 'error':'',
                    'cached':True}
    except (OSError,ValueError,TypeError):pass
    raw=json.loads(M5STACK_CATALOG_SEED.read_text(encoding='utf-8'))
    items=[dict(row,library_candidate=m5_library_candidate(row)) for row in raw['items']]
    return {'source':'offline curated seed (not all repositories)', 'items':items,
            'complete':False, 'updated_at':None, 'error':'', 'cached':True}


def fetch_m5stack_catalog(force=False, fetcher=None):
    """Fetch every paginated repo (100/page) with an offline fallback.

    7-second timeout per GitHub page; rate limits / no network never make the editor fail.
    A partial fetch is NOT labelled complete and does not overwrite a good cache.
    """
    with M5STACK_CATALOG_LOCK:
        cached=read_m5_fallback()
        try:
            age=time.time()-M5STACK_CATALOG_CACHE.stat().st_mtime
        except OSError:age=1e20
        if cached['source']=='cached GitHub inventory' and age<M5STACK_REFRESH_SECONDS and not force:
            return cached
        fetcher=fetcher or get_github_json
        items=[]; complete=False
        try:
            for page in range(1,16):
                url=f'https://api.github.com/orgs/m5stack/repos?per_page=100&page={page}&type=public'
                data=fetcher(url, max_bytes=1_400_000)
                if not isinstance(data,list):raise ValueError('GitHub returned unexpected payload (possibly rate limit).')
                items.extend(clean_m5_repo(info) for info in data)
                if len(data)<100:
                    complete=True
                    break
            if not complete:raise ValueError('More than 1500 repositories; inventory is incomplete.')
            names=[x['full_name'].lower() for x in items]
            if len(names)!=len(set(names)):raise ValueError('Duplicate repositories in GitHub pagination.')
            result={'source':'GitHub API / m5stack (public repositories)',
                    'items':sorted(items,key=lambda r:r['name'].lower()),
                    'updated_at':int(time.time()),'complete':True,'cached':False, 'error':''}
            tmp=M5STACK_CATALOG_CACHE.with_suffix('.tmp')
            tmp.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
            tmp.replace(M5STACK_CATALOG_CACHE)
            return result
        except (OSError,ValueError,urllib.error.URLError,urllib.error.HTTPError,TimeoutError,KeyError,TypeError) as ex:
            cached['error']='GitHub refresh unavailable: '+str(ex)[:190]
            return cached


def fallback_template(owner,repo):
    slug=(owner+'/'+repo).lower()
    if slug=='adafruit/adafruit_mpu6050':
        return {'name':'MPU6050 · acceleration X','inputs':[],
                'headers':['Adafruit_MPU6050.h','Wire.h'],
                'globals':'Adafruit_MPU6050 cydMpu; bool cydMpuOK=false; sensors_event_t cydAcc, cydGyro, cydTemp;',
                'setup':'Wire.begin($i2c_sda,$i2c_scl); cydMpuOK=cydMpu.begin();',
                'preloop':'if(cydMpuOK)cydMpu.getEvent(&cydAcc,&cydGyro,&cydTemp);',
                'expression':'cydMpuOK ? cydAcc.acceleration.x : 0.0f',
                'ready':True,'details':'Reads X acceleration in m/s². Connect sensor to I2C.'}
    if slug=='adafruit/adafruit_ads1x15':
        return {'name':'ADS1115 · voltage A0','inputs':[],
                'headers':['Adafruit_ADS1X15.h','Wire.h'],
                'globals':'Adafruit_ADS1115 cydAds; bool cydAdsOK=false;',
                'setup':'Wire.begin($i2c_sda,$i2c_scl); cydAdsOK=cydAds.begin();',
                'expression':'cydAdsOK ? cydAds.computeVolts(cydAds.readADC_SingleEnded(0)) : 0.0f',
                'ready':True,'details':'Reads ADS1115 channel A0 in volts; verify module address and ADC input range.'}
    return {'name':repo.replace('_',' ')+' · custom','inputs':['IN'], 'headers':[],
            'globals':'','setup':'','preloop':'','expression':'$in0', 'ready':False,
            'details':'Library added. Define its C++ function/API before using it as a sensor.'}


def parse_cyd_manifest(raw, template):
    if not isinstance(raw,dict):return template
    if raw.get('schema') not in ('cyd-studio-block/1','cyd-studio-block/1.0'):
        return template
    allowed=('name','inputs','headers','globals','setup','preloop','expression','details')
    x=dict(template)
    for field in allowed:
        if field in raw:x[field]=raw[field]
    x['ready']=bool(x.get('expression'))
    return x


def inspect_github_library(url):
    owner, repo, ref, normalized = github_url(url)
    base=f'https://api.github.com/repos/{owner}/{repo}'
    info=get_github_json(base)
    if not isinstance(info,dict) or info.get('private') or not info.get('full_name'):
        raise ValueError('Repository not found or not public.')
    branch=ref or info.get('default_branch','main')
    if not re.fullmatch(r'[A-Za-z0-9._/-]{1,100}',branch):raise ValueError('Unsupported Git ref.')
    from urllib.parse import quote
    rawroot=f'https://raw.githubusercontent.com/{owner}/{repo}/{quote(branch,safe="/")}/'
    detected=[]
    manifest=None
    for filename in ('cyd-block.json','cyd-studio-block.json','library.json'):
        try:
            manifest=get_github_json(rawroot+filename,30000)
            if filename!='library.json': break
            detected.append(manifest)
            manifest=None
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,json.JSONDecodeError):pass
    preset=fallback_template(owner,repo)
    if manifest:preset=parse_cyd_manifest(manifest,preset)
    if not preset.get('headers') and detected and isinstance(detected[0],dict):
        headers=detected[0].get('headers')
        if isinstance(headers,str):headers=[headers]
        if isinstance(headers,list):preset['headers']=[h for h in headers if isinstance(h,str) and HEADER_RE.fullmatch(h)][:6]
    result={'id':f'{owner}_{repo}'.lower().replace('-','_').replace('.','_')[:90],
            'url':normalized,'repo':f'{owner}/{repo}',
            'description':str(info.get('description') or '')[:300]}
    result.update(preset)
    return sanitize_github_library(result)


def sanitize_github_library(lib):
    if not isinstance(lib,dict):raise ValueError('Invalid GitHub library block.')
    _,_,_,url=github_url(lib.get('url',''))
    ident=str(lib.get('id',''))
    if not re.fullmatch(r'[a-zA-Z0-9_-]{3,90}',ident):raise ValueError('Invalid GitHub block identifier.')
    inputs=lib.get('inputs',[])
    if not isinstance(inputs,list) or len(inputs)>8 or any(not isinstance(x,str) or len(x)>30 for x in inputs):
        raise ValueError('A GitHub block supports 0–8 named inputs.')
    headers=lib.get('headers',[])
    if not isinstance(headers,list) or len(headers)>12 or any(not isinstance(x,str) or not HEADER_RE.fullmatch(x) for x in headers):
        raise ValueError('Invalid C++ header list.')
    result={'id':ident,'url':url,'repo':str(lib.get('repo',''))[:120],
            'name':str(lib.get('name','GitHub block'))[:90],
            'description':str(lib.get('description',''))[:300],
            'details':str(lib.get('details',''))[:300],
            'headers':headers,'inputs':inputs,'ready':bool(lib.get('ready',False))}
    for key in ('globals','setup','preloop','expression'):
        v=lib.get(key,'')
        if not isinstance(v,str) or len(v)>5000:raise ValueError('Library C++ field too large: '+key)
        result[key]=v
    return result


def libraries_for_device(device):
    raw=device.get('githubLibraries') or []
    if not isinstance(raw,list) or len(raw)>35:raise ValueError('Too many GitHub libraries (maximum 35).')
    libs=[sanitize_github_library(x) for x in raw]
    if len({x['id'] for x in libs})!=len(libs):raise ValueError('Duplicate GitHub library block IDs.')
    return {x['id']:x for x in libs}

def validate_device(data, requested):
    if not isinstance(data,dict) or not isinstance(data.get('devices'),list):
        raise ValueError('Projekt nie zawiera listy urządzeń.')
    if len(data['devices']) > 30: raise ValueError('Maksymalnie 30 urządzeń.')
    device = next((d for d in data['devices'] if d.get('id')==requested),None)
    if not device: raise ValueError('Nie znaleziono urządzenia w projekcie.')
    profile = device.get('profile')
    if profile not in PROFILES: raise ValueError('Nieobsługiwany profil płytki: '+str(profile))
    return device, PROFILES[profile]


def checked_int(raw, name='integer'):
    """Strict numeric input validation; no nonfinite/fractional values in GPIO/timing settings."""
    try: number = float(raw)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f'Invalid {name}: expected a finite integer.') from None
    if not math.isfinite(number) or not number.is_integer():
        raise ValueError(f'Invalid {name}: expected a finite integer.')
    return int(number)


def checked_float(raw, name='number'):
    try: number = float(raw)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f'Invalid {name}: expected a finite number.') from None
    if not math.isfinite(number):
        raise ValueError(f'Invalid {name}: expected a finite number.')
    return number


def get_number(obj, key, default, low=0, high=320):
    try: return max(low, min(high,int(obj.get(key,default))))
    except (ValueError,TypeError,AttributeError,OverflowError): return default


def color(s):
    if not isinstance(s,str) or not re.fullmatch(r'#[a-fA-F0-9]{6}',s):return '0xFFFFFF'
    return '0x'+s[1:].upper()


def clean_text(s,n=70):
    s=unicodedata.normalize('NFKD', str(s))
    s=''.join(c for c in s if not unicodedata.combining(c))
    s=s.encode('ascii','replace').decode('ascii')
    return s.replace('\n',' ').replace('\r',' ')[:n]


def cstr(s,n=80): return json.dumps(clean_text(s,n),ensure_ascii=True)


def value(s, n=70): return str(s if s is not None else '')[:n]


def boolv(obj,key):return bool(obj.get(key,False))


def widget_value_cpp(w, feat, logic_ids, ui_ids):
    src=str(w.get('source','constant'))
    if src=='battery_percent' and boolv(feat,'battery'):
        return '((float)batteryPercent())'
    if src=='battery_voltage' and boolv(feat,'battery'):
        return 'batteryVolts()'
    if src.startswith('logic:'):
        ident=src[6:]
        if ident not in logic_ids:raise ValueError('Widget odwołuje się do usuniętego bloczka: '+ident)
        return f'logicValue{logic_ids[ident]}'
    if src=='wifi_rssi':
        return '((WiFi.status()==WL_CONNECTED) ? (float)WiFi.RSSI() : NAN)' if str(feat.get('wifi_mode','off')) in ('sta','ap_sta') else 'NAN'
    if w.get('id') in ui_ids and w.get('type') in ('slider','switch','checkbox'):
        return f'uiValues[{ui_ids[w["id"]]}]'
    v=svg_num(w,'level',65,-1000000,1000000)
    return f'{v:.6f}f'


def draw_widget(w, feat, logic_ids=None, ui_ids=None, width_screen=240, height_screen=320):
    logic_ids=logic_ids or {};ui_ids=ui_ids or {}
    typ=str(w.get('type','button'))
    x=get_number(w,'x',15,0,width_screen-1)
    y=get_number(w,'y',20,0,height_screen-1)
    width=get_number(w,'w',100,1,width_screen-x)
    height=get_number(w,'h',40,1,height_screen-y)
    bg=color(w.get('bg','#2384b9'))
    fg=color(w.get('fg','#ffffff'))
    label=cstr(w.get('text',''))
    lines=[]
    if typ=='button':
        lines += [f'tft.fillRoundRect({x},{y},{width},{height},8,C565({bg}));',
                  f'tft.setTextColor(C565({fg}),C565({bg}));',
                  f'tft.drawCentreString({label},{x+width//2},{y+max(0,(height-16)//2)},2);']
    elif typ=='text':
        source=w.get('source','constant')
        if source in ('battery_percent','battery_voltage') or str(source).startswith('logic:'):
            expr=widget_value_cpp(w,feat,logic_ids,ui_ids)
            unit='%' if source=='battery_percent' else ' V' if source=='battery_voltage' else str(w.get('unit',''))[:8]
            result=f'String({expr},2) + {cstr(unit)}'
            lines += [f'tft.setTextColor(C565({fg}),C565({color(w.get("screenBg","#101928"))}));',
                      f'tft.drawCentreString({result},{x+width//2},{y+max(0,(height-16)//2)},2);']
        else:
            lines += [f'tft.setTextColor(C565({fg}),C565({color(w.get("screenBg","#101928"))}));',
                      f'tft.drawCentreString({label},{x+width//2},{y+max(0,(height-16)//2)},2);']
    elif typ in ('rect','frame'):
        lines += [f'tft.{"drawRect" if typ=="frame" else "fillRect"}({x},{y},{width},{height},C565({bg}));']
    elif typ=='circle':
        lines += [f'tft.fillCircle({x+width//2},{y+height//2},{min(width,height)//2},C565({bg}));']
    elif typ=='line':
        lines += [f'tft.drawLine({x},{y},{x+width-1},{y+height-1},C565({bg}));']
    elif typ=='battery':
        if str(w.get('source','')).startswith('logic:'):
            expr=widget_value_cpp(w,feat,logic_ids,ui_ids)
            lines += ['{',f'float pct=constrain((float)({expr}),0.0f,100.0f);',
              f'tft.drawRoundRect({x},{y},{width-7},{height},3,TFT_WHITE);',
              f'tft.fillRect({x+width-5},{y+height//3},5,{height//3},TFT_WHITE);',
              f'tft.fillRect({x+3},{y+3},(int)(({width}-13)*pct/100.0f),{height-6},pct<20?TFT_RED:TFT_GREEN);',
              f'tft.setTextColor(TFT_WHITE,TFT_BLACK);tft.drawCentreString(String((int)roundf(pct))+"%",{x+(width-7)//2},{y+height//2-8},2);','}']
        else:
            lines += [f'drawBattery({x},{y},{width},{height});']
    elif typ=='waterfall':
        lines += [f'drawCydSpectrum({x},{y},{width},{height});' if w.get('waterfallMode')=='adc_fft' else f'drawCydRF({x},{y},{width},{height});']
    elif typ=='spectrum':
        lines += [f'drawCydSpectrum({x},{y},{width},{height});']
    elif typ in ('rfwave','rfsignal','rfrssi'):
        rf=str(w.get('radioType','wifi')).lower()
        types={'wifi':'Wi-Fi','ble':'BLE','bt':'BT Classic','espnow':'ESP-NOW','lora':'LoRa','cc1101':'CC1101', 'nrf24':'nRF24', 'zigbee':'Zigbee','rf433':'433 MHz','rf868':'868 MHz','rf915':'915 MHz','custom':'RADIO'}
        src=str(w.get('source','constant'))
        caption=cstr(types.get(rf,'RADIO') + (' DEMO' if src=='constant' else ''))
        dbm=widget_value_cpp(w,feat,logic_ids,ui_ids)
        minimum=svg_num(w,'min',-110,-200,100)
        maximum=svg_num(w,'max',-30,-200,100)
        variant={'rfwave':0,'rfsignal':1,'rfrssi':2}[typ]
        lines += [f'drawRadioSignal({x},{y},{width},{height},{caption},(float)({dbm}),{minimum:.2f}f,{maximum:.2f}f,C565({bg}),{variant});']
    elif typ=='wifi':
        lines += [f'tft.fillRoundRect({x},{y},{width},{height},6,C565(0x123448));',
                  f'drawCydSensorIcon({x+int(width*0.22)},{y+height//2},{max(6,int(min(width*.17,height*.37)))},"wifi",C565({bg}));',
                  f'tft.setTextColor(TFT_WHITE,C565(0x123448));tft.drawCentreString("Wi-Fi",{x+int(width*.7)},{y+max(0,(height-16)//2)},2);']
    elif typ=='gyro':
        lines += [f'drawGyro({x},{y},{width},{height});']
    elif typ in ('audio','mic'):
        lines += [f'drawAudio({x},{y},{width},{height});']
    elif typ=='icon':
        symbol=str(w.get('iconName','wifi')).lower()
        known={'wifi','bluetooth','radio','antenna','can','temperature','pressure','gyro','microphone','battery','voltage','water','light','gps','speed','nfc','vibration','sensor','signal','waves'}
        if symbol not in known:symbol='wifi'
        lines += [f'drawCydSensorIcon({x+width//2},{y+height//2},{int(min(width,height)*0.36)},{cstr(symbol)},C565({bg}));']
    elif typ=='custom':
        lines += [f'drawState({x},{y},{width},{height},{label},true);']
    elif typ in ('bar','progress','slider','gauge','value','integer','analog','digital','led','switch','checkbox'):
        expr=widget_value_cpp(w,feat,logic_ids,ui_ids)
        minimum=svg_num(w,'min',0,-1000000,1000000)
        maximum=svg_num(w,'max',100,-1000000,1000000)
        threshold=svg_num(w,'threshold',0.5,-1000000,1000000)
        precision=int(svg_num(w,'precision',1,0,3))
        unit=cstr(str(w.get('unit',''))[:8])
        lines.extend(['{', f'float v=(float)({expr});',
                      f'float frac=constrain((v-({minimum:.6f}f))/max(0.000001f,({maximum-minimum:.6f}f)),0.0f,1.0f);'])
        if typ in ('bar','progress'):
            lines += [f'tft.drawRect({x},{y},{width},{height},C565({fg}));',
                      f'tft.fillRect({x+2},{y+2},(int)(({width}-4)*frac),max(0,{height}-4),C565({bg}));']
            if typ=='progress':
                lines += [f'tft.setTextColor(C565({fg}));',f'tft.drawCentreString(String((int)roundf(frac*100.0f))+"%",{x+width//2},{y+height//2-7},2);']
        elif typ in ('analog','integer','value'):
            as_text='String((long)lroundf(v))' if typ=='integer' else f'String(v,{precision})'
            lines += [f'tft.fillRoundRect({x},{y},{width},{height},6,C565(0x172b40));',
                      f'tft.setTextColor(C565({bg}),C565(0x172b40));',
                      f'tft.drawCentreString({as_text}+String({unit}),{x+width//2},{y+height//2-8},2);']
            if height>40:lines += [f'tft.setTextColor(C565({fg}),C565(0x172b40));',f'tft.drawString({label},{x+5},{y+2},1);']
        elif typ in ('led','digital','switch','checkbox'):
            lines += [f'bool on=(v>={threshold:.6f}f);']
            if typ=='led':
                lines += [f'tft.fillCircle({x+width//2},{y+height//2},{int(min(width,height)*0.33)},on?C565({bg}):C565(0x394957));',
                          f'tft.drawCircle({x+width//2},{y+height//2},{int(min(width,height)*0.33)},C565({fg}));']
            elif typ=='digital':
                lines += [f'tft.fillRoundRect({x},{y},{width},{height},7,on?C565({bg}):C565(0x42506b));',
                          f'tft.setTextColor(TFT_WHITE);tft.drawCentreString(on?"ON":"OFF",{x+width//2},{y+height//2-8},2);']
            elif typ=='switch':
                lines += [f'tft.fillRoundRect({x},{y},{width},{height},7,C565(0x203448));',
                          f'tft.fillRoundRect({x+5},{y+height//2-13},{max(1,width-10)},26,12,on?C565({bg}):C565(0x485b6b));',
                          f'tft.fillCircle(on?{x+width-17}:{x+17},{y+height//2},10,TFT_WHITE);',
                          f'tft.setTextColor(TFT_WHITE,C565(0x203448));tft.drawCentreString({label},{x+width//2},{y+2},1);']
            else:
                lines += [f'tft.fillRoundRect({x},{y},{width},{height},5,C565(0x18314a));',
                          f'tft.drawRect({x+5},{y+height//2-9},18,18,C565({fg}));',
                          f'if(on)tft.fillRect({x+8},{y+height//2-6},12,12,C565({bg}));',
                          f'tft.setTextColor(C565({fg}),C565(0x18314a));tft.drawString({label},{x+30},{y+height//2-6},1);']
        elif typ=='slider':
            lines += [f'tft.fillRoundRect({x},{y},{width},{height},6,C565(0x172b40));',
                      f'tft.fillRect({x+13},{y+int(height*0.59)-3},{max(1,width-26)},6,C565(0x456179));',
                      f'tft.fillRect({x+13},{y+int(height*0.59)-3},(int)({max(1,width-26)}*frac),6,C565({bg}));',
                      f'tft.fillCircle({x+13}+(int)({max(1,width-26)}*frac),{y+int(height*0.59)},9,C565({fg}));',
                      f'tft.setTextColor(C565({fg}),C565(0x172b40));tft.drawCentreString({label}+String(": ")+String(v,{precision})+String({unit}),{x+width//2},{y+2},1);']
        elif typ=='gauge':
            rad=int(min(width*0.41,height*0.59));cx=x+width//2;cy=y+int(height*0.73)
            lines += [f'tft.fillRoundRect({x},{y},{width},{height},7,C565(0x152738));',
                      f'const int cx={cx},cy={cy},rad={rad};',
                      'for(int j=0;j<24;j++){',
                      '  float a=3.14159265f+j*3.14159265f/24.0f;',
                      '  float b=3.14159265f+(j+1)*3.14159265f/24.0f;',
                      f'  uint16_t c=(j<((int)(24*frac)))?C565({bg}):C565(0x435267);',
                      '  tft.drawLine(cx+(int)(rad*cosf(a)),cy+(int)(rad*sinf(a)),cx+(int)(rad*cosf(b)),cy+(int)(rad*sinf(b)),c);',
                      '}',
                      'float angle=3.14159265f+frac*3.14159265f;',
                      f'tft.drawLine(cx,cy,cx+(int)((rad-9)*cosf(angle)),cy+(int)((rad-9)*sinf(angle)),C565({fg}));',
                      f'tft.setTextColor(C565({fg}),C565(0x152738));tft.drawCentreString(String(v,{precision})+String({unit}),cx,cy+2,2);']
        lines.append('}')
    elif typ=='draw':
        paths=w.get('paths',[])
        if isinstance(paths,list):
            for path in paths[:100]:
                if not isinstance(path,list):continue
                points=[p for p in path[:600] if isinstance(p,list) and len(p)>=2]
                for a,b in zip(points,points[1:]):
                    x1=max(0,min(width_screen-1,int(a[0])));y1=max(0,min(height_screen-1,int(a[1])))
                    x2=max(0,min(width_screen-1,int(b[0])));y2=max(0,min(height_screen-1,int(b[1])))
                    lines += [f'tft.drawLine({x1},{y1},{x2},{y2},C565({bg}));']
    return '\n'.join('    '+line for line in lines)


# Block graph compiler: each connected element becomes an actual C++ signal.
# Serial/scope blocks emit NAME=value to the firmware's UART monitor.
LOGIC_INPUTS = {
    'adc':0, 'digital':0, 'battery':0, 'voltage':0,
    'constant':0, 'timer':0, 'map':1, 'clamp':1,
    'add':2, 'subtract':2, 'multiply':2, 'divide':2, 'abs':1,
    'ema':1, 'schmitt':1, 'greater':1, 'not':1,
    'and':2, 'or':2, 'pwm':1, 'gpioout':1,
    'brightness':1, 'serial':1, 'scope':1, 'uiinput':0, 'github':8,
    'screenout':1, 'groveanalog':0, 'grovedigital':0, 'groveout':1,
    'min':2,'max':2,'power':2,'modulo':2,'sqrt':1,'round':1,'floor':1,'ceil':1,'sin':1,'cos':1,
    'less':2,'equals':2,'xor':2,'nand':2,'nor':2,'between':1,
    'negate':1,'square':1,'sign':1,'log':1,'exp':1,'tan':1,'radians':1,'degrees':1,
    'average':2,'lerp':3,'quantize':1,'deadband':1,
    'select':3,'greater2':2,'gte':2,'lte':2,'neq':2,
    'edge_rise':1,'edge_fall':1,'toggle':1,'counter':2,'debounce':1,
    'integrate':1,'derivative':1,'pulse':0,'saw':0,'triangle':0,
    'canrx':0,'cc1101rssi':0,'rfbin':1,'fftpeak':0,'fftbin':1
}


def generate_logic(device, p, features):
    graph = device.get('logic') or {}
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    if not nodes: return '', '', ''
    if not isinstance(nodes, list) or not isinstance(edges, list) or len(nodes) > 100 or len(edges) > 200:
        raise ValueError('Schemat: maksymalnie 100 bloczków i 200 połączeń.')
    github_libs=libraries_for_device(device)
    ids = {}
    for i, n in enumerate(nodes):
        if not isinstance(n, dict) or n.get('type') not in LOGIC_INPUTS:
            raise ValueError('Schemat zawiera nieznany bloczek.')
        if n.get('type')=='github' and str((n.get('props') or {}).get('library_id','')) not in github_libs:
            raise ValueError('GitHub block refers to a missing library. Reimport it.')
        ident = n.get('id')
        if not isinstance(ident, str) or len(ident) > 100 or ident in ids:
            raise ValueError('Schemat zawiera powtarzający się identyfikator.')
        ids[ident] = i
    inputs = {}
    indeg = [0] * len(nodes)
    outgoing = [[] for _ in nodes]
    for edge in edges:
        if not isinstance(edge, dict) or edge.get('from') not in ids or edge.get('to') not in ids:
            raise ValueError('Połączenie wskazuje nieistniejący bloczek.')
        src, dst = ids[edge['from']], ids[edge['to']]
        channel = edge.get('input')
        max_input=len(github_libs[nodes[dst].get('props',{}).get('library_id')]['inputs']) if nodes[dst]['type']=='github' else LOGIC_INPUTS[nodes[dst]['type']]
        if not isinstance(channel, int) or not 0 <= channel < max_input:
            raise ValueError('Nieprawidłowe wejście w połączeniu bloczków.')
        if (dst, channel) in inputs:
            raise ValueError('Do jednego wejścia podłączono dwa przewody.')
        inputs[dst, channel] = src
        indeg[dst] += 1
        outgoing[src].append(dst)
    queue = [i for i, d in enumerate(indeg) if d == 0]
    order = []
    while queue:
        i = queue.pop(0)
        order.append(i)
        for j in outgoing[i]:
            indeg[j] -= 1
            if indeg[j] == 0: queue.append(j)
    if len(order) != len(nodes):
        raise ValueError('Bloczki tworzą pętlę. Usuń połączenie zwrotne.')

    def number(node, key, default=0., low=-1000000., high=1000000.):
        try: v = float((node.get('props') or {}).get(key, default))
        except (ValueError, TypeError): raise ValueError(f'Nieprawidłowa wartość bloku: {key}.')
        if not math.isfinite(v) or not low <= v <= high:
            raise ValueError(f'Wartość poza zakresem w bloczku: {key}.')
        part = f'{v:.8g}'
        if '.' not in part and 'e' not in part and 'E' not in part:
            part += '.0'
        return part + 'f'

    def pin(node, key, default):
        v = checked_int((node.get('props') or {}).get(key, default), key)
        if not 0 <= v <= (48 if device.get('profile') in S3_PROFILES else 39):
            raise ValueError('Nieprawidłowy numer GPIO w bloczku.')
        return v

    def inp(i, channel=0):
        src = inputs.get((i, channel))
        return f'logicValue{src}' if src is not None else '0.0f'

    def grove_pin(node):
        props=node.get('props') or {}
        port=str(props.get('port','B')).upper()
        line=str(props.get('line','io1')).lower()
        if port not in ('A','B','C') or line not in ('io1','io2'):
            raise ValueError('Grove: select port A/B/C and line io1/io2.')
        grove=device.get('grove') or {}
        pins=grove.get(port) or {}
        gp=checked_int(pins.get(line,-1), f'Grove {port}.{line}')
        if gp < 0:raise ValueError(f'Grove Port {port} {line} is not mapped to a physical GPIO.')
        if gp > (48 if device.get('profile') in S3_PROFILES else 39):raise ValueError('Invalid Grove pin.')
        return gp
    decl = ['// CYD Studio: compiled visual logic']
    setup = []
    active_lib_ids={str((n.get('props') or {}).get('library_id')) for n in nodes if n.get('type')=='github'}
    for lib_id, lib in github_libs.items():
        if lib_id in active_lib_ids:
            if lib['globals']:decl.append(lib['globals'].replace('$i2c_sda',str(get_number(device.get('pins') or {},'i2c_sda',27,0,48))).replace('$i2c_scl',str(get_number(device.get('pins') or {},'i2c_scl',22,0,48))))
            if lib['setup']:setup.append('  '+lib['setup'].replace('$i2c_sda',str(get_number(device.get('pins') or {},'i2c_sda',27,0,48))).replace('$i2c_scl',str(get_number(device.get('pins') or {},'i2c_scl',22,0,48))))
    loop = ['void pollLogic(){',
            '  static uint32_t lastLogicTick = 0;',
            '  if((uint32_t)(millis()-lastLogicTick)<20) return; // maks. 50 Hz, bez delay()',
            '  lastLogicTick=millis();']
    pwm_count = 0
    for lib_id, lib in github_libs.items():
        if lib_id in active_lib_ids and lib['preloop']:
            pre=lib['preloop'].replace('$i2c_sda',str(get_number(device.get('pins') or {},'i2c_sda',27,0,48))).replace('$i2c_scl',str(get_number(device.get('pins') or {},'i2c_scl',22,0,48)))
            loop.append('  '+pre)
    for i in order:
        n = nodes[i]; typ = n['type']
        v = f'logicValue{i}'
        decl.append(f'float {v}=0.0f;')
        if typ == 'github':
            lib=github_libs[str((n.get('props') or {}).get('library_id',''))]
            expr=lib['expression'].strip() or '$in0'
            expr=re.sub(r'\$in([0-7])\b',lambda m:inp(i,int(m.group(1))) if int(m.group(1))<len(lib['inputs']) else '0.0f',expr)
            expr=expr.replace('$i2c_sda',str(get_number(device.get('pins') or {},'i2c_sda',27,0,48))).replace('$i2c_scl',str(get_number(device.get('pins') or {},'i2c_scl',22,0,48)))
            loop.append(f'  {v}=(float)({expr});')
        elif typ in ('groveanalog','grovedigital','groveout'):
            gp=grove_pin(n)
            busy={15,14,13,12,2,21,25,32,39,33,36,18,23,19,5} if device.get('profile') in ('cyd28','cyd28usb','cyd28t') else ({15,14,13,12,2,27,33,36,18,23,19,5} if device.get('profile')=='cyd24' else set())
            if typ=='groveanalog':
                adc1=range(1,11) if device.get('profile') in S3_PROFILES else (32,33,34,35,36,39)
                if gp not in adc1:raise ValueError(f'Grove ADC GPIO{gp} is not ADC1 on this board.')
                loop.append(f'  {v}=analogReadMilliVolts({gp})*0.001f*({number(n,"mul",1,0.001,1000)});')
            elif typ=='grovedigital':
                setup.append(f'  pinMode({gp},INPUT);')
                loop.append(f'  {v}=digitalRead({gp}) ? 1.0f : 0.0f;')
            else:
                if gp in busy or (device.get('profile') not in S3_PROFILES and gp in (34,35,36,39)):
                    raise ValueError(f'Grove output GPIO{gp} is reserved/input-only on this board.')
                setup.append(f'  pinMode({gp},OUTPUT);')
                loop += [f'  {v}=({inp(i)}>=0.5f)?1.0f:0.0f;',f'  digitalWrite({gp},{v}>=0.5f?HIGH:LOW);']
        elif typ == 'screenout':
            target=str((n.get('props') or {}).get('widgetId',''))
            possible={w.get('id') for sc in device.get('scenes',[]) for w in sc.get('widgets',[]) if isinstance(w,dict)}
            if target not in possible:raise ValueError('Screen input block: select a valid screen widget.')
            loop.append(f'  {v}={inp(i)};')
        elif typ == 'adc':
            gp = pin(n, 'gpio', 35)
            adc1 = range(1,11) if device.get('profile') in S3_PROFILES else (32,33,34,35,36,39)
            if gp not in adc1:
                raise ValueError('Blok ADC: wybierz ADC1 (ESP32: GPIO32–39, S3: GPIO1–10).')
            loop.append(f'  {v}=analogReadMilliVolts({gp})*0.001f*({number(n,"mul",1,0.001,1000)});')
        elif typ == 'digital':
            gp = pin(n,'gpio',34)
            setup.append(f'  pinMode({gp},INPUT);')
            loop.append(f'  {v}=digitalRead({gp}) ? 1.0f : 0.0f;')
        elif typ in ('battery','voltage'):
            if not bool(features.get('battery')):
                raise ValueError('Blok Bateria wymaga włączenia pomiaru baterii w zakładce Peryferia.')
            loop.append(f'  {v}={"batteryPercent()" if typ=="battery" else "batteryVolts()"};')
        elif typ == 'uiinput':
            ident=str((n.get('props') or {}).get('widgetId',''))
            all_widgets=[w for sc in device.get('scenes',[]) for w in sc.get('widgets',[]) if isinstance(w,dict) and w.get('type') in ('slider','switch','checkbox') and w.get('source','constant')=='constant']
            ui_ids={w.get('id'):idx for idx,w in enumerate(all_widgets)}
            if ident not in ui_ids:raise ValueError('UI input: choose an existing Slider/Switch/Checkbox widget (Data source = Constant).')
            loop.append(f'  {v}=uiValues[{ui_ids[ident]}];')
        elif typ == 'constant':
            loop.append(f'  {v}={number(n,"value",50)};')
        elif typ == 'timer':
            period = checked_int((n.get('props') or {}).get('period',1000), 'timer.period')
            pulse = checked_int((n.get('props') or {}).get('pulse',150), 'timer.pulse')
            if not 1 <= period <= 3600000 or pulse < 0 or pulse > period:
                raise ValueError('Timer: okres 1–3600000 ms, ON nie może przekroczyć okresu.')
            loop.append(f'  {v}=((millis()%{period}UL)<{pulse}UL)?1.0f:0.0f;')
        elif typ == 'map':
            a = number(n, 'inMin',3.2); b=number(n,'inMax',4.2)
            c = number(n,'outMin',0); d=number(n,'outMax',100)
            loop.append(f'  {v}=(fabsf(({b})-({a}))>0.000001f) ? (({inp(i)}-({a}))*(({d})-({c}))/(({b})-({a}))+({c})) : ({c});')
        elif typ == 'clamp':
            lo = number(n,'min',0);hi=number(n,'max',100)
            loop.append(f'  {v}=constrain({inp(i)},{lo},{hi});')
        elif typ in ('add','subtract','multiply','divide'):
            a=inp(i,0);b=inp(i,1)
            expr={'add':f'{a}+{b}', 'subtract':f'{a}-{b}', 'multiply':f'{a}*{b}',
                  'divide':f'(fabsf({b})<0.000001f?0.0f:{a}/{b})'}[typ]
            loop.append(f'  {v}=({expr});')
        elif typ in ('min','max','power','modulo'):
            a=inp(i,0);b=inp(i,1)
            expr={'min':f'fminf({a},{b})','max':f'fmaxf({a},{b})','power':f'powf({a},{b})',
                  'modulo':f'(fabsf({b})<0.000001f?0.0f:fmodf({a},{b}))'}[typ]
            loop.append(f'  {v}={expr};')
        elif typ in ('sqrt','round','floor','ceil','sin','cos'):
            arg=inp(i)
            expr={'sqrt':f'sqrtf(fmaxf(0.0f,{arg}))','round':f'roundf({arg})','floor':f'floorf({arg})',
                  'ceil':f'ceilf({arg})','sin':f'sinf({arg})','cos':f'cosf({arg})'}[typ]
            loop.append(f'  {v}={expr};')
        elif typ == 'less':
            loop.append(f'  {v}=({inp(i,0)}<{inp(i,1)})?1.0f:0.0f;')
        elif typ == 'equals':
            tolerance=number(n,'tolerance',.001,0,1000000)
            loop.append(f'  {v}=(fabsf({inp(i,0)}-{inp(i,1)})<={tolerance})?1.0f:0.0f;')
        elif typ in ('xor','nand','nor'):
            a=f'({inp(i,0)}>=0.5f)';b=f'({inp(i,1)}>=0.5f)'
            expr={'xor':f'({a}!={b})','nand':f'!({a}&&{b})','nor':f'!({a}||{b})'}[typ]
            loop.append(f'  {v}=({expr})?1.0f:0.0f;')
        elif typ == 'between':
            lo=number(n,'low',0);hi=number(n,'high',100)
            loop.append(f'  {v}=({inp(i)}>={lo}&&{inp(i)}<={hi})?1.0f:0.0f;')
        elif typ == 'abs':
            loop.append(f'  {v}=fabsf({inp(i)});')
        elif typ == 'ema':
            alpha = number(n,'alpha',0.2,0,1)
            decl.append(f'static bool logicEmaReady{i}=false;')
            loop.append(f'  if(!logicEmaReady{i}){{{v}={inp(i)};logicEmaReady{i}=true;}}else {v}=({alpha})*{inp(i)}+(1.0f-({alpha}))*{v};')
        elif typ == 'schmitt':
            lo = number(n,'low',3.55);hi=number(n,'high',3.7)
            if float(lo[:-1]) >= float(hi[:-1]):
                raise ValueError('Histereza: próg dolny musi być mniejszy od górnego.')
            loop.append(f'  if({inp(i)}>=({hi})) {v}=1.0f; else if({inp(i)}<=({lo})) {v}=0.0f;')
        elif typ == 'greater':
            loop.append(f'  {v}=({inp(i)}>{number(n,"threshold",50)})?1.0f:0.0f;')
        elif typ == 'not':
            loop.append(f'  {v}=({inp(i)}>=0.5f)?0.0f:1.0f;')
        elif typ in ('and','or'):
            op='&&' if typ=='and' else '||'
            loop.append(f'  {v}=(({inp(i,0)}>=0.5f){op}({inp(i,1)}>=0.5f))?1.0f:0.0f;')
        elif typ == 'pwm':
            gp=pin(n,'gpio',22)
            if gp in (34,35,36,39) and device.get('profile') not in S3_PROFILES:
                raise ValueError('Blok PWM: GPIO34–39 w ESP32 są tylko wejściami.')
            if p.get('screen') and gp==p.get('bl'):
                raise ValueError('PWM na pinie LCD: użyj bloczka Jasność LCD zamiast GPIO PWM.')
            hz=checked_int((n.get('props') or {}).get('hz',1000), 'pwm.hz')
            if not 1<=hz<=40000:raise ValueError('PWM: częstotliwość 1–40000 Hz.')
            if pwm_count>=6:raise ValueError('W tej wersji maksymalnie 6 niezależnych wyjść PWM.')
            channel=8+pwm_count;pwm_count+=1
            setup.extend([f'#if ESP_ARDUINO_VERSION_MAJOR >= 3',
                          f'  ledcAttach({gp},{hz},8);', '#else',
                          f'  ledcSetup({channel},{hz},8);',
                          f'  ledcAttachPin({gp},{channel});', '#endif'])
            loop.extend([f'  {v}=constrain({inp(i)},0.0f,100.0f);',
                         '#if ESP_ARDUINO_VERSION_MAJOR >= 3',
                         f'  ledcWrite({gp},(uint32_t)({v}*255.0f/100.0f));', '#else',
                         f'  ledcWrite({channel},(uint32_t)({v}*255.0f/100.0f));', '#endif'])
        elif typ == 'gpioout':
            gp=pin(n,'gpio',22)
            if gp in (34,35,36,39) and device.get('profile') not in S3_PROFILES:
                raise ValueError('GPIO OUT: GPIO34–39 w ESP32 są tylko wejściami.')
            setup.append(f'  pinMode({gp},OUTPUT);')
            loop.extend([f'  {v}=({inp(i)}>=0.5f)?1.0f:0.0f;',
                         f'  digitalWrite({gp},{v}>=0.5f?HIGH:LOW);'])
        elif typ == 'brightness':
            if not p.get('screen'):
                raise ValueError('Bloczek Jasność LCD wymaga urządzenia z wyświetlaczem.')
            loop.extend([f'  {v}=constrain({inp(i)},0.0f,100.0f);',
                         f'  if(!backlightDimmed)setBacklight((uint8_t){v});'])
        elif typ in ('negate','square','sign','log','exp','tan','radians','degrees'):
            a=inp(i)
            expr={
              'negate':f'-({a})','square':f'({a})*({a})',
              'sign':f'(({a})>0.0f?1.0f:(({a})<0.0f?-1.0f:0.0f))',
              'log':f'logf(fmaxf(0.000001f,{a}))',
              'exp':f'expf(constrain({a},-80.0f,80.0f))',
              'tan':f'tanf({a})',
              'radians':f'({a})*0.01745329252f',
              'degrees':f'({a})*57.295779513f'
            }[typ]
            loop.append(f'  {v}={expr};')
        elif typ in ('average','lerp'):
            a=inp(i,0);b=inp(i,1)
            loop.append(f'  {v}='+ (f'({a}+{b})*0.5f;' if typ=='average' else f'{a}+({b}-{a})*constrain({inp(i,2)},0.0f,1.0f);'))
        elif typ=='quantize':
            step=number(n,'step',0.1,0.000001,100000)
            loop.append(f'  {v}=roundf({inp(i)}/({step}))*({step});')
        elif typ=='deadband':
            center=number(n,'center',0);width=number(n,'width',0.1,0,100000)
            loop.append(f'  {v}=(fabsf({inp(i)}-({center}))<=({width}))?({center}):({inp(i)});')
        elif typ=='select':
            loop.append(f'  {v}=({inp(i,0)}>=0.5f)?{inp(i,2)}:{inp(i,1)};')
        elif typ in ('greater2','gte','lte','neq'):
            a,b=inp(i,0),inp(i,1)
            expr={'greater2':f'{a}>{b}','gte':f'{a}>={b}','lte':f'{a}<={b}',
                  'neq':f'fabsf({a}-{b})>{number(n,"tolerance",0.001,0,1000000)}'}[typ]
            loop.append(f'  {v}=({expr})?1.0f:0.0f;')
        elif typ in ('edge_rise','edge_fall','toggle','counter'):
            decl.append(f'static bool lastEdge{i}=false;')
            decl.append(f'static float storedValue{i}=0.0f;')
            if typ=='counter':
                loop.extend([f'  bool inputNow{i}=({inp(i,0)}>=0.5f);',
                             f'  if({inp(i,1)}>=0.5f)storedValue{i}=0.0f;',
                             f'  else if(inputNow{i}&&!lastEdge{i})storedValue{i}+=1.0f;',
                             f'  {v}=storedValue{i};lastEdge{i}=inputNow{i};'])
            else:
                loop.append(f'  bool inputNow{i}=({inp(i)}>=0.5f);')
                if typ=='toggle':
                    loop.append(f'  if(inputNow{i}&&!lastEdge{i})storedValue{i}=1.0f-storedValue{i};{v}=storedValue{i};')
                elif typ=='edge_rise':
                    loop.append(f'  {v}=(inputNow{i}&&!lastEdge{i})?1.0f:0.0f;')
                else:loop.append(f'  {v}=(!inputNow{i}&&lastEdge{i})?1.0f:0.0f;')
                loop.append(f'  lastEdge{i}=inputNow{i};')
        elif typ=='debounce':
            ms=checked_int((n.get('props') or {}).get('ms',60), 'debounce.ms')
            if ms<0 or ms>60000:raise ValueError('Debounce 0–60000 ms.')
            decl.extend([f'static bool rawPrev{i}=false;',f'static uint32_t rawChanged{i}=0;'])
            loop.extend([f'  bool rawNow{i}=({inp(i)}>=0.5f);',
                         f'  if(rawNow{i}!=rawPrev{i}){{rawPrev{i}=rawNow{i};rawChanged{i}=millis();}}',
                         f'  if((uint32_t)(millis()-rawChanged{i})>={ms}UL){v}=rawNow{i}?1.0f:0.0f;'])
        elif typ in ('integrate','derivative'):
            decl.extend([f'static float lastInput{i}=0.0f;',f'static uint32_t previousTime{i}=0;'])
            loop.append(f'  float dt{i}=previousTime{i}?constrain((millis()-previousTime{i})*0.001f,0.0f,1.0f):0.0f;')
            if typ=='integrate':
                gain=number(n,'gain',1,0,1000000)
                loop.append(f'  {v}+=({inp(i)})*dt{i}*({gain});')
            else:
                loop.append(f'  {v}=(dt{i}>0.0f)?({inp(i)}-lastInput{i})/dt{i}:0.0f;')
            loop.extend([f'  previousTime{i}=millis();',f'  lastInput{i}={inp(i)};'])
        elif typ in ('pulse','saw','triangle'):
            period=checked_int((n.get('props') or {}).get('period',2000), 'wave.period')
            if not 1<=period<=3600000:raise ValueError('Wave generator period 1–3600000 ms.')
            if typ=='pulse':
                duty=number(n,'duty',25,0,100)
                loop.append(f'  {v}=((millis()%{period}UL)<({period}UL*({duty})/100.0f))?1.0f:0.0f;')
            elif typ=='saw':loop.append(f'  {v}=100.0f*(millis()%{period}UL)/{period}.0f;')
            else:loop.append(f'  {v}=100.0f*(1.0f-fabsf(2.0f*(millis()%{period}UL)/{period}.0f-1.0f));')
        elif typ=='canrx':
            byte=checked_int((n.get('props') or {}).get('byte',0), 'can.byte')
            if not 0<=byte<=7:raise ValueError('CAN data byte must be 0–7.')
            loop.append(f'  {v}=cydCANAvailable?((float)cydCANData[{byte}]):0.0f;')
        elif typ=='cc1101rssi':
            loop.append(f'  {v}=cydRFReady?cydRFLatest:-130.0f;')
        elif typ=='rfbin':
            loop.append(f'  {v}=cydRFReady?cydRFBins[constrain((int)({inp(i)}),0,63)]:-130.0f;')
        elif typ=='fftpeak':
            loop.append(f'  {v}=cydFFTPeakHz;')
        elif typ=='fftbin':
            loop.append(f'  {v}=cydFFTBins[constrain((int)({inp(i)}),0,31)];')
        elif typ in ('serial','scope'):
            name=clean_text((n.get('props') or {}).get('name','SCOPE' if typ=='scope' else 'SYGNAL'),24)
            period=checked_int((n.get('props') or {}).get('ms',200), 'serial.ms')
            if not 20<=period<=60000:raise ValueError('Serial/Oscyloskop: odświeżanie 20–60000 ms.')
            decl.append(f'static uint32_t logicPrintLast{i}=0;')
            loop.extend([f'  {v}={inp(i)};',
                         f'  if((uint32_t)(millis()-logicPrintLast{i})>={period}UL){{',
                         f'    logicPrintLast{i}=millis();',
                         f'    Serial.print({cstr(name,24)});Serial.print("=");Serial.println({v},3);',
                         '  }'])
    # Lightweight runtime probe: all node outputs, round-robin, no blocking delay().
    # Packets are tagged by stable block ID so a changed graph cannot silently relabel values.
    trace = [
        'static bool debugTraceEnabled=true;',
        'static uint16_t debugTraceRateMs=100;',
        'static uint32_t debugTraceLast=0;',
        'static uint16_t debugTraceCursor=0;',
        'static int16_t debugTraceFocus=-1;',
        'static char debugCommand[48];',
        'static uint8_t debugCommandLen=0;',
        'void emitDebugTrace(uint16_t idx){',
        '  switch(idx){',
    ]
    for i,n in enumerate(nodes):
        ident=cstr(n['id'],100)
        trace += [f'    case {i}: Serial.print("@DBG|");Serial.print({ident});Serial.print("|");Serial.println(logicValue{i},4);break;']
    trace += [
        '    default:break;',
        '  }',
        '}',
        'void pollDebugCommands(){',
        '  uint8_t processed=0;',
        '  while(Serial.available() && processed++<48){',
        '    const char c=(char)Serial.read();',
        '    if(c==\'\\n\' || c==\'\\r\'){',
        '      debugCommand[debugCommandLen]=0;',
        '      if(strcmp(debugCommand,"@DBG ON")==0)debugTraceEnabled=true;',
        '      else if(strcmp(debugCommand,"@DBG OFF")==0)debugTraceEnabled=false;',
        '      else if(strcmp(debugCommand,"@DBG ALL")==0)debugTraceFocus=-1;',
        '      else if(strncmp(debugCommand,"@DBG RATE ",10)==0){',
        '        long r=atol(debugCommand+10);if(r>=50 && r<=5000)debugTraceRateMs=(uint16_t)r;',
        '      }else if(strncmp(debugCommand,"@DBG FOCUS ",11)==0){',
        f'        long i=atol(debugCommand+11);if(i>=0 && i<{len(nodes)})debugTraceFocus=(int16_t)i;',
        '      }',
        '      debugCommandLen=0;',
        '    }else if(debugCommandLen<sizeof(debugCommand)-1 && c>=32 && c<=126){',
        '      debugCommand[debugCommandLen++]=c;',
        '    }else{debugCommandLen=0;}',
        '  }',
        '}',
        'void pollDebugTrace(){',
        '  if(!debugTraceEnabled || (uint32_t)(millis()-debugTraceLast)<debugTraceRateMs)return;',
        '  debugTraceLast=millis();',
        '  if(debugTraceFocus>=0){emitDebugTrace((uint16_t)debugTraceFocus);return;}',
        '  // At most six tagged samples per interval: safe at 115200 baud for typical graphs.',
        '  for(uint8_t k=0;k<6 && k<'+str(len(nodes))+';k++){',
        '    emitDebugTrace(debugTraceCursor);',
        '    if(++debugTraceCursor>='+str(len(nodes))+')debugTraceCursor=0;',
        '  }',
        '}',
    ]
    decl.extend(trace)
    loop.append('  pollDebugTrace();')
    loop.append('}')
    return '\n'.join(decl)+'\n'+'\n'.join(loop)+'\n', '\n'.join(setup)+'\n', '  pollDebugCommands();\n  pollLogic();\n' 

def generate_instrument_hardware(device,p):
    # Return extra includes, globals, setup, loop and PlatformIO dependencies.
    # RF is RSSI-tuned scanning. FFT is audio analogue samples.
    nodes=(device.get('logic') or {}).get('nodes',[])
    radio=[n for n in nodes if n.get('type')=='cc1101rssi']
    fft=[n for n in nodes if n.get('type')=='fftpeak']
    can=[n for n in nodes if n.get('type')=='canrx']
    if (any(n.get('type')=='rfbin' for n in nodes) or any(w.get('type')=='waterfall' and w.get('waterfallMode','rf')!='adc_fft' for sc in device.get('scenes',[]) for w in sc.get('widgets',[]))) and not radio:
        raise ValueError('Waterfall CC1101: dodaj w Block Logic bloczek Radio / CC1101 -> CC1101 RSSI scanner. Dla waterfall z ADC wybierz ADC FFT oraz dodaj FFT peak ADC.')
    # FFT display widgets work without manually creating a hidden source block.
    # On CYD 2.8 R/2.4, GPIO35 (ADC1) is the default analogue source.
    # This creates a source only in generated firmware, never in the user's saved graph.
    fft_needed=(any(n.get('type')=='fftbin' for n in nodes) or
                any(w.get('type')=='spectrum' or
                    (w.get('type')=='waterfall' and w.get('waterfallMode')=='adc_fft')
                    for sc in device.get('scenes',[]) for w in sc.get('widgets',[])))
    fft_auto=False
    if fft_needed and not fft:
        pin=(device.get('pins') or {}).get('fft_adc',4 if device.get('profile') in S3_PROFILES else 35)
        try: pin=checked_int(pin,'FFT auto ADC GPIO')
        except (TypeError,ValueError):raise ValueError('FFT ADC: nieprawidłowy GPIO.')
        # Full GPIO/ADC1 validation still happens below, as for a manual FFT block.
        fft=[{'id':'cyd_auto_fft','type':'fftpeak','props':{'gpio':pin,'sampleHz':4000}}]
        fft_auto=True
    if max(len(radio),len(fft),len(can))>1:
        raise ValueError('Only one CC1101, FFT and CAN RX hardware source per device in this version.')
    includes=[];decl=[];setup=[];loop=[];libs=[]
    def gp(node,key,default):
        try:v=checked_int((node.get('props') or {}).get(key,default), key)
        except (TypeError,ValueError):raise ValueError('GPIO must be an integer: '+key)
        if v<0 or v>(48 if device.get('profile') in S3_PROFILES else 39):raise ValueError('GPIO out of range: '+key)
        return v
    busy=set()
    if p.get('screen'):
        if p.get('m5display'):
            reserved={
              'atoms3':{21,17,15,33,34,16,38,39},
              'cores3':{37,36,3,35,11,12},
              'core2':{21,22,23,18,5,14,15},
              'm5basic':{23,19,18,14,27,33,32},
              'stickcplus2':{15,13,14,12,5,27,21,22,4},
            }
            busy=reserved.get(device.get('profile'),set())
        else:
            busy={2,12,13,14,15,p['bl']}
            if p.get('touch'):busy.update(p['touchpins'])
    if radio:
        n=radio[0];props=n.get('props') or {}
        shared_touch=device.get('profile') in ('cyd28','cyd28usb')
        default_sck,default_miso,default_mosi=(p['touchpins'][0],p['touchpins'][1],p['touchpins'][2]) if shared_touch else (18,19,23)
        cs=gp(n,'cs',22);gdo=gp(n,'gdo0',27)
        sck=gp(n,'sck',default_sck);miso=gp(n,'miso',default_miso);mosi=gp(n,'mosi',default_mosi)
        if len({cs,gdo,sck,miso,mosi})!=5 or cs in busy or gdo in busy:
            raise ValueError('CC1101: CS/GDO0 must be distinct and free (not touch/display pins).')
        if shared_touch:
            if (sck,miso,mosi)!=(default_sck,default_miso,default_mosi):
                raise ValueError('CYD 2.8 CC1101: share XPT2046 HSPI pins SCK25/MISO39/MOSI32; use separate CS. ESP32 has no third SPI controller.')
        elif any(x in busy for x in (sck,miso,mosi)):
            raise ValueError('CC1101: SPI pins conflict with LCD/touch; choose free pins.')
        start=checked_float(props.get('from',433.3),'rf.from');end=checked_float(props.get('to',434.5),'rf.to')
        if not math.isfinite(start) or not math.isfinite(end) or start>=end or not any(lo<=start<end<=hi for lo,hi in ((300,348),(387,464),(779,928))):
            raise ValueError('CC1101: frequency span must fit a supported single RF band.')
        bins=checked_int(props.get('bins',48),'rf.bins');settle=checked_int(props.get('settle',8),'rf.settle')
        if not 16<=bins<=64 or not 5<=settle<=500:raise ValueError('CC1101: bins 16–64, settle 5–500 ms.')
        includes+=['#include <RadioLib.h>','#include <SPI.h>']
        libs+=['jgromes/RadioLib @ 7.8.1']
        bus=('extern SPIClass touchBus;\nstatic SPIClass& cydRFBus=touchBus;' if shared_touch else 'static SPIClass cydRFBus(HSPI);')
        bus_start='' if shared_touch else f'cydRFBus.begin({sck},{miso},{mosi},{cs});'
        decl.append(f'''// CC1101 is a tunable narrow-band RSSI scanner, not an RF/IQ FFT analyser.
// RadioLib direct receive reads current channel RSSI. One step per dwell time.
// FreeRTOS scans on a separate task: LVGL never waits for the radio.
static const int CYD_RF_BINS={bins};
static const float CYD_RF_START={start:.6f}f,CYD_RF_END={end:.6f}f;
static const uint32_t CYD_RF_SETTLE={settle}UL;
static float cydRFBins[64]={{}};
static float cydRFWf[24][64]={{}};
static uint8_t cydRFRow=0,cydRFCompletedRows=0,cydRFCursor=0;
static volatile uint32_t cydRFRevision=0;
static float cydRFLatest=-130.0f;
static bool cydRFReady=false;
static uint32_t cydRFLastTune=0;
static TaskHandle_t cydRFTaskHandle=nullptr;
{bus}
static CC1101 cydRadio=new Module({cs},{gdo},RADIOLIB_NC,RADIOLIB_NC,cydRFBus,SPISettings(2000000,MSBFIRST,SPI_MODE0));
void pollCydRF(){{
  if(!cydRFReady || (uint32_t)(millis()-cydRFLastTune)<CYD_RF_SETTLE)return;
  float level=cydRadio.getRSSI();
  if(!isfinite(level))level=-130.0f;
  level=constrain(level,-130.0f,-20.0f);
  cydRFLatest=level;
  cydRFBins[cydRFCursor]=level;
  cydRFWf[cydRFRow][cydRFCursor]=level;
  if(++cydRFCursor>=CYD_RF_BINS){{
    cydRFCursor=0;
    cydRFRow=(cydRFRow+1)%24;
    if(cydRFCompletedRows<24)cydRFCompletedRows++;
    // Publish complete sweeps only; do not invalidate canvas for individual bins.
    cydRFRevision++;
  }}
  const float MHz=CYD_RF_START+(CYD_RF_END-CYD_RF_START)*(float)cydRFCursor/(float)(CYD_RF_BINS-1);
  cydRFReady=(cydRadio.setFrequency(MHz)==RADIOLIB_ERR_NONE);
  if(cydRFReady)cydRFReady=(cydRadio.receiveDirectAsync()==RADIOLIB_ERR_NONE);
  cydRFLastTune=millis();
}}
static void cydRFWorker(void*){{
  while(true){{pollCydRF();vTaskDelay(1);}}
}}
void initCydRF(){{
  {bus_start}
  cydRFReady=(cydRadio.begin()==RADIOLIB_ERR_NONE);
  if(cydRFReady){{
    cydRFReady=(cydRadio.setFrequency(CYD_RF_START)==RADIOLIB_ERR_NONE);
    if(cydRFReady)cydRFReady=(cydRadio.receiveDirectAsync()==RADIOLIB_ERR_NONE);
  }}
  cydRFLastTune=millis();
  if(cydRFReady){{
    BaseType_t ok=xTaskCreatePinnedToCore(cydRFWorker,"cyd_cc1101",3072,nullptr,1,&cydRFTaskHandle,0);
    if(ok!=pdPASS)cydRFTaskHandle=nullptr; // fallback to cooperative polling
  }}
  Serial.println(cydRFReady?(cydRFTaskHandle?"CC1101: async RSSI online":"CC1101: polling fallback"):
                 "CC1101: offline, check SPI CS, 3.3V and wiring");
}}
''')
        if p.get('screen'):
            decl.append('''void drawCydRF(int x,int y,int w,int h){
  // Legacy TFT direct drawing path is unused for LVGL displays.
  (void)x;(void)y;(void)w;(void)h;
}
''')
        setup.append('  initCydRF();')
        loop.append('  if(!cydRFTaskHandle)pollCydRF();')
    if can:
        n=can[0];rx=gp(n,'rx',27);tx=gp(n,'tx',22)
        speed=checked_int((n.get('props') or {}).get('bitrate',500),'can.bitrate')
        if speed not in (125,250,500,1000):raise ValueError('TWAI bitrates supported: 125, 250, 500, 1000 kbps.')
        if rx==tx or rx in busy or tx in busy or (device.get('profile') not in S3_PROFILES and tx in (34,35,36,39)):
            raise ValueError('CAN RX/TX GPIO conflicts with display/touch/backlight or input-only pins.')
        if radio and ({rx,tx}&{cs,gdo,sck,miso,mosi}):raise ValueError('CAN and CC1101 have overlapping pins.')
        includes.append('#include <driver/twai.h>')
        decl.append(f'''// CAN passive monitor: external 3.3 V CAN transceiver REQUIRED.
static bool cydCANReady=false,cydCANAvailable=false;
static uint8_t cydCANData[8]={{}};
static uint32_t cydCANID=0;
void initCydCAN(){{
 twai_general_config_t general=TWAI_GENERAL_CONFIG_DEFAULT((gpio_num_t){tx},(gpio_num_t){rx},TWAI_MODE_LISTEN_ONLY);
 twai_timing_config_t timing=TWAI_TIMING_CONFIG_{"1M" if speed==1000 else str(speed)+"K"}BITS();
 twai_filter_config_t filter=TWAI_FILTER_CONFIG_ACCEPT_ALL();
 cydCANReady=(twai_driver_install(&general,&timing,&filter)==ESP_OK);
 if(cydCANReady)cydCANReady=(twai_start()==ESP_OK);
 Serial.println(cydCANReady?"CAN RX: listen-only":"CAN RX: failed, check transceiver/pins");
}}
void pollCydCAN(){{
 if(!cydCANReady)return;
 twai_message_t msg;
 for(uint8_t k=0;k<5 && twai_receive(&msg,0)==ESP_OK;k++){{
  if(msg.rtr)continue;
  cydCANID=msg.identifier;
  for(uint8_t i=0;i<8;i++)cydCANData[i]=(i<msg.data_length_code)?msg.data[i]:0;
  cydCANAvailable=true;
 }}
}}
''')
        setup.append('  initCydCAN();')
        loop.append('  pollCydCAN();')
    if fft:
        n=fft[0];gpio=gp(n,'gpio',35);rate=checked_int((n.get('props') or {}).get('sampleHz',4000),'fft.sampleHz')
        if fft_auto:
            decl.append('// CYD_AUTO_FFT: FFT widget automatically uses ADC1 GPIO%d at %d Hz.' % (gpio,rate))
            setup.append('  Serial.println("[FFT] AUTO: ADC GPIO%d, %d Hz; change pins.fft_adc to select input");' % (gpio,rate))
        adc1=range(1,11) if device.get('profile') in S3_PROFILES else (32,33,34,35,36,39)
        if gpio not in adc1:raise ValueError('FFT requires ADC1 input (GPIO32–39 on ESP32 or GPIO1–10 on S3).')
        if not 1000<=rate<=16000:raise ValueError('FFT sample rate must be 1000–16000 Hz.')
        decl.append(f'''// 64 point FFT of ADC audio samples, not RF RSSI. Acquisition runs off the GUI loop.
static const int CYD_FFT_GPIO={gpio};
static const uint32_t CYD_FFT_RATE={rate}UL;
static const uint32_t CYD_FFT_STEP_US=1000000UL/CYD_FFT_RATE;
static float cydFFTBins[32]={{}};
static float cydFFTPeakHz=0.0f;
static volatile uint32_t cydFFTRevision=0;
static float cydFFTRe[64]={{}},cydFFTIm[64]={{}};
static uint8_t cydFFTIndex=0;
static uint32_t cydFFTNext=0;
static TaskHandle_t cydFFTTaskHandle=nullptr;
void runCydFFT(){{
 const float PI2=6.28318530718f;
 float avg=0.0f;
 for(int i=0;i<64;i++)avg+=cydFFTRe[i];
 avg*=1.0f/64.0f; // suppress DC offset before Hann window
 for(int i=0;i<64;i++){{
  float taper=0.5f*(1.0f-cosf(PI2*i/63.0f));
  cydFFTRe[i]=(cydFFTRe[i]-avg)*taper;cydFFTIm[i]=0.0f;
 }}
 for(int i=1,j=0;i<64;i++){{
  int bit=32;for(;j&bit;bit>>=1)j^=bit;j^=bit;
  if(i<j){{float t=cydFFTRe[i];cydFFTRe[i]=cydFFTRe[j];cydFFTRe[j]=t;}}
 }}
 for(int len=2;len<=64;len<<=1){{
  const float angle=-PI2/len;
  for(int i=0;i<64;i+=len)for(int j=0;j<len/2;j++){{
    int a=i+j,b=a+len/2;float theta=angle*j;
    float cr=cosf(theta),sr=sinf(theta);
    float tr=cr*cydFFTRe[b]-sr*cydFFTIm[b],ti=cr*cydFFTIm[b]+sr*cydFFTRe[b];
    float ar=cydFFTRe[a],ai=cydFFTIm[a];
    cydFFTRe[a]=ar+tr;cydFFTIm[a]=ai+ti;
    cydFFTRe[b]=ar-tr;cydFFTIm[b]=ai-ti;
  }}
 }}
 float best=0.0f;int peak=0;
 for(int i=0;i<32;i++){{
  float v=sqrtf(cydFFTRe[i]*cydFFTRe[i]+cydFFTIm[i]*cydFFTIm[i])/32.0f;
  // Slight smoothing across successive FFTs to limit flashing bars.
  cydFFTBins[i]=0.28f*v+0.72f*cydFFTBins[i];
  if(i>1&&cydFFTBins[i]>best){{best=cydFFTBins[i];peak=i;}}
 }}
 cydFFTPeakHz=(float)peak*CYD_FFT_RATE/64.0f;
 cydFFTRevision++;
}}
void pollCydFFT(){{
  uint32_t now=micros();
  if((int32_t)(now-cydFFTNext)<0)return;
  if((uint32_t)(now-cydFFTNext)>CYD_FFT_STEP_US*2)cydFFTNext=now;
  cydFFTNext+=CYD_FFT_STEP_US;
  cydFFTRe[cydFFTIndex++]=(float)analogRead(CYD_FFT_GPIO);
  if(cydFFTIndex>=64){{cydFFTIndex=0;runCydFFT();}}
}}
static void cydFFTWorker(void*){{
  cydFFTNext=micros();
  while(true){{
    uint32_t now=micros();
    int32_t until=(int32_t)(cydFFTNext-now);
    if(until<=0){{pollCydFFT();continue;}}
    // Small cooperatively scheduled waits; avoid delaying 1ms per sample.
    if(until>700){{vTaskDelay(1);}}
    else if(until>180){{delayMicroseconds((uint32_t)until-100);}}
    else {{taskYIELD();}}
  }}
}}
void initCydFFT(){{
  analogReadResolution(12);
  analogSetPinAttenuation(CYD_FFT_GPIO,ADC_11db);
  cydFFTNext=micros();
  if(xTaskCreatePinnedToCore(cydFFTWorker,"cyd_fft",4096,nullptr,2,&cydFFTTaskHandle,1)!=pdPASS)
    cydFFTTaskHandle=nullptr;
}}
''')
        if p.get('screen'):
            decl.append("void drawCydSpectrum(int,int,int,int){}\n")
        setup.append('  initCydFFT();')
        loop.append('  if(!cydFFTTaskHandle)pollCydFFT();')
    return includes,'\n'.join(decl), '\n'.join(setup), '\n'.join(loop),libs


TOUCH_CAL_CODE = r'''
// 5-point affine calibration for XPT2046; independent from the old X/Y mirror flags.
// Dedicated, independent NVS partition labelled "touchcal" in partitions_cyd.csv.
// Never store touch calibration in the default WiFi/application NVS partition.
static const uint32_t CYD_CAL_MAGIC=0x35445943UL;  // "CYD5"
static const uint16_t CYD_CAL_VERSION=1;
struct CydTouchCalibration {
  uint32_t magic;
  uint16_t version, rotation;
  uint16_t width, height;
  float x[3], y[3]; // logicalX = x0*rawX+x1*rawY+x2, same for logicalY
  uint32_t crc;
};
static CydTouchCalibration cydCal={};
static bool cydCalValid=false;
static uint32_t cydCalCRC(const uint8_t *buffer,size_t len){
  uint32_t crc=0xFFFFFFFFUL;
  for(size_t k=0;k<len;k++){
    crc^=buffer[k];
    for(int j=0;j<8;j++)crc=(crc>>1)^((crc&1)?0xEDB88320UL:0UL);
  }
  return ~crc;
}
static uint32_t cydCalCheck(const CydTouchCalibration& c){
  return cydCalCRC(reinterpret_cast<const uint8_t*>(&c),offsetof(CydTouchCalibration,crc));
}
static bool cydLoadCalibration(){
  Preferences prefs;
  if(!prefs.begin("touch5",true,"touchcal"))return false;
  bool ok=prefs.getBytesLength("affine")==sizeof(cydCal)
       && prefs.getBytes("affine",&cydCal,sizeof(cydCal))==sizeof(cydCal);
  prefs.end();
  if(!ok)return false;
  if(cydCal.magic!=CYD_CAL_MAGIC || cydCal.version!=CYD_CAL_VERSION
      || cydCal.rotation!=SCREEN_ROTATION || cydCal.width!=tft.width()
      || cydCal.height!=tft.height() || cydCal.crc!=cydCalCheck(cydCal))return false;
  for(int i=0;i<3;i++)if(!isfinite(cydCal.x[i])||!isfinite(cydCal.y[i]))return false;
  return true;
}
static bool cydSaveCalibration(){
  cydCal.crc=cydCalCheck(cydCal);
  Preferences prefs;
  // The custom NVS partition must be present; no fallback to the default NVS.
  if(!prefs.begin("touch5",false,"touchcal")){
    Serial.println("[TOUCH] ERROR: custom NVS partition touchcal missing");
    return false;
  }
  bool ok=prefs.putBytes("affine",&cydCal,sizeof(cydCal))==sizeof(cydCal);
  prefs.end();
  Serial.println(ok?"[TOUCH] 5-point calibration saved to touchcal":"[TOUCH] failed to save calibration");
  return ok;
}
static bool cydSolve3(float a[3][4],float out[3]){
  for(int i=0;i<3;i++){
    int pivot=i;
    for(int j=i+1;j<3;j++)if(fabsf(a[j][i])>fabsf(a[pivot][i]))pivot=j;
    if(fabsf(a[pivot][i])<0.0000001f)return false;
    if(pivot!=i)for(int k=0;k<4;k++){float t=a[i][k];a[i][k]=a[pivot][k];a[pivot][k]=t;}
    float scale=a[i][i];for(int k=i;k<4;k++)a[i][k]/=scale;
    for(int j=0;j<3;j++)if(j!=i){float f=a[j][i];for(int k=i;k<4;k++)a[j][k]-=f*a[i][k];}
  }
  for(int i=0;i<3;i++)out[i]=a[i][3];
  return true;
}
static bool cydFit5(const float rx[5],const float ry[5],const int sx[5],const int sy[5]){
  float A[3][4]={{0}},B[3][4]={{0}};
  for(int i=0;i<5;i++){
    float row[3]={rx[i],ry[i],1.0f};
    for(int c=0;c<3;c++){
      for(int d=0;d<3;d++){A[c][d]+=row[c]*row[d];B[c][d]+=row[c]*row[d];}
      A[c][3]+=row[c]*(float)sx[i];B[c][3]+=row[c]*(float)sy[i];
    }
  }
  if(!cydSolve3(A,cydCal.x)||!cydSolve3(B,cydCal.y))return false;
  for(int i=0;i<5;i++){
    float x=cydCal.x[0]*rx[i]+cydCal.x[1]*ry[i]+cydCal.x[2];
    float y=cydCal.y[0]*rx[i]+cydCal.y[1]*ry[i]+cydCal.y[2];
    float error=hypotf(x-(float)sx[i],y-(float)sy[i]);
    if(!isfinite(error)||error>18.0f)return false;
  }
  return true;
}
static void cydCalibrationTarget(int idx,int x,int y){
  const int w=tft.width(),h=tft.height();
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE,TFT_BLACK);
  tft.setTextSize(1);
  tft.drawCentreString("KALIBRACJA DOTYKU",w/2,max(0,h/2-75),2);
  tft.drawCentreString("Dotknij i pusc celownik",w/2,max(0,h/2-50),2);
  char label[24];snprintf(label,sizeof(label),"PUNKT %d / 5",idx+1);
  tft.drawCentreString(label,w/2,max(0,h/2-25),2);
  const uint16_t c=TFT_CYAN;
  tft.drawCircle(x,y,11,c); tft.drawCircle(x,y,3,c);
  tft.drawLine(x-16,y,x+16,y,c);tft.drawLine(x,y-16,x,y+16,c);
}
static bool cydReadTap(float &ox,float &oy,uint32_t timeoutMs){
  uint32_t start=millis();
  while(touch.touched() && millis()-start<timeoutMs)delay(15); // wait for finger release
  delay(80);
  float xs=0,ys=0;int count=0;
  while(millis()-start<timeoutMs){
    if(touch.touched()){
      TS_Point raw=touch.getPoint();
      if(raw.x>=0 && raw.x<=4095 && raw.y>=0 && raw.y<=4095){
        xs+=(float)raw.x;ys+=(float)raw.y;count++;
      }
      delay(18);
    }else if(count>=5){
      ox=xs/count;oy=ys/count;return true;
    }else{count=0;xs=0;ys=0;delay(12);}
  }
  return false;
}
static bool cydRun5PointCalibration(){
  const int w=tft.width(),h=tft.height();
  const int mx=min(26,max(15,w/8)),my=min(26,max(15,h/8));
  const int sx[5]={mx,w-1-mx,w-1-mx,mx,w/2};
  const int sy[5]={my,my,h-1-my,h-1-my,h/2};
  float rx[5]={},ry[5]={};
  for(int i=0;i<5;i++){
    cydCalibrationTarget(i,sx[i],sy[i]);
    if(!cydReadTap(rx[i],ry[i],30000UL))return false;
  }
  cydCal.magic=CYD_CAL_MAGIC;
  cydCal.version=CYD_CAL_VERSION;
  cydCal.rotation=SCREEN_ROTATION;
  cydCal.width=w;cydCal.height=h;
  if(!cydFit5(rx,ry,sx,sy)){
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_RED,TFT_BLACK);
    tft.drawCentreString("BLAD KALIBRACJI",w/2,h/2-8,2);
    delay(1100);
    return false;
  }
  if(!cydSaveCalibration()){
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_RED,TFT_BLACK);
    tft.drawCentreString("BRAK PARTYCJI touchcal",w/2,h/2-8,2);
    delay(1500);
    return false;
  }
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_GREEN,TFT_BLACK);
  tft.drawCentreString("KALIBRACJA ZAPISANA",w/2,h/2,2);
  delay(550);
  return true;
}
static void cydInitializeTouchCalibration(){
#ifdef CYD_SIMULATOR
  cydCalValid=true;
  Serial.println("[SIM] calibration bypassed (XPT2046 not present)");
  return;
#endif

  // A standalone firmware.bin cannot install a changed partition table.
  if(!esp_partition_find_first(ESP_PARTITION_TYPE_DATA,ESP_PARTITION_SUBTYPE_DATA_NVS,"touchcal")){
    Serial.println("[TOUCH] Missing touchcal partition: flash via PlatformIO USB Upload with partitions_cyd.csv");
    tft.fillScreen(TFT_BLACK);tft.setTextColor(TFT_RED,TFT_BLACK);
    tft.drawCentreString("BRAK PARTYCJI touchcal",tft.width()/2,tft.height()/2-12,2);
    tft.drawCentreString("FLASH VIA USB / PIO",tft.width()/2,tft.height()/2+15,2);
    while(true)delay(1000);
  }
  // Touch-and-hold during BOOT (>2 seconds) to force manual recalibration.
  bool force=false;
  if(touch.touched()){
    uint32_t start=millis();
    while(touch.touched() && millis()-start<2300UL)delay(20);
    force=millis()-start>=2000UL;
  }
  cydCalValid=(!force && cydLoadCalibration());
  if(cydCalValid){Serial.println("[TOUCH] calibration loaded from touchcal");return;}
  Serial.println("[TOUCH] new 5-point calibration required");
  while(!cydCalValid){
    cydCalValid=cydRun5PointCalibration();
    if(!cydCalValid){
      Serial.println("[TOUCH] retrying calibration; check custom partition table");
      delay(450);
    }
  }
}
static void cydMapTouch(const TS_Point &raw,int &x,int &y){
  float fx=cydCal.x[0]*raw.x+cydCal.x[1]*raw.y+cydCal.x[2];
  float fy=cydCal.y[0]*raw.x+cydCal.y[1]*raw.y+cydCal.y[2];
  x=constrain((int)lroundf(fx),0,tft.width()-1);
  y=constrain((int)lroundf(fy),0,tft.height()-1);
}
'''

def generate_cpp(device, p):
    f=device.get('features') or {}
    pins=device.get('pins') or {}
    touch=device.get('touch') or {}
    mode=value(f.get('wifi_mode','off'))
    if mode not in ('off','ap','sta','ap_sta'):mode='off'
    wifi=mode!='off';rx=boolv(f,'audio_rx');tx=boolv(f,'audio_tx')
    if (rx or tx) and not wifi:raise ValueError('Audio Wi-Fi wymaga włączonego Wi-Fi STA/AP.')
    if rx and not p['screen']:raise ValueError('Odbiór audio DAC w tym generatorze działa na CYD/klasycznym ESP32.')
    if rx and device.get('profile') in S3_PROFILES:raise ValueError('ESP32-S3 nie ma wewnętrznego DAC; potrzebny zewnętrzny I2S.')
    if (boolv(f,'bt_classic') and device.get('profile') in S3_PROFILES):
        raise ValueError('ESP32-S3 nie obsługuje Bluetooth Classic. Wybierz BLE.')
    if device.get('profile')=='cyd24' and boolv(f,'gyro') and 27 in (get_number(pins,'i2c_sda',27,0,48),get_number(pins,'i2c_scl',22,0,48)):
        raise ValueError('CYD 2.4: GPIO27 zajmuje podświetlenie; zmień piny I2C, zanim włączysz żyroskop.')
    if device.get('profile') in ('cyd28','cyd28usb','cyd28t') and boolv(f,'gyro') and 21 in (get_number(pins,'i2c_sda',27,0,48),get_number(pins,'i2c_scl',22,0,48)):
        raise ValueError('CYD 2.8: GPIO21 zajmuje podświetlenie; zmień piny I2C.')
    if boolv(f,'bt_classic') and boolv(f,'ble'):
        raise ValueError('W tym generatorze wybierz BLE albo Bluetooth Classic, nie obydwa.')
    if tx and rx:raise ValueError('W tej wersji wybierz nadawanie albo odbiór dźwięku na urządzeniu.')
    cyd_click_beeps = device.get('profile')=='cyd28' and str(f.get('click_beeps', True)).lower() not in ('false','0','off','no')
    battery=boolv(f,'battery')
    if battery:
        adc=get_number(pins,'battery_adc',35,0,48)
        if device.get('profile') in S3_PROFILES:
            if adc not in range(1,11):raise ValueError('ESP32-S3 z Wi-Fi: do ADC baterii wybierz GPIO1–GPIO10 (ADC1).')
        elif adc not in (32,33,34,35,36,39):
            raise ValueError('ESP32 z Wi-Fi: do ADC baterii wybierz ADC1 (GPIO32,33,34,35,36,39).')
        try:divider=float(pins.get('battery_divider',2))
        except (TypeError,ValueError):divider=2
        if not 1.0<=divider<=25.0:raise ValueError('Mnożnik dzielnika musi mieścić się w 1–25.')
        try:
            b_min=float(f.get('battery_v_min',3.2))
            b_max=float(f.get('battery_v_max',4.2))
            smoothing=checked_int(f.get('battery_smooth',20),'battery.smooth')
        except (ValueError,TypeError):raise ValueError('Nieprawidłowe napięcie lub filtr mapowania baterii.')
        if not (0 <= b_min < b_max <= 120):raise ValueError('Zakres mapowania musi spełniać 0 ≤ minimum < maksimum ≤ 120 V.')
        if not 0<=smoothing<=95:raise ValueError('Wygładzanie musi mieścić się w zakresie 0–95%.')
    rotation=get_number(device,'rotation',0,0,3)
    if p.get('m5display'):
        native_w,native_h=p['size']
        screen_w,screen_h=(native_h,native_w) if rotation%2 else (native_w,native_h)
    else:
        screen_w,screen_h=((240,135) if rotation%2 else (135,240)) if p.get('cardputer_adv') else ((320,240) if rotation%2 else (240,320))
    if p['screen']:
        brightness=get_number(f,'backlight_brightness',85,0,100)
        timeout_s=get_number(f,'backlight_timeout_s',0 if p.get('cardputer_adv') else 60,0,86400)
        sleep_brightness=get_number(f,'backlight_dim',0,0,100)
        if timeout_s and not p['touch']:raise ValueError('Automatyczne wygaszanie wymaga obsługi dotyku do wybudzania. Na wariancie T ustaw czas 0 s.')

    if tx and boolv(f,'gyro') and (get_number(pins,'i2c_sda',27,0,48) in [get_number(pins,'mic_din',23,0,48),get_number(pins,'mic_bclk',19,0,48),get_number(pins,'mic_ws',22,0,48)] or get_number(pins,'i2c_scl',22,0,48) in [get_number(pins,'mic_din',23,0,48),get_number(pins,'mic_bclk',19,0,48),get_number(pins,'mic_ws',22,0,48)]):
        raise ValueError('Mikrofon i czujnik I2C używają tych samych pinów. Zmień piny.')
    extra_inc,extra_decl,extra_setup,extra_loop,extra_libs=generate_instrument_hardware(device,p)
    includes=['#include <Arduino.h>', '#include <esp_arduino_version.h>']
    if cyd_click_beeps:includes.append('#include <esp_system.h>')
    includes+=extra_inc
    if p['screen']:
        includes += (['#include <M5Unified.h>'] if p.get('m5display') else ['#include <TFT_eSPI.h>', '#include <SPI.h>'])
        if p['touch'] and not p.get('native_touch'): includes += ['#include <XPT2046_Touchscreen.h>', '#include <Preferences.h>', '#include <esp_partition.h>', '#include <stddef.h>']
    if device.get('profile') in ('coreink','stamplc'):includes+=['#include <M5Unified.h>']
    if wifi:includes+=['#include <WiFi.h>']
    if rx or tx:includes+=['#include <WiFiUdp.h>']
    if tx:includes+=['#include <driver/i2s.h>']
    if boolv(f,'gyro'):includes+=['#include <Wire.h>']
    if boolv(f,'bt_classic'):includes+=['#include <BluetoothSerial.h>']
    if boolv(f,'ble'):includes+=['#include <BLEDevice.h>']
    custom=device.get('custom') or {}
    github_libs=libraries_for_device(device)
    for lib in github_libs.values():
        for header in lib['headers']:
            include=f'#include <{header}>'
            if include not in includes:includes.append(include)
    includes += [str(custom.get('includes',''))[:6000]]
    code='\n'.join(includes)+'\n\n'
    code+='// Automatycznie wygenerowany projekt CYD Studio.\n'

    code+=f'// Screen orientation: rotation={rotation}  dimensions={screen_w}x{screen_h}\n'
    code+='static uint32_t lastRefresh=0;\n'
    if cyd_click_beeps and rx:code+='#define CYD_CLICK_PCM_MIX 1\n'
    if not p['screen'] and extra_decl:code+=extra_decl+'\n'
    if p['screen']:
        code+=('#define tft M5.Display\n' if p.get('m5display') else 'TFT_eSPI tft = TFT_eSPI();\n')
        code+=r'''void drawCydSensorIcon(int cx,int cy,int r,const char*name,uint16_t fg){
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
'''

        if extra_decl:code+=extra_decl+'\n'
        code+=f'static const int SCREEN_ROTATION={((rotation+3)%4) if p.get("m5display") and device.get("profile") in ("cores3","core2","m5basic") else rotation};\n'
        code+='uint16_t C565(uint32_t rgb){return tft.color565((rgb>>16)&255,(rgb>>8)&255,rgb&255);}\n'
        code+=f'static const int BACKLIGHT_PIN = {p.get("bl",-1)};\n'
        if p['touch'] and not p.get('native_touch'):
            sck,miso,mosi,cs,irq=p['touchpins']
            code+=(f'SPIClass touchBus(HSPI);\nXPT2046_Touchscreen touch({cs},{irq});\n' if device.get('profile') in ('cyd28','cyd28usb') else f'XPT2046_Touchscreen touch({cs},{irq});\n')
        code+='static int activeScene=0;\nstatic bool touchWasDown=false;\n'
        if p['touch'] and not p.get('native_touch'):code+=TOUCH_CAL_CODE

        widgets=[w for sc in (device.get('scenes') or []) for w in (sc.get('widgets') or []) if isinstance(w,dict) and w.get('type') in ('slider','switch','checkbox') and w.get('source','constant')=='constant']
        ui_ids={w.get('id'):i for i,w in enumerate(widgets)}
        initial_ui=','.join(f'{svg_num(w,"level",65,-1000000,1000000):.6f}f' for w in widgets) or '0.0f'
        code+=f'static float uiValues[{max(1,len(widgets))}]={{{initial_ui}}};\n'
        code+='static int activeSlider=-1;\n'
        logic_ids={n.get('id'):i for i,n in enumerate((device.get('logic') or {}).get('nodes',[]))}
        for idx in sorted(logic_ids.values()):code+=f'extern float logicValue{idx};\n'

        code+=f'''static const uint8_t BL_CHANNEL=7;
static const uint8_t BL_NORMAL={brightness}, BL_IDLE={sleep_brightness};
static const uint32_t BL_TIMEOUT_MS={timeout_s}UL * 1000UL;
static uint32_t lastTouchMs=0;
static bool backlightDimmed=false;
void setBacklight(uint8_t percent){{
  uint32_t duty=constrain((int)percent,0,100)*255/100;
#ifdef CYD_M5_DISPLAY
  M5.Display.setBrightness(duty);
  return;
#endif
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(BACKLIGHT_PIN,duty);
#else
  ledcWrite(BL_CHANNEL,duty);
#endif
}}
void initBacklight(){{
#ifndef CYD_M5_DISPLAY
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(BACKLIGHT_PIN,1000,8);
#else
  ledcSetup(BL_CHANNEL,1000,8);
  ledcAttachPin(BACKLIGHT_PIN,BL_CHANNEL);
#endif
#endif
  setBacklight(BL_NORMAL);
  lastTouchMs=millis();
}}
void wakeBacklight(){{
  lastTouchMs=millis();
  backlightDimmed=false;
  setBacklight(BL_NORMAL);
}}
void pollBacklight(){{
  if(BL_TIMEOUT_MS && !backlightDimmed && millis()-lastTouchMs>=BL_TIMEOUT_MS){{
    backlightDimmed=true;
    setBacklight(BL_IDLE);
  }}
}}
'''

    if wifi:
        code+='bool wifiStarted=false;\n'
        if mode in ('sta','ap_sta'):
            code+=f'static const char *STA_SSID={cstr(f.get("sta_ssid", ""),64)}, *STA_PASSWORD={cstr(f.get("sta_password", ""),64)};\n'
        if mode in ('ap','ap_sta'):
            pw=value(f.get('ap_password','cyd12345'),64)
            if pw and len(pw)<8:raise ValueError('Hasło hotspotu musi mieć co najmniej 8 znaków.')
            code+=f'static const char *AP_SSID={cstr(f.get("ap_ssid","CYD-DIAG"),50)}, *AP_PASSWORD={cstr(pw,64)};\n'
    if rx or tx:
        port=get_number(f,'audio_port',3333,1024,65535)
        code+=f'WiFiUDP soundUDP;\nstatic const uint16_t SOUND_PORT={port};\nstatic uint8_t soundLevel=0;\n'
    if cyd_click_beeps:
        code+=r'''// CYD 2.8 R P4 speaker output. Random short tones, no delay() and no audio pin conflicts.
static const uint8_t CYD_CLICK_PIN=26;
static uint32_t cydClickEnds=0;
static uint16_t cydClickHz=0;
static uint32_t cydClickPhase=0;
static void cydClickStart(uint8_t kind){
  const uint32_t r=esp_random();
  const uint16_t base=kind==1?500:kind==2?1450:kind==3?1150:700;
  const uint16_t spread=kind==1?420:kind==2?850:kind==3?950:1200;
  cydClickHz=(uint16_t)(base+(r%spread));
  cydClickEnds=millis()+25+((r>>11)%46);
  cydClickPhase=0;
#ifndef CYD_CLICK_PCM_MIX
  #if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcWriteTone(CYD_CLICK_PIN,cydClickHz);
  #else
    ledcWriteTone(6,cydClickHz);
  #endif
#endif
  Serial.printf("@BEEP|%u|%u|%u\n",(unsigned)kind,(unsigned)cydClickHz,(unsigned)(25+((r>>11)%46)));
}
static void cydClickInit(){
#ifndef CYD_CLICK_PCM_MIX
  #if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcAttach(CYD_CLICK_PIN,1800,8);
    ledcWriteTone(CYD_CLICK_PIN,0);
  #else
    ledcSetup(6,1800,8);
    ledcAttachPin(CYD_CLICK_PIN,6);
    ledcWriteTone(6,0);
  #endif
#endif
}
static void cydClickPoll(){
  if(cydClickHz && (int32_t)(millis()-cydClickEnds)>=0){
    cydClickHz=0;
#ifndef CYD_CLICK_PCM_MIX
  #if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcWriteTone(CYD_CLICK_PIN,0);
  #else
    ledcWriteTone(6,0);
  #endif
#endif
  }
}
#ifdef CYD_CLICK_PCM_MIX
static uint8_t cydClickMixPCM(uint8_t original){
  if(!cydClickHz || (int32_t)(millis()-cydClickEnds)>=0)return original;
  cydClickPhase=(cydClickPhase+cydClickHz)%8000U;
  int v=(int)original+(cydClickPhase<4000U?46:-46);
  return (uint8_t)constrain(v,0,255);
}
#endif
'''
    if rx:
        code+='static uint8_t pcmRing[8192];\nstatic uint16_t pcmHead=0,pcmTail=0;\nstatic uint32_t nextSampleUs=0;\n'
        code+='''void pollAudio() {
  int packet=soundUDP.parsePacket();
  if (packet > 0) {
    uint8_t b[512];
    while (packet>0) {
      int n=soundUDP.read(b,min(packet,(int)sizeof(b)));
      if(n<=0)break;
      packet-=n;
      for(int i=0;i<n;i++) {
        uint16_t next=(pcmHead+1)&8191;
        if(next!=pcmTail){pcmRing[pcmHead]=b[i];pcmHead=next;}
        soundLevel=abs((int)b[i]-128);
      }
    }
  }
  uint32_t now=micros();
  if((int32_t)(now-nextSampleUs)>=0) {
    nextSampleUs=now+125; // 8000 Hz, unsigned 8 bit mono
    uint8_t sample=128;
    if(pcmHead!=pcmTail){sample=pcmRing[pcmTail];pcmTail=(pcmTail+1)&8191;}
    dacWrite(26,sample); // CYD amplifier GPIO26
  }
}
'''
    if rx and cyd_click_beeps:code=code.replace('dacWrite(26,sample); // CYD amplifier GPIO26','dacWrite(26,cydClickMixPCM(sample)); // overlay short UI click over PCM')
    if tx:
        dest=value(f.get('audio_dest','192.168.4.1'),60)
        if not re.fullmatch(r'\d{1,3}(\.\d{1,3}){3}',dest) or any(int(part)>255 for part in dest.split('.')):
            raise ValueError('Adres IP odbiornika audio jest nieprawidłowy.')
        bclk=get_number(pins,'mic_bclk',19,0,48); ws=get_number(pins,'mic_ws',22,0,48);din=get_number(pins,'mic_din',23,0,48)
        if len({bclk,ws,din})!=3:raise ValueError('Mikrofon I2S: BCLK, WS i DIN muszą mieć różne piny.')
        code+=f'static IPAddress audioDestination({",".join(dest.split("."))});\n'
        code+=f'''void setupMicrophone() {{
  i2s_config_t cfg = {{}};
  cfg.mode=(i2s_mode_t)(I2S_MODE_MASTER|I2S_MODE_RX);
  cfg.sample_rate=8000;
  cfg.bits_per_sample=I2S_BITS_PER_SAMPLE_32BIT;
  cfg.channel_format=I2S_CHANNEL_FMT_ONLY_LEFT;
  cfg.communication_format=I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags=0;cfg.dma_buf_count=4;cfg.dma_buf_len=128;cfg.use_apll=false;
  i2s_pin_config_t pins={{}};
  pins.bck_io_num={bclk};pins.ws_io_num={ws};pins.data_out_num=I2S_PIN_NO_CHANGE;pins.data_in_num={din};
  i2s_driver_install(I2S_NUM_0,&cfg,0,nullptr);
  i2s_set_pin(I2S_NUM_0,&pins);
}}
void sendAudio() {{
  if(WiFi.status()!=WL_CONNECTED)return;
  int32_t raw[128];size_t got=0;
  if(i2s_read(I2S_NUM_0,raw,sizeof(raw),&got,0)!=ESP_OK || got==0)return;
  uint8_t compressed[128];size_t n=min(got/4,(size_t)128);
  for(size_t i=0;i<n;i++) {{
    int sample=(raw[i]>>24)+128;
    compressed[i]=(uint8_t)constrain(sample,0,255);
  }}
  soundUDP.beginPacket(audioDestination,SOUND_PORT);
  soundUDP.write(compressed,n);
  soundUDP.endPacket();
}}
'''
    if boolv(f,'gyro'):
        sda=get_number(pins,'i2c_sda',27,0,48);scl=get_number(pins,'i2c_scl',22,0,48)
        if sda==scl:raise ValueError('I2C: SDA i SCL nie mogą być identyczne.')
        code+='''static bool imuOK=false;
int16_t readGyroX(){
  if(!imuOK)return 0;
  Wire.beginTransmission(0x68);Wire.write(0x43);
  if(Wire.endTransmission(false)!=0)return 0;
  if(Wire.requestFrom(0x68,2)!=2)return 0;
  return (int16_t)((Wire.read()<<8)|Wire.read());
}
'''
    if battery:
        code+=f'''static const int BAT_ADC_PIN={adc};
static const float BAT_DIVIDER={divider:.4f}f;
static const float BAT_MIN_V={b_min:.3f}f, BAT_MAX_V={b_max:.3f}f;
static const float BAT_SMOOTH={smoothing/100.0:.3f}f;
static float batMeasuredV=0.0f;
static bool batHasReading=false;
static uint32_t batLastRead=0;
void pollBattery(){{
  if(batHasReading && millis()-batLastRead<250)return;
  batLastRead=millis();
  float sample=analogReadMilliVolts(BAT_ADC_PIN)*0.001f*BAT_DIVIDER;
  if(!batHasReading){{batMeasuredV=sample;batHasReading=true;}}
  else batMeasuredV=BAT_SMOOTH*batMeasuredV+(1.0f-BAT_SMOOTH)*sample;
}}
float batteryVolts(){{return batMeasuredV;}}
int batteryPercent(){{return constrain((int)roundf((batMeasuredV-BAT_MIN_V)*100.0f/(BAT_MAX_V-BAT_MIN_V)),0,100);}}
'''
    if p['screen']:
        if not wifi:code+='namespace WiFi { static const int fake=0; }\n'
        code+='''void drawState(int x,int y,int w,int h,const char *name,bool ok){
  tft.fillRoundRect(x,y,w,h,7,ok?TFT_DARKGREEN:TFT_MAROON);
  tft.setTextColor(TFT_WHITE,ok?TFT_DARKGREEN:TFT_MAROON);
  tft.drawCentreString(name,x+w/2,y+h/2-8,2);
}
'''
        if any(w.get('type') in ('rfwave','rfsignal','rfrssi') for sc in (device.get('scenes') or []) for w in (sc.get('widgets') or [])):
            code += '''// RF indicator: RSSI values are in dBm (negative values); no invented radio measurements.
void drawRadioSignal(int x,int y,int w,int h,const char*radio,float dbm,float minDbm,float maxDbm,uint16_t accent,int style){
  uint16_t base=C565(0x10273C),fg=TFT_WHITE,off=C565(0x344E63);
  tft.fillRoundRect(x,y,w,h,7,base);
  tft.setTextColor(fg,base);tft.drawString(radio,x+6,y+4,1);
  bool valid=isfinite(dbm);
  float fraction=valid?constrain((dbm-minDbm)/max(0.001f,maxDbm-minDbm),0.0f,1.0f):0.0f;
  uint16_t signalColor=valid ? (fraction<0.25f?TFT_RED:(fraction<0.55f?TFT_ORANGE:accent)) : off;
  if(style==0){
    int cx=x+min(35,(int)(w*0.22f)),cy=y+(int)(h*0.61f),rad=max(4,min((int)(h*0.34f),(int)(w*0.17f)));
    tft.fillCircle(cx,cy,3,signalColor);
    int waveFrame=(millis()/240UL)%3;
    for(int k=0;k<3;k++){
      int r=rad*(k+1)/3;
      uint16_t c=valid && ((k+waveFrame)%3!=0)?signalColor:off;
      for(int a=-70;a<70;a+=14){
        float aa=a*0.017453293f,bb=(a+14)*0.017453293f;
        tft.drawLine(cx+(int)(r*cosf(aa)),cy+(int)(r*sinf(aa)),cx+(int)(r*cosf(bb)),cy+(int)(r*sinf(bb)),c);
      }
    }
    tft.setTextColor(fg,base);
    tft.drawCentreString(valid?String((int)roundf(dbm))+" dBm":String("NO RSSI"),x+(int)(w*0.70f),y+h/2-6,2);
  }else if(style==1){
    int spacing=max(5,min(17,(w-19)/8)),barHeight=(int)(h*0.5f),bottom=y+(int)(h*0.76f);
    for(int k=0;k<5;k++){
      int bh=barHeight*(k+1)/5;
      tft.fillRect(x+8+k*spacing,bottom-bh,max(3,spacing-3),bh,(valid && fraction>k/5.0f)?signalColor:off);
    }
    tft.setTextColor(fg,base);tft.drawRightString(valid?String((int)roundf(dbm))+" dBm":String("N/A"),x+w-5,y+h/2-5,2);
  }else{
    tft.setTextColor(signalColor,base);
    tft.drawCentreString(valid?String((int)roundf(dbm))+" dBm":String("N/A"),x+w/2,y+h/2-6,2);
  }
}
'''
        code+='''void drawBattery(int x,int y,int w,int h){
  tft.drawRoundRect(x,y,w-7,h,3,TFT_WHITE);
  tft.fillRect(x+w-5,y+h/3,5,h/3,TFT_WHITE);
'''
        if boolv(f,'battery'):
            code+='''  float v=batteryVolts();
  int pct=batteryPercent(); // mapowanie ustawione w edytorze
  tft.fillRect(x+3,y+3,(w-13)*pct/100,h-6,pct<20?TFT_RED:TFT_GREEN);
  tft.setTextColor(TFT_WHITE,TFT_BLACK);
  tft.drawCentreString(String(pct)+"% " + String(v,2)+"V",x+w/2,y+h/2-8,2);
'''
        else:
            code+='''  tft.setTextColor(TFT_WHITE,TFT_BLACK);tft.drawCentreString("BAT ?",x+w/2,y+h/2-8,2);
'''
        code+='}\n'
        if boolv(f,'gyro'):
            code+='''void drawGyro(int x,int y,int w,int h){
  tft.fillRoundRect(x,y,w,h,6,TFT_DARKCYAN);
  tft.setTextColor(TFT_WHITE,TFT_DARKCYAN);
  tft.drawCentreString(imuOK?"GYRO:"+String(readGyroX()):"GYRO: BRAK",x+w/2,y+h/2-8,2);
}
'''
        else:
            code+='''void drawGyro(int x,int y,int w,int h){drawState(x,y,w,h,"GYRO OFF",false);}\n'''
        if rx or tx:
            code+='''void drawAudio(int x,int y,int w,int h){
  tft.fillRoundRect(x,y,w,h,6,TFT_DARKGREY);
  tft.setTextColor(TFT_WHITE,TFT_DARKGREY);
  tft.drawCentreString("AUDIO",x+w/2,y+4,2);
  tft.fillRect(x+5,y+h-14,(w-10)*constrain((int)soundLevel,0,127)/127,9,TFT_GREEN);
}
'''
        else:
            code+='''void drawAudio(int x,int y,int w,int h){drawState(x,y,w,h,"MIC OFF",false);}\n'''
        if not wifi:
            code=code.replace('WiFi.status()==WL_CONNECTED || WiFi.getMode()==WIFI_AP || WiFi.getMode()==WIFI_AP_STA','false')
        scenes=device.get('scenes') or []
        if not isinstance(scenes,list) or len(scenes)>40:raise ValueError('Projekt ma nieprawidłowe ekrany.')
        if not scenes:raise ValueError('To urządzenie nie ma ekranów.')
        code+='void drawScene(){\n  switch(activeScene){\n'
        for index,sc in enumerate(scenes):
            if not isinstance(sc,dict):continue
            bg=color(sc.get('bg','#101928'))
            code+=f'  case {index}: {{\n    tft.fillScreen(C565({bg}));\n'
            for w in sc.get('widgets',[])[:150]:
                if not isinstance(w,dict):continue
                w={**w,'screenBg':sc.get('bg','#101928')}
                code+=draw_widget(w,f,logic_ids,ui_ids,screen_w,screen_h)+'\n'
            code+='    break;\n  }\n'
        code+='  default:activeScene=0;break;\n  }\n}\n'
        if p['touch']:
            if cyd_click_beeps:
                code+='''static int cydQueuedScene=-1;
static uint32_t cydQueueAt=0;
static void cydQueueNavigation(int target,int widget){
  if(widget>=0 && widget<64 && cyd_widgets[widget]){lv_obj_add_state(cyd_widgets[widget],LV_STATE_PRESSED);cyd_pressed_widget=widget;}
  cydQueuedScene=target;cydQueueAt=millis()+60;
}
static void cydPollNavigation(){
  if(cydQueuedScene>=0 && (int32_t)(millis()-cydQueueAt)>=0){
    activeScene=cydQueuedScene;cydQueuedScene=-1;drawScene();
    cyd_pressed_widget=-1;
  }
}
'''
            code+='void onTouch(int x,int y){\n  switch(activeScene){\n'
            for index,sc in enumerate(scenes):
                code+=f'    case {index}:\n'
                for widget_idx,w in enumerate(sc.get('widgets',[])[:64]):
                    if not isinstance(w,dict) or w.get('type')!='button':continue
                    dest=w.get('to','')
                    targets=[j for j,s in enumerate(scenes) if s.get('id')==dest]
                    x=get_number(w,'x',0,0,screen_w-1);y=get_number(w,'y',0,0,screen_h-1)
                    wid=get_number(w,'w',50,1,screen_w-x);hei=get_number(w,'h',30,1,screen_h-y)
                    # Buttons without a screen target still generate a press event (no more dead controls).
                    if targets:
                        code+=f'      if(x>={x} && x<{x+wid} && y>={y} && y<{y+hei}){{'+(f'cydClickStart(0);cydQueueNavigation({targets[0]},{widget_idx});' if cyd_click_beeps else f'activeScene={targets[0]};drawScene();')+'return;}\n'
                    else:
                        msg=cstr('@BUTTON:'+str(w.get('id','button')),96)
                        code+=f'      if(x>={x} && x<{x+wid} && y>={y} && y<{y+hei}){{'+('cydClickStart(0);' if cyd_click_beeps else '')+f'Serial.println({msg});if(cyd_widgets[{widget_idx}])lv_obj_add_state(cyd_widgets[{widget_idx}],LV_STATE_PRESSED);cyd_pressed_widget={widget_idx};return;}}\n'
                for w in sc.get('widgets',[]):
                    if not isinstance(w,dict) or w.get('id') not in ui_ids:continue
                    x=get_number(w,'x',0,0,screen_w-1);y=get_number(w,'y',0,0,screen_h-1)
                    wid=get_number(w,'w',50,1,screen_w-x);hei=get_number(w,'h',30,1,screen_h-y)
                    idx=ui_ids[w['id']]
                    if w.get('type')=='slider':
                        v_min=svg_num(w,'min',0,-1000000,1000000);v_max=svg_num(w,'max',100,-1000000,1000000)
                        code+=f'      if(x>={x} && x<{x+wid} && y>={y} && y<{y+hei}){{'+('cydClickStart(3);' if cyd_click_beeps else '')+f'activeSlider={idx};uiValues[{idx}]={v_min:.5f}f + constrain((x-{x+13})/(float){max(1,wid-26)},0.0f,1.0f)*({v_max-v_min:.5f}f);drawScene();return;}}\n'
                    elif w.get('type') in ('switch','checkbox'):
                        code+=f'      if(x>={x} && x<{x+wid} && y>={y} && y<{y+hei}){{'+(('cydClickStart(1);' if w.get('type')=='switch' else 'cydClickStart(2);') if cyd_click_beeps else '')+f'uiValues[{idx}]=uiValues[{idx}]>=0.5f?0.0f:1.0f;drawScene();return;}}\n'
                code+='      break;\n'
            code+='  }\n}\n'
            # A slider stays responsive while the finger is moved; switches only toggle on the first touch edge.
            code+='void moveSlider(int x){\n  switch(activeSlider){\n'
            for w in widgets:
                if w.get('type')!='slider':continue
                idx=ui_ids[w['id']]
                vmin=svg_num(w,'min',0,-1000000,1000000);vmax=svg_num(w,'max',100,-1000000,1000000)
                x=get_number(w,'x',0,0,screen_w-1);width=get_number(w,'w',100,1,screen_w-x)
                code+=f'    case {idx}: uiValues[{idx}]={vmin:.5f}f+constrain((x-{x+13})/(float){max(1,width-26)},0.0f,1.0f)*({vmax-vmin:.5f}f);drawScene();break;\n'
            code+='    default:break;\n  }\n}\n'
            if p.get('native_touch'):
                code+='''void pollTouch(){
  const bool pressed=M5.Touch.getCount()>0;
  if(pressed){
    const auto pt=M5.Touch.getDetail(0);
    const int x=pt.x, y=pt.y;
    if(!touchWasDown){
      bool wasDimmed=backlightDimmed;
      wakeBacklight();
      if(!wasDimmed)onTouch(x,y);
    }else if(activeSlider>=0){
      static uint32_t lastSlideRefresh=0;
      if(millis()-lastSlideRefresh>=35){moveSlider(x);lastSlideRefresh=millis();}
    }
  }else {activeSlider=-1;if(cyd_pressed_widget>=0){if(cyd_widgets[cyd_pressed_widget])lv_obj_remove_state(cyd_widgets[cyd_pressed_widget],LV_STATE_PRESSED);cyd_pressed_widget=-1;}}
  touchWasDown=pressed;
}
'''
            else:
                sck,miso,mosi,cs,irq=p['touchpins']
                code+=f'''void pollTouch(){{
  bool pressed=touch.touched();
  if(pressed){{
    if(!touchWasDown){{
      bool wasDimmed=backlightDimmed;
      wakeBacklight();
      if(wasDimmed){{touchWasDown=true;return;}} // first touch only wakes LCD
    }}
    static uint32_t lastSlideRefresh=0;
    if(!touchWasDown || (activeSlider>=0 && millis()-lastSlideRefresh>=35UL)){{
      TS_Point p=touch.getPoint();
      int x=0,y=0;
      cydMapTouch(p,x,y);
      if(!touchWasDown){{Serial.printf("@TOUCH raw=%d,%d xy=%d,%d rot=%d\\n",(int)p.x,(int)p.y,x,y,SCREEN_ROTATION);onTouch(x,y);}}
      else if(activeSlider>=0){{moveSlider(x);lastSlideRefresh=millis();}}
    }}
  }}else{{activeSlider=-1;if(cyd_pressed_widget>=0){{if(cyd_widgets[cyd_pressed_widget])lv_obj_remove_state(cyd_widgets[cyd_pressed_widget],LV_STATE_PRESSED);cyd_pressed_widget=-1;}}}}
  touchWasDown=pressed;
}}
'''
    logic_code,logic_init,logic_poll=generate_logic(device,p,f)
    code+=logic_code
    code+='void setup(){\n  Serial.begin(115200);\n'
    if device.get('profile') in ('coreink','stamplc') or p.get('m5display'):
        code+='  auto m5cfg=M5.config(); M5.begin(m5cfg);\n'
    if p['screen']:
        if p.get('m5display'):
            code+='  tft.setColorDepth(16);tft.setRotation(SCREEN_ROTATION);tft.fillScreen(TFT_BLACK);\n'
            code+='  initBacklight();\n'
        else:
            code+='  initBacklight();\n'
            code+='  tft.init();tft.setRotation(SCREEN_ROTATION);tft.fillScreen(TFT_BLACK);\n'
            if p['touch']:
                sck,miso,mosi,cs,irq=p['touchpins']
                code+=(f'  touchBus.begin({sck},{miso},{mosi},{cs});touch.begin(touchBus);touch.setRotation(0);\n' if device.get('profile') in ('cyd28','cyd28usb') else '  touch.begin(SPI);touch.setRotation(0);\n')
                code+='  cydInitializeTouchCalibration();\n'
    if wifi:
        if mode=='ap':code+='  WiFi.mode(WIFI_AP);WiFi.softAP(AP_SSID,AP_PASSWORD);\n'
        elif mode=='sta':code+='  WiFi.mode(WIFI_STA);WiFi.begin(STA_SSID,STA_PASSWORD);\n'
        else:code+='  WiFi.mode(WIFI_AP_STA);WiFi.softAP(AP_SSID,AP_PASSWORD);WiFi.begin(STA_SSID,STA_PASSWORD);\n'
    if rx:
        code+='  soundUDP.begin(SOUND_PORT);dacWrite(26,128);\n'
    if cyd_click_beeps:code+='  cydClickInit();\n'
    if tx:
        code+='  soundUDP.begin(0);setupMicrophone();\n'
    if boolv(f,'gyro'):
        code+=f'''  Wire.begin({get_number(pins,'i2c_sda',27,0,48)},{get_number(pins,'i2c_scl',22,0,48)});
  Wire.beginTransmission(0x68);Wire.write(0x6B);Wire.write(0);
  imuOK=(Wire.endTransmission()==0); // MPU6050 lub kompatybilny
'''
    if boolv(f,'bt_classic'):code+=f'  SerialBT.begin({cstr(device.get("name","DIAG-BT"),32)});\n'
    if boolv(f,'ble'):code+=f'  BLEDevice::init({cstr(device.get("name","DIAG-BLE"),32)});BLEDevice::createServer();BLEDevice::getAdvertising()->start();\n'
    if battery:code+='  analogReadResolution(12);analogSetPinAttenuation(BAT_ADC_PIN,ADC_11db);pollBattery();\n'
    if extra_setup:code+=extra_setup+'\n'
    code+=logic_init
    code+=str(custom.get('setup',''))[:16000]+'\n'
    if p['screen']:code+='  drawScene();\n'
    code+='}\nvoid loop(){\n'
    if device.get('profile') in ('coreink','stamplc') or p.get('m5display'):
        code+='  M5.update();\n'
    if p['touch']:code+='  pollTouch();\n'
    if cyd_click_beeps:code+='  cydClickPoll();\n'
    if cyd_click_beeps:code+='  cydPollNavigation();\n'
    if p['screen']:code+='  pollBacklight();\n'
    if battery:code+='  pollBattery();\n'
    if rx:code+='  pollAudio();\n'
    if tx:code+='  sendAudio();\n'
    if extra_loop:code+=extra_loop+'\n'
    code+=logic_poll
    if p['screen']:
        live=any(w.get('type') in ('battery','wifi','gyro','audio','mic','rfwave','rfsignal','rfrssi','waterfall','spectrum') or w.get('source') in ('battery_percent','battery_voltage') or str(w.get('source','')).startswith('logic:') for sc in device.get('scenes',[]) for w in sc.get('widgets',[]))
        if live:code+='  if(millis()-lastRefresh>250){lastRefresh=millis();drawScene();}\n'
    code+=str(custom.get('loop',''))[:16000]+'\n'
    code+='}\n'
    if boolv(f,'bt_classic'):
        code=code.replace('BluetoothSerial.h>','BluetoothSerial.h>\nBluetoothSerial SerialBT;')
    if cyd_click_beeps:code=code.replace('if(cyd_widgets[cyd_pressed_widget])lv_obj_remove_state(cyd_widgets[cyd_pressed_widget],LV_STATE_PRESSED);cyd_pressed_widget=-1;','if(cydQueuedScene<0){if(cyd_widgets[cyd_pressed_widget])lv_obj_remove_state(cyd_widgets[cyd_pressed_widget],LV_STATE_PRESSED);cyd_pressed_widget=-1;}')
    if not wifi:
        code=code.replace('(WiFi.status()==WL_CONNECTED || WiFi.getMode()==WIFI_AP || WiFi.getMode()==WIFI_AP_STA)','false')
    if p.get('m5display'):
        # M5GFX and TFT_eSPI share drawing API, except spelling of centre/center.
        code=code.replace('.drawCentreString(','.drawCenterString(')

    if p.get('screen') and p.get('touch') and not p.get('native_touch'):
        # The SIM image uses the same LVGL/TFT_eSPI renderer but virtual UART taps.
        sim_touch=(ROOT/'sim_touch_cpp.txt').read_text(encoding='utf-8')
        sim_touch=sim_touch.replace('@@SCENES@@',str(len(device.get('scenes') or [])))
        if 'void pollTouch(){' not in code:raise RuntimeError('Expected pollTouch missing')
        code=code.replace('void pollTouch(){','void pollTouch(){\n'+sim_touch,1)
    return convert_lvgl(code,device,p,rotation)



WOKWI_CYD_DIAGRAM={
  'version':1,'author':'CYD Studio','editor':'wokwi',
  'parts':[{'type':'board-esp32-devkit-c-v4','id':'esp','top':50,'left':260,'attrs':{'flashSize':'4'}},
           {'type':'wokwi-ili9341','id':'lcd','top':0,'left':0,'attrs':{}},
           {'type':'wokwi-buzzer','id':'speaker','top':250,'left':240,'attrs':{'mode':'accurate','volume':'0.15'}}],
  'connections':[
    ['esp:TX','$serialMonitor:RX','',[]],['esp:RX','$serialMonitor:TX','',[]],
    ['lcd:VCC','esp:3V3','red',[]],['lcd:GND','esp:GND.1','black',[]],
    ['lcd:LED','esp:21','orange',[]],['lcd:D/C','esp:2','cyan',[]],
    ['lcd:CS','esp:15','green',[]],['lcd:MOSI','esp:13','blue',[]],
    ['lcd:MISO','esp:12','purple',[]],['lcd:SCK','esp:14','yellow',[]],
    ['speaker:1','esp:GND.2','black',[]],['speaker:2','esp:26','magenta',[]]],'dependencies':{}
}
def cyd_wokwi_files(dest, scenes):
    dest=Path(dest)
    (dest/'diagram.json').write_text(json.dumps(WOKWI_CYD_DIAGRAM,indent=2)+'\n',encoding='utf-8')
    (dest/'wokwi.toml').write_text("[wokwi]\nversion = 1\nfirmware = '.pio/build/sim/firmware.merged.bin'\nelf = '.pio/build/sim/firmware.elf'\n",encoding='utf-8')
    for filename in ('merge_firmware.py','SIMULUJ_CYD.ps1','README_SIMULATOR.md','README_MOKXI_PL.md'):
        (dest/filename).write_bytes((ROOT/filename).read_bytes())
    (dest/'sim_screens').mkdir(exist_ok=True)
    (dest/'sim_screens'/'readme.txt').write_text('Wokwi CLI saves screenshots in this directory.\n',encoding='utf-8')
    count=min(len(scenes),30)
    steps=['name: CYD LVGL screenshots','version: 1','author: CYD Studio','steps:','  - delay: 2000ms']
    for i in range(count):
        steps.extend([f'  - write-serial: "@SIM SCENE {i}\\n"', '  - delay: 500ms',
                      '  - take-screenshot:', '      part-id: lcd', f'      save-to: sim_screens/scene_{i:02d}.png'])
    (dest/'screens.test.yaml').write_text('\n'.join(steps)+'\n',encoding='utf-8')
    (dest/'MOKXI_IMPORTUJ.txt').write_text('Mokxi: zbuduj firmware.merged.bin przez SIMULUJ_CYD.ps1, potem importuj projekt ZIP lub diagram.json i wgraj firmware na ESP32. Zrzuty przyciskow testuj przez Serial: @SIM TAP 120 60.\n',encoding='utf-8')
    # Test button hitbox and actual LVGL PRESSED state before the next scene.
    tap=['name: CYD LVGL clicks and tones','version: 1','author: CYD Studio','steps:','  - delay: 1500ms']
    for scene_index,sc in enumerate(scenes[:30]):
        for button in sc.get('widgets',[]):
            if not isinstance(button,dict) or button.get('type')!='button':continue
            if not button.get('to'):continue
            try:
                x=int(float(button.get('x',0))+float(button.get('w',0))/2)
                y=int(float(button.get('y',0))+float(button.get('h',0))/2)
            except (ValueError,TypeError):continue
            if not (0<=x<320 and 0<=y<320):continue
            tap+= [f'  - write-serial: "@SIM SCENE {scene_index}\\n"','  - delay: 300ms',f'  - write-serial: "@SIM TAP {x} {y}\\n"','  - delay: 20ms',
                   '  - take-screenshot:', '      part-id: lcd', f'      save-to: sim_screens/pressed_{scene_index:02d}_{x}_{y}.png',
                   '  - delay: 220ms','  - take-screenshot:', '      part-id: lcd',f'      save-to: sim_screens/released_{scene_index:02d}_{x}_{y}.png']
            break
    (dest/'clicks.test.yaml').write_text('\n'.join(tap)+'\n',encoding='utf-8')


def generate_project(data,requested):
    device,p=validate_device(data,requested)
    did=re.sub(r'[^a-zA-Z0-9_-]','_',str(requested))[:45]
    if not did:raise ValueError('Nieprawidłowy identyfikator urządzenia.')
    dest=OUTPUT/did
    (dest/'src').mkdir(parents=True,exist_ok=True)
    if device.get('profile')!='cyd28':
        # Do not leak a stale CYD simulator configuration when device/profile changes.
        for name in ('diagram.json','wokwi.toml','merge_firmware.py','SIMULUJ_CYD.ps1','README_SIMULATOR.md','README_MOKXI_PL.md','MOKXI_IMPORTUJ.txt','screens.test.yaml','clicks.test.yaml'):
            (dest/name).unlink(missing_ok=True)
    cpp=generate_cpp(device,p)
    libs=[]
    if device.get('profile') in ('coreink','stamplc') or p.get('m5display'):
        libs=['https://github.com/m5stack/M5Unified.git']
        if device.get('profile')=='stamplc':libs.append('https://github.com/m5stack/M5StamPLC.git')
    if p['screen']:
        if p.get('m5display'):
            libs=['https://github.com/m5stack/M5Unified.git','lvgl/lvgl @ 9.6.0']
        else:
            libs=['bodmer/TFT_eSPI @ ^2.5.43','lvgl/lvgl @ 9.6.0']
        if p['touch'] and not p.get('native_touch'):libs+=['https://github.com/PaulStoffregen/XPT2046_Touchscreen.git']
    _ei,_ed,_es,_el,extra_libs=generate_instrument_hardware(device,p)
    for lib in extra_libs:
        if lib not in libs:libs.append(lib)
    for lib in libraries_for_device(device).values():
        if lib['url'] not in libs:libs.append(lib['url'])
    for line in device.get('libraries',[]):
        if not isinstance(line,str):continue
        line=line.strip()
        if not line:continue
        if len(line)>200 or '\n' in line or '\r' in line or not re.fullmatch(r'[A-Za-z0-9._/ @^~:+\-=#]+',line):
            raise ValueError('Niedozwolony zapis biblioteki: '+line[:60])
        if line not in libs:libs.append(line)
    ini=f'[env:{p["board"]}]\nplatform = espressif32\nboard = {p["board"]}\nframework = arduino\nmonitor_speed = 115200\n'
    if p.get('m5display'):
        ini+='board_build.partitions = partitions_m5_lvgl.csv\nboard_upload.maximum_size = 3145728\n'
        (dest/'partitions_m5_lvgl.csv').write_text((ROOT/'partitions_m5_lvgl.csv').read_text(encoding='utf-8'),encoding='utf-8')
    if p['screen'] and p['touch'] and not p.get('native_touch'):
        ini+='board_build.partitions = partitions_cyd.csv\nboard_upload.maximum_size = 3145728\n'
        (dest/'partitions_cyd.csv').write_text((ROOT/'partitions_cyd.csv').read_text(encoding='utf-8'),encoding='utf-8')
    if p['screen']:
        # LVGL 9.6 builtin pool: 48 KiB instead of 64 KiB (16 KiB less DRAM).
        # Works with LV_CONF_SKIP and LVGL builtin malloc; see LVGL Kconfig.
        ini+='board_build.flash_mode = dio\nbuild_flags =\n    -D USER_SETUP_LOADED=1\n    -D LV_CONF_SKIP=1\n    -D LV_MEM_SIZE=49152\n    -D LV_FONT_MONTSERRAT_12=1\n    -D LV_FONT_MONTSERRAT_14=1\n    -D LV_FONT_MONTSERRAT_16=1\n    -D LOAD_GLCD=1\n    -D LOAD_FONT2=1\n'
        if p.get('m5display'):
            pass  # M5Unified auto-configures ILI9342/GC9107/ST7789 and the PMIC.
        elif p.get('cardputer_adv'):
            # Cardputer ADV: ST7789V2, 135 x 240 native (240 x 135 after rotation 1).
            ini+='    -D ST7789_DRIVER=1\n    -D TFT_WIDTH=135\n    -D TFT_HEIGHT=240\n    -D TFT_MISO=-1\n    -D TFT_MOSI=35\n    -D TFT_SCLK=36\n    -D TFT_CS=37\n    -D TFT_DC=34\n    -D TFT_RST=33\n    -D SPI_FREQUENCY=27000000\n    -D ARDUINO_USB_CDC_ON_BOOT=1\n    -D ARDUINO_USB_MODE=1\n'
        else:
            lcd=device.get('lcd',{}) if isinstance(device.get('lcd'),dict) else {}
            driver=lcd.get('driver','st7789' if device.get('profile')=='cyd28usb' else 'ili9341_2')
            if driver not in ('ili9341_2','ili9341','st7789'):driver='ili9341_2'
            order=lcd.get('order','bgr' if device.get('profile')=='cyd28usb' else 'rgb')
            if order not in ('rgb','bgr'):order='bgr'
            inversion=lcd.get('inversion','on' if device.get('profile')=='cyd24' else 'off')
            if inversion not in ('on','off'):inversion='off'
            ini+=f'    -D {dict(ili9341_2="ILI9341_2_DRIVER",ili9341="ILI9341_DRIVER",st7789="ST7789_DRIVER")[driver]}=1\n'
            ini+=f'    -D TFT_RGB_ORDER={"TFT_BGR" if order=="bgr" else "TFT_RGB"}\n'
            ini+=f'    -D TFT_INVERSION_{"ON" if inversion=="on" else "OFF"}=1\n'
            ini+='    -D TFT_WIDTH=240\n    -D TFT_HEIGHT=320\n    -D TFT_MISO=12\n    -D TFT_MOSI=13\n    -D TFT_SCLK=14\n    -D TFT_CS=15\n    -D TFT_DC=2\n    -D TFT_RST=-1\n    -D SPI_FREQUENCY=40000000\n'
    if p.get('m5display'):
        # M5GFX auto-detects the panel, rotation, touch IC and power controller.
        ini+='    -D CYD_M5_DISPLAY=1\n'
    if device.get('profile') in S3_PROFILES:
        ini+='    -D ARDUINO_USB_CDC_ON_BOOT=1\n    -D ARDUINO_USB_MODE=1\n' if p['screen'] else 'build_flags =\n    -D ARDUINO_USB_CDC_ON_BOOT=1\n    -D ARDUINO_USB_MODE=1\n'
    if device.get('profile')=='stamplc':ini+='board_build.flash_size = 8MB\n'
    if libs:ini+='lib_deps =\n'+''.join('    '+lib+'\n' for lib in libs)
    (dest/'platformio.ini').write_text(ini,encoding='utf-8')
    (dest/'src/main.cpp').write_text(cpp,encoding='utf-8')
    if device.get('profile')=='cyd28' and p.get('screen') and p.get('touch'):
        ini+='\n[env:sim]\nextends = env:esp32dev\nbuild_flags = ${env:esp32dev.build_flags}\n    -D CYD_SIMULATOR=1\nextra_scripts = post:merge_firmware.py\n'
        (dest/'platformio.ini').write_text(ini,encoding='utf-8')
        cyd_wokwi_files(dest,device.get('scenes') or [])
    (dest/'CYD_Projekt.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    return dest,p


# Portable export uses documented, unencrypted interchange formats, not a proprietary binary.
# JSON is the source of truth; SVG files are editable illustrations, not a substitute
# for the original widgets and block graph.
PROJECT_SCHEMA = {
  '$schema': 'https://json-schema.org/draft/2020-12/schema',
  '$id': 'urn:cyd-studio:project-schema:1.0',
  'title': 'CYD Studio Project',
  'description': 'Portable, versioned project data; device-specific properties remain extensible.',
  'type': 'object', 'required': ['devices','version'],
  'properties': {
    'format': {'const':'cyd-studio-project'},
    'schema_version': {'type':'string'},
    'version': {'type':'integer'},
    'currentDevice': {'type':['string','null']},
    'devices': {'type':'array','items':{
      'type':'object','required':['id','profile','name','scenes'],
      'properties': {
        'id':{'type':'string'},'profile':{'type':'string'},'name':{'type':'string'},
        'scenes':{'type':'array','items':{'type':'object','required':['id','name','widgets'],
         'properties':{'id':{'type':'string'},'name':{'type':'string'},'bg':{'type':'string'},'widgets':{'type':'array'}}}},
        'logic':{'type':'object','properties':{'nodes':{'type':'array'},'edges':{'type':'array'}}},
        'features':{'type':'object'},'pins':{'type':'object'},'touch':{'type':'object'},
        'libraries':{'type':'array','items':{'type':'string'}},'githubLibraries':{'type':'array'},'grove':{'type':'object'},'custom':{'type':'object'}
      },'additionalProperties':True
    }}
  },'additionalProperties':True
}

def portable_project(data):
    if not isinstance(data,dict) or not isinstance(data.get('devices'),list) or len(data['devices'])>30:
        raise ValueError('Invalid project format or too many devices.')
    if not data['devices']: raise ValueError('Project is empty.')
    out = dict(data)
    out['format']='cyd-studio-project'
    out['schema_version']='1.0'
    return out

def identifier(s):
    return (re.sub(r'[^a-zA-Z0-9_-]','_',str(s)) or 'item')[:48]

def svg_color(c,default='#ffffff'):
    return c if isinstance(c,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',c) else default

def svg_num(obj,key,default,low=0,high=320):
    try:return max(low,min(high,float(obj.get(key,default))))
    except (ValueError,TypeError,AttributeError):return default

def screen_svg(scene,rotation=0):
    if not isinstance(scene,dict):raise ValueError('Invalid screen.')
    def txt(value):return xml_escape(str(value or '')[:120], {'"':'&quot;'})
    sw,sh=(320,240) if int(rotation)%2 else (240,320)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{sw}" height="{sh}" viewBox="0 0 {sw} {sh}">',
           f'<title>{txt(scene.get("name","Screen"))}</title>',
           f'<rect width="{sw}" height="{sh}" fill="{svg_color(scene.get("bg"),"#101d32")}"/>']
    for w in (scene.get('widgets') or [])[:800]:
        if not isinstance(w,dict):continue
        typ=w.get('type','');x=svg_num(w,'x',10,0,sw-1);y=svg_num(w,'y',10,0,sh-1)
        width=svg_num(w,'w',90,1,sw-x);height=svg_num(w,'h',40,1,sh-y)
        bg=svg_color(w.get('bg'),'#2384b9');fg=svg_color(w.get('fg'),'#ffffff')
        label=txt(w.get('text',''))
        if typ in ('button','rect','frame','custom','battery','wifi','gyro','audio','mic','bar','progress','value','integer','analog','digital','led','slider','gauge','switch','checkbox','waterfall','spectrum'):
            style=f'fill="{bg if typ not in ("frame",) else "none"}" stroke="{fg if typ=="frame" else bg}"'
            parts.append(f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="{6 if typ=="button" else 0}" {style}/>')
            if typ in ('bar','progress','slider'):
                amount=svg_num(w,'level',65,0,100)
                parts.append(f'<rect x="{x+2:g}" y="{y+2:g}" width="{max(0,(width-4)*amount/100):g}" height="{max(0,height-4):g}" fill="{fg}"/>')
            if typ in ('button','custom','wifi','gyro','audio','mic','battery','value','integer','analog','digital','led','gauge','switch','checkbox','slider','progress','waterfall','spectrum'):
                shown=label if typ in ('button','custom','wifi','gyro','audio','mic','battery','checkbox','waterfall','spectrum') else ('ON' if typ=='digital' else str(w.get('level',65))+str(w.get('unit','')))
                parts.append(f'<text x="{x+width/2:g}" y="{y+height/2+5:g}" fill="{fg}" text-anchor="middle" font-family="Arial,sans-serif" font-size="13">{txt(shown)}</text>')
        elif typ in ('rfwave','rfsignal','rfrssi'):
            radio=str(w.get('radioType','wifi')).upper()[:12]
            dbm=svg_num(w,'level',-67,-200,100)
            low=svg_num(w,'min',-110,-200,100);high=svg_num(w,'max',-30,-200,100)
            frac=max(0,min(1,(dbm-low)/max(.001,high-low)))
            parts.append(f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" rx="7" fill="#10273c"/>')
            parts.append(f'<text x="{x+7:g}" y="{y+13:g}" fill="{fg}" font-family="Arial" font-size="10" font-weight="bold">{txt(radio)}</text>')
            if typ=='rfwave':
                cx=x+min(35,width*.22);cy=y+height*.61
                for k in range(1,4):
                    rad=max(4,min(height*.34,width*.17))*k/3
                    parts.append(f'<path d="M {cx+rad*.34:g},{cy-rad*.94:g} Q {cx+rad*1.45:g},{cy:g} {cx+rad*.34:g},{cy+rad*.94:g}" stroke="{bg}" stroke-width="2" fill="none"/>')
            elif typ=='rfsignal':
                spacing=max(5,min(17,(width-19)/8))
                for k in range(5):
                    bh=height*.50*(k+1)/5
                    parts.append(f'<rect x="{x+8+k*spacing:g}" y="{y+height*.76-bh:g}" width="{max(3,spacing-3):g}" height="{bh:g}" fill="{bg if frac>k/5 else "#344e63"}"/>')
            parts.append(f'<text x="{x+width-6:g}" y="{y+height*.62:g}" text-anchor="end" fill="{fg}" font-family="Arial" font-size="12">{dbm:g} dBm</text>')
        elif typ=='text':
            parts.append(f'<text x="{x+width/2:g}" y="{y+height/2+5:g}" fill="{fg}" text-anchor="middle" font-family="Arial,sans-serif" font-size="15">{label}</text>')
        elif typ=='circle':
            parts.append(f'<circle cx="{x+width/2:g}" cy="{y+height/2:g}" r="{min(width,height)/2:g}" fill="{bg}"/>')
        elif typ=='line':
            parts.append(f'<line x1="{x:g}" y1="{y:g}" x2="{x+width:g}" y2="{y+height:g}" stroke="{bg}" stroke-width="2"/>')
        elif typ=='draw':
            for path in (w.get('paths') or [])[:100]:
                if not isinstance(path,list):continue
                pts=[]
                for p in path[:600]:
                    if isinstance(p,list) and len(p)>=2:
                        try: pts.append(f'{max(0,min(sw-1,float(p[0]))):g},{max(0,min(sh-1,float(p[1]))):g}')
                        except (ValueError,TypeError):continue
                if len(pts)>=2:parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{bg}" stroke-width="2" stroke-linecap="round"/>')
    parts.append('</svg>')
    return '\n'.join(parts).encode('utf-8')

def portable_zip(data):
    data=portable_project(data)
    with io.BytesIO() as out:
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            def add(filename,contents):archive.writestr(filename,contents)
            def json_add(filename,obj):add(filename,json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
            json_add('project.json',data)
            json_add('schema/project.schema.json',PROJECT_SCHEMA)
            add('README.md', """# CYD Studio — portable project

Open formats: JSON (data and logic), SVG (vector scenes), C++ (source),
PlatformIO INI (build configuration), and ZIP (archive).

`project.json` is the editable source of truth; SVGs are visual exports.
Restore the project in CYD Studio using Open > ZIP or Open > JSON.
Each `devices/<id>/` folder is a standalone PlatformIO project.
Open that device folder in VS Code with PlatformIO installed.
The generated C++ is a starting point and may require hardware checks.
The ZIP does not contain a compiled firmware.bin.

WARNING: exported JSON and ZIP may include Wi-Fi SSIDs and passwords.
Do not publish them without reviewing credentials.

Other programs can read these standards; importing every widget or logic
connection into third-party graphical editors is not guaranteed.
""")
            archive_ids=set()
            for idx,device in enumerate(data['devices']):
                if not isinstance(device,dict):continue
                did=identifier(device.get('id',idx))
                prefix=f'devices/{idx+1:02d}_{did}/'
                try:
                    d,p=validate_device(data,device.get('id'))
                    source=generate_cpp(d,p)
                    # platformio.ini comes from the same generator as Build.
                    path,_=generate_project(data,device.get('id'))
                    add(prefix+'src/main.cpp',source)
                    add(prefix+'platformio.ini',(path/'platformio.ini').read_bytes())
                    if (path/'partitions_cyd.csv').exists():add(prefix+'partitions_cyd.csv',(path/'partitions_cyd.csv').read_bytes())
                    for filename in ('diagram.json','wokwi.toml','merge_firmware.py','SIMULUJ_CYD.ps1','README_SIMULATOR.md','README_MOKXI_PL.md','MOKXI_IMPORTUJ.txt','screens.test.yaml','clicks.test.yaml'):
                        if (path/filename).exists():add(prefix+filename,(path/filename).read_bytes())
                except (ValueError,TypeError,KeyError) as e:
                    add(prefix+'GENERATION_ERROR.txt',str(e)+'\n')
                json_add(prefix+'device.json',device)
                json_add(prefix+'logic/graph.json',device.get('logic') or {'nodes':[],'edges':[]})
                json_add(prefix+'libraries/github-blocks.json',device.get('githubLibraries') or [])
                json_add(prefix+'settings/peripherals.json',{'features':device.get('features',{}),'pins':device.get('pins',{}),'touch':device.get('touch',{}),'grove':device.get('grove',{})})
                for sc_idx,sc in enumerate(device.get('scenes') or []):
                    if not isinstance(sc,dict):continue
                    key=f'{sc_idx+1:02d}_{identifier(sc.get("id",sc_idx))}'
                    json_add(prefix+'screens/'+key+'.json',sc)
                    add(prefix+'screens/'+key+'.svg',screen_svg(sc,device.get('rotation',0)))
        return out.getvalue()


def detect_progress(line, kind, current):
    """Return phase and indicative progress. Upload write percentages are exact."""
    clean = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
    low = clean.lower()
    if not clean:
        return None
    progress, phase, accurate = current
    if 'processing ' in low or 'platform:' in low:
        progress, phase = max(progress, 5), 'Konfiguracja PlatformIO'
    elif 'installing ' in low or 'downloading ' in low or 'resolving ' in low:
        progress, phase = max(progress, 10), 'Pobieranie bibliotek'
    elif 'compiling ' in low:
        progress, phase = max(progress, 27), 'Kompilacja kodu C++'
    elif 'archiving ' in low:
        progress, phase = max(progress, 55), 'Budowanie bibliotek'
    elif 'linking ' in low:
        progress, phase = max(progress, 66), 'Linkowanie programu'
    elif 'building ' in low and ('.bin' in low or 'firmware' in low):
        progress, phase = max(progress, 83), 'Tworzenie pliku BIN'
    elif 'checking size' in low or low.startswith('ram:') or low.startswith('flash:'):
        progress, phase = max(progress, 90), 'Sprawdzanie pamięci'
    if kind == 'flash':
        if 'serial port ' in low or 'connecting' in low:
            progress, phase = max(progress, 91), 'Łączenie z ESP32 przez USB'
        elif 'erasing flash' in low or 'chip erase completed' in low:
            progress, phase = max(progress, 92), 'Kasowanie pamięci ESP32'
        elif 'writing at ' in low or 'write_flash' in low:
            m = re.search(r'\(\s*(\d{1,3})\s*%\s*\)', clean)
            if m:
                pct = min(100, int(m.group(1)))
                progress, phase, accurate = max(progress, 92 + int(pct * 0.07)), f'Zapisywanie ESP32: {pct}%', True
            else:
                progress, phase = max(progress, 93), 'Zapisywanie pamięci ESP32'
        elif 'hash of data verified' in low or 'hard resetting' in low:
            progress, phase = max(progress, 99), 'Weryfikacja i restart urządzenia'
    if 'success' in low and kind == 'build':
        progress, phase = max(progress, 99), 'Sprawdzanie wyniku'
    return min(progress, 99), phase, accurate


def terminate_build_process(proc):
    """Terminate our own PlatformIO process tree. Do not use while USB flash is underway."""
    try:
        if proc.poll() is not None:return
        if os.name == 'nt':
            subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],
                           timeout=8,capture_output=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        else:
            import signal
            os.killpg(proc.pid,signal.SIGTERM)
    except (OSError,subprocess.TimeoutExpired):
        try:proc.terminate()
        except OSError:pass


def cancel_build(jobid):
    with LOCK:
        j=JOBS.get(jobid)
        if not j:raise ValueError('Nie znaleziono zadania PlatformIO.')
        if j['kind']=='flash':raise ValueError('Nie można przerwać zapisu USB tym przyciskiem.')
        if j['state'] in ('success','failed','cancelled'):
            return {'state':j['state'],'stopped':False}
        j['cancel_requested']=True
        proc=RUNNING_PROCS.get(jobid)
    if proc:terminate_build_process(proc)
    return {'state':'stopping','stopped':True}


def job_worker(jobid,command,cwd,kind):
    with LOCK:
        j=JOBS[jobid]
        if j['cancel_requested']:
            j['state']='cancelled';j['phase']='Kompilacja przerwana';return
        j['state']='running'
    try:
        proc=subprocess.Popen(command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,encoding='utf-8',errors='replace',bufsize=1,
                              creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0),
                              start_new_session=(os.name!='nt'))
        with LOCK:
            RUNNING_PROCS[jobid]=proc
            cancel_now=JOBS[jobid]['cancel_requested']
        if cancel_now:terminate_build_process(proc)
        for line in proc.stdout:
            with LOCK:
                j=JOBS[jobid]
                j['log']=(j['log']+line)[-55000:]
                result=detect_progress(line,kind,(j['progress'],j['phase'],j['accurate']))
                if result is not None:j['progress'],j['phase'],j['accurate']=result
        ret=proc.wait()
        with LOCK:
            j=JOBS[jobid];j['exitcode']=ret
            if j['cancel_requested']:
                j['state']='cancelled';j['phase']='Kompilacja przerwana';j['log']+='\n[USER] Zatrzymano kompilację.\n'
            else:
                j['state']='success' if ret==0 else 'failed'
                if ret==0 and kind=='build':
                    fw=cwd/'.pio'/'build'/j['env']/'firmware.bin'
                    if fw.exists():j['file']=str(fw)
                    else:j['state']='failed';j['log']+='\nBrak firmware.bin w katalogu .pio.\n'
                if j['state']=='success':
                    j['progress']=100
                    j['phase']='BIN gotowy' if kind=='build' else 'Sprawdzenie C++ poprawne' if kind=='check' else 'Flashowanie zakończone'
                else:j['phase']='Błąd — sprawdź log PlatformIO'
    except Exception as e:
        with LOCK:
            j=JOBS[jobid]
            j['state']='cancelled' if j['cancel_requested'] else 'failed'
            j['phase']='Kompilacja przerwana' if j['cancel_requested'] else 'Błąd kompilacji lub wgrywania'
            j['log']+='\n'+repr(e)+'\n'
    finally:
        with LOCK:RUNNING_PROCS.pop(jobid,None)


def make_job(args,cwd,kind,env):
    jobid=uuid.uuid4().hex[:12]
    with LOCK:JOBS[jobid]={'state':'queued','kind':kind,'log':'','env':env,'exitcode':None,'file':None,'progress':0,'phase':'Oczekiwanie','accurate':False,'created':time.time(),'cancel_requested':False}
    threading.Thread(target=job_worker,args=(jobid,args,cwd,kind),daemon=True).start()
    return jobid


class Handler(BaseHTTPRequestHandler):
    def json_out(self,status,obj):
        body=json.dumps(obj,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
    def binary_out(self,data,mimetype,filename):
        self.send_response(200)
        self.send_header('Content-Type',mimetype)
        self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(data)
    def do_GET(self):
        path=unquote(urlsplit(self.path).path)
        # Local, read-only gallery. IDs are resolved exclusively from the trusted
        # catalog, never interpolated into a filesystem path from the request.
        if path=='/api/examples':
            try:
                catalog=json.loads((ROOT/'katalog_przykladow.json').read_text(encoding='utf-8'))
                return self.json_out(200,catalog)
            except (OSError,ValueError) as e:
                return self.json_out(500,{'error':'Katalog przykładów: '+str(e)})
        if path.startswith('/api/example/'):
            ident=path.split('/')[-1]
            if not re.fullmatch(r'[0-9]{2}',ident):
                return self.json_out(404,{'error':'Nieznany przykład.'})
            try:
                catalog=json.loads((ROOT/'katalog_przykladow.json').read_text(encoding='utf-8'))
                item=next((e for e in catalog['examples'] if e['id']==ident),None)
                if not item:return self.json_out(404,{'error':'Brak przykładu.'})
                filename=item['file']
                if not re.fullmatch(r'[0-9]{2}_[A-Za-z0-9_-]+\.json',filename):
                    return self.json_out(500,{'error':'Nieprawidłowa nazwa przykładu.'})
                project=json.loads((ROOT/'examples'/filename).read_text(encoding='utf-8'))
                if not isinstance(project.get('devices'),list) or not project['devices']:
                    return self.json_out(500,{'error':'Niekompletny przykład.'})
                return self.json_out(200,{'project':project,'title':item['title']})
            except (OSError,ValueError) as e:
                return self.json_out(500,{'error':'Błąd odczytu przykładu: '+str(e)})
        if path=='/api/m5stack/catalog':
            query=urllib.parse.parse_qs(urlsplit(self.path).query)
            force=query.get('refresh',['0'])[0]=='1'
            return self.json_out(200,fetch_m5stack_catalog(force=force))
        if path=='/api/status':
            pio=find_pio();return self.json_out(200,{'online':True,'pio':bool(pio),'pio_path':pio})
        if path=='/api/ports':
            return self.json_out(200,detect_serial_ports())
        if path.startswith('/api/job/'):
            jobid=path.rsplit('/',1)[-1]
            with LOCK:j=JOBS.get(jobid)
            if not j:return self.json_out(404,{'error':'Nie znaleziono zadania.'})
            return self.json_out(200,{k:v for k,v in j.items() if k!='file'}|{'ready':bool(j.get('file'))})
        if path.startswith('/api/bin/'):
            jobid=path.rsplit('/',1)[-1]
            with LOCK:j=JOBS.get(jobid)
            if not j or j.get('state')!='success' or not j.get('file'):
                return self.json_out(404,{'error':'Nie ma poprawnie zbudowanego BIN.'})
            f=Path(j['file'])
            if not f.is_file():return self.json_out(404,{'error':'Plik BIN nie istnieje.'})
            data=f.read_bytes()
            self.send_response(200);self.send_header('Content-Type','application/octet-stream')
            self.send_header('Content-Disposition',f'attachment; filename="{f.parent.parent.parent.name}_firmware.bin"')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        if path=='/sim-fft-rf':
            data=(ROOT/'SIMULATOR_FFT_WATERFALL.html').read_bytes()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data);return
        if path=='/' or path=='/index.html':
            data=(ROOT/'index.html').read_bytes()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data);return
        if path=='/favicon.ico':self.send_response(204);self.end_headers();return
        return self.json_out(404,{'error':'Nie znaleziono.'})

    def do_POST(self):
        path=urlsplit(self.path).path
        origin=self.headers.get('Origin','')
        if origin and not (re.fullmatch(r'https?://(localhost|127\.0\.0\.1)(:\d+)?',origin)):
            return self.json_out(403,{'error':'Dostęp tylko z lokalnej strony CYD Studio.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<2 or length>MAX_BODY:raise ValueError('Nieprawidłowa wielkość projektu.')
            request=json.loads(self.rfile.read(length).decode('utf-8'))
            if not isinstance(request,dict):raise ValueError('Nieprawidłowy format JSON.')
            if path=='/api/export':
                data=portable_zip(request.get('project'))
                return self.binary_out(data,'application/zip','CYD_Studio_Portable_Project.zip')
            if path=='/api/svg':
                d,_=validate_device(request.get('project'),request.get('device_id'))
                sc=next((x for x in d.get('scenes',[]) if x.get('id')==request.get('scene_id')),None)
                if not sc:raise ValueError('Screen not found.')
                data=screen_svg(sc,d.get('rotation',0))
                return self.binary_out(data,'image/svg+xml',identifier(sc.get('name','screen'))+'.svg')
            if path=='/api/import':
                encoded=request.get('zip_base64','')
                if not isinstance(encoded,str) or len(encoded)>3_600_000:raise ValueError('ZIP file too large.')
                raw=base64.b64decode(encoded,validate=True)
                if len(raw)>2_600_000:raise ValueError('ZIP file too large.')
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    info=archive.getinfo('project.json')
                    if info.file_size>MAX_BODY:raise ValueError('Project JSON too large.')
                    project=portable_project(json.loads(archive.read(info)))
                return self.json_out(200,{'project':project})
            if path=='/api/github/inspect':
                lib=inspect_github_library(request.get('url',''))
                return self.json_out(200,{'library':lib})
            if path=='/api/source':
                device,profile=validate_device(request['project'],request['device_id'])
                code=generate_cpp(device,profile)
                return self.json_out(200,{'code':code})
            if path=='/api/validate':
                device,profile=validate_device(request['project'],request['device_id'])
                code=generate_cpp(device,profile)
                auto_fft=bool(re.search(r'CYD_AUTO_FFT:.*?GPIO\d+',code))
                return self.json_out(200,{'valid':True,'message':'Generator: OK. Full C++ compilation requires Check C++.', 'lines':len(code.splitlines()), 'auto_fft':auto_fft})
            if path=='/api/cancel':
                return self.json_out(200,cancel_build(str(request.get('job_id',''))))
            pio=find_pio()
            if not pio:raise ValueError('PlatformIO not found. Check installation.')
            if path=='/api/check':
                d,p=generate_project(request['project'],request['device_id'])
                jobid=make_job([pio,'run','-d',str(d)],d,'check',p['board'])
                return self.json_out(202,{'job_id':jobid,'project_path':str(d)})
            if path=='/api/build':
                d,p=generate_project(request['project'],request['device_id'])
                jobid=make_job([pio,'run','-d',str(d)],d,'build',p['board'])
                return self.json_out(202,{'job_id':jobid,'project_path':str(d)})
            if path=='/api/flash':
                device_id=str(request.get('device_id',''))
                port=str(request.get('port','')).strip()
                if not re.fullmatch(r'(COM\d{1,3}|/dev/(tty(USB|ACM|S)\d+|cu\.[\w.-]+))',port,re.IGNORECASE):
                    raise ValueError('Wpisz poprawny port, np. COM4.')
                d,p=generate_project(request['project'],device_id)
                jobid=make_job([pio,'run','-d',str(d),'-t','upload','--upload-port',port],d,'flash',p['board'])
                return self.json_out(202,{'job_id':jobid,'project_path':str(d)})
            return self.json_out(404,{'error':'Nieznana operacja.'})
        except (ValueError,KeyError,TypeError,zipfile.BadZipFile,base64.binascii.Error) as e:return self.json_out(400,{'error':str(e)})
        except Exception as e:return self.json_out(500,{'error':repr(e)})

    def log_message(self,fmt,*args): pass


def main():
    port=int(os.environ.get('CYD_STUDIO_PORT','8765'))
    try:
        server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    except OSError as e:
        print(f'BLAD: Port {port} jest zajety lub niedostepny: {e}',flush=True)
        print('Zamknij poprzednie okno CYD Studio albo wybierz inny CYD_STUDIO_PORT.',flush=True)
        raise SystemExit(1)
    print(f'CYD STUDIO: http://127.0.0.1:{port}',flush=True)
    print('PlatformIO: '+(find_pio() or 'NIE ZNALEZIONO'),flush=True)
    print('Kompilacja i flashowanie: USB musi byc podlaczone do TEGO komputera.',flush=True)
    if os.environ.get('CYD_STUDIO_NO_BROWSER') != '1':
        webbrowser.open(f'http://127.0.0.1:{port}')
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()