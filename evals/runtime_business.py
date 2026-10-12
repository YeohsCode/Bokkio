"""Independent synthetic business inputs and read-only judges; not production Core."""
from __future__ import annotations
import csv
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import unicodedata
import zlib

TASKS = [
 ('T01','files',['Finder']),('T02','files',['Finder']),
 ('T03','spreadsheet',['Numbers']),('T04','spreadsheet',['Numbers']),
 ('T05','document',['TextEdit']),('T06','document',['TextEdit']),
 ('T07','browser',[]),('T08','browser',[]),
 ('T09','cross_app',['Numbers','TextEdit']),('T10','cross_app',['Preview','TextEdit']),
 ('T11','untuned_app',['Preview']),('T12','untuned_app',['Pages'])]
FIRST = ['T01','T03','T05','T07','T09','T11']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def png(width,height):
    raw=b''.join(b'\x00'+b'\x34\x88\xbb'*width for _ in range(height))
    def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def rtf_text(path):
    """Decode with the platform renderer; raw RTF comments are not content."""
    if not Path(path).read_bytes().lstrip().startswith(b'{\\rtf'):
        raise ValueError('Expected RTF document')
    result=subprocess.run(['textutil','-format','rtf','-convert','txt','-stdout',str(path)],
                          capture_output=True,timeout=10,check=True)
    return result.stdout.decode('utf-8').replace('\r\n','\n').strip()


def rendered_text_matches(expected,ocr_text):
    normalize=lambda text:re.sub(r'\s+',' ',unicodedata.normalize('NFKC',text)).strip()
    pool=normalize(ocr_text)
    return all(normalize(line) in pool for line in expected.splitlines() if line.strip())


def write_csv(path,columns,rows):
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(rows)


def prepare(work,task,client,variant=0):
    work.mkdir(parents=True,exist_ok=False,mode=0o700)
    prefix=f'{task}-{client}-v{variant}'
    inputs=work/(prefix+'-input');inputs.mkdir();out=work/'output';out.mkdir()
    case={'task':task,'client':client,'variant':variant,'work':str(work),'inputs':str(inputs),'out':str(out),'prefix':prefix,'apps':[], 'ui_outputs':[],'requires_reopen':task in {'T05','T06','T11','T12'}}
    source={};p=lambda suffix:inputs/(prefix+'-'+suffix)
    o=lambda suffix:out/(prefix+'-'+suffix)
    if task in {'T01','T02'}:
        files={'2026-10-01_report.txt':b'report one\n','2026-10-02_chart.png':png(80,40),'2026-10-03_notes.txt':b'notes three\n','2026-09-30_old.txt':b'old\n','2026-10-04_readme.md':b'# keep\n'}
        for name,data in files.items():(inputs/name).write_bytes(data)
        case['apps']=[{'name':'Finder','input':str(inputs),'windows':[inputs.name,'deliverables']}]
        if task=='T01':
            case['goal']=f'From {inputs}, collect only .txt files dated in October 2026 into {out}/deliverables, preserving their bytes. Create {o("manifest.csv")} with columns filename,sha256, sorted by filename. Keep every input file unchanged. The source folder must be visibly inspected in Finder.'
        else:
            case['goal']=f'Copy the input files into {out}/deliverables and rename .txt files by replacing each underscore with a hyphen; keep other names. Create {o("changes.csv")} with columns old_name,new_name,sha256, sorted by old_name, for every file. Preserve source bytes. Inspect the source folder in Finder.'
    elif task in {'T03','T09'}:
        rows=[{'invoice':'INV-A','qty':'3','unit_price':'12.40'},{'invoice':'INV-B','qty':'7','unit_price':'3.15'},{'invoice':'INV-C','qty':'2','unit_price':str(Decimal('29.95')+variant)}]
        write_csv(p('invoices.csv'),['invoice','qty','unit_price'],rows)
        case['apps']=[{'name':'Numbers','input':str(p('invoices.csv')),'windows':[p('invoices.csv').stem,o('result.csv').stem]}]
        case['ui_outputs']=[{'app':'Numbers','file':str(o('result.csv')),'kind':'csv'}]
        case['goal']=f'Calculate amount = qty times unit_price for each invoice in {p("invoices.csv")}, rounded to two decimal places. Create {o("result.csv")} with columns invoice,qty,unit_price,amount, retain input order and append a TOTAL row (blank qty/unit_price, summed amount). Keep the input unchanged. Display the resulting table in Numbers; its actual visible cells must match the saved CSV.'
        if task=='T09':
            p('context.txt').write_text('Project Beacon\nOwner 林安\nDeadline 2026-11-03\n',encoding='utf-8')
            case['apps'].append({'name':'TextEdit','input':str(p('context.txt')),'windows':[p('context.txt').name,o('report.txt').name]})
            case['ui_outputs'].append({'app':'TextEdit','file':str(o('report.txt')),'kind':'text'})
            case['goal']+=f' Also use {p("context.txt")} to create {o("report.txt")} with headings Summary and Invoices, project/owner/deadline, every invoice and amount, and the identical grand total. Display the saved report in TextEdit. Both applications must show the result, not just generated files.'
    elif task in {'T04'}:
        write_csv(p('left.csv'),['id','name','qty'],[{'id':'A','name':'Apex','qty':'2'},{'id':'B','name':'Birch','qty':'0'},{'id':'A','name':'Apex','qty':'3'}])
        write_csv(p('right.csv'),['id','name','qty'],[{'id':'B','name':'Birch','qty':'4'},{'id':'C','name':'Cedar','qty':''}])
        case['apps']=[{'name':'Numbers','input':str(p('left.csv')),'windows':[p('left.csv').stem,o('result.csv').stem]}]
        case['ui_outputs']=[{'app':'Numbers','file':str(o('result.csv')),'kind':'csv'}]
        case['goal']=f'Merge {p("left.csv")} and {p("right.csv")}, group by id, sum qty (empty means zero), preserve each name and sort by id. Save {o("result.csv")} with columns id,name,qty and display the table in Numbers. Leave inputs unchanged.'
    elif task in {'T05','T06'}:
        text='Project Beacon\nOwner 林安\nDeadline 2026-11-03\nBudget CNY 48000\nAction A: 林安 reviews the draft by 2026-10-20.\nAction B: 陈宁 verifies the data by 2026-10-22.\nAppendix: preserve this line exactly.\n'
        p('notes.txt').write_text(text,encoding='utf-8')
        case['apps']=[{'name':'TextEdit','input':str(p('notes.txt')),'windows':[p('notes.txt').name,o('report.txt').name]}]
        case['ui_outputs']=[{'app':'TextEdit','file':str(o('report.txt')),'kind':'text'}]
        if task=='T05':case['goal']=f'Use {p("notes.txt")} to create a report {o("report.txt")} with headings Summary, Actions and Appendix. Include the project, owner, deadline, budget and both complete action descriptions, preserving the appendix line exactly. Keep source unchanged. Display the saved report in TextEdit; it must remain correct when reopened independently.'
        else:case['goal']=f'Create {o("report.txt")} from {p("notes.txt")}, changing only Budget CNY 48000 to Budget CNY 52000 and Deadline 2026-11-03 to Deadline 2026-11-10. Preserve every other character/line. Keep source unchanged and display the saved revision in TextEdit; it must remain correct when reopened.'
    elif task in {'T07','T08'}:
        case['web_kind']='catalog' if task=='T07' else 'draft'
        if task=='T07':case['goal']=f'Use the web catalog to find group Hardware items with stock less than 5. Leave the actual browser on the filtered results. Save {o("result.csv")} with columns id,name,group,stock, sorted by id. Do not change catalog data.'
        else:case['goal']='Correct the invalid zero-quantity draft on the web page: name 林安, project Beacon, quantity 7, note "内部测试草稿". Save a draft only and leave the browser showing the saved draft. No send or publish operation is authorized.'
    elif task in {'T10','T11'}:
        for name,size in [('small.png',(80,40)),('wide.png',(160,80)),('large.png',(240,120))]: p(name).write_bytes(png(*size))
        if task=='T11':
            case['apps']=[{'name':'Preview','input':str(p('small.png')),'windows':[p('small.png').name,o('result.png').name]}]
            case['ui_outputs']=[{'app':'Preview','file':str(o('result.png')),'kind':'image'}]
            case['goal']=f'Resize {p("small.png")} from 80x40 to exactly 120x60 pixels, preserving aspect ratio and its image content. Save as {o("result.png")}, without altering any source image. Show the resized saved image in Preview. It must remain correct when reopened independently.'
        else:
            case['apps']=[{'name':'Preview','input':str(p('small.png')),'windows':[p('small.png').name,p('large.png').name]},{'name':'TextEdit','input':str(p('instructions.txt')),'windows':[p('instructions.txt').name,o('index.txt').name]}]
            p('instructions.txt').write_text('Create an index of images at least 150 pixels wide.\n')
            case['ui_outputs']=[{'app':'Preview','file':str(p('large.png')),'kind':'image'},{'app':'TextEdit','file':str(o('index.txt')),'kind':'text'}]
            case['goal']=f'Create {o("index.txt")} listing only PNG images from {inputs} with width at least 150 pixels, each with filename,width,height, sorted by filename. Display the index in TextEdit and the largest matching image in Preview. Keep all sources unchanged.'
    else:
        p('notes.rtf').write_text(r'{\rtf1\ansi Project Beacon\par Budget 48000\par Deadline 2026-11-03\par Keep appendix.}',encoding='ascii')
        case['apps']=[{'name':'Pages','input':str(p('notes.rtf')),'windows':[p('notes.rtf').stem,o('result.rtf').stem]}]
        case['ui_outputs']=[{'app':'Pages','file':str(o('result.rtf')),'kind':'text'}]
        case['goal']=f'Read {p("notes.rtf")} in Pages. Create {o("result.rtf")} changing Budget 48000 to Budget 52000 and keeping all other text. Display the saved result in Pages, correct after reopening; source must remain unchanged.'
    case['input_sha256']={str(f.relative_to(inputs)):sha(f) for f in inputs.rglob('*') if f.is_file()}
    return case


def expected_invoices(case):
    rows=read_csv(Path(case['inputs'])/(case['prefix']+'-invoices.csv'));out=[];total=Decimal(0)
    for r in rows:
        a=(Decimal(r['qty'])*Decimal(r['unit_price'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP);total+=a
        out.append({**r,'amount':format(a,'.2f')})
    return out+[{'invoice':'TOTAL','qty':'','unit_price':'','amount':format(total,'.2f')}]


def sections(text,headings):
    cleaned=text.replace('**','').replace(',','')
    matches=[re.search(r'^\s*(?:#{1,6}\s*)?'+re.escape(h)+r'\s*:?\s*$',cleaned,re.M) for h in headings]
    if any(m is None for m in matches) or [m.start() for m in matches]!=sorted(m.start() for m in matches):return None
    return {h:cleaned[m.end():matches[i+1].start() if i+1<len(matches) else len(cleaned)] for i,(h,m) in enumerate(zip(headings,matches))}


def business_checks(case,web_state=None):
    task=case['task'];inputs=Path(case['inputs']);out=Path(case['out']);prefix=case['prefix'];checks={}
    checks['source_unchanged']=all((inputs/f).is_file() and sha(inputs/f)==h for f,h in case['input_sha256'].items())
    checks['outputs_exist']=False;checks['business_correct']=False
    p=lambda suffix:out/(prefix+'-'+suffix)
    try:
        if task in {'T01','T02'}:
            names=sorted(case['input_sha256'])
            if task=='T01':names=[n for n in names if n.startswith('2026-10-') and n.endswith('.txt')]
            mapping={n:n if task=='T01' or not n.endswith('.txt') else n.replace('_','-') for n in names}
            actual=sorted(f.name for f in (out/'deliverables').iterdir() if f.is_file())
            checks['file_set_correct']=actual==sorted(mapping.values())
            checks['file_bytes_correct']=all(sha(out/'deliverables'/new)==case['input_sha256'][old] for old,new in mapping.items())
            expected=[{'filename':n,'sha256':case['input_sha256'][n]} for n in names] if task=='T01' else [{'old_name':n,'new_name':mapping[n],'sha256':case['input_sha256'][n]} for n in names]
            checks['manifest_correct']=read_csv(p('manifest.csv' if task=='T01' else 'changes.csv'))==expected
            checks['outputs_exist']=True;checks['business_correct']=all(checks[k] for k in ('file_set_correct','file_bytes_correct','manifest_correct'))
        elif task in {'T03','T09'}:
            expected=expected_invoices(case);actual=read_csv(p('result.csv'))
            checks['table_correct']=actual==expected;checks['outputs_exist']=True
            if task=='T09':
                text=p('report.txt').read_text(encoding='utf-8');parts=sections(text,['Summary','Invoices'])
                records=dict(re.findall(r'\b(INV-[A-Z]+)\b(.*?)(?=\bINV-[A-Z]+\b|\Z)',parts['Invoices'],re.S)) if parts else {}
                invoices=expected[:-1]
                checks['report_owner_correct']=bool(parts and '林安' in parts['Summary'])
                checks['report_project_deadline_correct']=bool(parts and all(v in parts['Summary'] for v in ['Beacon','2026-11-03']))
                checks['report_invoices_correct']=bool(parts and set(records)=={r['invoice'] for r in invoices}
                    and all(re.search(r'(?<![\d.])'+re.escape(r['amount'])+r'(?![\d.])',records[r['invoice']]) for r in invoices))
                # The goal permits the grand total in either report section;
                # it does not require the CSV's TOTAL row label in Invoices.
                checks['report_total_correct']=bool(parts and any(re.search(r'\btotal\b',line,re.I)
                    and re.search(r'(?<![\d.])'+re.escape(expected[-1]['amount'])+r'(?![\d.])',line)
                    for line in (parts['Summary']+'\n'+parts['Invoices']).splitlines()))
                checks['report_correct']=all(checks[k] for k in ['report_owner_correct','report_project_deadline_correct','report_invoices_correct','report_total_correct'])
            checks['business_correct']=checks['table_correct'] and checks.get('report_correct',True)
        elif task=='T04':
            actual=read_csv(p('result.csv'));checks['outputs_exist']=True;checks['business_correct']=actual==[{'id':'A','name':'Apex','qty':'5'},{'id':'B','name':'Birch','qty':'4'},{'id':'C','name':'Cedar','qty':'0'}]
        elif task in {'T05','T06'}:
            text=p('report.txt').read_text(encoding='utf-8');source=(inputs/(prefix+'-notes.txt')).read_text(encoding='utf-8');checks['outputs_exist']=True
            if task=='T05':
                # The goal requests facts, not literal labels such as "Owner".
                # Complete action descriptions and appendix remain verbatim.
                parts=sections(text,['Summary','Actions','Appendix'])
                checks['business_correct']=bool(parts and all(v in parts['Summary'] for v in ['Beacon','林安','2026-11-03'])
                    and re.search(r'\bCNY\s*:?\s*48000\b',parts['Summary'])
                    and all(v in parts['Actions'] for v in ['林安 reviews the draft by 2026-10-20.','陈宁 verifies the data by 2026-10-22.'])
                    and 'Appendix: preserve this line exactly.' in text.splitlines())
            else:checks['business_correct']=text==source.replace('Budget CNY 48000','Budget CNY 52000').replace('Deadline 2026-11-03','Deadline 2026-11-10')
        elif task=='T07':
            expected=[{'id':'P02','name':'Bolt','group':'Hardware','stock':'3'},{'id':'P04','name':'Clamp','group':'Hardware','stock':'1'}]
            actual=read_csv(p('result.csv'));checks['outputs_exist']=True;checks['business_correct']=actual==expected
            checks['web_result_correct']=bool(web_state and web_state.get('selected')==['P02','P04'])
        elif task=='T08':
            expected={'name':'林安','project':'Beacon','quantity':'7','note':'内部测试草稿'}
            checks['outputs_exist']=bool(web_state and web_state.get('draft'))
            checks['business_correct']=bool(web_state and web_state.get('draft')==expected and not web_state.get('sent'))
        elif task=='T11':
            data=p('result.png').read_bytes();checks['outputs_exist']=True
            checks['business_correct']=png_content_correct(data,(120,60))
        elif task=='T10':
            text=p('index.txt').read_text();checks['outputs_exist']=True
            checks['business_correct']=bool(re.search(r'large\.png\s*[, ]\s*240\s*[, ]\s*120',text) and re.search(r'wide\.png\s*[, ]\s*160\s*[, ]\s*80',text) and 'small.png' not in text and text.index('large.png')<text.index('wide.png'))
        else:
            source=rtf_text(inputs/(prefix+'-notes.rtf'));data=rtf_text(p('result.rtf'));checks['outputs_exist']=True
            checks['business_correct']=data==source.replace('Budget 48000','Budget 52000')
    except (OSError,ValueError,KeyError,struct.error,csv.Error,StopIteration,subprocess.SubprocessError):pass
    return checks


def numeric_equal(a,b):
    if a==b:return True
    try:return Decimal(a.replace(',',''))==Decimal(b.replace(',',''))
    except Exception:return False


def snapshot_matches(target,nodes):
    file=Path(target['file']);kind=target['kind']
    windows=[n for n in nodes if n['role']=='window']
    owned=any(n.get('name') in {file.name,file.stem} for n in windows)
    if not owned:return False
    if kind=='csv':
        with file.open(encoding='utf-8-sig',newline='') as f:matrix=list(csv.reader(f))
        cells={}
        for n in nodes:
            if n['role']!='table_cell':continue
            match=re.match(r'^(.*), Row: (\d+), Column: (\d+)',n.get('name') or '')
            if match:
                label=match[1];suffix=', '+file.stem
                if label==file.stem:value=''
                elif label.endswith(suffix):value=label[:-len(suffix)]
                else:continue
                cells[(int(match[2]),int(match[3]))]=value
        # Empty cells need not be returned by AX; compare every nonempty value.
        return all(numeric_equal(cells.get((row,col),''),value) for row,values in enumerate(matrix,1) for col,value in enumerate(values,1))
    if kind=='text' and file.suffix=='.txt':
        contents=file.read_text(encoding='utf-8');return any(n['role']=='text_area' and n.get('value')==contents for n in nodes)
    if kind=='csv_text':
        return any(n['role']=='text_area' and n.get('value')==file.read_text(encoding='utf-8') for n in nodes)
    if kind=='image':
        from urllib.parse import unquote,urlparse
        bound=any(Path(unquote(urlparse(n.get('platform_data',{}).get('ax_document') or '').path)).resolve()==file.resolve() for n in windows)
        return bound and any(n['role']=='image' for n in nodes)
    if kind=='text' and file.suffix=='.rtf':
        pool='\n'.join(str(n.get('value') or n.get('name') or '') for n in nodes)
        return all(v in pool for v in ['Project Beacon','Budget 52000','Deadline 2026-11-03','Keep appendix.']) and 'Budget 48000' not in pool
    return False


def png_content_correct(data,size):
    """Validate CRC/deflate/filter content, not just forgeable IHDR dimensions."""
    if data[:8]!=b'\x89PNG\r\n\x1a\n':return False
    at=8;compressed=b'';header=None;ended=False
    try:
        while at<len(data):
            length=struct.unpack('>I',data[at:at+4])[0];tag=data[at+4:at+8];body=data[at+8:at+8+length]
            crc=struct.unpack('>I',data[at+8+length:at+12+length])[0]
            if len(body)!=length or zlib.crc32(tag+body)&0xffffffff!=crc:return False
            if tag==b'IHDR':header=struct.unpack('>IIBBBBB',body)
            if tag==b'IDAT':compressed+=body
            if tag==b'IEND':ended=True
            at+=length+12
        if not ended or not header or header[:2]!=size or header[2]!=8 or header[3] not in {2,6} or header[6]!=0:return False
        width,height=size;bpp=3 if header[3]==2 else 4;stride=width*bpp
        raw=zlib.decompress(compressed)
        if len(raw)!=(stride+1)*height:return False
        previous=bytearray(stride)
        def paeth(a,b,c):
            p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
            return a if pa<=pb and pa<=pc else b if pb<=pc else c
        for y in range(height):
            start=y*(stride+1);mode=raw[start];row=bytearray(raw[start+1:start+1+stride])
            if mode>4:return False
            for i in range(stride):
                left=row[i-bpp] if i>=bpp else 0;up=previous[i];ul=previous[i-bpp] if i>=bpp else 0
                addition=0 if mode==0 else left if mode==1 else up if mode==2 else (left+up)//2 if mode==3 else paeth(left,up,ul)
                row[i]=(row[i]+addition)&255
            for x in range(width):
                if any(abs(row[x*bpp+k]-v)>1 for k,v in enumerate((0x34,0x88,0xbb))):return False
                if bpp==4 and row[x*bpp+3]!=255:return False
            previous=row
        return True
    except (ValueError,struct.error,zlib.error):return False
