"""Literal workflow parameters and independent file-version contracts."""
from __future__ import annotations

import copy
import hashlib
import ntpath
from pathlib import Path
import re

from .model import BokkioError

SCHEMA_V2 = 'bokkio.workflow.v2'
NAME = re.compile(r'^[a-z][a-z0-9_]{0,63}$')
HASH = re.compile(r'^[0-9a-f]{64}$')


def absolute_path(value):
    return isinstance(value, str) and (Path(value).is_absolute() or
           (ntpath.isabs(value) and bool(ntpath.splitdrive(value)[0])))


def declarations_valid(parameters):
    if not isinstance(parameters, dict) or len(parameters) > 32:
        raise BokkioError('Workflow requires at most 32 declared parameters')
    for name, spec in parameters.items():
        if not NAME.fullmatch(name) or not isinstance(spec, dict) or set(spec) != {'type', 'max_length'}:
            raise BokkioError('Invalid workflow parameter declaration')
        if spec['type'] not in {'string', 'path', 'sha256'} or type(spec['max_length']) is not int or not 1 <= spec['max_length'] <= 65536:
            raise BokkioError('Invalid workflow parameter type or length')


def values_valid(parameters, values):
    declarations_valid(parameters)
    if not isinstance(values, dict) or set(values) != set(parameters):
        raise BokkioError('Supply exactly the declared workflow parameters')
    for name, spec in parameters.items():
        value = values[name]
        if not isinstance(value, str) or '\0' in value or len(value) > spec['max_length']:
            raise BokkioError(f'Invalid parameter value: {name}')
        if spec['type'] == 'path' and not absolute_path(value):
            raise BokkioError(f'Parameter requires an absolute path: {name}')
        if spec['type'] == 'sha256' and not HASH.fullmatch(value):
            raise BokkioError(f'Parameter requires a SHA-256: {name}')


def parameter_slot(parts):
    # Bind whole literal values only. Apps, actions, risks and refs cannot be inputs.
    if len(parts) == 4 and parts[0] == 'steps' and parts[1].isdigit():
        return (parts[2] == 'arguments' and parts[3] in {'value', 'expected_value'}) or (parts[2] == 'target' and parts[3] == 'name')
    if len(parts) == 5 and parts[0] == 'steps' and parts[1].isdigit():
        return parts[2] in {'wait', 'verify'} and parts[3].isdigit() and parts[4] in {'name', 'parent_name', 'equals'}
    if len(parts) == 6 and parts[0] == 'steps' and parts[1].isdigit():
        return parts[2:4] == ['target', 'ancestors'] and parts[4].isdigit() and parts[5] == 'name'
    return len(parts) == 3 and parts[0] in {'inputs', 'deliveries'} and parts[1].isdigit() and parts[2] in {'path', 'sha256'}


def materialize(template, values):
    values_valid(template['parameters'], values)
    def visit(value, parts):
        if isinstance(value, dict):
            if set(value) == {'param'}:
                name = value['param']
                if not isinstance(name, str) or name not in values or not parameter_slot(parts):
                    raise BokkioError('Parameter reference outside a permitted literal slot')
                return values[name]
            return {key: visit(v, parts + [key]) for key, v in value.items()}
        if isinstance(value, list):
            return [visit(v, parts + [str(i)]) for i, v in enumerate(value)]
        return value
    result = visit(copy.deepcopy(template), [])
    from .workflow import digest
    result['sha256'] = digest({k: v for k, v in result.items() if k != 'sha256'})
    return result


def validate_contracts(workflow):
    for kind in ('inputs', 'deliveries'):
        rows = workflow.get(kind)
        if not isinstance(rows, list) or len(rows) > 32:
            raise BokkioError('Invalid workflow file contracts')
        ids = set()
        paths = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {'id', 'path', 'sha256'} or not isinstance(row['id'], str) or not NAME.fullmatch(row['id']) or row['id'] in ids:
                raise BokkioError('Invalid workflow file contract identity')
            if not absolute_path(row['path']) or '\0' in row['path'] or not isinstance(row['sha256'], str) or not HASH.fullmatch(row['sha256']):
                raise BokkioError('File contracts require absolute paths and SHA-256 values')
            key = ntpath.normcase(row['path']) if ntpath.splitdrive(row['path'])[0] else str(Path(row['path']).resolve())
            if key in paths:
                raise BokkioError('Duplicate workflow file contract path')
            ids.add(row['id']); paths.add(key)
    canon=lambda p:ntpath.normcase(ntpath.normpath(p)) if ntpath.splitdrive(p)[0] else str(Path(p).resolve())
    ins = {canon(row['path']) for row in workflow['inputs']}
    if any(canon(row['path']) in ins for row in workflow['deliveries']):
        raise BokkioError('A preserved input cannot be an output')


def file_version(path):
    p = Path(path)
    if not p.is_file():
        raise BokkioError('Workflow file contract is missing: ' + str(p))
    sha = hashlib.sha256(); size = 0
    with p.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            sha.update(chunk); size += len(chunk)
    return {'path': str(p), 'sha256': sha.hexdigest(), 'bytes': size}


def check_files(contracts):
    records = []
    for row in contracts:
        record = {'id': row['id'], **file_version(row['path'])}
        if record['sha256'] != row['sha256']:
            raise BokkioError('Workflow file version mismatch: ' + row['id'])
        records.append(record)
    return records


def parameterize(workflow, parameters, slots, *, inputs=None, deliveries=None):
    """Create a parent-linked template from reviewed JSON-pointer literal slots."""
    from .workflow import digest, validate_workflow
    validate_workflow(workflow); declarations_valid(parameters)
    result = copy.deepcopy(workflow)
    result.update(schema=SCHEMA_V2, parameters=copy.deepcopy(parameters), inputs=copy.deepcopy(inputs or []),
                  deliveries=copy.deepcopy(deliveries or []), revision=workflow['revision'] + 1,
                  parent_sha256=workflow['sha256'])
    if not isinstance(slots, dict):
        raise BokkioError('Parameter slots must map JSON pointers to parameter names')
    for pointer, name in slots.items():
        if not isinstance(pointer, str) or not pointer.startswith('/') or name not in parameters:
            raise BokkioError('Invalid parameter slot')
        parts = pointer[1:].split('/')
        if not parameter_slot(parts):
            raise BokkioError('Parameter reference outside a permitted literal slot')
        target = result
        try:
            for part in parts[:-1]:target = target[int(part)] if isinstance(target, list) else target[part]
            key = int(parts[-1]) if isinstance(target, list) else parts[-1]
            if not isinstance(target[key], str):raise BokkioError('Only existing literal strings can be parameterized')
            target[key] = {'param': name}
        except (KeyError, IndexError, ValueError, TypeError):
            raise BokkioError('Parameter pointer does not identify a literal slot') from None
    result['sha256'] = digest({k: v for k, v in result.items() if k != 'sha256'})
    validate_workflow(result)
    return result
