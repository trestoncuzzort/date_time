from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

root=Path.cwd()
out=root/'validation-output'
out.mkdir()
compiler=os.environ['VALIDATION_COMPILER']
fixed_sha='b02a36674afc109ea23716d0c671548e605dd96c'
original_sha='6248d64ed94916e446c83a038e8c8208ebb262ee'
records={'scope':'Pinned original/fixed wide scalar probe, dual-resolution regression and tick oracle; targeted platform validation, not full Boost.CI.',
         'compiler':compiler,'steps':[]}

def save():
    (out/'results.json').write_text(json.dumps(records,indent=2)+'\n')

def dependency(item):
    name=item['repository'].split('/')[-1]
    directory=root/'deps'/name
    directory.mkdir(parents=True)
    with (out/('dependency-'+name+'.log')).open('w') as stream:
        for command in [['git','init',str(directory)],
                        ['git','-C',str(directory),'fetch','--depth=1','https://github.com/'+item['repository']+'.git',item['head']],
                        ['git','-C',str(directory),'checkout','--detach','FETCH_HEAD']]:
            subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True)
    actual=subprocess.check_output(['git','-C',str(directory),'rev-parse','HEAD'],text=True).strip()
    assert actual==item['head'],(item,actual)
    return dict(item,include=str(directory/'include'))

items=json.loads((root/'validation/dependencies.json').read_text())
with ThreadPoolExecutor(max_workers=6) as pool:
    records['dependencies']=list(pool.map(dependency,items))
for label,expected in [('original',original_sha),('fixed',fixed_sha)]:
    actual=subprocess.check_output(['git','-C',str(root/label),'rev-parse','HEAD'],text=True).strip()
    assert actual==expected,(label,actual)
records.update(original_sha=original_sha,fixed_sha=fixed_sha)
save()

def execute(command,label,expected=0):
    start=time.monotonic()
    log=out/(label+'.log')
    with log.open('w') as stream:
        result=subprocess.run(list(map(str,command)),cwd=out,stdin=subprocess.DEVNULL,
                              stdout=stream,stderr=subprocess.STDOUT)
    content=log.read_text(errors='replace')
    records['steps'].append({'label':label,'command':list(map(str,command)),
                             'returncode':result.returncode,'expected':expected,
                             'seconds':time.monotonic()-start,'output_tail':content[-1500:]})
    save()
    print(label,'exit',result.returncode,flush=True)
    assert result.returncode==expected,(label,result.returncode,content[-4000:])
    return content

def build(source,owner,label,nano=False):
    exe=out/(label+('.exe' if os.name=='nt' else ''))
    includes=[root/owner/'include']+[Path(x['include']) for x in records['dependencies']]
    if compiler=='msvc':
        command=['cl','/nologo','/EHsc','/std:c++14','/Zc:__cplusplus','/permissive-',
                 '/DBOOST_ALL_NO_LIB=1','/Od','/Fo:'+str(out/(label+'.obj')),
                 '/Fe:'+str(exe)]
        if nano:command+=['/DBOOST_DATE_TIME_POSIX_TIME_STD_CONFIG']
        command+=['/I'+str(p) for p in includes]+[str(source)]
    else:
        command=['g++-11' if compiler=='gcc11' else 'clang++','-std=c++11','-O1','-g','-DBOOST_ALL_NO_LIB=1']
        if compiler=='clang-sanitized':
            command+=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
        if nano:command+=['-DBOOST_DATE_TIME_POSIX_TIME_STD_CONFIG']
        command+=['-I'+str(p) for p in includes]+[str(source),'-o',str(exe)]
    execute(command,label+'-build')
    return exe

for phase in ['original','fixed']:
    exe=build(root/'validation/probe.cpp',phase,'probe-'+phase)
    text=execute([exe],'probe-'+phase+'-run',expected=4 if phase=='original' else 0)
    assert text.strip()==('-15014117180 -18 -15014117180 -18' if phase=='original' else '27935555780 10 27935555780 10'),text

for config in ['micro','nano']:
    exe=build(root/'fixed/test/posix_time/testduration_scalars.cpp','fixed',
              'regression-'+config,nano=config=='nano')
    text=execute([exe],'regression-'+config+'-run')
    assert 'No errors detected.' in text,text
    small=[]
    for phase in ['original','fixed']:
        exe=build(root/'validation/scalar-oracle.cpp',phase,'oracle-'+phase+'-'+config,nano=config=='nano')
        text=execute([exe],'oracle-'+phase+'-'+config+'-wide',expected=1 if phase=='original' else 0)
        row=json.loads(text)
        assert row['scenarios']==60000 and row['comparisons']==480000,row
        assert row['failures']==(359172 if phase=='original' else 0),row
        text=execute([exe,'small'],'oracle-'+phase+'-'+config+'-small')
        small.append(json.loads(text))
    assert small[0]==small[1] and small[0]['failures']==0,small

paths=['include/boost/date_time/int_adapter.hpp','include/boost/date_time/time_duration.hpp',
       'test/posix_time/testduration_scalars.cpp','test/Jamfile.v2','xmldoc/time_duration.xml']
records['source_sha256']={p:hashlib.sha256((root/'fixed'/p).read_bytes()).hexdigest() for p in paths}
records['oracle_sha256']=hashlib.sha256((root/'validation/scalar-oracle.cpp').read_bytes()).hexdigest()
records['probe_sha256']=hashlib.sha256((root/'validation/probe.cpp').read_bytes()).hexdigest()
for label in ['original','fixed']:
    assert not subprocess.check_output(['git','-C',str(root/label),'status','--porcelain','--untracked-files=no'],text=True)
records['all_checks_passed']=True
save()
print('Pinned original failures and fixed wide scalar results verified in both resolutions.',flush=True)
