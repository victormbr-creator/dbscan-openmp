"""Mediciones reanudables; --full sólo estima salvo --run."""
import argparse, csv, hashlib, itertools, json, os, platform, random, statistics, subprocess, time
from pathlib import Path
from generar_datos import ROOT, generar
N_FULL=[20000,40000,80000,120000,140000,160000,180000,200000]
K=[2,4,8,16,32,64]
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def execute(mode,path,t,k,eps,minimum):
    r=subprocess.run([str(ROOT/'bin'/mode),str(path),'-',str(eps),str(minimum),str(t),str(k)],capture_output=True,text=True,check=True)
    result=json.loads(r.stdout)
    if result['threads']!=t: raise RuntimeError('Número efectivo de hilos incorrecto')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(); group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--quick',action='store_true');group.add_argument('--full',action='store_true')
    p.add_argument('--individual',action='store_true');p.add_argument('--sizes',nargs='+',type=int)
    p.add_argument('--repetitions',type=int,default=10);p.add_argument('--run',action='store_true')
    p.add_argument('--force',action='store_true');p.add_argument('--epsilon',type=float,default=.03);p.add_argument('--min-samples',type=int,default=10)
    a=p.parse_args()
    if a.repetitions<1: p.error('repetitions debe ser positivo')
    v=os.cpu_count() or 1; threads=sorted(set([1,max(1,v//2),v,2*v]))
    sizes=a.sizes or ([4000,20000] if a.quick else ([20000,80000,140000,200000] if a.individual else N_FULL))
    if any(n<1 for n in sizes): p.error('sizes debe ser positivo')
    configs=[(n,m,t,k) for n in sizes for m in ['serial','paralelo1','paralelo2'] for t in ([1] if m=='serial' else threads) for k in (K if m=='paralelo2' else [0])]
    out=ROOT/'results'/'benchmarks';out.mkdir(parents=True,exist_ok=True)
    binaries={m:digest(ROOT/'bin'/m) for m in ['serial','paralelo1','paralelo2']}
    env={key:os.environ.get(key) for key in ['OMP_PROC_BIND','OMP_PLACES','OMP_WAIT_POLICY']}
    metadata={'platform':platform.platform(),'cpu_count':v,'threads':threads,'sizes':sizes,'repetitions':a.repetitions,'binaries':binaries,'environment':env,'epsilon':a.epsilon,'min_samples':a.min_samples}
    # Piloto explícito antes de permitir el conjunto completo. N² es una extrapolación conservadora, no una garantía.
    pilot=generar(20000); begin=time.perf_counter()
    sample=execute('serial',pilot,1,2,a.epsilon,a.min_samples)
    wall=time.perf_counter()-begin
    estimate=sum((sample['seconds']*(n/20000)**2+max(0,wall-sample['seconds']))*(a.repetitions+1) for n,m,t,k in configs)
    print(json.dumps({'configurations':len(configs),'measured_pilot':sample,'estimated_minutes_no_parallel_gain':estimate/60},indent=2),flush=True)
    if a.full and not a.run:
        print('Sólo estimación. Para ejecutar, añadir --run después de autorizar la duración.');raise SystemExit(0)
    # Verificar todos los programas antes de cualquier medición registrada.
    subprocess.run([str(ROOT/'.venv/bin/python'),str(ROOT/'scripts/validar_resultados.py')],check=True)
    paths={n:generar(n) for n in sizes};metadata['datasets']={n:digest(path) for n,path in paths.items()}
    signature=hashlib.sha256(json.dumps(metadata,sort_keys=True).encode()).hexdigest()[:16]
    if a.force: signature+='_'+str(time.time_ns())
    folder=out/signature;folder.mkdir(exist_ok=True)
    (folder/'metadata.json').write_text(json.dumps(metadata,indent=2))
    raw=folder/'raw.csv'; fields=['n','mode','threads','k','repeat','seconds','status','error']
    rows=list(csv.DictReader(raw.open())) if raw.exists() else []
    done={(int(r['n']),r['mode'],int(r['threads']),int(r['k']),int(r['repeat'])) for r in rows if r['status']=='ok'}
    jobs=list(itertools.product(range(a.repetitions),configs));random.Random(11).shuffle(jobs)
    warmed=set()
    with raw.open('a',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        if not rows:writer.writeheader()
        for rep,(n,m,t,k) in jobs:
            if (n,m,t,k,rep) in done:continue
            r=dict(n=n,mode=m,threads=t,k=k,repeat=rep,seconds='',status='ok',error='')
            try:
                if (n,m,t,k) not in warmed:
                    execute(m,paths[n],t,max(1,k),a.epsilon,a.min_samples);warmed.add((n,m,t,k))
                r['seconds']=execute(m,paths[n],t,max(1,k),a.epsilon,a.min_samples)['seconds']
            except Exception as e:r.update(status='failed',error=str(e))
            writer.writerow(r);f.flush();rows.append(r)
    values={}
    for r in rows:
        if r['status']=='ok':values.setdefault((int(r['n']),r['mode'],int(r['threads']),int(r['k'])),{})[int(r['repeat'])]=float(r['seconds'])
    complete={key:list(val.values()) for key,val in values.items() if len(val)==a.repetitions}
    with (folder/'summary.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['n','mode','threads','k','repetitions','mean_seconds','std_seconds','speedup','efficiency'])
        for key,vals in sorted(complete.items()):
            n,m,t,k=key; base=complete.get((n,'serial',1,0));avg=statistics.mean(vals)
            speed=statistics.mean(base)/avg if base else None
            w.writerow([n,m,t,k,len(vals),avg,statistics.stdev(vals) if len(vals)>1 else 0,speed,speed/t if speed else None])
    print('Resultados:',folder)
    missing=len(configs)-len(complete);print('Configuraciones incompletas:',missing)
    if missing:raise SystemExit(1)
