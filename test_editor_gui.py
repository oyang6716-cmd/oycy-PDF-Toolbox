"""GUI smoke test for editor opening, applying changes, and actual export."""
import tempfile
from pathlib import Path
import fitz
from app import ModernApp
from page_editor_ui import PageEditor, OutputPreview
from page_layout import edits_from_paths, compose_document

with tempfile.TemporaryDirectory() as tmp:
    f=Path(tmp)/'source.pdf'
    d=fitz.open();d.new_page(width=300,height=700).insert_text((40,60),'EDITOR TEST');d.save(f);d.close()
    app=ModernApp()
    app.files=[str(f)]
    app._refresh_files()
    edits=edits_from_paths(app.files)
    editor=PageEditor(app,edits,'A4 纵向',(210,297),app._accept_page_edits)
    editor.update_idletasks()
    editor.rotation.set('90');editor.scale.set(75)
    editor.horizontal.set('右对齐');editor.vertical.set('底部对齐')
    editor._update_selected()
    editor._apply()
    assert app.page_edits and app.page_edits[0].rotation==90
    out=Path(tmp)/'edited.pdf'
    doc=compose_document(app.page_edits,out,app.merge_page_size.get(),app.custom_page_mm)
    doc.close()
    with fitz.open(out) as d:
        assert len(d)==1 and 'EDITOR TEST' in d[0].get_text()
    viewer=OutputPreview(app,out)
    viewer.update_idletasks();viewer.render();viewer.close()
    app.destroy()
print('PASS: editor GUI, controls, apply, PDF output, preview window')
