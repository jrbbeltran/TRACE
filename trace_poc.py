#!/usr/bin/env python3
"""TRACE Stage 1 deterministic proof of concept.

This intentionally narrow runnable example separates claims, preserves source
locations, and links only explicit in-text table/figure references. No LLM,
remote calls, methodological audit, or external citation verification.
"""
import argparse, html, json, re
from pathlib import Path

CLAIM = re.compile(r'\b(hypothes(?:is|es)|we (?:find|found|argue|theorize|show|predict|propose)|our (?:results|findings|study) (?:show|suggest|indicate|demonstrate)|(?:positively|negatively) (?:associated|related)|(?:supported|not supported))\b', re.I)
EMPR = re.compile(r'\b(hypothes(?:is|es)|results|findings|supported|not supported|significan(?:t|ce)|table\s*\d|figure\s*\d|β|coefficient|effect)\b', re.I)
CITED = re.compile(r'\(([A-Z][^()]{1,110}?,\s*(?:19|20)\d{2}[^()]*)\)')
LOC = re.compile(r'\b(?:Table|Figure)\s+([A-Za-z]?\d+(?:\.\d+)?)', re.I)
YEAR = re.compile(r'\b(?:19|20)\d{2}\b')

def normalize(s): return re.sub(r'\s+', ' ', s).strip()

def records(path):
    p=Path(path); ext=p.suffix.lower()
    if ext=='.pdf':
        try: import fitz
        except ImportError: raise SystemExit('Install PyMuPDF: pip install pymupdf')
        with fitz.open(str(p)) as d:
            for i,page in enumerate(d):
                text=page.get_text('text')
                # Paragraph approximation only; preserve PDF page location.
                for block in re.split(r'\n\s*\n',text):
                    s=normalize(block)
                    if len(s)>35:yield {'page':i+1,'section':'PDF page','text':s}
    elif ext=='.docx':
        try: from docx import Document
        except ImportError: raise SystemExit('Install python-docx: pip install python-docx')
        d=Document(str(p));sec='Document'
        for i,paragraph in enumerate(d.paragraphs,1):
            s=normalize(paragraph.text)
            if not s:continue
            if paragraph.style and paragraph.style.name.startswith('Heading'):sec=s
            yield {'page':None,'section':sec,'paragraph':i,'text':s}
        for i,table in enumerate(d.tables,1):
            for row in table.rows:
                s=normalize(' | '.join(c.text for c in row.cells))
                if s:yield {'page':None,'section':f'Table {i}','text':s}
    else:raise SystemExit('Only PDF and DOCX supported')

def analyze(path):
    rec=list(records(path))
    # Detect references in a human-readable manner; NOT bibliographic existence checks.
    refs=[]
    for r in rec:
        s=r['text']
        if YEAR.search(s) and len(s)<550 and (re.search(r'\b(journal|doi|volume|review|academy|science)\b',s,re.I)):
            refs.append(s)
    claims=[]
    seen=set()
    for r in rec:
        # Limit sentential extraction to avoid huge full-paragraph cards
        for sent in re.split(r'(?<=[.!?])\s+(?=[A-Z“])',r['text']):
            sent=normalize(sent)
            if not (45<=len(sent)<=500 and CLAIM.search(sent)):continue
            if sent.lower() in seen:continue
            seen.add(sent.lower())
            cl='empirical' if EMPR.search(sent) else 'theoretical'
            explicit=list(dict.fromkeys(' '.join(m.group(0).split()) for m in LOC.finditer(sent)))
            cited=[m.group(1) for m in CITED.finditer(sent)]
            # A same-sentence table reference is a pointer, not evidence validation.
            claims.append({'type':cl,'original_excerpt':sent,'source':{'page':r.get('page'), 'section':r.get('section'), 'paragraph':r.get('paragraph')},
               'explicit_table_figure_pointers':explicit,'citations_mentioned':cited,
               'evidence_status': 'Explicit pointer identified; not verified' if explicit else 'Support not automatically located'})
            if len(claims)>=150:break
        if len(claims)>=150:break
    return {'file_name':Path(path).name,'method':'Deterministic heuristic extractor, no external services',
     'warnings':['Not validated for accuracy. Not an AI review, statistical check, or publication recommendation.',
       'Theoretical/empirical classification is approximate.',
       'A pointer to a table is not an independent claim-evidence validation.',
       'No external bibliographic existence checking is implemented in this proof of concept.'],
     'claims':claims, 'reference_like_spans':refs[:35]}

def render_html(data):
    q=html.escape
    cards=[]
    for i,c in enumerate(data['claims'],1):
        src=c['source'];where=('PDF p. '+str(src['page'])) if src.get('page') else f"DOCX paragraph {src.get('paragraph','?')}"
        pointers=', '.join(c['explicit_table_figure_pointers']) or 'None in claim sentence'
        cites='; '.join(c['citations_mentioned']) or 'None detected'
        cards.append(f'<article class="claim"><div class="meta">{i} · {q(c["type"].upper())} · {q(where)}</div><p>{q(c["original_excerpt"])}</p><div class="detail">Explicit table/figure reference: <b>{q(pointers)}</b><br>Cited works: {q(cites)}<br>Evidence status: <b>{q(c["evidence_status"])}</b></div></article>')
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TRACE proof of concept</title><style>body{max-width:960px;margin:35px auto;padding:0 20px;font:16px/1.55 system-ui;color:#23313b;background:#fcfcfc}header{border-bottom:2px solid #526780;padding-bottom:18px}.claim{background:white;border:1px solid #cbd2da;border-radius:9px;padding:18px;margin:15px 0}.meta{font-size:.8rem;letter-spacing:.07em;font-weight:700;color:#566b7b}.detail{font-size:.88rem;background:#f4f6f8;border-radius:5px;padding:10px}ul{padding-left:23px}h1{margin-bottom:0}small{color:#526780}</style></head><body><header><h1>TRACE · Proof of Concept</h1><p>Transparent Retrieval and Alignment of Claims and Evidence</p><small>Runnable stage-one heuristic demonstration; no model-assisted judgment</small></header><h2>Input</h2><p>''' + q(data['file_name']) + '''</p><h2>Limits</h2><ul>''' + ''.join('<li>'+q(s)+'</li>' for s in data['warnings']) + '''</ul><h2>Candidate claim excerpts (''' + str(len(data['claims'])) + ''')</h2>'''+ ''.join(cards) + '''</body></html>'''

def main():
    a=argparse.ArgumentParser();a.add_argument('document');a.add_argument('--out',default='trace_output');args=a.parse_args()
    data=analyze(args.document)
    prefix=Path(args.out);prefix.parent.mkdir(parents=True,exist_ok=True)
    prefix.with_suffix('.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    prefix.with_suffix('.html').write_text(render_html(data),encoding='utf-8')
    print('Found',len(data['claims']),'candidate claim excerpts; saved',str(prefix)+'.{json,html}')
if __name__=='__main__':main()
