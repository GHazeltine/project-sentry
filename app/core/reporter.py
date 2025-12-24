import os
import time
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlmodel import Session, select
from app.database.models import engine, FileRecord

class Reporter:
    def __init__(self):
        self.report_dir = "/app/reports"
        os.makedirs(self.report_dir, exist_ok=True)

    def generate_report(self, mission_id, total_scanned, duplicates_removed, ghost_folders, target_paths, vault_info=None):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"SENTRY_REPORT_{timestamp}.pdf"
        filepath = os.path.join(self.report_dir, filename)

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        
        table_text_style = ParagraphStyle('TableText', parent=styles['Normal'], fontSize=8, fontName='Courier')
        elements = []

        # TITLE
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=20)
        elements.append(Paragraph("SENTRY COMMAND // SANITATION REPORT", title_style))
        elements.append(Spacer(1, 12))

        # STATS
        target_str = ", ".join(target_paths)
        data = [
            ["METRIC", "VALUE"],
            ["Mission ID", str(mission_id)],
            ["Total Files Scanned", str(total_scanned)],
            ["Duplicates Deleted", str(duplicates_removed)],
            ["Visual Groups Created", str(ghost_folders)],
            ["Target Drives", Paragraph(target_str, table_text_style)]
        ]
        t = Table(data, colWidths=[150, 350])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.black),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.gold),
            ('FONTNAME', (0, 0), (-1, 0), 'Courier-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 25))

        # VAULT SECTION
        if vault_info and vault_info['count'] > 0:
            elements.append(Paragraph("🛡️ CONFIDENTIAL ASSETS SECURED", styles['Heading2']))
            warning = "SENSITIVE FILES MOVED TO SECURE VAULT. GOOGLE PHOTOS SYNC DISABLED (.nomedia)."
            elements.append(Paragraph(warning, ParagraphStyle('Warn', parent=styles['Normal'], textColor=colors.red)))
            elements.append(Spacer(1, 10))
            
            vault_data = [
                ["VAULT LOCATION", Paragraph(vault_info['path'], table_text_style)],
                ["FILE COUNT", str(vault_info['count'])],
                ["ARCHIVE PASSWORD", Paragraph(vault_info['password'], table_text_style)]
            ]
            vt = Table(vault_data, colWidths=[120, 380])
            vt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.darkred),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Courier-Bold'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(vt)
            elements.append(Spacer(1, 20))

        # VISUAL GROUPS
        elements.append(Paragraph("EVIDENCE: VISUAL GROUPS (EDITS PRESERVED)", styles['Heading2']))
        with Session(engine) as session:
            grouped = session.exec(select(FileRecord).where(FileRecord.mission_id == mission_id, FileRecord.tag == "GROUPED").limit(40)).all()
            if not grouped:
                elements.append(Paragraph("No visual groups detected.", styles['Normal']))
            else:
                group_data = [["Filename", "Location"]]
                for f in grouped:
                    group_data.append([Paragraph(f.filename[:35], table_text_style), Paragraph(f.path, table_text_style)])
                
                gt = Table(group_data, colWidths=[150, 350])
                gt.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
                elements.append(gt)

        doc.build(elements)
        return filepath
