"""Deterministic NewSphere layout geometry, shared by stills and motion layers."""
import math


def boxes(spec,w,h):
    n=len(spec.items);m=w*.075;top=h*.27;bottom=h*.76;gap=w*.025
    kind=spec.kind
    if kind=='comparison':
        cols=2 if w>h else 1
    elif kind in ('process_diagram','timeline'):
        cols=n if w>h else 1
    elif kind in ('flow_diagram','scientific_schematic'):
        cols=min(3,n) if w>h else min(2,n)
    elif kind=='fact_card':cols=2 if n>1 else 1
    else:cols=1
    rows=math.ceil(n/cols);cw=(w-2*m-gap*(cols-1))/cols;ch=(bottom-top-gap*(rows-1))/rows
    if kind=='geographic_map':cw=w*.38
    return [(round(m+(i%cols)*(cw+gap)),round(top+(i//cols)*(ch+gap)),round(cw),round(ch)) for i in range(n)]


def wrapped(draw,text,font,width):
    lines=[];current=''
    for word in text.split():
        candidate=(current+' '+word).strip()
        if draw.textbbox((0,0),candidate,font=font)[2]>width:
            if not current:raise ValueError('A word is too wide for this layout')
            lines.append(current);current=word
        else:current=candidate
    return lines+[current]


def item(draw,spec,index,box,font):
    x,y,w,h=box;entry=spec.items[index]
    if spec.kind=='scientific_schematic':
        draw.ellipse((x,y,x+w,y+h),fill='#102f42',outline='#25ccd9',width=3)
    else:
        draw.rounded_rectangle((x,y,x+w,y+h),radius=16 if spec.kind!='comparison' else 2,fill='#102f42',outline='#258799',width=2)
    size=34 if spec.aspect_ratio=='16:9' else 32
    lines=wrapped(draw,entry.label,font(size),w-36)
    extra=(80 if spec.kind=='fact_card' and entry.value is not None else
           40 if spec.kind=='comparison' else 26 if spec.kind=='timeline' else
           22 if spec.kind in ('flow_diagram','process_diagram') else 0)
    if len(lines)*(size+8)+extra>h-30:raise ValueError('Too much text for graphic layout')
    if spec.kind=='timeline':
        draw.ellipse((x+14,y+12,x+34,y+32),fill='#ffbd65');y+=26
    if spec.kind=='comparison':
        draw.rectangle((x,y,x+w,y+7),fill='#25ccd9' if index%2==0 else '#ffbd65')
        draw.text((x+18,y+18),f'{index+1:02}',font=font(25),fill='#ffbd65');y+=40
    if spec.kind=='fact_card' and entry.value is not None:
        draw.text((x+18,y+18),f'{entry.value:g} {spec.unit}',font=font(60),fill='#ffbd65');y+=80
    if spec.kind=='scientific_schematic':
        y+=max(0,(h-len(lines)*(size+8))/2-14)
        x+=w*.1;w*=.8
    if spec.kind in ('process_diagram','flow_diagram'):
        draw.text((x+16,y+10),str(index+1),font=font(24),fill='#ffbd65');y+=22
    for line in lines:
        draw.text((x+18,y+14),line,font=font(size),fill='white');y+=size+8
    if spec.kind=='statistical_chart':
        maximum=max(v.value for v in spec.items) or 1.
        length=(w-220)*entry.value/maximum
        draw.rectangle((x+18,y+8,x+18+max(1,length),y+28),fill='#25ccd9')
        draw.text((x+w-180,y),f'{entry.value:g} {spec.unit}',font=font(26),fill='#ffbd65')


def connections(draw,spec,positions,font):
    relations=spec.relations
    if spec.kind in ('timeline','process_diagram'):
        relations=[{'source':i,'target':i+1,'label':''} for i in range(len(positions)-1)]
    for rel in relations:
        a=positions[rel['source']];b=positions[rel['target']]
        start=(a[0]+a[2]/2,a[1]+a[3]/2);end=(b[0]+b[2]/2,b[1]+b[3]/2)
        dx=end[0]-start[0];dy=end[1]-start[1];length=math.hypot(dx,dy)
        if not length:continue
        ux,uy=dx/length,dy/length
        sa=min(a[2]/2/max(abs(ux),1e-8),a[3]/2/max(abs(uy),1e-8))
        sb=min(b[2]/2/max(abs(ux),1e-8),b[3]/2/max(abs(uy),1e-8))
        p=(start[0]+ux*sa,start[1]+uy*sa);q=(end[0]-ux*sb,end[1]-uy*sb)
        draw.line((*p,*q),fill='#ffbd65',width=4)
        draw.polygon([q,(q[0]-ux*12-uy*6,q[1]-uy*12+ux*6),(q[0]-ux*12+uy*6,q[1]-uy*12-ux*6)],fill='#ffbd65')
        if rel['label']:draw.text(((p[0]+q[0])/2,(p[1]+q[1])/2),rel['label'],font=font(19),fill='white',anchor='mm')
