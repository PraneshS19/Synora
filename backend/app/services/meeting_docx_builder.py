import io
import re
from datetime import datetime
from typing import Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from app.models.schemas import MeetingDraft, MeetingJobResponse


def _set_cell_background(cell, hex_color: str):
    """Set background color of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tc_pr.append(shd)


def _set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner padding for table cells (in dxa: 20 dxa = 1 pt)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)


def build_meeting_docx(draft: MeetingDraft, job: Optional[MeetingJobResponse] = None) -> bytes:
    """
    Builds a professional institutional DOCX document from a MeetingDraft.
    Includes Title, Executive Summary, Discussion Topics, Formal Decisions,
    Action Items with owners and deadlines, and Identified Uncertainties.
    """
    doc = docx.Document()

    # 1. Page Margins (0.75 in for standard readable institutional layout)
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # 2. Document Title
    title_text = (draft.title or "Meeting Record · Draft").strip()
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(4)
    run_title = title_p.add_run(title_text)
    run_title.font.name = "Calibri"
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x11, 0x18, 0x27)  # Slate-900

    # 3. Subtitle / Metadata Bar
    meta_p = doc.add_paragraph()
    meta_p.paragraph_format.space_before = Pt(0)
    meta_p.paragraph_format.space_after = Pt(14)
    
    source_desc = "Meeting Transcript"
    if job:
        if job.source == "audio":
            source_desc = f"Audio Recording ({job.audioFileName or 'uploaded audio'})"
        elif job.source == "hybrid":
            source_desc = "Audio Recording & Supporting Transcript"
        elif job.source == "transcript":
            source_desc = "Meeting Transcript"

    date_str = datetime.now().strftime("%d %B %Y")
    meta_run = meta_p.add_run(
        f"SYNORA Institutional Intelligence  |  {date_str}  |  Source: {source_desc}"
    )
    meta_run.font.name = "Calibri"
    meta_run.font.size = Pt(9.5)
    meta_run.font.color.rgb = RGBColor(0x4B, 0x55, 0x63)  # Slate-600

    # 4. Executive Summary Section
    h_sum = doc.add_heading("Executive Summary", level=1)
    h_sum.paragraph_format.space_before = Pt(12)
    h_sum.paragraph_format.space_after = Pt(4)
    for run in h_sum.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)

    sum_p = doc.add_paragraph(draft.summary or "No summary recorded.")
    sum_p.paragraph_format.space_before = Pt(0)
    sum_p.paragraph_format.space_after = Pt(12)
    sum_p.paragraph_format.line_spacing = 1.15
    for run in sum_p.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(10.5)

    # 5. Discussion Topics Section
    h_disc = doc.add_heading(f"Discussion Topics ({len(draft.discussions)})", level=1)
    h_disc.paragraph_format.space_before = Pt(14)
    h_disc.paragraph_format.space_after = Pt(6)
    for run in h_disc.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)

    if not draft.discussions:
        p_empty = doc.add_paragraph("No explicit discussion topics recorded.")
        p_empty.paragraph_format.space_after = Pt(8)
    else:
        for idx, topic in enumerate(draft.discussions, 1):
            t_head = doc.add_paragraph()
            t_head.paragraph_format.space_before = Pt(6)
            t_head.paragraph_format.space_after = Pt(2)
            run_num = t_head.add_run(f"{idx}. {topic.topic}")
            run_num.font.name = "Calibri"
            run_num.font.size = Pt(11)
            run_num.font.bold = True
            run_num.font.color.rgb = RGBColor(0x11, 0x18, 0x27)
            if topic.timestamp:
                run_ts = t_head.add_run(f"  [{topic.timestamp}]")
                run_ts.font.name = "Calibri"
                run_ts.font.size = Pt(9.5)
                run_ts.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

            for pt in topic.points:
                p_bullet = doc.add_paragraph(pt, style="List Bullet")
                p_bullet.paragraph_format.space_before = Pt(0)
                p_bullet.paragraph_format.space_after = Pt(2)
                p_bullet.paragraph_format.line_spacing = 1.15
                for run in p_bullet.runs:
                    run.font.name = "Calibri"
                    run.font.size = Pt(10)

    # 6. Formal Decisions Section
    h_dec = doc.add_heading(f"Formal Decisions ({len(draft.decisions)})", level=1)
    h_dec.paragraph_format.space_before = Pt(14)
    h_dec.paragraph_format.space_after = Pt(6)
    for run in h_dec.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)

    if not draft.decisions:
        p_nodec = doc.add_paragraph("No formal resolutions or voting outcomes recorded.")
        p_nodec.paragraph_format.space_after = Pt(8)
    else:
        table_dec = doc.add_table(rows=1, cols=4)
        table_dec.alignment = WD_TABLE_ALIGNMENT.CENTER
        table_dec.autofit = False

        headers = ["No.", "Decision", "Status", "Evidence / Proposer"]
        col_widths = [Inches(0.5), Inches(3.5), Inches(1.0), Inches(2.0)]

        hdr_row = table_dec.rows[0]
        for c_idx, text in enumerate(headers):
            cell = hdr_row.cells[c_idx]
            cell.width = col_widths[c_idx]
            _set_cell_background(cell, "F3F4F6")
            _set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            run = p.add_run(text)
            run.font.name = "Calibri"
            run.font.size = Pt(10)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x11, 0x18, 0x27)

        for d_idx, dec in enumerate(draft.decisions, 1):
            row = table_dec.add_row()
            vals = [str(d_idx), dec.decision, dec.status.capitalize(), dec.evidence or "Identified in source"]
            for c_idx, text in enumerate(vals):
                cell = row.cells[c_idx]
                cell.width = col_widths[c_idx]
                _set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
                p = cell.paragraphs[0]
                run = p.add_run(text)
                run.font.name = "Calibri"
                run.font.size = Pt(9.5)

    # 7. Action Items & Assignments Section
    h_act = doc.add_heading(f"Action Items & Assignments ({len(draft.actionItems)})", level=1)
    h_act.paragraph_format.space_before = Pt(14)
    h_act.paragraph_format.space_after = Pt(6)
    for run in h_act.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(13)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)

    if not draft.actionItems:
        p_noact = doc.add_paragraph("No action assignments or task commitments recorded.")
        p_noact.paragraph_format.space_after = Pt(8)
    else:
        table_act = doc.add_table(rows=1, cols=5)
        table_act.alignment = WD_TABLE_ALIGNMENT.CENTER
        table_act.autofit = False

        headers_act = ["No.", "Action Item / Task", "Owner", "Due Date", "Status"]
        col_widths_act = [Inches(0.5), Inches(3.2), Inches(1.3), Inches(1.1), Inches(0.9)]

        hdr_row_act = table_act.rows[0]
        for c_idx, text in enumerate(headers_act):
            cell = hdr_row_act.cells[c_idx]
            cell.width = col_widths_act[c_idx]
            _set_cell_background(cell, "F3F4F6")
            _set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
            p = cell.paragraphs[0]
            run = p.add_run(text)
            run.font.name = "Calibri"
            run.font.size = Pt(10)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x11, 0x18, 0x27)

        for a_idx, act in enumerate(draft.actionItems, 1):
            row = table_act.add_row()
            status_text = "Review required" if act.uncertain else "Confirmed"
            vals = [
                str(a_idx),
                act.task,
                act.owner or "Unassigned",
                act.dueDate or "Not specified",
                status_text,
            ]
            for c_idx, text in enumerate(vals):
                cell = row.cells[c_idx]
                cell.width = col_widths_act[c_idx]
                _set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
                p = cell.paragraphs[0]
                run = p.add_run(text)
                run.font.name = "Calibri"
                run.font.size = Pt(9.5)
                if c_idx == 4 and act.uncertain:
                    run.font.color.rgb = RGBColor(0xB4, 0x53, 0x09)  # Amber-700

    # 8. Identified Uncertainties Section (if present)
    if draft.uncertainties:
        h_unc = doc.add_heading("Identified Source Uncertainties", level=1)
        h_unc.paragraph_format.space_before = Pt(14)
        h_unc.paragraph_format.space_after = Pt(4)
        for run in h_unc.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x92, 0x40, 0x0E)  # Amber-800

        for unc in draft.uncertainties:
            p_unc = doc.add_paragraph(unc, style="List Bullet")
            p_unc.paragraph_format.space_before = Pt(0)
            p_unc.paragraph_format.space_after = Pt(2)
            for run in p_unc.runs:
                run.font.name = "Calibri"
                run.font.size = Pt(9.5)
                run.font.color.rgb = RGBColor(0x78, 0x35, 0x0F)

    # 9. Institutional Review Notice Footer
    doc.add_paragraph().paragraph_format.space_before = Pt(16)
    foot_p = doc.add_paragraph()
    foot_p.paragraph_format.space_before = Pt(8)
    foot_p.paragraph_format.space_after = Pt(0)
    foot_run = foot_p.add_run(
        "Institutional Draft Notice: This record was generated with automated evidence reconciliation. "
        "Formal institutional review and approval are required prior to executive publication."
    )
    foot_run.font.name = "Calibri"
    foot_run.font.size = Pt(8.5)
    foot_run.font.italic = True
    foot_run.font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
