#!/usr/bin/env python3
"""Keep original/latest ISOs; retain verified compressed deltas for old builds."""
import argparse,gzip,hashlib,json,struct
from pathlib import Path
from localization_pipeline import ROOT,file_hash,write_json
from iso_archive_stage import ISO,CHUNK,exact,source_sha

MAGIC=b'PPDELTA1';BLOCK=65536;OUT=ROOT/'build/iso_backups'


def load_blocks(patch):
    rows=[];last=0
    with gzip.open(patch,'rb') as f:
        if exact(f,8)!=MAGIC:raise ValueError('Invalid delta')
        while True:
            raw=f.read(12)
            if not raw:break
            if len(raw)!=12:raise ValueError('Truncated delta')
            pos,size=struct.unpack('<QI',raw)
            if pos<last or not 0<size<=BLOCK:raise ValueError('Invalid block')
            data=exact(f,size);rows.append((pos,data));last=pos+size
    return rows


def reconstruct(source,patch,output=None):
    rows=iter(load_blocks(patch));current=next(rows,None);h=hashlib.sha256();size=0
    with source.open('rb') as fp:
        while True:
            raw=fp.read(CHUNK)
            if not raw:break
            data=bytearray(raw)
            while current is not None and current[0]<size+len(data):
                pos,value=current;local=pos-size
                if local<0 or local+len(value)>len(data):raise ValueError('Delta outside source chunk')
                data[local:local+len(value)]=value;current=next(rows,None)
            h.update(data)
            if output is not None:output.write(data)
            size+=len(data)
    if current is not None:raise ValueError('Delta past EOF')
    return h.hexdigest(),size


def pack(target):
    relative=str(target.relative_to(ROOT));stem=relative.replace('/','__')
    manifest=OUT/(stem+'.json');patch=OUT/(stem+'.delta.gz')
    if manifest.exists():
        row=json.loads(manifest.read_text())
        if file_hash(patch)!=row['patch_sha256'] or file_hash(target)!=row['sha256']:raise ValueError('Existing backup mismatch')
        return row
    if patch.exists():raise ValueError('Unfinished delta exists')
    ht=hashlib.sha256();hs=hashlib.sha256();offset=0;count=0
    with ISO.open('rb') as source,target.open('rb') as trial,patch.open('xb') as dest:
        with gzip.GzipFile(fileobj=dest,mode='wb',mtime=0,filename='',compresslevel=9) as gz:
            gz.write(MAGIC)
            while True:
                a=source.read(CHUNK)
                if not a:break
                b=exact(trial,len(a));ht.update(b);hs.update(a)
                if a!=b:
                    for start in range(0,len(a),BLOCK):
                        aa=a[start:start+BLOCK];bb=b[start:start+BLOCK]
                        if aa!=bb:gz.write(struct.pack('<QI',offset+start,len(bb))+bb);count+=1
                offset+=len(a)
            if trial.read(1):raise ValueError('Different ISO size')
    if hs.hexdigest()!=source_sha(ISO):raise ValueError('Original ISO changed')
    recovered,size=reconstruct(ISO,patch)
    if (recovered,size)!=(ht.hexdigest(),offset):raise ValueError('Delta reconstruction mismatch')
    row=dict(path=relative,sha256=ht.hexdigest(),bytes=offset,source=str(ISO.relative_to(ROOT)),source_sha256=hs.hexdigest(),patch=str(patch.relative_to(ROOT)),patch_sha256=file_hash(patch),patch_bytes=patch.stat().st_size,blocks=count,reconstruction_verified=True)
    write_json(manifest,row);print('Verified backup:',relative,patch.stat().st_size,flush=True)
    return row


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['archive','prune','restore']);p.add_argument('--path');a=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    latest=json.loads((ROOT/'localization/pipeline.json').read_text())['latest_experimental_build']
    protected={ISO.resolve(),(ROOT/latest['path']).resolve()}
    if file_hash(ISO)!=source_sha(ISO) or file_hash(ROOT/latest['path'])!=latest['sha256']:raise ValueError('Protected ISO mismatch')
    if a.command=='restore':
        rows=[json.loads(p.read_text()) for p in OUT.glob('*.iso.json')];row=next((r for r in rows if r['path']==a.path),None)
        if row is None:raise ValueError('Unknown archived path')
        dest=ROOT/row['path'];patch=ROOT/row['patch']
        if dest.resolve() in protected or dest.exists() or (ROOT/'build').resolve() not in dest.resolve().parents:raise ValueError('Unsafe/existing restore destination')
        if file_hash(patch)!=row['patch_sha256']:raise ValueError('Delta changed')
        with dest.open('xb') as fp:h,n=reconstruct(ISO,patch,fp)
        if (h,n)!=(row['sha256'],row['bytes']):raise ValueError('Restored ISO mismatch')
        print('Restored:',row['path']);return
    report=OUT/'retention.json'
    if a.command=='archive':
        rows=[]
        for path in sorted((ROOT/'build').rglob('*.iso')):
            if path.is_symlink():raise ValueError('Symlink ISO rejected')
            if path.resolve() not in protected:rows.append(pack(path))
        write_json(report,dict(protected=[str(p.relative_to(ROOT)) for p in sorted(protected)],archives=rows,deleted=[],bytes_freed=0))
    else:
        r=json.loads(report.read_text())
        for row in r['archives']:
            path=ROOT/row['path'];patch=ROOT/row['patch']
            if row['path'] in r['deleted']:continue
            if path.is_symlink() or path.resolve() in protected or (ROOT/'build').resolve() not in path.resolve().parents:raise ValueError('Unsafe prune path')
            if not row['reconstruction_verified'] or file_hash(patch)!=row['patch_sha256'] or file_hash(path)!=row['sha256']:raise ValueError('Prune input changed')
            path.unlink();r['deleted'].append(row['path']);r['bytes_freed']+=row['bytes'];write_json(report,r)
            print('Deleted obsolete ISO:',row['path'],flush=True)
        write_json(ROOT/'reports/iso_retention.json',r)
        print('Freed bytes:',r['bytes_freed'])


if __name__=='__main__':main()
