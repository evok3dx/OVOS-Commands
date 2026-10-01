"""Bound the reviewed standalone weather skill to fixed provider operations.

Same-user code remains trusted. This is not a sandbox for malicious plugins.
"""
import json
from copy import deepcopy
from functools import wraps
import hashlib
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

MAX_BYTES=2*1024*1024
FORECAST='https://api.open-meteo.com/v1/forecast'
NOMINATIM='https://nominatim.openstreetmap.org/'
WEATHER_SOURCES={
    '__init__.py':'7eca96084ad5c4c8c3be44ffd7f2e9204f83ff339e791a393a4964f834cb22a9',
    'weather_helpers/intent.py':'844d3c476623a216826b6eacaa77a61c2022b117213a578b034282626e43fa9d',
    'weather_helpers/openmeteo.py':'c83d4e4ff633720dc266a21db4a5db48f61660979555aba9aca7b60c20536685',
}


def install_weather_skill():
    """Correct the exact pinned skill's requested-city forecast in memory.

    Upstream resolves the named city but passes the home configuration to
    get_report. Clone that request's configuration with its resolved coordinates
    and timezone. Never change the saved configuration or session location.
    Timings contain stage names only, never city/coordinate/query values.
    """
    import ovos_skill_weather as weather
    from ovos_utils.log import LOG
    root=Path(weather.__file__).parent
    for name,digest in WEATHER_SOURCES.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Weather source differs from the reviewed runtime')
    cls=weather.WeatherSkill
    if getattr(cls,'_jarvis_location_installed',False):return
    original=cls._get_intent_data

    @wraps(original)
    def intent_data(self,message):
        started=time.monotonic()
        try:
            result=original(self,message)
            if result is not None and result.location:
                geo=result.geolocation
                config=deepcopy(result.config)
                config.core_config['location']['coordinate']={
                    'latitude':coordinate(geo['latitude'],90),
                    'longitude':coordinate(geo['longitude'],180)}
                config.core_config['location']['timezone']={'code':geo['timezone']}
                result.config=config
            return result
        finally:LOG.info('Weather intent/location stage: %.2f seconds',time.monotonic()-started)
    cls._get_intent_data=intent_data

    def timed(name,function):
        @wraps(function)
        def call(self,*args,**kwargs):
            started=time.monotonic()
            try:return function(self,*args,**kwargs)
            finally:LOG.info('Weather %s stage: %.2f seconds',name,time.monotonic()-started)
        return call
    for name,stage in (('_get_weather','forecast'),('_display_current_conditions','display'),
                       ('_speak_weather','speech submission')):
        setattr(cls,name,timed(stage,getattr(cls,name)))
    cls._jarvis_location_installed=True


def coordinate(value,bound):
    if isinstance(value,bool):raise ValueError('Invalid coordinate')
    number=float(value)
    if not math.isfinite(number) or abs(number)>bound:raise ValueError('Invalid coordinate')
    return number


def parameters(url,values):
    if not isinstance(values,dict):raise ValueError('Weather parameters must be an object')
    data=dict(values)
    if url==FORECAST:
        if set(data)!={'latitude','longitude','hourly','daily','current_weather','temperature_unit',
                       'windspeed_unit','precipitation_unit','timezone'}:
            raise ValueError('Unknown forecast operation')
        data['latitude']=coordinate(data['latitude'],90);data['longitude']=coordinate(data['longitude'],180)
        for key in ('hourly','daily'):
            if not isinstance(data[key],str) or not re.fullmatch(r'[A-Za-z0-9_,]{1,3000}',data[key]):
                raise ValueError('Invalid forecast fields')
        if (data['current_weather'] is not True or data['temperature_unit'] not in {'celsius','fahrenheit'}
                or data['windspeed_unit'] not in {'kmh','ms','mph','kn'} or data['precipitation_unit'] not in {'mm','inch'}):
            raise ValueError('Invalid forecast units')
        zone=data['timezone']
        if not isinstance(zone,str) or len(zone)>64 or '..' in zone:raise ValueError('Invalid timezone')
        if zone not in {'gmt','GMT','UTC','auto'}:
            try:ZoneInfo(zone)
            except (ZoneInfoNotFoundError,ValueError):raise ValueError('Invalid timezone') from None
    elif url==NOMINATIM+'search':
        if set(data)!={'q','format','limit'} or data['format']!='json' or type(data['limit']) is not int or data['limit']!=1:
            raise ValueError('Unknown city lookup')
        text=data['q']
        if not isinstance(text,str) or not 1<=len(text.strip())<=160 or any(not(c.isalnum() or c in " ,.'-()") for c in text):
            raise ValueError('Invalid city lookup')
    elif url==NOMINATIM+'reverse':
        if set(data)!={'lat','lon','format'} or data['format']!='json':raise ValueError('Unknown reverse lookup')
        data['lat']=coordinate(data['lat'],90);data['lon']=coordinate(data['lon'],180)
    elif url==NOMINATIM+'details.php':
        if (set(data)!={'osmid','osmtype','format'} or data['format']!='json' or data['osmtype'] not in {'N','W','R'}
                or not re.fullmatch(r'[0-9]{1,20}',str(data['osmid']))):raise ValueError('Unknown place details')
    else:raise ValueError('Weather provider/path is not reviewed')
    return data


def validated(method,url,kwargs):
    if str(method).upper()!='GET' or set(kwargs)-{'params','headers','timeout','allow_redirects'}:
        raise ValueError('Only reviewed weather GET operations are allowed')
    data=parameters(url,kwargs.get('params'))
    headers=kwargs.get('headers') or {}
    if not isinstance(headers,dict) or set(headers)-{'User-Agent','Accept-Language'}:
        raise ValueError('Unreviewed weather headers')
    language=headers.get('Accept-Language','en')
    if not isinstance(language,str) or not re.fullmatch(r'[A-Za-z0-9,;= .*-]{1,64}',language):
        raise ValueError('Invalid language')
    return data,language


def fetch(original,session,url,data,language):
    import requests
    session.trust_env=False;session.auth=None;session.cert=None
    session.proxies.clear();session.cookies.clear();session.headers.clear()
    session.params={};session.hooks={'response':[]}
    response=original(session,'GET',url,params=data,headers={'User-Agent':'Jarvis-OVOS/4.0','Accept-Language':language},
                      timeout=(5,5),allow_redirects=False,stream=True,verify=True)
    try:
        if response.status_code!=200:raise requests.RequestException('Weather request failed')
        size=response.headers.get('Content-Length')
        if size and(not size.isdigit() or int(size)>MAX_BYTES):raise requests.RequestException('Weather response too large')
        body=bytearray()
        for chunk in response.iter_content(65536):
            body.extend(chunk)
            if len(body)>MAX_BYTES:raise requests.RequestException('Weather response too large')
        if not isinstance(json.loads(body),(dict,list)):raise requests.RequestException('Invalid weather response')
        response._content=bytes(body);response._content_consumed=True
        return response
    finally:response.close()


def request(session,method,url,**kwargs):
    import requests
    from ovos_utils.log import LOG
    started=time.monotonic()
    operation='validation'
    try:
        data,language=validated(method,url,kwargs)
        operation='forecast' if url==FORECAST else url.removeprefix(NOMINATIM)
        payload=json.dumps({'url':url,'params':data,'language':language})
        if len(payload.encode())>8192:raise ValueError('Request too large')
        env={key:value for key,value in os.environ.items() if not key.lower().endswith('_proxy')}
        result=subprocess.run([sys.executable,'-I',str(Path(__file__).resolve()),'--fetch'],input=payload,
                              capture_output=True,text=True,encoding='utf-8',timeout=14,env=env)
        if result.returncode or len(result.stdout.encode())>MAX_BYTES or not isinstance(json.loads(result.stdout),(dict,list)):
            raise ValueError('Invalid response')
    except (OSError,UnicodeError,ValueError,TypeError,subprocess.SubprocessError):
        raise requests.RequestException('Weather request unavailable') from None
    finally:LOG.info('Weather provider %s operation: %.2f seconds',operation,time.monotonic()-started)
    response=requests.Response();response.status_code=200;response.encoding='utf-8'
    response._content=result.stdout.encode();response._content_consumed=True
    return response


def install():
    import requests
    requests.sessions.Session.request=request
    install_weather_skill()


def main():
    if sys.argv[1:]!=['--fetch'] or os.getuid()<=0 or os.geteuid()!=os.getuid() or os.getgid()!=os.getegid():
        raise ValueError('Internal ordinary-user weather operation only')
    props=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    expected=f'0::/system.slice/jarvis-v4-{os.getuid()}-weather.service'
    if int(props.get('CapEff','-1').strip(),16) or props.get('NoNewPrivs','').strip()!='1' or expected not in Path('/proc/self/cgroup').read_text().splitlines():
        raise ValueError('Weather operation context unverified')
    raw=sys.stdin.buffer.read(8193)
    if len(raw)>8192:raise ValueError('Request too large')
    payload=json.loads(raw)
    if not isinstance(payload,dict) or set(payload)!={'url','params','language'}:raise ValueError('Unknown operation')
    data,language=validated('GET',payload['url'],{'params':payload['params'],'headers':{'Accept-Language':payload['language']}})
    import requests
    with requests.Session() as session:
        response=fetch(requests.sessions.Session.request,session,payload['url'],data,language)
    sys.stdout.buffer.write(response.content)


if __name__=='__main__':
    try:main()
    except Exception:raise SystemExit('Bounded weather operation failed') from None
