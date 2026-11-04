from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
import subprocess
import sys
from .protocol import PROTOCOL_HASH, digest, extractor_hash, file_hash, read_jsonl, write_json, write_jsonl
from .protocol import read_json
from .schema import unique_cases, validate_prediction
from .predict import predict


def predict_file(input_path,output,models_path=None,primary='J24.PROTO',jobs=1):
    if type(jobs) is not int or not 1<=jobs<=4:raise ValueError('jobs must be 1..4')
    output=Path(output)
    if output.exists():raise ValueError('prediction output already exists')
    cases=read_jsonl(input_path);unique_cases(cases)
    models=None;binding={}
    if models_path is not None:
        from .calibration import load_models
        models,binding=load_models(models_path)
    if primary=='J24.CAL' and models is None:raise ValueError('CAL primary requires --models')
    code=extractor_hash();rows=[];channels=[]
    if jobs==1:
        for c in cases:
            if models is not None and c['cluster_id'] not in binding:raise ValueError('no outer model binding for case cluster')
            row,detail=predict(c,binding.get(c['cluster_id']),primary,context=code)
            validate_prediction(row)
            rows.append(row);channels.append({'set_id':c['set_id'],'channels':detail})
    else:
        # Subprocesses avoid shared-memory semaphore requirements in restricted environments.
        output.parent.mkdir(parents=True,exist_ok=True)
        with TemporaryDirectory(prefix='.judges-blind-shards-',dir=output.parent) as td:
            td=Path(td);commands=[]
            for i in range(min(jobs,len(cases))):
                ip=td/f'input{i}.jsonl';op=td/f'pred{i}';write_jsonl(ip,cases[i::jobs])
                cmd=[sys.executable,'-m','judges','v03','predict','--input',str(ip.resolve()),'--primary',primary,'--output',str(op.resolve())]
                if models_path:cmd+=['--models',str(Path(models_path).resolve())]
                commands.append((cmd,op))
            def run(item):
                cmd,op=item
                r=subprocess.run(cmd,cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True)
                if r.returncode:raise ValueError('blind prediction worker failed: '+r.stderr[-1500:])
                m=read_json(op/'manifest.json')
                if m['extractor_hash']!=code or m['model_set_hash']!=(digest(models) if models else None) or m['predictions_sha256']!=file_hash(op/'predictions.jsonl') or m['channels_sha256']!=file_hash(op/'channels.jsonl'):
                    raise ValueError('worker prediction seal mismatch')
                return read_jsonl(op/'predictions.jsonl'),read_jsonl(op/'channels.jsonl')
            with ThreadPoolExecutor(max_workers=jobs) as pool:
                results=list(pool.map(run,commands))
            byid={r['set_id']:r for rr,ch in results for r in rr}
            bychannel={r['set_id']:r for rr,ch in results for r in ch}
            if len(byid)!=len(cases) or set(byid)!=set(bychannel):raise ValueError('worker coverage mismatch')
            rows=[byid[c['set_id']] for c in cases];channels=[bychannel[c['set_id']] for c in cases]
            for r in rows:validate_prediction(r)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    write_jsonl(output/'predictions.jsonl',rows);write_jsonl(output/'channels.jsonl',channels)
    write_json(output/'manifest.json',{'status':'predictions_sealed','protocol_hash':PROTOCOL_HASH,
        'input_file_sha256':file_hash(input_path),'extractor_hash':code,'input_profile':cases[0]['input_profile'],
        'model_set_hash':digest(models) if models is not None else None,'calibration_corpus_hash':models['corpus_hash'] if models else None,
        'primary':primary,'sets':len(rows),'execution_workers':jobs,
        'predictions_sha256':file_hash(output/'predictions.jsonl'),'channels_sha256':file_hash(output/'channels.jsonl'),
        'candidate_hashes':{c['set_id']:{s:digest(c['candidates'][s]) for s in ['A','B']} for c in cases},'answer_key_read':False})
    return rows
