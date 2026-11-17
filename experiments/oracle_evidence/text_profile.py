"""Optional text-only profile: reuse the downloaded language blob, omit vision."""
import json
from pathlib import Path
from .client import api

def main():
 store=Path('.local_models')
 parent=json.loads((store/'manifests/registry.ollama.ai/library/qwen3.5/27b').read_text())
 language=[x for x in parent['layers'] if x['mediaType']=='application/vnd.ollama.image.model']
 assert len(language)==1
 info=api('/api/show',{'model':'qwen3.5:27b'})
 body={'model':'qwen3.5:27b-text-oracle','files':{'model.gguf':language[0]['digest']},'template':info['template'],'renderer':'qwen3.5','parser':'qwen3.5','stream':False}
 if info.get('license'):body['license']=info['license']
 result=api('/api/create',body,timeout=120)
 created=json.loads((store/'manifests-v2/ollama.com/library/qwen3.5/27b-text-oracle').read_text())
 blobs=[x['digest'] for x in created['layers'] if x['mediaType']=='application/vnd.ollama.image.model']
 assert blobs==[language[0]['digest']]
 assert not any('projector' in x['mediaType'] for x in created['layers'])
 report={'parent':'qwen3.5:27b','profile':body['model'],'language_blob_sha256':blobs[0],'requantized':False,'additional_weight_download':False,'vision_projector':False,'renderer':'qwen3.5','parser':'qwen3.5','creation_response':result,'note':'Text-only profile is a separate experimental condition, not the stock multimodal model.'}
 Path('results/oracle_evidence/text-profile.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Verified text profile reuses the exact downloaded language weights.')
if __name__=='__main__':main()
