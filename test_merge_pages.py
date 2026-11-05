"""Offline integration checks for PDF merge paper-size preservation."""
import tempfile
from pathlib import Path
import fitz
from app import merge_pdfs, MERGE_PAGE_RECTS

def main():
    with tempfile.TemporaryDirectory() as td:
        t=Path(td)
        paths=[]
        for i, (w,h) in enumerate([(180,270),(595,842),(1100,640)]):
            f=t/f'input{i}.pdf'
            doc=fitz.open()
            page=doc.new_page(width=w,height=h)
            page.insert_text((20,40),f'UNIQUE TEXT {i}',fontsize=13)
            page.draw_rect(fitz.Rect(10,10,w-10,h-10),color=(0,0,1))
            doc.save(str(f))
            doc.close()
            paths.append(str(f))
        target=t/'uniform.pdf'
        merge_pdfs(paths,target,'A4 纵向')
        with fitz.open(target) as out:
            assert len(out)==3
            for i,p in enumerate(out):
                assert abs(p.rect.width-MERGE_PAGE_RECTS['A4 纵向'][0])<1
                assert abs(p.rect.height-MERGE_PAGE_RECTS['A4 纵向'][1])<1
                assert f'UNIQUE TEXT {i}' in p.get_text(), (i,p.get_text())
        raw=t/'original.pdf'
        merge_pdfs(paths,raw,'原始尺寸')
        with fitz.open(raw) as out:
            assert [round(p.rect.width) for p in out]==[180,595,1100]
        print('PASS: A4 uniform sizes, extractable vector text, original-sizes mode')

if __name__=='__main__':main()
