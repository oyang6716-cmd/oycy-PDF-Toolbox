"""Interactive per-page preview, alignment and non-rasterizing layout UI."""
from pathlib import Path
import io
import tkinter as tk
from tkinter import ttk, messagebox
import fitz
from PIL import Image, ImageTk
from page_layout import (PAGE_SIZES, PageLayout, compose_page, auto_arrange,
                         page_dimensions)

BG='#f5f7fb'; WHITE='#ffffff'; BLUE='#1768ee'; INK='#17243a'; SOFT='#64748b'
FONT='Microsoft YaHei UI'

class PageEditor(tk.Toplevel):
    def __init__(self, parent, edits, mode, custom_mm, on_apply):
        super().__init__(parent)
        self.title('页面排版编辑器  ·  oycy的PDF工具箱')
        self.geometry('1380x850'); self.minsize(950,610)
        self.configure(bg=BG)
        self.transient(parent)
        self.edits=[e.clone() for e in edits]
        self.on_apply=on_apply
        self._syncing=False
        self._photo=None
        self._doc_photo=None
        self._drag_origin=None
        self.mode=tk.StringVar(value=mode if mode in PAGE_SIZES else 'A4 纵向')
        self.mm_w=tk.StringVar(value=str(custom_mm[0])); self.mm_h=tk.StringVar(value=str(custom_mm[1]))
        self.scale=tk.DoubleVar(value=100)
        self.rotation=tk.StringVar(value='0')
        self.horizontal=tk.StringVar(value='居中')
        self.vertical=tk.StringVar(value='居中')
        self.zoom=tk.DoubleVar(value=100)
        self.status=tk.StringVar(value='选择左侧页面，右侧修改排版，中央查看实时效果。')
        self._build()
        self._load_list()
        if self.edits:
            self.page_list.selection_set(0)
            self._choose_page()
        self.protocol('WM_DELETE_WINDOW',self.destroy)

    def _btn(self,par,text,cmd,primary=False):
        return tk.Button(par,text=text,command=cmd,bg=BLUE if primary else WHITE,
                         fg=WHITE if primary else INK,relief='flat',cursor='hand2',
                         padx=12,pady=8,font=(FONT,10,'bold'),activebackground='#dbeafe')

    def _build(self):
        top=tk.Frame(self,bg=WHITE);top.pack(fill='x')
        tk.Label(top,text='页面预览与局部编辑',bg=WHITE,fg=INK,font=(FONT,17,'bold')).pack(side='left',padx=17,pady=14)
        self._btn(top,'自动排版',self._auto).pack(side='right',padx=8)
        self._btn(top,'重置选中页面',self._reset).pack(side='right',padx=8)
        self._btn(top,'应用并返回',self._apply,True).pack(side='right',padx=12)
        row=tk.Frame(self,bg=BG);row.pack(fill='x',padx=14,pady=8)
        tk.Label(row,text='目标纸张',bg=BG,fg=INK,font=(FONT,10,'bold')).pack(side='left')
        self.mode_box=ttk.Combobox(row,textvariable=self.mode,values=list(PAGE_SIZES),state='readonly',width=17)
        self.mode_box.pack(side='left',padx=8)
        self.mode_box.bind('<<ComboboxSelected>>',lambda e:self._mode_changed())
        tk.Label(row,text='自定义宽(mm)',bg=BG).pack(side='left',padx=(12,3))
        ttk.Entry(row,textvariable=self.mm_w,width=8).pack(side='left')
        tk.Label(row,text='高(mm)',bg=BG).pack(side='left',padx=(8,3))
        ttk.Entry(row,textvariable=self.mm_h,width=8).pack(side='left')
        self._btn(row,'更新预览',self._render).pack(side='left',padx=8)
        tk.Label(row,text='等比例排版 · 保留 PDF 矢量和可搜索文字',bg=BG,fg=SOFT,font=(FONT,9)).pack(side='right',padx=8)

        panes=tk.PanedWindow(self,orient='horizontal',sashwidth=9,bg='#e0e6ef',bd=0)
        panes.pack(fill='both',expand=True,padx=12,pady=4)
        left=tk.Frame(panes,bg=WHITE,width=265)
        middle=tk.Frame(panes,bg='#e7ecf4')
        right=tk.Frame(panes,bg=WHITE,width=250)
        panes.add(left,minsize=190);panes.add(middle,minsize=380,stretch='always');panes.add(right,minsize=225)
        self.after(200,lambda:self._place_sashes(panes))
        tk.Label(left,text='页面列表 · Ctrl/Shift 可多选',bg=WHITE,fg=INK,font=(FONT,11,'bold')).pack(anchor='w',padx=12,pady=11)
        self.page_list=tk.Listbox(left,selectmode='extended',exportselection=False,activestyle='none',
                                  font=(FONT,10),bd=0,bg=WHITE,fg=INK,selectbackground='#dbeafe',selectforeground=INK)
        self.page_list.pack(fill='both',expand=True,padx=9,pady=2)
        self.page_list.bind('<<ListboxSelect>>',lambda e:self._choose_page())
        tools=tk.Frame(left,bg=WHITE);tools.pack(fill='x',padx=8,pady=8)
        self._btn(tools,'上移',lambda:self._move(-1)).pack(side='left')
        self._btn(tools,'下移',lambda:self._move(1)).pack(side='left')
        self._btn(tools,'移除',self._delete).pack(side='left')
        tk.Label(left,text='左侧为页面顺序；选中页面后单独旋转、对齐或缩放。',
                 bg=WHITE,fg=SOFT,wraplength=220,justify='left').pack(anchor='w',padx=12,pady=9)

        zoomrow=tk.Frame(middle,bg='#e7ecf4');zoomrow.pack(fill='x',padx=10,pady=8)
        tk.Label(zoomrow,text='实时页面预览',bg='#e7ecf4',fg=INK,font=(FONT,11,'bold')).pack(side='left')
        self._btn(zoomrow,'适应窗口',self._fit).pack(side='right')
        ttk.Scale(zoomrow,from_=50,to=180,variable=self.zoom,command=lambda x:self._render()).pack(side='right',padx=10)
        tk.Label(zoomrow,text='预览缩放',bg='#e7ecf4',fg=SOFT).pack(side='right')
        self.canvas=tk.Canvas(middle,bg='#e7ecf4',highlightthickness=0,cursor='fleur')
        self.canvas.pack(fill='both',expand=True,padx=10,pady=(0,9))
        self.canvas.bind('<Configure>',lambda e:self._schedule_render())
        self.canvas.bind('<ButtonPress-1>',self._drag_start)
        self.canvas.bind('<ButtonRelease-1>',self._drag_end)
        self.canvas.bind('<B1-Motion>',self._drag_feedback)
        self._render_task=None

        tk.Label(right,text='所选页面的内容排版',bg=WHITE,fg=INK,font=(FONT,12,'bold')).pack(anchor='w',padx=15,pady=(15,8))
        tk.Label(right,text='旋转角度',bg=WHITE,fg=SOFT).pack(anchor='w',padx=15)
        for label,deg in [('0°','0'),('90°','90'),('180°','180'),('270°','270')]:
            tk.Radiobutton(right,text=label,variable=self.rotation,value=deg,
                           command=self._update_selected,bg=WHITE).pack(anchor='w',padx=16)
        tk.Label(right,text='内容大小（%）',bg=WHITE,fg=SOFT).pack(anchor='w',padx=15,pady=(14,4))
        scale=tk.Scale(right,from_=30,to=150,orient='horizontal',resolution=5,variable=self.scale,
                       command=lambda v:self._update_selected(),bg=WHITE,highlightthickness=0)
        scale.pack(fill='x',padx=13)
        tk.Label(right,text='水平对齐',bg=WHITE,fg=SOFT).pack(anchor='w',padx=15,pady=(12,4))
        hrow=tk.Frame(right,bg=WHITE);hrow.pack(fill='x',padx=10)
        for label in ('左对齐','居中','右对齐'):
            tk.Radiobutton(hrow,text=label,variable=self.horizontal,value=label,
                           indicatoron=False,command=self._update_selected,bg='#eff3f8',
                           selectcolor='#bfdbfe',font=(FONT,9)).pack(side='left',padx=2)
        tk.Label(right,text='垂直对齐',bg=WHITE,fg=SOFT).pack(anchor='w',padx=15,pady=(15,4))
        vrow=tk.Frame(right,bg=WHITE);vrow.pack(fill='x',padx=10)
        for label in ('顶部对齐','居中','底部对齐'):
            tk.Radiobutton(vrow,text=label,variable=self.vertical,value=label,
                           indicatoron=False,command=self._update_selected,bg='#eff3f8',
                           selectcolor='#bfdbfe',font=(FONT,9)).pack(side='left',padx=2)
        tk.Label(right,text='等距排版：四边留白一致，选中多页可批量设置。',
                 bg=WHITE,fg=SOFT,wraplength=210,justify='left').pack(anchor='w',padx=14,pady=17)
        self._btn(right,'选中页居中 + 等距留白',self._center_pages).pack(fill='x',padx=14)
        self._btn(right,'将当前设置应用到全部页面',self._apply_all).pack(fill='x',padx=14,pady=10)
        tk.Label(right,text='提示：可在预览区拖动页面内容微调位置。缩放超过可用区域时自动限制，避免裁切。',
                 bg=WHITE,fg=SOFT,wraplength=212,justify='left').pack(anchor='w',padx=15,pady=12)
        footer=tk.Label(self,textvariable=self.status,bg='#eaf2ff',fg=BLUE,anchor='w',padx=16,pady=9,font=(FONT,10))
        footer.pack(fill='x')

    def _place_sashes(self,p):
        try:
            width=p.winfo_width()
            if width>800:
                p.sash_place(0,250,0); p.sash_place(1,width-265,0)
        except tk.TclError:pass

    def _load_list(self,prefer=0):
        self.page_list.delete(0,'end')
        for n,e in enumerate(self.edits):
            self.page_list.insert('end',f'{n+1:03d}  {Path(e.source).name} · 第 {e.index+1} 页')
        if self.edits:
            index=min(max(prefer,0),len(self.edits)-1)
            self.page_list.selection_set(index)
            self.page_list.see(index)

    def _indices(self):
        return list(self.page_list.curselection())

    def _choose_page(self):
        if self._syncing:return
        indexes=self._indices()
        if not indexes:return
        edit=self.edits[indexes[0]]
        self._syncing=True
        self.rotation.set(str(edit.rotation));self.scale.set(round(edit.scale*100))
        self.horizontal.set(edit.horizontal);self.vertical.set(edit.vertical)
        self._syncing=False
        self._render()

    def _custom(self):
        try:
            a=float(self.mm_w.get());b=float(self.mm_h.get())
            if not (30<=a<=2000 and 30<=b<=2000):raise ValueError()
            return a,b
        except (ValueError,OverflowError):
            raise ValueError('自定义宽高须为 30–2000 之间的毫米数。')

    def _mode_changed(self):
        self._render()
        self.status.set('目标纸张已切换为 '+self.mode.get())

    def _update_selected(self):
        if self._syncing:return
        selected=self._indices()
        if not selected:return
        for index in selected:
            e=self.edits[index]
            e.rotation=int(self.rotation.get())
            e.scale=self.scale.get()/100
            e.horizontal=self.horizontal.get()
            e.vertical=self.vertical.get()
            e.dx=e.dy=0.0
        self.status.set(f'已更新 {len(selected)} 页的旋转、缩放和对齐设置')
        self._render()

    def _render(self):
        if not hasattr(self,'canvas'):return
        self.canvas.delete('all')
        indexes=self._indices()
        if not indexes:return
        edit=self.edits[indexes[0]]
        doc=None
        try:
            custom=self._custom() if self.mode.get()=='自定义尺寸' else (210,297)
            with fitz.open(edit.source) as source:
                doc=fitz.open()
                target=compose_page(doc,source,edit.index,edit,self.mode.get(),custom)
                width=max(200,self.canvas.winfo_width()-30)
                height=max(200,self.canvas.winfo_height()-30)
                ratio=min(width/target.rect.width,height/target.rect.height)*self.zoom.get()/100
                ratio=min(2.5,max(0.1,ratio))
                pix=target.get_pixmap(matrix=fitz.Matrix(ratio,ratio),alpha=False)
                image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                self._photo=ImageTk.PhotoImage(image)
                cx=self.canvas.winfo_width()/2;cy=self.canvas.winfo_height()/2
                self.canvas.create_rectangle(cx-pix.width/2+7,cy-pix.height/2+7,
                                            cx+pix.width/2+7,cy+pix.height/2+7,fill='#bac5d2',outline='')
                self.canvas.create_image(cx,cy,image=self._photo)
                self._render_factor=ratio
                self._page_origin=(cx-pix.width/2,cy-pix.height/2)
            self.status.set(f'预览第 {indexes[0]+1} 页 / 共 {len(self.edits)} 页 · '+self.mode.get()+
                            ' · 保留可搜索的 PDF 内容')
        except Exception as ex:
            self.canvas.create_text(30,40,text='无法显示预览：'+str(ex),anchor='nw',fill='#bd2738',width=460)
        finally:
            if doc is not None: doc.close()

    def _schedule_render(self):
        if self._render_task is not None:self.after_cancel(self._render_task)
        self._render_task=self.after(120,lambda:self._render())

    def _fit(self):self.zoom.set(100);self._render()
    def _drag_start(self,e):self._drag_origin=(e.x,e.y)
    def _drag_feedback(self,e):
        if self._drag_origin:
            self.canvas.configure(cursor='fleur')
    def _drag_end(self,e):
        if self._drag_origin is None:return
        dx=e.x-self._drag_origin[0];dy=e.y-self._drag_origin[1];self._drag_origin=None
        if abs(dx)+abs(dy)<5:return
        # Drag only current selected page; values are in PDF points.
        indexes=self._indices()
        if not indexes:return
        factor=max(.001,getattr(self,'_render_factor',1))
        edit=self.edits[indexes[0]]
        edit.dx += dx/factor;edit.dy += dy/factor
        self._render()
        self.status.set('已拖动所选页面内容；放开鼠标后更新预览')

    def _auto(self):
        try:
            auto_arrange(self.edits,self.mode.get(),self._custom() if self.mode.get()=='自定义尺寸' else (210,297))
            self._choose_page()
            self.status.set('已自动排版：根据纸张方向旋转，所有页面居中并保持等距留白')
        except Exception as e:messagebox.showerror('自动排版失败',str(e),parent=self)

    def _center_pages(self):
        for i in self._indices():
            item=self.edits[i];item.horizontal=item.vertical='居中';item.dx=item.dy=0.0
        self._choose_page();self.status.set('已将选中页面居中并保持等距留白')

    def _apply_all(self):
        ids=self._indices()
        if not ids:return
        template=self.edits[ids[0]]
        for edit in self.edits:
            if edit is template:continue
            for field in ('rotation','scale','horizontal','vertical','dx','dy'):
                setattr(edit,field,getattr(template,field))
        self._render();self.status.set('已将所选页面设置应用到全部 '+str(len(self.edits))+' 页')

    def _reset(self):
        for i in self._indices():
            e=self.edits[i];e.rotation=0;e.scale=1;e.horizontal=e.vertical='居中';e.dx=e.dy=0
        self._choose_page();self.status.set('选中页面已恢复默认布局')

    def _move(self,step):
        ids=self._indices()
        if len(ids)!=1:
            self.status.set('调整页序请只选中一页');return
        i=ids[0];j=i+step
        if not 0<=j<len(self.edits):return
        self.edits[i],self.edits[j]=self.edits[j],self.edits[i]
        self._load_list(j);self._choose_page()
        self.status.set('页面顺序已调整')

    def _delete(self):
        ids=self._indices()
        if len(ids)==len(self.edits):
            messagebox.showwarning('不能删除全部页面','至少要保留一个页面。',parent=self);return
        for i in reversed(ids):del self.edits[i]
        self._load_list(ids[0] if ids else 0);self._choose_page()
        self.status.set('已从此次编辑任务移除所选页面（源文件不受影响）')

    def _apply(self):
        try:
            custom=self._custom() if self.mode.get()=='自定义尺寸' else (210,297)
            # Validate page target against actual source page.
            first=self.edits[0]
            with fitz.open(first.source) as source:
                page_dimensions(self.mode.get(),source[first.index].rect,custom)
            self.on_apply(self.edits,self.mode.get(),custom)
            self.destroy()
        except Exception as e:messagebox.showerror('无法应用排版',str(e),parent=self)

class OutputPreview(tk.Toplevel):
    """PDF viewer with page navigation and zoom. Created from actual output bytes."""
    def __init__(self,parent,path,cleanup=None):
        super().__init__(parent)
        self.title('处理后效果预览  ·  oycy的PDF工具箱')
        self.geometry('1040x790');self.minsize(670,480)
        self.configure(bg=BG)
        self.cleanup=cleanup
        self.doc=fitz.open(path)
        self.index=0
        self.zoom=tk.DoubleVar(value=100)
        self.photo=None
        bar=tk.Frame(self,bg=WHITE);bar.pack(fill='x')
        tk.Label(bar,text='输出效果预览（实际处理结果）',bg=WHITE,font=(FONT,13,'bold')).pack(side='left',padx=15,pady=12)
        tk.Button(bar,text='上一页',command=lambda:self._change(-1)).pack(side='left',padx=5)
        tk.Button(bar,text='下一页',command=lambda:self._change(1)).pack(side='left',padx=5)
        self.page_label=tk.Label(bar,bg=WHITE,font=(FONT,10));self.page_label.pack(side='left',padx=9)
        ttk.Scale(bar,from_=60,to=200,variable=self.zoom,command=lambda v:self.render()).pack(side='right',padx=18)
        tk.Label(bar,text='缩放',bg=WHITE).pack(side='right')
        self.canvas=tk.Canvas(self,bg='#e7ecf4',highlightthickness=0)
        self.canvas.pack(fill='both',expand=True,padx=8,pady=8)
        self.canvas.bind('<Configure>',lambda e:self._later())
        self.pending=None
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.after(150,self.render)

    def _later(self):
        if self.pending:self.after_cancel(self.pending)
        self.pending=self.after(120,self.render)
    def _change(self,step):
        self.index=max(0,min(len(self.doc)-1,self.index+step));self.render()
    def render(self):
        if self.doc.is_closed:return
        page=self.doc[self.index];w=max(100,self.canvas.winfo_width()-24);h=max(100,self.canvas.winfo_height()-24)
        factor=min(w/page.rect.width,h/page.rect.height)*self.zoom.get()/100
        pix=page.get_pixmap(matrix=fitz.Matrix(factor,factor),alpha=False)
        im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        self.photo=ImageTk.PhotoImage(im)
        self.canvas.delete('all');self.canvas.create_image(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,image=self.photo)
        self.page_label.config(text=f'{self.index+1} / {len(self.doc)} 页')
    def close(self):
        self.doc.close()
        self.destroy()
        if self.cleanup:
            try:self.cleanup.cleanup()
            except Exception:pass
