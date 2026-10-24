"""Validate the catalog and generate the README and model pages."""
import argparse
import json
from pathlib import Path
from urllib.parse import quote
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
LABELS = {'setup-documented':'Setup documented','setup-needed':'Setup to document','update-needed':'Example update needed'}
KINDS = {'learning-resource':'Learning resources','method-example':'Modelling methods','research-model':'Research models'}

def load_catalog():
    catalog = json.loads((ROOT/'catalog/models.json').read_text())
    schema = json.loads((ROOT/'catalog/schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(catalog),key=lambda e:list(map(str,e.path)))
    if errors:
        raise ValueError('\n'.join(f'{list(e.path)}: {e.message}' for e in errors))
    ids = [m['id'] for m in catalog['models']]
    if len(ids) != len(set(ids)):
        raise ValueError('Model ids must be unique')
    for m in catalog['models']:
        source = m['source']
        if source['entrypoint'] and (source['entrypoint'].startswith('/') or '..' in Path(source['entrypoint']).parts):
            raise ValueError(f"Invalid entrypoint in {m['id']}")
        if source['repository'].split('/')[-2] != source['owner']:
            raise ValueError(f"Source owner mismatch in {m['id']}")
        execution = m['execution']
        if (execution['status']=='not-run') != (execution['verified_at'] is None):
            raise ValueError(f"Execution date must match verification status in {m['id']}")
        if execution['status']!='not-run':
            raise ValueError('Add the execution evidence contract before publishing verified records')
    return catalog

def revision_url(m):
    s=m['source']
    return f"{s['repository']}/tree/{s['commit']}"

def entry_url(m):
    s=m['source']
    return f"{s['repository']}/blob/{s['commit']}/{quote(s['entrypoint'],safe='/')}" if s['entrypoint'] else revision_url(m)

def card(m):
    s=m['source']
    out=[f"# {m['title']}\n\n",f"{m['summary']}\n\n",
         f"[Source repository]({s['repository']}) · [Starting point]({entry_url(m)}) · [Back to the gallery](../README.md)\n\n",
         '## What you can learn\n\n']
    out += [f'- {x}\n' for x in m['what_to_learn']]
    out += ['\n## Before you run it\n\n',f"**{LABELS[m['readiness']['status']]}.** {m['readiness']['notes']}\n\n",
            f"MARIO distribution: `mariopy`; version: **{m['mario']['version'] or 'not pinned in this catalog'}**.\n\n"]
    for d in m['data']:
        out.append(f"- [{d['name']}]({d['url']}) — {d['notes']}\n")
    if m['publications']:
        out.append('\n## Publications\n\n')
        for p in m['publications']:
            note=' **Study association to confirm.**' if p['association']=='candidate' else ''
            out.append(f"- [{p['title']}](https://doi.org/{p['doi']}).{note}\n")
    if m['links']:
        out.append('\n## Further resources\n\n')
        out += [f"- [{l['label']}]({l['url']})\n" for l in m['links']]
    out += ['\n## Source and verification\n\n',
            f"Source maintained by [{s['owner']}](https://github.com/{s['owner']}). "
            f"This catalog records revision [`{s['commit'][:12]}`]({revision_url(m)}), inspected on {m['source_reviewed_at']}.\n\n",
            '**Execution has not been independently checked for this catalog.** The source review identifies available code and documentation; it does not certify reproduction of published results. Consult the source repository and data providers for their reuse terms.\n\n',
            '[Suggest a correction](../CONTRIBUTING.md)\n']
    return ''.join(out)

def readme(c):
    out=['<p align="center"><a href="https://github.com/it-is-me-mario"><img src="https://raw.githubusercontent.com/it-is-me-mario/.github/main/profile/assets/mario-logo.png" width="80" alt="MARIO"></a></p>\n\n',
         '# MARIO model gallery\n\n',
         'Learn MARIO, explore modelling methods, and find research applications built with it.\n\n',
         '[MARIO library](https://github.com/it-is-me-mario/MARIO) · [Documentation](https://www.marioproject.com/en/latest/) · [Contribute a resource](CONTRIBUTING.md)\n\n',
         f"The initial collection contains **{len(c['models'])} resources**. Each page links to the original code, records the source revision, and explains the setup information available. Code remains with its maintainers.\n\n"]
    for kind,label in KINDS.items():
        subset=[m for m in c['models'] if m['kind']==kind]
        if not subset:continue
        out += [f'## {label}\n\n','| Resource | What it covers | Setup |\n|---|---|---|\n']
        for m in subset:
            out.append(f"| [{m['title']}](models/{m['id']}.md) | {m['summary']} | {LABELS[m['readiness']['status']]} |\n")
        out.append('\n')
    out += ['## Reading the collection\n\n',
            '**Setup documented** means the source provides installation or execution instructions. **Setup to document** means those instructions need to be assembled. **Example update needed** marks an example with a known setup or code issue.\n\n',
            '**None of the resources has been independently rerun for this catalog yet.** A source review and an executed reproduction are separate checks. The individual pages explain the current evidence and any uncertainty about a paper association.\n\n',
            'When comparing results, keep the database release, MARIO version, scientific assumptions and calculation profile together. An updated analysis may differ from the version used in a paper.\n\n',
            f"Last source review: **{c['updated_at']}**. [Catalog data](catalog/models.json) · [Catalog schema](catalog/schema.json) · [How to contribute](CONTRIBUTING.md)\n"]
    return ''.join(out)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['build','check'])
    args=p.parse_args()
    c=load_catalog()
    generated={ROOT/'README.md':readme(c)}
    generated.update({ROOT/'models'/f"{m['id']}.md":card(m) for m in c['models']})
    stale=[]
    for path,expected in generated.items():
        if args.command=='build':
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(expected)
        elif not path.exists() or path.read_text()!=expected:
            stale.append(str(path.relative_to(ROOT)))
    extra=set((ROOT/'models').glob('*.md'))-set(generated)
    stale += [str(p.relative_to(ROOT))+' (not in catalog)' for p in sorted(extra)]
    if stale:
        raise SystemExit('Generated pages need attention: '+', '.join(stale))
    print(f"Catalog valid: {len(c['models'])} resources; {len(generated)} generated pages {'written' if args.command=='build' else 'current'}.")

if __name__=='__main__':main()
