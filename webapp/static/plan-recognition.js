(function(root) {
  "use strict";
  // 常见线稿符号识别：按真实像素连通轮廓、内部枕垫、座垫和椅子排列筛选候选。
  // 不根据房间名称凭空补家具；无法分类的轮廓保留为待核对家具。
  function components(mask, width, height) {
    const visited = new Uint8Array(mask.length), queue = new Int32Array(mask.length), result = [];
    for (let start = 0; start < mask.length; start++) {
      if (!mask[start] || visited[start]) continue;
      let head = 0, tail = 1, x0 = width, y0 = height, x1 = 0, y1 = 0, count = 0;
      queue[0] = start; visited[start] = 1;
      while (head < tail) {
        const index = queue[head++], x = index % width, y = (index / width) | 0;
        x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); count++;
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          const nx = x + dx, ny = y + dy, ni = ny * width + nx;
          if (nx < 0 || nx >= width || ny < 0 || ny >= height || visited[ni] || !mask[ni]) continue;
          visited[ni] = 1; queue[tail++] = ni;
        }
      }
      if (count >= 5) result.push({x0, y0, x1, y1, w:x1-x0+1, h:y1-y0+1, count, cx:(x0+x1)/2, cy:(y0+y1)/2});
    }
    return result;
  }
  function borderCoverage(c, mask, width, height) {
    let hits = 0, total = 0;
    for (let x = c.x0; x <= c.x1; x++) {
      for (const y of [c.y0, c.y1]) {
        total++; let hit = false;
        for (let d = -2; d <= 2; d++) if (y+d >= 0 && y+d < height && mask[(y+d)*width+x]) hit = true;
        if (hit) hits++;
      }
    }
    for (let y = c.y0; y <= c.y1; y++) {
      for (const x of [c.x0, c.x1]) {
        total++; let hit = false;
        for (let d = -2; d <= 2; d++) if (x+d >= 0 && x+d < width && mask[y*width+x+d]) hit = true;
        if (hit) hits++;
      }
    }
    return hits / total;
  }
  function analyze(imageData, options = {}) {
    const {width:w, height:h, data} = imageData, ratio = options.ratio || 1;
    const dark = new Uint8Array(w*h), blue = new Uint8Array(w*h);
    for (let i=0;i<w*h;i++) {
      const r=data[i*4], g=data[i*4+1], b=data[i*4+2], alpha=data[i*4+3];
      dark[i] = alpha > 80 && .299*r+.587*g+.114*b < 165 ? 1 : 0;
      blue[i] = alpha > 80 && b-r > 25 && g-r > 10 && b > 95 ? 1 : 0;
    }
    const parts=components(dark,w,h), candidates=[];
    for (const c of parts) {
      const long=Math.max(c.w,c.h), short=Math.min(c.w,c.h), area=c.w*c.h;
      if (short<18 || long<28 || long>Math.min(w,h)*.45 || area>w*h*.14 || long/short>5.5) continue;
      const thickness=c.count/(2*(c.w+c.h));
      if (thickness>3.2 || c.count/area>.62) continue;
      const coverage=borderCoverage(c,dark,w,h);
      if (coverage<.65) continue;
      const inner=parts.filter(p=>p!==c && p.x0>c.x0+2 && p.y0>c.y0+2 && p.x1<c.x1-2 && p.y1<c.y1-2 && p.w*p.h>area*.025 && p.w*p.h<area*.55);
      let type="other", name="待分类家具", confidence=.48, length=c.w, breadth=c.h, alpha=0;
      // 沙发：长条框内有两个以上并列座垫。
      const horizontal=c.w>=c.h, span=horizontal?c.w:c.h;
      const seats=inner.filter(p=>(horizontal?p.w:p.h)>span*.12 && (horizontal?p.w:p.h)<span*.55);
      if (long/short>1.85 && seats.length>=2 && (Math.max(...seats.map(p=>horizontal?p.cx:p.cy))-Math.min(...seats.map(p=>horizontal?p.cx:p.cy)))>span*.25) {
        type="sofa";name="沙发（识别）";confidence=.80;length=short;breadth=long;alpha=horizontal?90:0;
      } else {
        const edges=[
          {alpha:90, pillows:inner.filter(p=>(p.cy-c.y0)/c.h<.29 && p.h<c.h*.3 && p.w<c.w*.8)},
          {alpha:270,pillows:inner.filter(p=>(c.y1-p.cy)/c.h<.29 && p.h<c.h*.3 && p.w<c.w*.8)},
          {alpha:0,  pillows:inner.filter(p=>(p.cx-c.x0)/c.w<.29 && p.w<c.w*.3 && p.h<c.h*.8)},
          {alpha:180,pillows:inner.filter(p=>(c.x1-p.cx)/c.w<.29 && p.w<c.w*.3 && p.h<c.h*.8)},
        ].sort((a,b)=>b.pillows.length-a.pillows.length);
        if (edges[0].pillows.length>=1 && long/short<2.4 && inner.length<=5) {
          type="bed";name="床（识别）";confidence=edges[0].pillows.length>=2?.86:.72;alpha=edges[0].alpha;
          length=alpha%180?c.h:c.w;breadth=alpha%180?c.w:c.h;
        } else {
          const chairs=parts.filter(p=>p!==c && p.w*p.h>area*.025 && p.w*p.h<area*.3 &&
            p.cx>c.x0-short*.8 && p.cx<c.x1+short*.8 && p.cy>c.y0-short*.8 && p.cy<c.y1+short*.8 &&
            !(p.cx>c.x0 && p.cx<c.x1 && p.cy>c.y0 && p.cy<c.y1) && Math.max(p.w,p.h)/Math.min(p.w,p.h)<2);
          if (chairs.length>=3) {type="table";name="桌子（识别）";confidence=.74;}
        }
      }
      if (type==="other" && (long<45 || short<24 || coverage<.85)) continue;
      candidates.push({...c,type,name,confidence,pixelLen:length*ratio,pixelWid:breadth*ratio,
        heading:((360-alpha)%360),cx:c.cx*ratio,cy:c.cy*ratio,
        bbox:{x0:c.x0*ratio,y0:c.y0*ratio,x1:c.x1*ratio,y1:c.y1*ratio},area});
    }
    candidates.sort((a,b)=>b.area-a.area);
    const furniture=[];
    for (const c of candidates) {
      if (furniture.some(p=>c.bbox.x0>=p.bbox.x0-2 && c.bbox.y0>=p.bbox.y0-2 && c.bbox.x1<=p.bbox.x1+2 && c.bbox.y1<=p.bbox.y1+2)) continue;
      furniture.push(c);
      if (furniture.length>=100) break;
    }
    const windows=components(blue,w,h).filter(p=>Math.max(p.w,p.h)>22 && Math.max(p.w,p.h)/Math.min(p.w,p.h)>4)
      .map(p=>({a:(p.w>p.h?[p.x0,p.cy]:[p.cx,p.y0]).map(v=>v*ratio),b:(p.w>p.h?[p.x1,p.cy]:[p.cx,p.y1]).map(v=>v*ratio)}));
    return {furniture,windows,dark,width:w,height:h,ratio,method:"local-symbols"};
  }
  function doorGaps(walls, result) {
    const doors=[], consumed=new Set(), {dark,width,height,ratio}=result;
    for(let i=0;i<walls.length;i++) for(let j=i+1;j<walls.length;j++) {
      if(consumed.has(i)||consumed.has(j)||doors.length>=30)continue;
      const a=walls[i],b=walls[j];
      if(a.kind!=="wall"||b.kind!=="wall")continue;
      const horizontal=Math.abs(a.a[1]-a.b[1])<5 && Math.abs(b.a[1]-b.b[1])<5;
      const vertical=Math.abs(a.a[0]-a.b[0])<5 && Math.abs(b.a[0]-b.b[0])<5;
      if(!horizontal&&!vertical)continue;
      const axis=horizontal?0:1,other=1-axis;
      if(Math.abs((a.a[other]+a.b[other]-b.a[other]-b.b[other])/2)>6)continue;
      const aa=[a.a,a.b].sort((p,q)=>p[axis]-q[axis]),bb=[b.a,b.b].sort((p,q)=>p[axis]-q[axis]);
      const left=aa[0][axis]<bb[0][axis]?aa:bb,right=left===aa?bb:aa;
      const gap=right[0][axis]-left[1][axis];
      if(gap<22*ratio ||gap>Math.min(width,height)*ratio*.16)continue;
      const start=left[1],end=right[0],cx=(start[0]+end[0])/2,cy=(start[1]+end[1])/2;
      let ink=0,total=0,near=0;
      for(let t=.15;t<.9;t+=.1){
        const x=Math.round((start[0]+(end[0]-start[0])*t)/ratio),y=Math.round((start[1]+(end[1]-start[1])*t)/ratio);
        total++;if(dark[y*width+x])ink++;
      }
      if(ink/total>.25)continue;
      // 门洞附近必须存在门扇/门弧笔迹，避免把任何断墙都当门。
      const radius=Math.round(gap/ratio*.8),px=Math.round(cx/ratio),py=Math.round(cy/ratio);
      for(let y=Math.max(0,py-radius);y<Math.min(height,py+radius);y++)for(let x=Math.max(0,px-radius);x<Math.min(width,px+radius);x++){
        if(Math.abs((horizontal?y-py:x-px))>6 && dark[y*width+x])near++;
      }
      if(near<Math.max(12,radius*.7))continue;
      doors.push({a:[...left[0]],b:[...right[1]],center:[cx,cy],width:gap,replace:[i,j],confidence:.60});
      consumed.add(i);consumed.add(j);
    }
    return doors;
  }
  root.PlanRecognition={analyze,doorGaps};
})(globalThis);
