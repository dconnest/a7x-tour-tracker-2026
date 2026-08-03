#!/usr/bin/env python3
import datetime as dt, html, json, os, sys, urllib.request
from pathlib import Path

ROOT=Path(__file__).parent
API='https://api.setlist.fm/rest/1.0'
MBID='24e1b53c-3085-4581-8472-0b0088d2508c'
START=dt.date(2026,7,25)
COUNTRIES={'US','CA'}
TOTAL=16

def get_json(path,key):
    req=urllib.request.Request(API+path,headers={'Accept':'application/json','X-Api-Key':key,'User-Agent':'A7XTourTracker/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def event_date(s):return dt.datetime.strptime(s,'%d-%m-%Y').date()

def flatten(item):
    songs=[]; tapes=[]
    for group in item.get('sets',{}).get('set',[]):
        for s in group.get('song',[]):
            name=(s.get('name') or '').strip()
            if not name:continue
            if s.get('tape'):tapes.append(name);continue
            songs.append({'name':name,'info':(s.get('info') or '').strip(),'encore':group.get('encore')})
    return songs,tapes

def normalize(item):
    try:d=event_date(item['eventDate'])
    except:return None
    venue=item.get('venue') or {}; city=venue.get('city') or {}; country=city.get('country') or {}
    code=(country.get('code') or '').upper()
    if d<START or code not in COUNTRIES:return None
    songs,tapes=flatten(item)
    if not songs:return None
    return {'id':item.get('id',''),'version':item.get('versionId',''),'date':d.isoformat(),'display_date':d.strftime('%B %d, %Y').replace(' 0',' '),'venue':venue.get('name') or 'Unknown venue','city':city.get('name') or 'Unknown city','state':city.get('state') or city.get('stateCode') or '','country':country.get('name') or code,'url':item.get('url') or '','songs':songs,'tape_tracks':tapes}

def fetch(key):
    found={}
    for page in range(1,7):
        items=get_json(f'/artist/{MBID}/setlists?p={page}',key).get('setlist',[])
        if not items:break
        dates=[]
        for item in items:
            try:dates.append(event_date(item['eventDate']))
            except:pass
            n=normalize(item)
            if n and (n['date'],n['venue']) not in found:found[(n['date'],n['venue'])]=n
        if dates and max(dates)<START:break
    shows=sorted(found.values(),key=lambda x:(x['date'],x['venue']))
    for i,s in enumerate(shows,1):s['number']=i
    return shows

def names(show):return [x['name'] for x in show['songs']]
def similarity(a,b):
    a,b=set(a),set(b); return round(100*len(a&b)/len(a|b)) if a|b else 100

def enrich(shows):
    seen=set()
    for i,s in enumerate(shows):
        cur=names(s); prev=names(shows[i-1]) if i else []
        s['set_length']=len(cur); s['opener']=cur[0]; s['closer']=cur[-1]
        s['tour_debuts']=[x for x in cur if x not in seen]
        s['live_debuts']=[x['name'] for x in s['songs'] if 'live debut' in x.get('info','').lower()]
        if i:
            s['added']=[x for x in cur if x not in prev]; s['dropped']=[x for x in prev if x not in cur]
            s['returned']=[x for x in s['added'] if any(x in names(old) for old in shows[:i-1])]
            s['similarity']=similarity(cur,prev)
        else:s['added']=[];s['dropped']=[];s['returned']=[];s['similarity']=None
        seen.update(cur)

def stats(shows):
    order=[]
    for s in shows:
        for n in names(s):
            if n not in order:order.append(n)
    out=[]
    for n in order:
        appearances=[];positions=[]
        for s in shows:
            ns=names(s)
            if n in ns:appearances.append(s['number']);positions.append(ns.index(n)+1)
        streak=0
        for s in reversed(shows):
            if n in names(s):streak+=1
            else:break
        out.append({'name':n,'appearances':len(appearances),'rate':round(100*len(appearances)/len(shows)) if shows else 0,'streak':streak,'average_position':round(sum(positions)/len(positions),1)})
    return sorted(out,key=lambda x:(-x['appearances'],x['name'].lower()))

def esc(x):return html.escape(str(x),quote=True)
def loc(s):return f"{s['city']}, {s['state'] or s['country']}"

def render(data):
    shows=data['shows']; ss=data['song_stats']; latest=shows[-1] if shows else None
    progress=round(100*len(shows)/TOTAL,1); unique=len(ss); avg=round(sum(x['set_length'] for x in shows)/len(shows),1) if shows else 0
    added=', '.join(latest['added']) if latest else ''; dropped=', '.join(latest['dropped']) if latest else ''; returned=', '.join(latest['returned']) if latest else ''
    sim=(str(latest['similarity'])+'%') if latest and latest['similarity'] is not None else '—'
    cards=''.join(f"<article class='card'><small>Show #{s['number']} · {esc(s['display_date'])}</small><h3>{esc(s['venue'])}</h3><p>{esc(loc(s))}</p><p>{esc('Added: '+(', '.join(s['added']) or 'None')+' · Dropped: '+(', '.join(s['dropped']) or 'None'))}</p><a href='{esc(s['url'])}' target='_blank'>setlist.fm source ↗</a></article>" for s in reversed(shows))
    setlist=''.join(f"<div class='song' data-song='{esc(x['name'].lower())}'><b>{i}</b><span><strong>{esc(x['name'])}</strong><small>{esc(' · '.join(([ 'Opener' ] if i==1 else [])+([ 'Closer' ] if i==len(latest['songs']) else [])+([ 'Tour debut' ] if x['name'] in latest['tour_debuts'] else [])+([x['info']] if x.get('info') else [])) or 'Latest show')}</small></span></div>" for i,x in enumerate(latest['songs'],1)) if latest else '<p>Waiting for a completed setlist.</p>'
    rows=''.join(f"<div class='row'><strong>{esc(x['name'])}</strong><span>{x['appearances']}</span><span>{x['rate']}%</span><span>{x['streak']}</span><span>{x['average_position']}</span></div>" for x in ss)
    heat_header=''.join(f"<b>#{s['number']}</b>" for s in shows)
    heat=''.join("<div class='heatrow'><span>"+esc(x['name'])+"</span>"+''.join("<i class='on'>✓</i>" if x['name'] in names(s) else '<i></i>' for s in shows)+"</div>" for x in ss)
    history=''.join(f"<div class='event'><b>{esc(dt.date.fromisoformat(s['date']).strftime('%b %d').upper())}</b><span><strong>{esc(s['venue'])}</strong><small>{esc(('Added: '+', '.join(s['added'])+'; ' if s['added'] else '')+('Dropped: '+', '.join(s['dropped']) if s['dropped'] else 'No changes from previous show' if s['number']>1 else 'Tour opener'))}</small></span></div>" for s in shows)
    latest_title=esc(latest['venue']) if latest else 'Waiting for data'; latest_meta=esc(loc(latest)+' · '+latest['display_date']) if latest else 'Automatic updater connected'
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>A7X Tour Tracker 2026</title><style>
:root{{--bg:#07080b;--panel:#13151c;--line:#2c3039;--text:#f6f7fb;--muted:#9ca3af;--red:#df252d}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:radial-gradient(circle at 85% 0,rgba(223,37,45,.18),transparent 30%),var(--bg);color:var(--text);font-family:system-ui}}a{{color:#ff747a}}.shell{{width:min(1150px,calc(100% - 32px));margin:auto}}header{{position:sticky;top:0;background:#08090ddd;border-bottom:1px solid var(--line);z-index:5}}nav{{min-height:68px;display:flex;align-items:center;justify-content:space-between}}nav div{{display:flex;gap:18px}}nav a{{color:var(--muted);text-decoration:none}}.hero{{padding:80px 0 42px}}h1{{font-size:clamp(45px,8vw,84px);line-height:.94;margin:10px 0}}.red,.eyebrow{{color:#ff5b63}}.eyebrow{{text-transform:uppercase;letter-spacing:.18em;font-size:12px;font-weight:800}}.lead,.muted,small{{color:var(--muted)}}section{{padding:34px 0}}.grid{{display:grid;gap:15px}}.stats{{grid-template-columns:repeat(4,1fr)}}.features{{grid-template-columns:1.35fr 1fr}}.cards{{grid-template-columns:repeat(3,1fr)}}.card,.panel,.stat{{background:linear-gradient(#191c24,#111318);border:1px solid var(--line);border-radius:17px;padding:20px}}.stat strong{{display:block;font-size:40px;margin:8px 0}}.progress{{height:11px;background:#292d36;border-radius:99px;overflow:hidden}}.progress i{{display:block;height:100%;width:{progress}%;background:var(--red)}}.change{{border-left:3px solid var(--red);padding:14px;background:#df252d14}}.compare{{grid-template-columns:repeat(4,1fr)}}.compare .card{{text-align:center}}.compare strong{{font-size:26px;display:block;word-break:break-word}}.head{{display:flex;justify-content:space-between;align-items:end;gap:15px;margin-bottom:15px}}input{{padding:11px;border-radius:10px;border:1px solid var(--line);background:#0d0f14;color:white}}.setlist{{grid-template-columns:repeat(2,1fr)}}.song{{display:flex;gap:13px;background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:13px}}.song>b{{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:#df252d22;color:#ff858a}}.song span strong,.song span small{{display:block}}.table{{border:1px solid var(--line);border-radius:15px;overflow:hidden}}.row{{display:grid;grid-template-columns:2fr repeat(4,1fr);padding:14px 18px;border-top:1px solid var(--line);background:var(--panel)}}.row:first-child{{border-top:0}}.heatwrap{{overflow-x:auto}}.heat{{min-width:max(700px,calc(220px + {max(1,len(shows))} * 60px));display:grid;grid-template-columns:220px repeat({max(1,len(shows))},52px);gap:7px;align-items:center}}.heatrow{{display:contents}}.heat i{{height:34px;border-radius:6px;background:#242832;display:grid;place-items:center;font-style:normal}}.heat i.on{{background:var(--red)}}.event{{display:grid;grid-template-columns:90px 1fr;gap:15px;padding:12px 0;border-bottom:1px solid var(--line)}}.event span strong,.event span small{{display:block}}footer{{padding:30px 0;border-top:1px solid var(--line);color:var(--muted)}}.hidden{{display:none!important}}@media(max-width:850px){{nav div{{display:none}}.stats,.compare{{grid-template-columns:repeat(2,1fr)}}.features,.cards{{grid-template-columns:1fr}}}}@media(max-width:600px){{.stats,.compare,.setlist{{grid-template-columns:1fr}}.row{{grid-template-columns:1fr 50px 50px}}.row span:nth-last-child(-n+2){{display:none}}}}
</style></head><body><header><nav class="shell"><strong>A7X TOUR TRACKER 2026</strong><div><a href="#shows">Shows</a><a href="#songs">Songs</a><a href="#heat">Heat map</a><a href="#history">History</a></div></nav></header><main><div class="shell"><div class="hero"><p class="eyebrow">North American Tour 2026</p><h1>Every show.<br>Every song.<br><span class="red">Every change.</span></h1><p class="lead">Automatically updated from confirmed setlist.fm data.</p></div><section><div class="grid stats"><div class="stat"><small>Shows completed</small><strong>{len(shows)} / {TOTAL}</strong></div><div class="stat"><small>Unique songs</small><strong>{unique}</strong></div><div class="stat"><small>Average set length</small><strong>{avg}</strong></div><div class="stat"><small>Latest similarity</small><strong>{sim}</strong></div></div><div class="grid features" style="margin-top:15px"><div class="panel"><p class="eyebrow">Latest completed show</p><h2>{latest_title}</h2><p class="muted">{latest_meta}</p><div class="change">Added: {esc(added or 'None')} · Dropped: {esc(dropped or 'None')} · Returned: {esc(returned or 'None')}</div></div><div class="panel"><p class="eyebrow">Tour progress</p><div class="progress"><i></i></div><h3>{len(shows)} of {TOTAL} shows complete</h3></div></div></section><section id="shows"><div class="head"><div><p class="eyebrow">Tracked shows</p><h2>Completed performances</h2></div></div><div class="grid cards">{cards or '<div class="panel">Waiting for setlist data.</div>'}</div></section><section><div class="head"><div><p class="eyebrow">Latest comparison</p><h2>What changed?</h2></div></div><div class="grid compare"><div class="card"><small>Added</small><strong>{esc(added or 'None')}</strong></div><div class="card"><small>Dropped</small><strong>{esc(dropped or 'None')}</strong></div><div class="card"><small>Returned</small><strong>{esc(returned or 'None')}</strong></div><div class="card"><small>Similarity</small><strong>{sim}</strong></div></div></section><section><div class="head"><div><p class="eyebrow">Latest setlist</p><h2>Running order</h2></div><input id="search" placeholder="Search songs..."></div><div class="grid setlist">{setlist}</div></section><section id="songs"><div class="head"><div><p class="eyebrow">Song database</p><h2>Current rotation</h2></div></div><div class="table">{rows}</div></section><section id="heat"><div class="head"><div><p class="eyebrow">Heat map</p><h2>Song usage by show</h2></div></div><div class="panel heatwrap"><div class="heat"><span></span>{heat_header}{heat}</div></div></section><section id="history"><div class="head"><div><p class="eyebrow">Tour history</p><h2>The story so far</h2></div></div><div class="panel">{history}</div></section></div></main><footer><div class="shell">Unofficial fan project. Not affiliated with Avenged Sevenfold. Data sourced from setlist.fm.</div></footer><script>const q=document.getElementById('search');if(q)q.addEventListener('input',()=>document.querySelectorAll('.song').forEach(x=>x.classList.toggle('hidden',!x.dataset.song.includes(q.value.toLowerCase().trim()))));</script></body></html>'''

def main():
    key=os.environ.get('SETLIST_FM_API_KEY','').strip()
    if not key:raise SystemExit('SETLIST_FM_API_KEY is missing')
    shows=fetch(key);enrich(shows);data={'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'shows':shows,'song_stats':stats(shows)}
    (ROOT/'data').mkdir(exist_ok=True);(ROOT/'data/tour-data.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    (ROOT/'index.html').write_text(render(data));print(f'Updated with {len(shows)} shows')
if __name__=='__main__':main()
