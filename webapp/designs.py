"""Dimensioned, editable bedroom starter layouts derived from the supplied styles."""
import json
import math
from pathlib import Path
from flask import jsonify, request

THEMES={
 'L01':dict(wood='#c3a377',soft='#9ba889',wall='#f1e9da',floor='#cfae7b',material='wood'),
 'L02':dict(wood='#d8d0bc',soft='#c4a39a',wall='#f4eade',floor='#c7ae8c',material='fabric'),
 'L03':dict(wood='#bab5ac',soft='#999a92',wall='#efede6',floor='#c5b69b',material='fabric'),
 'L04':dict(wood='#947251',soft='#947252',wall='#e9dece',floor='#b69670',material='leather'),
 'L05':dict(wood='#c1a079',soft='#ba8f6a',wall='#eee3ce',floor='#c3a075',material='tatami'),
 'L06':dict(wood='#99704b',soft='#8f9469',wall='#ece2d1',floor='#ac835a',material='wood'),
}

def create_design(case,width=3.6,depth=3.8,include_desk=False):
    if case not in THEMES: raise ValueError('未知参考风格')
    width,depth=float(width),float(depth)
    if not math.isfinite(width) or not math.isfinite(depth) or not 3.2<=width<=6 or not 3.4<=depth<=7:
        raise ValueError('本组卧室模板适用于宽 3.2–6 米、深 3.4–7 米的房间')
    theme=THEMES[case]
    catalog=json.loads((Path(__file__).parent/'static/reference-pack/catalog.json').read_text(encoding='utf-8'))
    source=next(c for c in catalog['cases'] if c['id']==case)
    def asset(key):
        obj=next((o for o in source['objects'] if o['key']==key),None)
        return obj['id'] if obj else None
    walls=[]
    def wall(a,b,window=False): walls.append(dict(id='W-'+str(len(walls)),a=a,b=b,is_window=window))
    # Based on the supplied dimensioned illustration: 950 x 500 mm notch, 750 mm door.
    win=min(2.1,width-1.3)
    start=(width-win)/2
    wall([0,0],[start,0]);wall([start,0],[start+win,0],True);wall([start+win,0],[width,0])
    wall([width,0],[width,depth]);wall([width,depth],[.95,depth]);wall([.95,depth],[.95,depth-.5]);wall([.95,depth-.5],[.75,depth-.5]);wall([0,depth-.5],[0,0])
    furn=[]
    def add(type,name,x,y,length,breadth,height,heading=0,material='wood',reference=None):
        item=dict(id='F-'+str(len(furn)),name=name,type=type,rect=dict(cx=round(x,3),cy=round(y,3),len=round(length,3),wid=round(breadth,3),heading=heading),height=height,material=material,color=theme['soft'] if type in ('bed','chair') else theme['wood'])
        if reference: item['referenceAssetId']=reference
        furn.append(item)
    bed_width=1.5 if width<4 else 1.8
    bed_y=min(depth*.46,depth-.65-bed_width/2-.55)
    add('bed','榻榻米' if case=='L05' else '双人床',width-1.04,bed_y,2,bed_width,.26 if case=='L05' else .52,180,theme['material'],asset('bed'))
    add('wardrobe','整墙收纳衣柜',(.95+width)/2,depth-.32,min(2,width-.95-.2),.56,2.25,0,'painted' if case in ('L02','L03') else 'wood',asset('wardrobe'))
    add('nightstand','床头柜',width-.34,bed_y+bed_width/2+.3,.48,.45,.48,0,'wood',asset('nightstand'))
    add('plant','空间绿植',.27,1.4,.32,.32,.85,0,'foliage',asset('plant'))
    if include_desk and width>=3.5:
        add('desk','求职与阅读书桌',.91,.44,1.1,.5,.74,0,'wood',asset('desk-refined') or asset('desk'))
        add('chair','书桌椅',.91,1.02,.44,.44,.84,0,'rattan' if case in ('L01','L05','L06') else 'fabric',asset('chair'))
    elif bed_y-bed_width/2-.3>=.35:
        add('nightstand','床侧边几',width-.34,bed_y-bed_width/2-.3,.48,.45,.48,0,'wood',asset('nightstand'))
    name=source['name']+' · 一键卧室方案'
    scene=dict(meta=dict(name=name,unit='m',origin='southwest',note='参考风格布局，房间与家具尺寸需现场核对；未从照片恢复真实几何',custom=True,scale_estimated=False,template_case=case,room_width=width,room_depth=depth,design_palette=theme,reference_image=source['image'],reference_plan=source['planImage']),walls=walls,doors=[dict(id='D-0',name='入户门',center=[.375,depth-.5],width=.75,normal=[0,-1],in_wall=1,is_entry=True)],beams=[],furniture=furn,rooms=[dict(name='卧室',polygon=[[0,0],[width,0],[width,depth],[.95,depth],[.95,depth-.5],[0,depth-.5]])])
    # The original editor uses mirrored world X; keep the supplied plan's door on the left.
    for item in walls:
        item['a'][0]=round(width-item['a'][0],3)
        item['b'][0]=round(width-item['b'][0],3)
    scene['doors'][0]['center'][0]=width-.375
    for item in furn:
        item['rect']['cx']=round(width-item['rect']['cx'],3)
        item['rect']['heading']=(180-item['rect']['heading'])%360
    for point in scene['rooms'][0]['polygon']:
        point[0]=round(width-point[0],3)
    scene['rooms'][0].update(id='ROOM-0',rect=dict(cx=width/2,cy=depth/2,len=width,wid=depth,heading=0))
    return scene

def install_designs(app):
    @app.route('/design')
    def design_page():
        return app.send_static_file('design.html')
    @app.route('/api/design',methods=['POST'])
    def design_create():
        data=request.get_json(silent=True)
        if not isinstance(data,dict): return jsonify(error='请提交方案参数'),400
        try:
            scene=create_design(data.get('case','L01'),data.get('width',3.6),data.get('depth',3.8),data.get('includeDesk',False) is True)
            return jsonify(scene=scene)
        except (TypeError,ValueError): return jsonify(error='请选择有效风格，房间宽 3.2–6 米、深 3.4–7 米'),400
