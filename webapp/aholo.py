"""AHOLO integration. Credentials are read only from process environment."""
import hashlib
import json
import math
import os
import secrets
import threading
import time
from pathlib import Path
from urllib import error, parse, request as net
from flask import jsonify, request, send_file

GATEWAY = 'https://api.aholo3d.cn'

class ProviderError(Exception):
    pass

class AholoClient:
    def key(self):
        return os.environ.get('AHOLO_API_KEY','').strip()

    def call(self,path,data=None):
        if not self.key():
            raise ProviderError('本次服务未配置 AHOLO 密钥，请设置服务端环境变量后重启')
        headers={'Authorization':self.key(),'Accept':'application/json','User-Agent':'ImmerseHome/1.2'}
        payload=None if data is None else json.dumps(data).encode()
        if payload is not None: headers['Content-Type']='application/json'
        return self.fetch(GATEWAY+path,payload,headers)

    @staticmethod
    def fetch(url,data=None,headers=None,method=None):
        try:
            with net.urlopen(net.Request(url,data=data,headers=headers or {},method=method),timeout=45) as response:
                result=json.load(response)
        except error.HTTPError as exc:
            status=exc.code
            exc.close()
            reason={401:'密钥无效或未获得接口权限',403:'接口权限不足',429:'调用频率或额度受限'}.get(status,'接口暂时不可用')
            raise ProviderError(f'AHOLO HTTP {status}：{reason}') from None
        except (error.URLError,TimeoutError,OSError,ValueError):
            raise ProviderError('无法连接 AHOLO，请检查网络后重试') from None
        if not isinstance(result,dict): raise ProviderError('平台返回了无法识别的数据')
        if 'c' in result and str(result['c'])!='0':
            raise ProviderError('AHOLO 拒绝了请求，请检查账号权限、余额或素材格式')
        return result

    @staticmethod
    def multipart(fields,content,filename):
        boundary='ImmerseHome'+secrets.token_hex(16)
        chunks=[f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k,v in fields.items()]
        chunks.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode(),content,f'\r\n--{boundary}--\r\n'.encode()])
        return b''.join(chunks),'multipart/form-data; boundary='+boundary

    def upload(self,file):
        token=self.call('/asset/v1/token')
        domain=token.get('globalDomain','').rstrip('/')
        host=parse.urlparse(domain)
        if host.scheme!='https' or not (host.hostname or '').endswith(('.kujiale.com','.aholo3d.cn')):
            raise ProviderError('平台返回的素材上传域名未获允许')
        headers={'ous-token-v2':token['ousToken']}
        content=Path(file).read_bytes()
        block=max(1,int(token.get('blockSize',1048576)))
        md5=hashlib.md5(content).hexdigest()
        if len(content)<=block:
            body,ctype=self.multipart({'md5':md5},content,Path(file).name)
            self.fetch(domain+'/ous/api/v2/single/upload',body,{**headers,'Content-Type':ctype})
        else:
            query=parse.urlencode({'md5':md5,'blocks':math.ceil(len(content)/block),'size':len(content),'name':Path(file).name})
            self.fetch(domain+'/ous/api/v2/block/upload/init?'+query,b'',headers,method='POST')
            for index,start in enumerate(range(0,len(content),block),1):
                body,ctype=self.multipart({'block':index},content[start:start+block],Path(file).name)
                self.fetch(domain+'/ous/api/v2/block/upload/part',body,{**headers,'Content-Type':ctype})
        for _ in range(20):
            data=self.fetch(domain+'/ous/api/v2/upload/status',headers=headers).get('d') or {}
            if data.get('url'): return data['url']
            if data.get('errorCode'): raise ProviderError('素材上传未完成，请稍后重试')
            time.sleep(.3)
        raise ProviderError('素材上传超时，请稍后重试')

def install_aholo(app):
    directory=Path(app.root_path)/'instance'
    client=AholoClient()
    app.extensions['aholo']=client
    catalog=json.loads((Path(app.static_folder)/'reference-pack/catalog.json').read_text(encoding='utf-8'))
    objects={o['id']:o for c in catalog['cases'] for o in c['objects']}
    recordfile=directory/'aholo-tasks.json'
    try: records=json.loads(recordfile.read_text(encoding='utf-8'))
    except (OSError,ValueError): records={}
    lock=threading.Lock()
    def persist():
        temp=recordfile.with_suffix('.tmp')
        temp.write_text(json.dumps(records,ensure_ascii=False),encoding='utf-8')
        temp.replace(recordfile)
    def safe(record):
        return {k:v for k,v in record.items() if k in ('assetId','taskId','status','error','label','modelUrl','createdAt')}
    def refresh(record):
        if not record.get('taskId') or record['status'] in ('failed','ready'): return record
        if time.time()-record.get('checkedAt',0)<5: return record
        data=client.call('/lux3d/v1/generate/task/get?'+parse.urlencode({'taskid':record['taskId']})).get('d') or {}
        record['checkedAt']=time.time()
        status=int(data.get('status',0))
        record['status']='failed' if status in (4,6) else 'generating'
        if status==3:
            urls=[o.get('content','') for o in data.get('outputs',[]) if isinstance(o,dict)]
            url=next((u for u in urls if isinstance(u,str) and parse.urlparse(u).path.lower().endswith('.glb')),None)
            host=parse.urlparse(url or '')
            if not url: record.update(status='failed',error='任务完成但没有 GLB 模型')
            elif host.scheme!='https' or not (host.hostname or '').endswith(('.kujiale.com','.aholo3d.cn','.aliyuncs.com','.myqcloud.com')):
                record.update(status='failed',error='平台模型下载域名未获允许')
            else:
                try:
                    with net.urlopen(url,timeout=60) as response: raw=response.read(120*1024*1024+1)
                    if len(raw)>120*1024*1024 or raw[:4]!=b'glTF': raise ValueError('Invalid GLB')
                    (directory/(record['assetId']+'.glb')).write_bytes(raw)
                    record.update(status='ready',modelUrl='/api/aholo/models/'+record['assetId'])
                    record.pop('error',None)
                except (OSError,error.URLError,ValueError):
                    record['error']='模型已生成，但本机下载未完成；可稍后刷新重试'
        persist()
        return record
    @app.route('/api/aholo/status')
    def provider_status():
        return jsonify(configured=bool(client.key()),provider='AHOLO Lux3D',model='G1-Turbo',tasks=[safe(v) for v in records.values()])
    @app.route('/api/aholo/check',methods=['POST'])
    def provider_check():
        try:
            client.call('/lux3d/v1/generate/task/list?page=1&pagesize=1')
            return jsonify(ok=True,message='AHOLO 连接与鉴权成功')
        except ProviderError as exc: return jsonify(error=str(exc)),502
    @app.route('/api/aholo/tasks',methods=['POST'])
    def generate_model():
        if request.headers.get('X-Requested-With')!='ImmerseHome': return jsonify(error='请从本站页面提交请求'),403
        data=request.get_json(silent=True)
        asset=data.get('assetId') if isinstance(data,dict) else None
        if not isinstance(asset,str) or asset not in objects: return jsonify(error='请选择资料包中的有效单件'),400
        with lock:
            if asset in records and records[asset]['status']!='failed': return jsonify(safe(records[asset]))
            if any(v['status'] in ('uploading','generating') for v in records.values()):
                return jsonify(error='已有一个模型正在生成，请完成后再创建下一个'),409
            record={'assetId':asset,'label':objects[asset]['label'],'status':'uploading','createdAt':time.time()}
            records[asset]=record
            persist()
        try:
            url=client.upload(Path(app.static_folder)/objects[asset]['image'].lstrip('/'))
            result=client.call('/lux3d/v1/generate/img-to-3d/task/create',{'img':url,'version':'G1-Turbo','faceCount':50000,'outputFormat':['glb'],'enablePbr':True,'aiPredictSize':False})
            if not isinstance(result.get('d'),int): raise ProviderError('模型任务没有返回有效编号')
            record.update(taskId=str(result['d']),status='generating')
            persist()
            return jsonify(safe(record)),202
        except ProviderError as exc:
            record.update(status='failed',error=str(exc))
            persist()
            return jsonify(error=str(exc)),502
    @app.route('/api/aholo/tasks/<asset>')
    def model_status(asset):
        if asset not in records: return jsonify(error='未找到该模型任务'),404
        try:
            with lock: return jsonify(safe(refresh(records[asset])))
        except ProviderError as exc: return jsonify(error=str(exc)),502
    @app.route('/api/aholo/models/<asset>')
    def model_file(asset):
        if asset not in records or records[asset]['status']!='ready': return jsonify(error='模型尚未就绪'),404
        return send_file(directory/(asset+'.glb'),mimetype='model/gltf-binary',conditional=True)
