import io
from typing import List, Dict, Any
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

class ReportService:
    def generate_incidents_excel(self, data: List[Dict[str, Any]]) -> io.BytesIO:
        """
        Genera un archivo Excel con la lista de incidentes/servicios.
        """
        df = pd.DataFrame(data)
        
        # Limpiar y formatear el DataFrame si no está vacío
        if not df.empty:
            # Columnas a mantener
            columns_to_keep = [
                "id", "status", "severity_level", "description", 
                "workshop_name", "mechanic_name", "client_phone", "mechanic_phone",
                "reported_at", "started_at", "finished_at", "rating", "review_comment"
            ]
            
            # Filtramos solo si las columnas existen
            df = df[[col for col in columns_to_keep if col in df.columns]]
            
            # Renombrar columnas para mayor legibilidad
            rename_map = {
                "id": "ID",
                "status": "Estado",
                "severity_level": "Severidad",
                "description": "Diagnóstico / Problema",
                "workshop_name": "Taller Asignado",
                "mechanic_name": "Mecánico",
                "client_phone": "Teléfono Cliente",
                "mechanic_phone": "Teléfono Mecánico",
                "reported_at": "Fecha Reporte",
                "started_at": "Fecha Inicio (Viaje)",
                "finished_at": "Fecha Finalización",
                "rating": "Calificación (1-5)",
                "review_comment": "Comentarios del Cliente"
            }
            df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
            
            # Formatear fechas
            for col in ["Fecha Reporte", "Fecha Inicio (Viaje)", "Fecha Finalización"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col]).dt.tz_localize(None)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Servicios')
            
            # Ajustar ancho de columnas automáticamente
            worksheet = writer.sheets['Servicios']
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)
                
        output.seek(0)
        return output

    def generate_incidents_pdf(self, title: str, data: List[Dict[str, Any]]) -> io.BytesIO:
        """
        Genera un archivo PDF tabular.
        """
        output = io.BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(letter))
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        title_style.alignment = 1 # Center
        
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 20))
        
        if not data:
            elements.append(Paragraph("No hay datos disponibles para los filtros seleccionados.", styles['Normal']))
            doc.build(elements)
            output.seek(0)
            return output

        # Definir encabezados
        headers = ["ID", "Fecha", "Taller", "Mecánico", "Estado", "Calificación"]
        table_data = [headers]
        
        for row in data:
            date_str = row.get("reported_at", "")
            if date_str:
                date_str = str(date_str).split("T")[0]
            
            rating = str(row.get("rating")) if row.get("rating") is not None else "N/A"
            
            table_data.append([
                str(row.get("id", "")),
                date_str,
                str(row.get("workshop_name", "N/A")),
                str(row.get("mechanic_name", "N/A")),
                str(row.get("status", "")).upper(),
                rating
            ])
            
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d47a1')), # Azul oscuro
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor('#e0e0e0')])
        ]))
        
        elements.append(t)
        doc.build(elements)
        output.seek(0)
        return output

report_service = ReportService()
