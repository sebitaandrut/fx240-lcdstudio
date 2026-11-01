# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only candidate scan. Findings need review; no scan proves absence of secrets.

Reports contain locations/categories, never the matched credential or identity text.
Git author/committer identity is intentionally outside source-content scanning.
"""
import argparse
from collections import Counter
import json
import io
import platform
import shutil
from pathlib import Path
import re
import subprocess
import zipfile

PATTERNS={
    'personal_home_path':rb'(?:/home/[A-Za-z0-9_.-]+|/Users/[A-Za-z0-9_.-]+|[A-Z]:\\Users\\[^\\\r\n]+)',
    'credential_signature':rb'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',
    'private_ipv4':rb'\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b',
    'mac_address':rb'(?<![A-Fa-f0-9])(?:[A-Fa-f0-9]{2}:){5}[A-Fa-f0-9]{2}(?![A-Fa-f0-9])',
    'uuid':rb'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b',
    'email_address':rb'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
}


def candidates(data,private_tokens=()):
    result=[name for name,pattern in PATTERNS.items() if re.search(pattern,data)]
    if any(token and (bool(re.search(rb'(?<![A-Za-z0-9_])'+re.escape(token)+rb'(?![A-Za-z0-9_])',data)) if len(token)<=5 else token in data) for token in private_tokens):result.append('local_identity_home_or_machine')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,action='append',default=[],help='Inspect a ZIP, wheel, or PyInstaller executable; repeatable')
    parser.add_argument('--output',type=Path,help='Optional local candidate report; review before publishing')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    def git(*arguments):return subprocess.check_output(['git','-C',str(root),*arguments])
    tokens={str(Path.home()).encode()}
    if len(Path.home().name)>3:tokens.add(Path.home().name.encode())
    # Compare local machine identifiers in memory only; never serialize their values.
    hostname=platform.node()
    if len(hostname)>3:tokens.add(hostname.encode())
    for source in (Path('/etc/machine-id'),Path('/proc/sys/kernel/random/boot_id'),*Path('/sys/class/net').glob('*/address')):
        try:value=source.read_text().strip()
        except OSError:continue
        if value and value!=('00:'*5+'00'):tokens.add(value.encode())
    if shutil.which('ip'):
        result=subprocess.run(['ip','-j','address','show'],capture_output=True,text=True)
        if result.returncode==0:
            for interface in json.loads(result.stdout):
                for entry in interface.get('addr_info',[]):
                    address=entry.get('local','')
                    if address and address not in ('127.0.0.1','::1'):tokens.add(address.encode())
    identity=git('log' ,'--all','--format=%an%x00%ae%x00%cn%x00%ce').decode().splitlines()
    for row in identity:
        tokens.update(value.encode() for value in row.split('\0') if len(value)>3)
    counts=Counter();findings=[]
    def scan(scope,name,data):
        counts[scope]+=1
        suffix=Path(name.split('::')[-1]).suffix.lower()
        if suffix in {'.pcap','.pcapng','.mp4','.mov','.mkv','.avi','.jpg','.jpeg','.gif','.heic','.webp','.pem','.key','.p12','.env'}:
            findings.append({'scope':scope,'file':name,'category':'sensitive_file_type_review'})
        if data.startswith(b'\x89PNG\r\n\x1a\n'):
            offset=8
            while offset+12<=len(data):
                size=int.from_bytes(data[offset:offset+4],'big')
                if data[offset+4:offset+8] in {b'eXIf',b'tEXt',b'iTXt',b'zTXt'}:
                    findings.append({'scope':scope,'file':name,'category':'png_text_or_exif_metadata'})
                    break
                offset+=size+12
        for category in candidates(data,tokens):findings.append({'scope':scope,'file':name,'category':category})
        if data.startswith(b'PK\x03\x04') and zipfile.is_zipfile(io.BytesIO(data)):
            with zipfile.ZipFile(io.BytesIO(data)) as nested:
                for item in nested.infolist():scan(scope+'_nested_zip',name+'::'+item.filename,nested.read(item))
    files=git('ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0')
    for name in filter(None,files):
        path=root/name
        if path.is_symlink():findings.append({'scope':'worktree','file':name,'category':'symlink'})
        if path.is_file():scan('worktree',name,path.read_bytes())
    for row in git('rev-list','--objects','--all').decode().splitlines():
        sha,_,name=row.partition(' ')
        if git('cat-file','-t',sha).strip()==b'blob':scan('history_blob',name,git('cat-file','blob',sha))
    for path in args.artifact:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for item in archive.infolist():
                    scan('zip_entry',path.name+'::'+item.filename,archive.read(item))
                    if item.extra or item.comment:findings.append({'scope':'zip_entry','file':item.filename,'category':'extra_metadata'})
        else:
            from PyInstaller.archive.readers import CArchiveReader
            archive=CArchiveReader(str(path))
            for name in archive.toc:
                if name.endswith('.pyz'):
                    pyz=archive.open_embedded_archive(name)
                    for module in pyz.toc:
                        data=pyz.extract(module,raw=True)
                        if data:scan('executable_python',module,data)
                else:
                    data=archive.extract(name)
                    if data:scan('executable_entry',name,data)
    result={'scope':'source contents, reachable Git blobs, and selected artifacts; commit identity intentionally retained',
            'counts':dict(counts),'candidates':findings,
            'limits':'Candidate scan only. Review manually, inspect image metadata and dependency provenance; unknown secret formats can be missed.'}
    rendered=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(rendered)
    else:print(rendered,end='')
    return 1 if findings else 0


if __name__=='__main__':raise SystemExit(main())
