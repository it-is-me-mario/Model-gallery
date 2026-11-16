"""Validate study editions and render GitHub pages or an offline Sphinx export."""
import argparse
import hashlib
from html import escape as esc
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
LEGACY = {
    'tutorials': ('MARIO tutorials', 'https://tutorials.marioproject.com/'),
    'crash-course': ('MARIO crash course', 'https://github.com/it-is-me-mario/Crash-course'),
    'mrio-disaggregation': ('Disaggregate MRIOs', 'https://tutorials.marioproject.com/'),
}
ICONS = {
    'steel': '<path d="M3 21V10l6 4V8l7 4V3h4v18H3Z"/><path d="M7 17h1m4 0h1m4 0h1"/>',
    'pv': '<path d="m5 10-2 10h18l-2-10H5Zm-1 5h16M10 10l-1 10m5-10 1 10M12 2v3M4 4l2 2m14-2-2 2"/>',
    'sufficiency': '<path d="m3 11 9-8 9 8M5 10v11h14V10M10 21v-7h4v7"/>',
    'electricity': '<path d="m13 2-9 12h7l-1 8 10-12h-7l1-8Z"/>',
}

def load_catalog():
    c=json.loads((ROOT/'catalog/models.json').read_text())
    schema=json.loads((ROOT/'catalog/schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(c)
    for collection in ('families','studies','foundations'):
        ids=[x['id'] for x in c[collection]]
        if len(ids)!=len(set(ids)): raise ValueError(f'Duplicate {collection} id')
    ids={s['id'] for s in c['studies']}
    families={f['id'] for f in c['families']}
    dois=[s['publication']['doi'] for s in c['studies']]
    if len(dois)!=len(set(dois)): raise ValueError('Each publication needs one study record')
    for s in c['studies']:
        if s['family'] not in families: raise ValueError('Unknown family')
        if any(r not in ids or r==s['id'] for r in s['related']): raise ValueError('Invalid related study')
        edition_ids=[e['id'] for e in s['editions']]
        if len(edition_ids)!=len(set(edition_ids)): raise ValueError('Duplicate edition id')
        for e in s['editions']:
            if e['role']=='unmapped':
                if e['source'] is not None or e['data']: raise ValueError('Unmapped editions cannot claim code or data')
            elif e['source'] is None: raise ValueError('Mapped editions require a pinned source')
            if e['source']:
                p=e['source']['entrypoint']
                if p and (p.startswith('/') or '..' in Path(p).parts): raise ValueError('Unsafe source entrypoint')
    return c

def href(src):
    suffix='/blob/'+src['commit']+'/'+quote(src['entrypoint'],safe='/') if src['entrypoint'] else '/tree/'+src['commit']
    return src['repository']+suffix

def link(label,url,web=False):
    return f'`{label} <{url}>`__' if web else f'[{label}]({url})'

def heading(title,level=1,web=False):
    return title+'\n'+('=-~'[level-1]*len(title))+'\n\n' if web else '#'*level+' '+title+'\n\n'

def publication(p,web=False):
    return ', '.join(p['authors'])+f" ({p['year']}). "+link(p['title'],'https://doi.org/'+p['doi'],web)+'. *'+p['journal']+'*.\n\n'

def detail(s,c,web=False):
    p=s['publication']
    out=(f":page-type: Research model\n:summary: {s['summary']}\n\n" if web else '')+heading(s['title'],web=web)
    out+=publication(p,web)+s['summary']+'\n\n'
    out+=heading('Model and scope',2,web)+s['contribution']+'\n\n'+s['scope']+'\n\n'
    out+=heading('Database',2,web)+s['data_lineage']+'\n\n'
    out+=(':doc:`Database lineage <databases>`' if web else '[Database lineage](../databases.md)')+'\n\n'
    if s['id']=='pv-hlca':
        out+=heading('PV reconstruction results',2,web)
        url='https://raw.githubusercontent.com/it-is-me-mario/pv-hlca-model/28a444dfb966887534ec6963dd3db8b7f5fee6b4/outputs/figures/Figure3.png'
        caption='PV electricity footprints in g CO2eq/kWh, decomposed by activity and region of origin (top), and the relative contributions in the hybrid and top-down calculations (bottom). Figure 3 from the recorded PV repository revision; these are existing reconstruction outputs, not a new gallery execution.'
        if web:
            out+='.. figure:: assets/pv-reconstruction.png\n   :alt: PV electricity footprints by producing region, with activity and origin contributions.\n   :width: 100%\n\n   '+caption+'\n\n'
        else:
            out+='![PV electricity footprints](../assets/pv-reconstruction.png)\n\n'+caption+'\n\n'
        out+=link('Original figure',url,web)+'\n\n'
    out+=heading('Available editions',2,web)
    for e in s['editions']:
        out+=heading(e['label'],3,web)+e['scope']+'\n\n'
        if e['source']:
            src=e['source']
            out+=link('Code and instructions',href(src),web)+' · '+link('Recorded revision '+src['commit'][:8],src['repository']+'/tree/'+src['commit'],web)+'\n\n'
        if e['mario']:out+='MARIO version: **'+e['mario']+'**.\n\n'
        for d in e['data']:out+='* '+link(d['label'],d['url'],web)+'\n'
        if e['data']:out+='\n'
        out+=e['limitations']+'\n\n'
        for evidence in e['evidence']:out+='* '+link(evidence['label'],evidence['url'],web)+'\n'
        if e['evidence']:out+='\n'
    if s['related']:
        out+=heading('Related studies',2,web)
        for id in s['related']:
            r=next(x for x in c['studies'] if x['id']==id)
            out+=('* :doc:`'+r['title']+' <'+id+'>`\n' if web else '* '+link(r['title'],id+'.md')+'\n')
        out+='\n'
    out+='Source review: '+c['updated_at']+'. Models have not been rerun by the gallery. Execution evidence linked above belongs to the source maintainers.\n\n'
    out+=(':doc:`All models <index>`' if web else '[All models](../README.md)')+'\n'
    return out

def databases(c,web=False):
    out=(":page-type: Explanation\n:summary: Historical database editions and shared foundations of MARIO research models.\n\n" if web else '')+heading('Database lineage',web=web)
    out+='A shared database connects studies without making their assumptions, code or results interchangeable. The editions on each study page identify the inputs actually documented by its authors.\n\n'
    for d in c['foundations']:
        out+=heading(d['title'],2,web)+d['description']+'\n\n'+link('Source and data',d['url'],web)+'\n\n'
    out+=heading('Relationships between studies',2,web)
    out+='The 2024 EU steel study introduces technology extensions to EXIOBASE Hybrid. Later Green steel releases broaden those extensions. The GCAM–MARIO workflow uses the steel modelling line; the PV model adds its own supply chain and regional aggregation. FULFILL develops a separate preparation from EXIOBASE Hybrid.\n\n'
    out+=link('PV archive: documented relationship to Green steel','https://zenodo.org/records/20734983',web)+' · '+link('NXSUT methods and source','https://github.com/eNextHub/nxsut',web)+'\n\n'
    out+=heading('Future editions using NXSUT',2,web)
    out+='NXSUT is a candidate shared background for future development. Such an edition would need its own assumptions and comparison with reference results. Historical study releases remain available with their original inputs.\n\n'
    out+=(':doc:`All models <index>`' if web else '[All models](README.md)')+'\n'
    return out

def index(c,web=False):
    out=(":page-type: Research models\n:summary: Research models built with MARIO, organised by application and publication.\n\n" if web else '')+heading('Model gallery',web=web)
    out+='Research models built with MARIO. Find the study, its modelling assumptions, and the available code and data.\n\n'
    if web:
        html=['<div class="mg-families">']
        for f in c['families']:
            html.append(f'<section class="mg-family" aria-labelledby="family-{f["id"]}"><div class="mg-heading"><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[f["id"]]}</svg><h2 id="family-{f["id"]}">{esc(f["title"])}</h2></div><p>{esc(f["summary"])}</p><ul>')
            for s in c['studies']:
                if s['family']!=f['id']:continue
                p=s['publication'];name=p['authors'][0].split()[-1]
                html.append(f'<li><a href="{s["id"]}.html"><strong>{esc(s["title"])}</strong><span>{esc(name)} et al. · {p["year"]}</span><span class="mg-arrow" aria-hidden="true">→</span></a></li>')
            html.append('</ul></section>')
        html.append('</div>')
        out+='.. raw:: html\n\n'+'\n'.join('   '+x for x in html)+'\n\n'
    else:
        for f in c['families']:
            out+=heading(f['title'],2)+f['summary']+'\n\n'
            for s in c['studies']:
                if s['family']==f['id']:out+='* '+link(s['title'],'models/'+s['id']+'.md')+f" — {s['publication']['year']}. "+s['summary']+'\n'
            out+='\n'
    out+=heading('Shared databases',2,web)
    out+='Steel, photovoltaic and sufficiency studies share roots in EXIOBASE Hybrid, with different extensions and historical editions. NXSUT provides a possible common background for future development.\n\n'
    out+=(':doc:`Follow the database lineage <databases>`' if web else '[Follow the database lineage](databases.md)')+'\n\n'
    out+=heading('Learning resources',2,web)
    out+=link('Tutorials','https://tutorials.marioproject.com/',web)+' and the '+link('MARIO crash course','https://github.com/it-is-me-mario/Crash-course',web)+' provide worked exercises and teaching material.\n\n'
    if web:
        out+='.. toctree::\n   :hidden:\n\n'+''.join('   '+s['id']+'\n' for s in c['studies'])+'   databases\n'
    else:
        out+='[Contributing](CONTRIBUTING.md) · [Catalog data](catalog/models.json)\n'
    return out

def outputs(c):
    pages={ROOT/'README.md':index(c),ROOT/'databases.md':databases(c)}
    pages.update({ROOT/'models'/f'{s["id"]}.md':detail(s,c) for s in c['studies']})
    for id,(title,url) in LEGACY.items():
        pages[ROOT/'models'/f'{id}.md']=heading(title)+'This learning resource is available at '+link(title,url)+'.\n\n[Model gallery](../README.md)\n'
    return pages

def export(c,dest):
    dest.mkdir(parents=True,exist_ok=True)
    pages={'index.rst':index(c,True),'databases.rst':databases(c,True)}
    pages.update({s['id']+'.rst':detail(s,c,True) for s in c['studies']})
    for name,content in pages.items(): (dest/name).write_text(content)
    (dest/'assets').mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'assets/pv-reconstruction.png',dest/'assets/pv-reconstruction.png')
    manifest={'repository':'https://github.com/it-is-me-mario/Model-gallery',
        'source_revision': None if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip() else subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'catalog_sha256':hashlib.sha256((ROOT/'catalog/models.json').read_bytes()).hexdigest(),
        'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'files':{n:hashlib.sha256(v.encode()).hexdigest() for n,v in pages.items()}}
    manifest['files']['assets/pv-reconstruction.png']=hashlib.sha256((ROOT/'assets/pv-reconstruction.png').read_bytes()).hexdigest()
    (dest/'catalog-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['build','check','export-sphinx'])
    p.add_argument('--output',type=Path)
    args=p.parse_args();c=load_catalog()
    if args.command=='export-sphinx':
        if not args.output:p.error('--output is required')
        export(c,args.output)
    else:
        stale=[]
        for path,content in outputs(c).items():
            if args.command=='build':path.write_text(content)
            elif not path.exists() or path.read_text()!=content:stale.append(str(path.relative_to(ROOT)))
        if stale:raise SystemExit('Regenerate pages: '+', '.join(stale))
    print(f"Catalog valid: {len(c['studies'])} studies in {len(c['families'])} families.")
if __name__=='__main__':main()
