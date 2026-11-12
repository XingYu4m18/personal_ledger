"""轻量 Qt 图表，绘图坐标使用逻辑像素。"""
import math
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter,QPen,QColor,QPainterPath
from PySide6.QtWidgets import QWidget,QToolTip


class Chart(QWidget):
    selected = Signal(str)

    def __init__(self, ring=False):
        super().__init__()
        self.ring = ring
        self.items = []
        self.targets = []
        self.setMouseTracking(True)

    def set_items(self, items):
        self.items = items
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self.targets = []
        if not self.items:
            p.drawText(self.rect(), Qt.AlignCenter, "本期暂无支出")
            return
        colors = ["#367ba5","#51a38b","#df9961","#9272af","#c36d80","#9aaabc"]
        if self.ring:
            size = min(self.width()-24, self.height()*.5)
            box = QRectF((self.width()-size)/2,8,size,size)
            total = sum(v for _,v in self.items)
            angle = 90.
            for i,(name,value) in enumerate(self.items):
                span = value/total*360 if total else 0
                path = QPainterPath()
                path.moveTo(box.center())
                path.arcTo(box,angle,-span)
                path.closeSubpath()
                hole = QPainterPath()
                hole.addEllipse(box.adjusted(size*.28,size*.28,-size*.28,-size*.28))
                path = path.subtracted(hole)
                p.fillPath(path,QColor(colors[i%6]))
                self.targets.append((path,name,f"{name}  ¥{value:.2f}"))
                y = int(size+28+i*20)
                p.fillRect(14,y-9,9,9,QColor(colors[i%6]))
                label = self.fontMetrics().elidedText(f"{name}  {value/total:.0%}",Qt.ElideRight,self.width()-42)
                p.setPen(QColor("#192e38"));p.drawText(30,y,label)
                angle -= span
        else:
            box = QRectF(58,18,max(1,self.width()-80),max(1,self.height()-55))
            maximum = max(1,max(v for _,v in self.items))*1.1
            points=[]
            for j in range(5):
                y=box.bottom()-box.height()*j/4
                p.setPen(QColor("#e5ebef"));p.drawLine(QPointF(box.left(),y),QPointF(box.right(),y))
                p.setPen(QColor("#526773"));p.drawText(QRectF(0,y-9,50,18),Qt.AlignRight,f"{maximum*j/4:.0f}")
            step=max(1,math.ceil(len(self.items)/max(1,box.width()//85)))
            for i,(name,value) in enumerate(self.items):
                x=box.left()+box.width()*(i/(len(self.items)-1) if len(self.items)>1 else .5)
                point=QPointF(x,box.bottom()-box.height()*value/maximum);points.append(point)
                hit=QPainterPath();hit.addRect(QRectF(x-12,box.top(),24,box.height()))
                self.targets.append((hit,name,f"{name}  ¥{value:.2f}"))
                if i%step==0:
                    p.drawText(QRectF(x-38,box.bottom()+8,76,22),Qt.AlignCenter,name)
            path=QPainterPath(points[0])
            for point in points[1:]:path.lineTo(point)
            p.setPen(QPen(QColor("#235e9a"),2));p.drawPath(path)
            p.setBrush(QColor("#235e9a"))
            for point in points:p.drawEllipse(point,3,3)

    def mouseMoveEvent(self,event):
        for path,_,text in self.targets:
            if path.contains(event.position()):
                QToolTip.showText(event.globalPosition().toPoint(),text,self)
                return
        QToolTip.hideText()

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.LeftButton:
            for path,name,_ in self.targets:
                if path.contains(event.position()):
                    self.selected.emit(name)
                    return
