import os
import time
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors

class Reporter:
    """
    Generates a professional PDF 'Certificate of Sanitation'
    for clients, detailing the cleaning operation.
    """
    
    def __init__(self, export_dir="/app/reports"):
        self.export_dir = export_dir
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)

    def generate_report(self, mission_id, total_scanned, duplicates_removed, ghost_folders, target_paths):
        filename = f"Sovereign_Sanitation_Report_{mission_id}.pdf"
        filepath = os.path.join(self.export_dir, filename)
        
        c = canvas.Canvas(filepath, pagesize=letter)
        width, height = letter
        
        # --- HEADER ---
        # Draw a dark header bar
        c.setFillColor(colors.black)
        c.rect(0, height - 1.5*inch, width, 1.5*inch, fill=1)
        
        # Company Name (White text)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(0.5*inch, height - 0.8*inch, "SOVEREIGN SILICON")
        
        c.setFont("Helvetica", 12)
        c.drawString(0.5*inch, height - 1.1*inch, "Cybersecurity & Data Sanitation Services")

        # --- BODY ---
        c.setFillColor(colors.black)
        
        # Title
        c.setFont("Helvetica-Bold", 18)
        c.drawString(0.5*inch, height - 2.5*inch, "CERTIFICATE OF SANITATION")
        
        # Metadata
        c.setFont("Helvetica", 12)
        y = height - 3.0*inch
        c.drawString(0.5*inch, y, f"Mission ID: {mission_id}")
        c.drawString(0.5*inch, y - 20, f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # --- STATS BOX ---
        # Draw a gray background box for stats
        c.setFillColor(colors.lightgrey)
        c.rect(0.5*inch, y - 2.5*inch, width - 1*inch, 1.5*inch, fill=1, stroke=0)
        
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(0.7*inch, y - 1.0*inch, "OPERATIONAL SUMMARY")
        
        c.setFont("Courier", 12)
        c.drawString(0.7*inch, y - 1.4*inch, f"Files Scanned:       {total_scanned}")
        c.drawString(0.7*inch, y - 1.6*inch, f"Duplicates Removed:  {duplicates_removed}")
        c.drawString(0.7*inch, y - 1.8*inch, f"Ghost Folders Purged: {ghost_folders}")
        c.drawString(0.7*inch, y - 2.0*inch, f"Target Drives:       {', '.join(target_paths)}")

        # --- FOOTER ---
        c.setFont("Helvetica-Oblique", 10)
        c.drawString(0.5*inch, 1*inch, "This document certifies that the storage media listed above has been processed")
        c.drawString(0.5*inch, 0.85*inch, "using Sovereign Silicon's proprietary cryptographic deduplication engine.")
        c.drawString(0.5*inch, 0.5*inch, "https://sovereignsilicon.com")

        c.save()
        return filepath
