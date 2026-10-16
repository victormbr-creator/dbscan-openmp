"""Gráficas por panel para conservar todas las configuraciones legibles."""
import argparse
import csv
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def plot(summary):
    with summary.open() as f:
        rows=list(csv.DictReader(f))
    if not rows:
        raise ValueError('El resumen no contiene configuraciones completas')
    for r in rows:
        for key in ['n','threads','k']:r[key]=int(r[key])
        for key in ['mean_seconds','speedup']:r[key]=float(r[key])
    sizes=sorted({r['n'] for r in rows})
    threads=sorted({r['threads'] for r in rows if r['mode']!='serial'})
    def panels(values):
        fig,axes=plt.subplots(math.ceil(len(values)/2),2,figsize=(12,4*math.ceil(len(values)/2)),squeeze=False)
        for ax in axes.flat[len(values):]:ax.set_visible(False)
        return fig,list(axes.flat)
    def finish(fig,name):
        fig.tight_layout(rect=(0,0,1,.96))
        fig.savefig(summary.parent/(name+'.png'),dpi=160)
        plt.close(fig)
    fig,axes=panels(threads)
    fig.suptitle('Tiempo medio de cálculo por configuración')
    for ax,t in zip(axes,threads):
        groups={}
        for r in rows:
            if r['mode']!='serial' and r['threads']!=t:continue
            label={'serial':'P0','paralelo1':'P1','paralelo2':'P2'}[r['mode']]
            if r['mode']=='paralelo2':label+=f", k={r['k']}"
            groups.setdefault(label,[]).append(r)
        for label,group in groups.items():
            group.sort(key=lambda r:r['n'])
            ax.plot([r['n']/1000 for r in group],[r['mean_seconds']*1000 for r in group],marker='.',label=label)
        ax.set(title=f'{t} hilos (P0 usa 1)',xlabel='Puntos (miles)',ylabel='Tiempo medio (ms)')
        ax.grid(alpha=.2);ax.legend(fontsize=7,ncol=2)
    finish(fig,'tiempo')
    for x,name in [('threads','speedup_hilos'),('k','speedup_particiones')]:
        fig,axes=panels(sizes)
        fig.suptitle('Speedup = tiempo medio P0 / tiempo medio paralelo')
        for ax,n in zip(axes,sizes):
            groups={}
            for r in rows:
                if r['n']!=n or r['mode']=='serial':continue
                if x=='k' and r['mode']!='paralelo2':continue
                label=('P1' if r['mode']=='paralelo1' else f"P2, k={r['k']}") if x=='threads' else f"P2, {r['threads']} hilos"
                groups.setdefault(label,[]).append(r)
            for label,group in groups.items():
                group.sort(key=lambda r:r[x]);ax.plot([math.log2(r[x]) if x=='k' else r[x] for r in group],[r['speedup'] for r in group],marker='.',label=label)
            ax.axhline(1.5,color='gray',linestyle='--',label='Meta 1.5×')
            ax.set(title=f'N = {n:,}',xlabel='Número de hilos' if x=='threads' else 'Particiones k',ylabel='Speedup (×)')
            ticks=sorted({r[x] for group in groups.values() for r in group})
            ax.set_xticks([math.log2(v) if x=='k' else v for v in ticks],labels=[str(v) for v in ticks])
            ax.grid(alpha=.2);ax.legend(fontsize=7,ncol=2)
        finish(fig,name)
    print(summary.parent)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('summary',type=Path)
    plot(parser.parse_args().summary)
