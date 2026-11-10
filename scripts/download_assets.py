"""Download pinned Windows Vulkan runtime and text-only model files; verify SHA256."""
import argparse,hashlib,json,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(); p.add_argument('--models-only',action='store_true'); a=p.parse_args()
 manifest=json.loads((ROOT/'artifact_manifest.json').read_text())
 def download(url,path,sha):
  path.parent.mkdir(parents=True,exist_ok=True)
  if not path.exists() or hashlib.file_digest(path.open('rb'),'sha256').hexdigest()!=sha:
   temp=path.with_suffix(path.suffix+'.part'); print('Downloading',path.name,flush=True); urllib.request.urlretrieve(url,temp)
   if hashlib.file_digest(temp.open('rb'),'sha256').hexdigest()!=sha: raise ValueError('SHA256 mismatch: '+path.name)
   temp.replace(path)
  print('Verified',path.name)
 if not a.models_only:
  r=manifest['runtime']; path=ROOT/'runtime/llama.zip'; download(r['url'],path,r['sha256'])
  with zipfile.ZipFile(path) as z:
   for entry in z.infolist():
    target=(ROOT/'runtime/llama'/entry.filename).resolve()
    if not target.is_relative_to((ROOT/'runtime/llama').resolve()): raise ValueError('unsafe_zip_path')
   z.extractall(ROOT/'runtime/llama')
 for m in manifest['models']: download(m['url'],ROOT/'models'/m['file'],m['sha256'])
if __name__=='__main__': main()
