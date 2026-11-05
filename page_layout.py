"""Vector-preserving PDF page composition and per-page layout state.

Each PageLayout maps one source page to one output page. Does not rasterize PDF
content, but annotations/links/form widgets are not carried into the new page.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import fitz

PAGE_SIZES = {
    '原始尺寸': None,
    'A4 纵向': (595.276, 841.890),
    'A4 横向': (841.890, 595.276),
    'A3 纵向': (841.890, 1190.551),
    'A3 横向': (1190.551, 841.890),
    'Letter 纵向': (612.0, 792.0),
    'Letter 横向': (792.0, 612.0),
    '自定义尺寸': 'custom',
}

@dataclass
class PageLayout:
    source: str
    index: int
    rotation: int = 0
    scale: float = 1.0
    horizontal: str = '居中'
    vertical: str = '居中'
    dx: float = 0.0
    dy: float = 0.0

    def clone(self):
        return PageLayout(**asdict(self))


def mm_to_pt(mm):
    return float(mm) * 72 / 25.4


def page_dimensions(mode, source_size, custom_mm=(210, 297)):
    if mode == '原始尺寸':
        return tuple(float(v) for v in source_size)
    target = PAGE_SIZES.get(mode)
    if target == 'custom':
        w, h = map(float, custom_mm)
        if not (30 <= w <= 2000 and 30 <= h <= 2000):
            raise ValueError('自定义纸张宽高须在 30–2000 mm 之间。')
        return mm_to_pt(w), mm_to_pt(h)
    if target is None:
        raise ValueError(f'未知纸张尺寸：{mode}')
    return target


def layout_rectangle(source_rect, target_rect, edit, margin_pt=14):
    """Calculate content rect; over-scale stays inside printable area to avoid cropping."""
    available = fitz.Rect(target_rect.x0+margin_pt, target_rect.y0+margin_pt,
                          target_rect.x1-margin_pt, target_rect.y1-margin_pt)
    if available.is_empty:
        raise ValueError('页边距过大，已经没有可用排版空间。')
    angle = edit.rotation % 360
    sw, sh = (source_rect.height, source_rect.width) if angle in (90,270) else (source_rect.width,source_rect.height)
    fit = min(available.width/sw, available.height/sh)
    # At scale 100%, page fills available area in one dimension. At 150%,
    # the requested scale is clipped to the available safe rectangle: never crop.
    factor = min(float(edit.scale), 1.5)
    width = min(sw * fit * factor, available.width)
    height = min(sh * fit * factor, available.height)
    # Re-clamp uniformly for a non-square source and prevent distortion.
    uniform = min(width/sw, height/sh)
    width, height = sw*uniform, sh*uniform
    x = (available.x0 if edit.horizontal == '左对齐' else
         available.x1-width if edit.horizontal == '右对齐' else
         available.x0+(available.width-width)/2)
    y = (available.y0 if edit.vertical == '顶部对齐' else
         available.y1-height if edit.vertical == '底部对齐' else
         available.y0+(available.height-height)/2)
    x = max(available.x0, min(available.x1-width, x + edit.dx))
    y = max(available.y0, min(available.y1-height, y + edit.dy))
    return fitz.Rect(x,y,x+width,y+height)


def compose_page(output, source, page_number, edit, mode, custom_mm, margin_pt=14):
    src = source[page_number]
    width,height = page_dimensions(mode, (src.rect.width,src.rect.height), custom_mm)
    target = output.new_page(width=width,height=height)
    place = layout_rectangle(src.rect,target.rect,edit,margin_pt)
    # Use PDF vector embedding; supports per-page rotation without bitmap loss.
    target.show_pdf_page(place, source, page_number, rotate=edit.rotation % 360,
                         keep_proportion=True)
    return target


def compose_document(edits, output_path=None, mode='A4 纵向', custom_mm=(210,297), margin_pt=14):
    if not edits:
        raise ValueError('请先添加 PDF 页面。')
    result = fitz.open()
    opened={}
    try:
        for edit in edits:
            source_path=str(Path(edit.source).resolve())
            if source_path not in opened:
                document = fitz.open(source_path)
                if document.needs_pass:
                    document.close()
                    raise ValueError(f'PDF 已加密，无法预览排版：{Path(edit.source).name}')
                opened[source_path]=document
            document=opened[source_path]
            compose_page(result,document,edit.index,edit,mode,custom_mm,margin_pt)
        if output_path is not None:
            output_path=Path(output_path)
            output_path.parent.mkdir(parents=True,exist_ok=True)
            result.save(str(output_path),garbage=4,deflate=True)
        return result
    except Exception:
        result.close()
        raise
    finally:
        for d in opened.values(): d.close()


def edits_from_paths(paths):
    edits=[]
    for path in paths:
        with fitz.open(path) as d:
            if d.needs_pass: raise ValueError('已加密文件无法直接进行页面排版。')
            edits.extend(PageLayout(str(Path(path).resolve()),i) for i in range(len(d)))
    return edits


def auto_arrange(edits, mode, custom_mm):
    """Choose portrait/landscape orientation that best fits the output page."""
    for edit in edits:
        with fitz.open(edit.source) as d:
            r=d[edit.index].rect
            w,h=page_dimensions(mode,(r.width,r.height),custom_mm)
            fit0=min(w/r.width,h/r.height)
            fit90=min(w/r.height,h/r.width)
            edit.rotation=90 if fit90>fit0+1e-6 else 0
            edit.scale=1.0
            edit.horizontal='居中'
            edit.vertical='居中'
            edit.dx=edit.dy=0
