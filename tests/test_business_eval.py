"""Business judge counterexamples; no application mutation in these tests."""
from pathlib import Path
import shutil
import pytest
from evals.runtime_business import prepare,business_checks,expected_invoices,write_csv,png


def populate(case):
    inputs=Path(case['inputs']);out=Path(case['out']);p=case['prefix'];task=case['task']
    if task=='T01':
        (out/'deliverables').mkdir()
        names=sorted(n for n in case['input_sha256'] if n.startswith('2026-10-') and n.endswith('.txt'))
        for n in names:shutil.copyfile(inputs/n,out/'deliverables'/n)
        write_csv(out/(p+'-manifest.csv'),['filename','sha256'],[{'filename':n,'sha256':case['input_sha256'][n]} for n in names])
    elif task in {'T03','T09'}:
        write_csv(out/(p+'-result.csv'),['invoice','qty','unit_price','amount'],expected_invoices(case))
        if task=='T09':(out/(p+'-report.txt')).write_text('Summary\nProject Beacon 林安 2026-11-03\nInvoices\n'+'\n'.join(r['invoice']+' '+r['amount'] for r in expected_invoices(case)))
    elif task=='T05':
        source=(inputs/(p+'-notes.txt')).read_text()
        (out/(p+'-report.txt')).write_text('Summary\n'+source.split('Action A:')[0]+'Actions\nAction A:'+source.split('Action A:')[1].split('Appendix:')[0]+'Appendix\nAppendix:'+source.split('Appendix:')[1])
    elif task=='T11':(out/(p+'-result.png')).write_bytes(png(120,60))


@pytest.mark.parametrize('task',['T01','T03','T05','T09','T11'])
def test_business_judge_missing_positive_and_changed_source(tmp_path,task):
    case=prepare(tmp_path/'work',task,'judge-test')
    assert not business_checks(case)['business_correct']
    populate(case)
    checks=business_checks(case)
    assert checks['business_correct'] and checks['source_unchanged'],checks
    source=next(f for f in Path(case['inputs']).iterdir() if f.is_file());source.write_bytes(b'corrupted')
    assert not business_checks(case)['source_unchanged']


def test_table_wrong_total_and_extra_row_rejected(tmp_path):
    case=prepare(tmp_path/'work','T03','judge-test');rows=expected_invoices(case)
    file=Path(case['out'])/(case['prefix']+'-result.csv')
    rows[-1]['amount']='0.00';write_csv(file,['invoice','qty','unit_price','amount'],rows)
    assert not business_checks(case)['business_correct']
    rows=expected_invoices(case);rows.append(rows[0]);write_csv(file,['invoice','qty','unit_price','amount'],rows)
    assert not business_checks(case)['business_correct']


def test_png_forged_header_and_wrong_content_rejected(tmp_path):
    case=prepare(tmp_path/'work','T11','judge-test');file=Path(case['out'])/(case['prefix']+'-result.png')
    file.write_bytes(png(120,60)[:24])
    assert not business_checks(case)['business_correct']


def test_recovered_terminal_failure_is_not_unknown_completion():
    from scripts.evaluate_runtime_business import protocol_complete
    assert protocol_complete(0,None,['s'],['s'],['failed','completed','cancelled','timed_out'],0)
    assert not protocol_complete(0,None,['s'],['s'],['running'],0)
    assert not protocol_complete(0,None,['s'],['s'],['completed'],1)
    assert not protocol_complete(130,'wall_clock_budget',['s'],['s'],['completed'],0)


def test_report_facts_do_not_require_source_labels_but_appendix_is_exact(tmp_path):
    case=prepare(tmp_path/'work','T05','judge-test')
    file=Path(case['out'])/(case['prefix']+'-report.txt')
    text=('Summary\nProject Beacon is owned by 林安, deadline 2026-11-03, budget CNY 48,000.\n'
          'Actions\n- 林安 reviews the draft by 2026-10-20.\n'
          '- 陈宁 verifies the data by 2026-10-22.\nAppendix\nAppendix: preserve this line exactly.\n')
    file.write_text(text)
    assert business_checks(case)['business_correct']
    file.write_text(text.replace('CNY 48,000','CNY 52,000'))
    assert not business_checks(case)['business_correct']
    file.write_text(text.replace('exactly.','exactly, .'))
    assert not business_checks(case)['business_correct']


def test_actual_spreadsheet_empty_cells_and_wrong_values(tmp_path):
    from evals.runtime_business import snapshot_matches
    case=prepare(tmp_path/'work','T03','judge-test');populate(case)
    file=Path(case['out'])/(case['prefix']+'-result.csv')
    import csv
    matrix=list(csv.reader(file.open()))
    nodes=[{'role':'window','name':file.stem}]
    for r,row in enumerate(matrix,1):
        for c,value in enumerate(row,1):
            label=value+', '+file.stem if value else file.stem
            nodes.append({'role':'table_cell','name':f'{label}, Row: {r}, Column: {c}'})
    assert snapshot_matches(case['ui_outputs'][0],nodes)
    nodes[-1]['name']=f'0.00, {file.stem}, Row: 5, Column: 4'
    assert not snapshot_matches(case['ui_outputs'][0],nodes)


def test_regrade_never_upgrades_jobs_finished_by_evaluator_cleanup():
    from scripts.regrade_runtime_business import jobs_before_judge
    events=[{'seq':1,'operation_id':'actor','kind':'job.finished','data':{'job_id':'a','status':'completed'}},
            {'seq':2,'operation_id':'independent-judge-Numbers','kind':'request.received','data':{'tool':'desktop.observe'}},
            {'seq':3,'operation_id':'cleanup','kind':'job.finished','data':{'job_id':'b','status':'cancelled'}}]
    assert jobs_before_judge(['a','b'],events)==['completed','unfinished_at_judge_start']


def test_cross_app_report_accepts_fact_labels_and_rejects_swapped_amounts(tmp_path):
    case=prepare(tmp_path/'work','T09','judge-test');populate(case)
    file=Path(case['out'])/(case['prefix']+'-report.txt')
    text=file.read_text().replace('Project Beacon 林安 2026-11-03','Project: Beacon\nOwner: 林安\nDeadline: 2026-11-03')
    file.write_text(text)
    assert business_checks(case)['business_correct']
    file.write_text(text.replace('INV-A 37.20','INV-A 22.05').replace('INV-B 22.05','INV-B 37.20'))
    assert not business_checks(case)['business_correct']


def test_report_owner_must_appear_in_summary_not_only_in_actions(tmp_path):
    case=prepare(tmp_path/'work','T05','judge-test');populate(case)
    file=Path(case['out'])/(case['prefix']+'-report.txt')
    file.write_text(file.read_text().replace('Owner 林安\n',''))
    assert not business_checks(case)['business_correct']


def test_cross_app_total_may_be_in_summary_but_wrong_owner_still_fails(tmp_path):
    case=prepare(tmp_path/'work','T09','judge-test');populate(case)
    file=Path(case['out'])/(case['prefix']+'-report.txt')
    text=file.read_text().replace('林安 2026-11-03','林安 2026-11-03\nGrand Total: 119.15').replace('TOTAL 119.15','')
    file.write_text(text)
    assert business_checks(case)['business_correct']
    file.write_text(text.replace('林安','张伟'))
    checks=business_checks(case)
    assert checks['report_invoices_correct'] and checks['report_total_correct']
    assert not checks['report_owner_correct'] and not checks['business_correct']
