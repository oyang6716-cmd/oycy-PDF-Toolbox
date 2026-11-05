"""Offline composition regression tests for new page editor output."""
import tempfile
from pathlib import Path
import fitz
from page_layout import edits_from_paths, compose_document, page_dimensions, mm_to_pt, auto_arrange


def main():
    with tempfile.TemporaryDirectory() as tmp:
        files=[]
        for index,(w,h) in enumerate(((420,640),(920,450))):
            f=Path(tmp)/f'test_{index}.pdf'
            doc=fitz.open()
            p=doc.new_page(width=w,height=h)
            p.insert_text((55,65),f'ORIGINAL TEXT {index}')
            doc.save(f);doc.close();files.append(str(f))
        edits=edits_from_paths(files)
        assert len(edits)==2
        edits[0].rotation=90
        edits[0].scale=.75
        edits[0].horizontal='右对齐'
        edits[0].vertical='底部对齐'
        edits[1].horizontal='左对齐'
        path=Path(tmp)/'rendered.pdf'
        result=compose_document(edits,path,'自定义尺寸',(220,310))
        assert len(result)==2
        for n,p in enumerate(result):
            assert abs(p.rect.width-mm_to_pt(220))<1
            assert abs(p.rect.height-mm_to_pt(310))<1
            assert f'ORIGINAL TEXT {n}' in p.get_text()
        result.close()
        auto_arrange(edits,'A4 纵向',(210,297))
        assert edits[0].horizontal=='居中' and edits[0].vertical=='居中'
        same=compose_document(edits,mode='原始尺寸')
        assert round(same[0].rect.width)==420 and round(same[1].rect.width)==920
        same.close()
    print('PASS: custom paper size, per-page rotation/scale/alignment, vector text, original size')

if __name__=='__main__':main()
