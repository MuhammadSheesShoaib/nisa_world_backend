import os
import re

from datetime import datetime
from io import BytesIO
from groq import Groq
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image
from reportlab.lib.units import inch
from config import settings

class ExportService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center
            textColor=colors.HexColor('#AEB877')  # Olive green
        ))
        self.styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#AEB877')  # Olive green
        ))
        self.styles.add(ParagraphStyle(
            name='AIContent',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            spaceAfter=20,
            textColor=colors.HexColor('#374151')
        ))
        self.styles.add(ParagraphStyle(
            name='TableCell',
            parent=self.styles['Normal'],
            fontSize=7,
            leading=8,
            textColor=colors.HexColor('#374151'),
            wordWrap='LTR'
        ))
        self.styles.add(ParagraphStyle(
            name='TableCellHeader',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=9,
            textColor=colors.white,
            fontName='Helvetica-Bold',
            wordWrap='LTR'
        ))

    async def _get_ai_insights(self, sales_data, inventory_data, expenses_data, users_data):
        if not self.client:
            return "AI Insights Unavailable: GROQ_API_KEY not found in environment."

        # Prepare summary for AI
        total_sales = sum(float(s.sale_price) * s.quantity for s in sales_data)
        total_cogs = sum(float(s.cost_price) * s.quantity for s in sales_data)  # Cost of Goods Sold
        total_expenses = sum(float(e.amount) for e in expenses_data)
        profit = total_sales - total_cogs - total_expenses  # Net Profit: Revenue - COGS - Expenses
        low_stock = len([p for p in inventory_data if p.quantity < 10])
        
        prompt = f"""
        Identify patterns, cost-saving opportunities, and sales trends.
        Do NOT use complex markdown. Use simple bullet points (-) for lists.
        Focus on "Executive Summary" (high-level status) and "Strategic Actions" (what to do next).
        
        Data Snapshot:
        - Total Revenue: Rs {total_sales:,.2f}
        - Total Expenses: Rs {total_expenses:,.2f}
        - Net Profit: Rs {profit:,.2f}
        - Sales Count: {len(sales_data)}
        - Inventory Count: {len(inventory_data)}
        - Low Stock Items: {low_stock}
        - Staff Count: {len([u for u in users_data if u.role_id == 2])}

        Keep the tone professional but direct. Avoid fluff.
        Ensure "Executive Summary" and "Strategic Actions" are clearly labeled if used.
        """

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business analyst expert. Provide clear, professional, and data-driven insights."
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=10000,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"AI Generation Failed: {str(e)}"

    def generate_pdf_report(self, sales, inventory, expenses, users):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        story = []

        # 1. Header
        story.append(Paragraph("Nisa World Furniture Business Report", self.styles['ReportTitle']))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", self.styles['Normal']))
        story.append(Spacer(1, 20))

        # 2. AI Insights (Synchronous call to internal helper, assuming async handled by caller or running sync for PDF gen)
        # Note: ReportLab is blocking. We'll run the AI part before PDF gen in the main async method.
        # But for this class structure, let's keep it clean.
        pass 

        return buffer

    async def create_full_report(self, sales, inventory, expenses, users):
        # 1. Get AI Insights first
        ai_text = await self._get_ai_insights(sales, inventory, expenses, users)
        
        # 2. Generate PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        story = []

        # Title
        story.append(Paragraph("Nisa World Furniture - Executive Business Report", self.styles['ReportTitle']))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%B %d, %Y')}", self.styles['Normal']))
        story.append(Spacer(1, 0.5 * inch))

        # AI Section
        story.append(Paragraph("AI Executive Summary & Insights", self.styles['SectionHeading']))
        
        # Parse and format AI text
        lines = ai_text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Parse bold markdown **text** -> <b>text</b>
            # This regex looks for double asterisks surrounding text that doesn't contain double asterisks
            line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            
            # Parse list items
            # Check for bullet points (* or - at start)
            if line.startswith('* ') or line.startswith('- '):
                # Use bullet character and indentation
                clean_line = line[2:].strip()
                # Use a bullet style or manual indentation
                story.append(Paragraph(f"&bull; {clean_line}", self.styles['AIContent']))
            elif line.startswith('###') or line.startswith('##'):
                 # Convert headers to bold
                clean_line = line.lstrip('#').strip()
                story.append(Paragraph(f"<b>{clean_line}</b>", self.styles['AIContent']))
            else:
                story.append(Paragraph(line, self.styles['AIContent']))
                
        story.append(Spacer(1, 0.2 * inch))

        # Financial Overview
        story.append(Paragraph("Financial Overview", self.styles['SectionHeading']))
        total_sales = sum(float(s.sale_price) * s.quantity for s in sales)
        total_cogs = sum(float(s.cost_price) * s.quantity for s in sales)  # Cost of Goods Sold
        total_expenses = sum(float(e.amount) for e in expenses)
        profit = total_sales - total_cogs - total_expenses  # Net Profit: Revenue - COGS - Expenses

        fin_data = [
            ["Metric", "Value"],
            ["Total Revenue", f"Rs {total_sales:,.2f}"],
            ["Cost of Goods Sold (COGS)", f"Rs {total_cogs:,.2f}"],
            ["Total Expenses", f"Rs {total_expenses:,.2f}"],
            ["Net Profit", f"Rs {profit:,.2f}"]
        ]
        t = Table(fin_data, colWidths=[3*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#AEB877')), # Olive green header
            ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (1, 1), colors.HexColor('#FFFBB1')), # Light yellow for first row
            ('BACKGROUND', (0, 2), (1, 2), colors.HexColor('#D8E983')), # Lime green for second row
            ('BACKGROUND', (0, 3), (1, 3), colors.HexColor('#A5C89E')), # Light green for third row
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#AEB877')) # Olive green grid
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4 * inch))

        # Inventory Highlights
        story.append(Paragraph("Inventory Status", self.styles['SectionHeading']))
        low_stock = [p for p in inventory if p.quantity < 10]
        story.append(Paragraph(f"Total Products: {len(inventory)} | Low Stock Items: {len(low_stock)}", self.styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
        
        if low_stock:
            inv_data = [["Product", "Category", "Qty"]]
            for item in low_stock[:5]:  # Top 5 low stock
                inv_data.append([item.product_name, item.category, str(item.quantity)])
            
            t_inv = Table(inv_data, colWidths=[3*inch, 1.5*inch, 1*inch])
            # Build style with alternating row colors
            style_list = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#AEB877')), # Olive green header
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#A5C89E')), # Light green grid
            ]
            # Add alternating row backgrounds
            for i in range(1, len(inv_data)):
                color = colors.HexColor('#FFFBB1') if i % 2 == 1 else colors.HexColor('#D8E983')
                style_list.append(('BACKGROUND', (0, i), (-1, i), color))
            
            t_inv.setStyle(TableStyle(style_list))
            story.append(Paragraph("Critical Low Stock Items:", self.styles['Normal']))
            story.append(Spacer(1, 5))
            story.append(t_inv)

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _create_wrapped_cell(self, text, style_name='TableCell'):
        """Create a Paragraph cell that wraps text"""
        if text is None:
            text = '-'
        text = str(text)
        # Escape special characters for ReportLab
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return Paragraph(text, self.styles[style_name])
    
    def _calculate_column_widths(self, num_cols, page_width, margins):
        """Calculate dynamic column widths based on available space"""
        available_width = page_width - (margins * 2)
        # Use proportional widths - adjust these ratios as needed
        # For sales: 11 columns, give more space to text columns
        if num_cols == 11:  # Sales table
            ratios = [1.0, 1.5, 1.5, 1.0, 0.6, 0.8, 0.8, 1.0, 1.2, 0.6, 0.8]
        elif num_cols == 10:  # Inventory table
            ratios = [1.0, 2.0, 1.2, 1.0, 1.0, 0.6, 1.2, 1.2, 0.6, 0.8]
        elif num_cols == 8:  # Expenses table
            ratios = [1.0, 2.0, 1.5, 1.0, 1.2, 1.2, 0.6, 0.8]
        else:
            # Default: equal widths
            ratios = [1.0] * num_cols
        
        total_ratio = sum(ratios)
        widths = [available_width * (r / total_ratio) for r in ratios]
        return widths

    def create_monthly_detailed_report(self, sales_data, inventory_data, expenses_data, month_name, year):
        """
        Create a detailed PDF report for a specific month with all entries
        """
        buffer = BytesIO()
        page_width = letter[0]
        margins = 40
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=margins, leftMargin=margins, topMargin=50, bottomMargin=50)
        story = []

        # Title
        story.append(Paragraph(f"Nisa World Furniture - Monthly Detailed Report", self.styles['ReportTitle']))
        story.append(Paragraph(f"{month_name} {year}", self.styles['SectionHeading']))
        story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", self.styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))

        # Summary Statistics
        total_sales_revenue = sum(float(s.get('sale_price', 0)) * s.get('quantity', 0) for s in sales_data)
        total_cogs = sum(float(s.get('cost_price', 0)) * s.get('quantity', 0) for s in sales_data)  # Cost of Goods Sold
        total_expenses = sum(float(e.get('amount', 0)) for e in expenses_data)
        total_inventory_value = sum(float(i.get('cost_price', 0)) * i.get('quantity', 0) for i in inventory_data)
        net_profit = total_sales_revenue - total_cogs - total_expenses  # Net Profit: Revenue - COGS - Expenses

        summary_data = [
            ["Metric", "Value"],
            ["Total Sales Entries", str(len(sales_data))],
            ["Total Sales Revenue", f"Rs {total_sales_revenue:,.2f}"],
            ["Cost of Goods Sold (COGS)", f"Rs {total_cogs:,.2f}"],
            ["Total Inventory Entries", str(len(inventory_data))],
            ["Total Inventory Value", f"Rs {total_inventory_value:,.2f}"],
            ["Total Expense Entries", str(len(expenses_data))],
            ["Total Expenses", f"Rs {total_expenses:,.2f}"],
            ["Net Profit", f"Rs {net_profit:,.2f}"]
        ]
        t_summary = Table(summary_data, colWidths=[3*inch, 2*inch])
        # Build style with alternating row colors
        style_list = [
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#AEB877')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#AEB877')),
        ]
        # Add alternating row colors
        for i in range(1, len(summary_data)):
            color = colors.HexColor('#FFFBB1') if i % 2 == 1 else colors.HexColor('#D8E983')
            style_list.append(('BACKGROUND', (0, i), (1, i), color))
        t_summary.setStyle(TableStyle(style_list))
        
        story.append(Paragraph("Summary", self.styles['SectionHeading']))
        story.append(t_summary)
        story.append(Spacer(1, 0.3 * inch))

        # Sales Section
        story.append(Paragraph("Sales Records", self.styles['SectionHeading']))
        if sales_data and len(sales_data) > 0:
            # Create header row with wrapped text
            sales_table_data = [[
                self._create_wrapped_cell("Invoice", 'TableCellHeader'),
                self._create_wrapped_cell("Customer", 'TableCellHeader'),
                self._create_wrapped_cell("Product", 'TableCellHeader'),
                self._create_wrapped_cell("Category", 'TableCellHeader'),
                self._create_wrapped_cell("Qty", 'TableCellHeader'),
                self._create_wrapped_cell("Price", 'TableCellHeader'),
                self._create_wrapped_cell("Total", 'TableCellHeader'),
                self._create_wrapped_cell("Payment", 'TableCellHeader'),
                self._create_wrapped_cell("Sold By", 'TableCellHeader'),
                self._create_wrapped_cell("Edited", 'TableCellHeader'),
                self._create_wrapped_cell("Date", 'TableCellHeader')
            ]]
            
            for sale in sales_data:
                created_date = sale.get('created_at', '')
                if created_date:
                    try:
                        date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                        date_str = date_obj.strftime('%Y-%m-%d')
                    except:
                        date_str = created_date[:10] if len(created_date) >= 10 else created_date
                else:
                    date_str = '-'
                
                # Use Paragraph objects for text wrapping - no truncation
                sales_table_data.append([
                    self._create_wrapped_cell(sale.get('invoice_no', '-')),
                    self._create_wrapped_cell(sale.get('customer_name', '-')),
                    self._create_wrapped_cell(sale.get('product_name', '-')),
                    self._create_wrapped_cell(sale.get('category', '-')),
                    self._create_wrapped_cell(str(sale.get('quantity', 0))),
                    self._create_wrapped_cell(f"Rs {float(sale.get('sale_price', 0)):.2f}"),
                    self._create_wrapped_cell(f"Rs {float(sale.get('total', 0)):.2f}"),
                    self._create_wrapped_cell(sale.get('payment_type', '-')),
                    self._create_wrapped_cell(sale.get('sold_by_name', 'Unknown')),
                    self._create_wrapped_cell('Yes' if sale.get('edited', False) else 'No'),
                    self._create_wrapped_cell(date_str)
                ])
            
            # Calculate dynamic column widths
            col_widths = self._calculate_column_widths(11, page_width, margins)
            t_sales = Table(sales_table_data, colWidths=col_widths, repeatRows=1)
            style_list = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#AEB877')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#A5C89E')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]
            # Add alternating row colors
            for i in range(1, len(sales_table_data)):
                color = colors.HexColor('#FFFBB1') if i % 2 == 1 else colors.HexColor('#D8E983')
                style_list.append(('BACKGROUND', (0, i), (-1, i), color))
            
            t_sales.setStyle(TableStyle(style_list))
            story.append(KeepTogether(t_sales))
        else:
            story.append(Paragraph("No sales records found for this month.", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3 * inch))

        # Inventory Section
        story.append(Paragraph("Inventory Records", self.styles['SectionHeading']))
        if inventory_data and len(inventory_data) > 0:
            inv_table_data = [[
                self._create_wrapped_cell("Invoice", 'TableCellHeader'),
                self._create_wrapped_cell("Product", 'TableCellHeader'),
                self._create_wrapped_cell("Category", 'TableCellHeader'),
                self._create_wrapped_cell("Cost Price", 'TableCellHeader'),
                self._create_wrapped_cell("Sale Price", 'TableCellHeader'),
                self._create_wrapped_cell("Qty", 'TableCellHeader'),
                self._create_wrapped_cell("Total Value", 'TableCellHeader'),
                self._create_wrapped_cell("Added By", 'TableCellHeader'),
                self._create_wrapped_cell("Edited", 'TableCellHeader'),
                self._create_wrapped_cell("Date", 'TableCellHeader')
            ]]
            
            for item in inventory_data:
                created_date = item.get('created_at', '')
                if created_date:
                    try:
                        date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                        date_str = date_obj.strftime('%Y-%m-%d')
                    except:
                        date_str = created_date[:10] if len(created_date) >= 10 else created_date
                else:
                    date_str = '-'
                
                # Use Paragraph objects for text wrapping - no truncation
                inv_table_data.append([
                    self._create_wrapped_cell(item.get('invoice_no', '-')),
                    self._create_wrapped_cell(item.get('product_name', '-')),
                    self._create_wrapped_cell(item.get('category', '-')),
                    self._create_wrapped_cell(f"Rs {float(item.get('cost_price', 0)):.2f}"),
                    self._create_wrapped_cell(f"Rs {float(item.get('sale_price', 0)):.2f}"),
                    self._create_wrapped_cell(str(item.get('quantity', 0))),
                    self._create_wrapped_cell(f"Rs {float(item.get('total_value', 0)):.2f}"),
                    self._create_wrapped_cell(item.get('added_by_name', 'Unknown')),
                    self._create_wrapped_cell('Yes' if item.get('edited', False) else 'No'),
                    self._create_wrapped_cell(date_str)
                ])
            
            # Calculate dynamic column widths
            col_widths = self._calculate_column_widths(10, page_width, margins)
            t_inv = Table(inv_table_data, colWidths=col_widths, repeatRows=1)
            style_list = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#AEB877')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#A5C89E')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]
            # Add alternating row colors
            for i in range(1, len(inv_table_data)):
                color = colors.HexColor('#FFFBB1') if i % 2 == 1 else colors.HexColor('#D8E983')
                style_list.append(('BACKGROUND', (0, i), (-1, i), color))
            
            t_inv.setStyle(TableStyle(style_list))
            story.append(KeepTogether(t_inv))
        else:
            story.append(Paragraph("No inventory records found for this month.", self.styles['Normal']))
        
        story.append(Spacer(1, 0.3 * inch))

        # Expenses Section
        story.append(Paragraph("Expense Records", self.styles['SectionHeading']))
        if expenses_data and len(expenses_data) > 0:
            exp_table_data = [[
                self._create_wrapped_cell("Invoice", 'TableCellHeader'),
                self._create_wrapped_cell("Material", 'TableCellHeader'),
                self._create_wrapped_cell("Vendor", 'TableCellHeader'),
                self._create_wrapped_cell("Amount", 'TableCellHeader'),
                self._create_wrapped_cell("Payment Method", 'TableCellHeader'),
                self._create_wrapped_cell("Added By", 'TableCellHeader'),
                self._create_wrapped_cell("Edited", 'TableCellHeader'),
                self._create_wrapped_cell("Date", 'TableCellHeader')
            ]]
            
            for expense in expenses_data:
                created_date = expense.get('created_at', '')
                if created_date:
                    try:
                        date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                        date_str = date_obj.strftime('%Y-%m-%d')
                    except:
                        date_str = created_date[:10] if len(created_date) >= 10 else created_date
                else:
                    date_str = '-'
                
                # Use Paragraph objects for text wrapping - no truncation
                exp_table_data.append([
                    self._create_wrapped_cell(expense.get('invoice_no', '-')),
                    self._create_wrapped_cell(expense.get('material_name', '-')),
                    self._create_wrapped_cell(expense.get('vendor_name', '-')),
                    self._create_wrapped_cell(f"Rs {float(expense.get('amount', 0)):.2f}"),
                    self._create_wrapped_cell(expense.get('payment_method', '-')),
                    self._create_wrapped_cell(expense.get('added_by_name', 'Unknown')),
                    self._create_wrapped_cell('Yes' if expense.get('edited', False) else 'No'),
                    self._create_wrapped_cell(date_str)
                ])
            
            # Calculate dynamic column widths
            col_widths = self._calculate_column_widths(8, page_width, margins)
            t_exp = Table(exp_table_data, colWidths=col_widths, repeatRows=1)
            style_list = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#AEB877')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#A5C89E')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]
            # Add alternating row colors
            for i in range(1, len(exp_table_data)):
                color = colors.HexColor('#FFFBB1') if i % 2 == 1 else colors.HexColor('#D8E983')
                style_list.append(('BACKGROUND', (0, i), (-1, i), color))
            
            t_exp.setStyle(TableStyle(style_list))
            story.append(KeepTogether(t_exp))
        else:
            story.append(Paragraph("No expense records found for this month.", self.styles['Normal']))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def create_invoice_pdf(self, sales_data, invoice_no):
        """
        Generate invoice PDF for a specific invoice_no
        sales_data: List of sales with the same invoice_no
        invoice_no: Invoice number
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        story = []
        
        # Get logo path
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logo', 'logo.png')
        
        # Calculate totals
        total_amount = sum(float(sale.sale_price) * sale.quantity for sale in sales_data)
        
        # Get customer info from first sale
        first_sale = sales_data[0]
        customer_name = first_sale.customer_name
        customer_address = first_sale.customer_address or ""
        customer_phone = first_sale.customer_phone or ""
        
        # Handle date formatting
        if first_sale.created_at:
            if isinstance(first_sale.created_at, str):
                try:
                    invoice_date = datetime.fromisoformat(first_sale.created_at.replace('Z', '+00:00')).strftime("%m/%d/%Y")
                except:
                    invoice_date = datetime.now().strftime("%m/%d/%Y")
            else:
                invoice_date = first_sale.created_at.strftime("%m/%d/%Y")
        else:
            invoice_date = datetime.now().strftime("%m/%d/%Y")
        
        # Header with Logo
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 0.2*inch))
            except Exception as e:
                print(f"Error loading logo: {e}")
        
        # Company Name
        story.append(Paragraph("Nisa World Furniture", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.1*inch))
        
        # Company Address
        company_address = "Plot @ A-132, 133, Shop # 5 Hira Heaven, Main Sir Shah Suleman Road Ishaqabad Near Gharibabad, Karachi."
        company_phone = "+92 307 3190861"
        
        story.append(Paragraph(f"<b>Address:</b> {company_address}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Phone No:</b> {company_phone}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Invoice Details and Bill To Section
        invoice_table_data = [
            ['Invoice No:', invoice_no, 'Bill To:', ''],
            ['Date:', invoice_date, 'Customer Name:', customer_name],
            ['', '', 'Customer Address:', customer_address],
            ['', '', 'Customer Phone:', customer_phone],
        ]
        
        invoice_info_table = Table(invoice_table_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2.5*inch])
        invoice_info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(invoice_info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Advance amount is invoice-level (same for all items in bulk sale) - use first sale
        first_sale_for_payment = sales_data[0]
        payment_type = str(getattr(first_sale_for_payment, 'payment_type', None) or "1")
        total_advance = float(getattr(first_sale_for_payment, 'advance_amount', None) or 0)
        total_remaining = total_amount - total_advance
        is_advance_payment = (payment_type == "2") or (total_advance > 0)
        
        # Items Table
        items_table_data = [['ITEM', 'QTY', 'PRICE/UNIT', 'TOTAL']]
        
        for sale in sales_data:
            item_name = f"{sale.product_name}"
            if sale.category:
                item_name += f" ({sale.category})"
            quantity = sale.quantity
            price_per_unit = float(sale.sale_price)
            total = price_per_unit * quantity
            
            items_table_data.append([
                item_name,
                str(quantity),
                f"Rs {price_per_unit:,.2f}",
                f"Rs {total:,.2f}"
            ])
        
        # Add empty rows if needed
        while len(items_table_data) < 5:
            items_table_data.append(['', '', '', ''])
        
        items_table = Table(items_table_data, colWidths=[3.5*inch, 1*inch, 1.5*inch, 1.5*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#AEB877')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Summary Section - Advance: Total, Advance Amount, Paid Amount, Balance Due; Full: Total only
        summary_data = [['TOTAL AMOUNT:', f"Rs {total_amount:,.2f}"]]
        if is_advance_payment:
            summary_data.append(['ADVANCE AMOUNT:', f"Rs {total_advance:,.2f}"])
            summary_data.append(['BALANCE DUE:', f"Rs {total_remaining:,.2f}"])
        
        summary_table = Table(summary_data, colWidths=[5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(KeepTogether(summary_table))
        story.append(Spacer(1, 0.5*inch))
        
        # Thank you message
        thank_you_style = ParagraphStyle(
            name='ThankYou',
            parent=self.styles['Normal'],
            fontSize=12,
            alignment=1,  # Center
            spaceBefore=20
        )
        story.append(Paragraph("Thank you for your business!", thank_you_style))
        
        doc.build(story)
        buffer.seek(0)
        return buffer

    def create_expense_invoice_pdf(self, expenses_data, invoice_no):
        """
        Generate expense invoice PDF for a specific invoice_no
        expenses_data: List of expenses with the same invoice_no
        invoice_no: Invoice number
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        story = []
        
        # Get logo path
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logo', 'logo.png')
        
        # Calculate totals
        total_amount = sum(float(expense.amount) for expense in expenses_data)
        
        # Get vendor info from first expense
        first_expense = expenses_data[0]
        # Split material_name to get vendor_name
        if " - " in first_expense.material_name:
            parts = first_expense.material_name.split(" - ", 1)
            vendor_name = parts[1] if len(parts) > 1 else "Unknown"
        else:
            vendor_name = "Unknown"
        
        # Handle date formatting
        if first_expense.created_at:
            if isinstance(first_expense.created_at, str):
                try:
                    invoice_date = datetime.fromisoformat(first_expense.created_at.replace('Z', '+00:00')).strftime("%m/%d/%Y")
                except:
                    invoice_date = datetime.now().strftime("%m/%d/%Y")
            else:
                invoice_date = first_expense.created_at.strftime("%m/%d/%Y")
        else:
            invoice_date = datetime.now().strftime("%m/%d/%Y")
        
        # Header with Logo
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 0.2*inch))
            except Exception as e:
                print(f"Error loading logo: {e}")
        
        # Company Name
        story.append(Paragraph("Nisa World Furniture", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.1*inch))
        
        # Company Address
        company_address = "Plot @ A-132, 133, Shop # 5 Hira Heaven, Main Sir Shah Suleman Road Ishaqabad Near Gharibabad, Karachi."
        company_phone = "+92 307 3190861"
        
        story.append(Paragraph(f"<b>Address:</b> {company_address}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Phone No:</b> {company_phone}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Invoice Details and Vendor Section
        invoice_table_data = [
            ['Invoice No:', invoice_no, 'Vendor:', ''],
            ['Date:', invoice_date, 'Vendor Name:', vendor_name],
        ]
        
        invoice_info_table = Table(invoice_table_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2.5*inch])
        invoice_info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(invoice_info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Advance amount is invoice-level (same for all items in bulk expense) - use first expense
        first_expense_for_payment = expenses_data[0]
        payment_method = str(getattr(first_expense_for_payment, 'payment_method', None) or "1")
        total_advance = float(getattr(first_expense_for_payment, 'advance_amount', None) or 0)
        total_remaining = total_amount - total_advance
        is_advance_payment = (payment_method == "2") or (total_advance > 0)
        
        # Items Table
        items_table_data = [['ITEM', 'AMOUNT']]
        
        for expense in expenses_data:
            # Split material_name to get material name
            if " - " in expense.material_name:
                parts = expense.material_name.split(" - ", 1)
                material_name = parts[0]
            else:
                material_name = expense.material_name
            amount = float(expense.amount)
            
            items_table_data.append([
                material_name,
                f"Rs {amount:,.2f}"
            ])
        
        # Add empty rows if needed
        while len(items_table_data) < 5:
            items_table_data.append(['', ''])
        
        items_table = Table(items_table_data, colWidths=[5*inch, 2*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#AEB877')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Summary Section - Advance: Total, Advance Amount, Balance Due; Full: Total only
        summary_data = [['TOTAL AMOUNT:', f"Rs {total_amount:,.2f}"]]
        if is_advance_payment:
            summary_data.append(['ADVANCE AMOUNT:', f"Rs {total_advance:,.2f}"])
            summary_data.append(['BALANCE DUE:', f"Rs {total_remaining:,.2f}"])
        
        summary_table = Table(summary_data, colWidths=[5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(KeepTogether(summary_table))
        story.append(Spacer(1, 0.5*inch))
        
        # Footer
        story.append(Paragraph("Thank you for your business!", self.styles['Heading3']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer

    def create_inventory_invoice_pdf(self, inventory_data, invoice_no):
        """
        Generate inventory invoice PDF for a specific invoice_no
        inventory_data: List of inventory items with the same invoice_no
        invoice_no: Invoice number
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        story = []
        
        # Get logo path
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logo', 'logo.png')
        
        # Calculate totals
        total_cost = sum(float(item.cost_price) * item.quantity for item in inventory_data)
        total_value = sum(float(item.cost_price) * item.quantity * 1.5 for item in inventory_data)  # Assuming 1.5x markup
        
        # Handle date formatting
        first_item = inventory_data[0]
        if first_item.created_at:
            if isinstance(first_item.created_at, str):
                try:
                    invoice_date = datetime.fromisoformat(first_item.created_at.replace('Z', '+00:00')).strftime("%m/%d/%Y")
                except:
                    invoice_date = datetime.now().strftime("%m/%d/%Y")
            else:
                invoice_date = first_item.created_at.strftime("%m/%d/%Y")
        else:
            invoice_date = datetime.now().strftime("%m/%d/%Y")
        
        # Header with Logo
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 0.2*inch))
            except Exception as e:
                print(f"Error loading logo: {e}")
        
        # Company Name
        story.append(Paragraph("Nisa World Furniture", self.styles['ReportTitle']))
        story.append(Spacer(1, 0.1*inch))
        
        # Company Address
        company_address = "Plot @ A-132, 133, Shop # 5 Hira Heaven, Main Sir Shah Suleman Road Ishaqabad Near Gharibabad, Karachi."
        company_phone = "+92 307 3190861"
        
        story.append(Paragraph(f"<b>Address:</b> {company_address}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Phone No:</b> {company_phone}", self.styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Invoice Details
        invoice_table_data = [
            ['Invoice No:', invoice_no, 'Date:', invoice_date],
        ]
        
        invoice_info_table = Table(invoice_table_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2.5*inch])
        invoice_info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(invoice_info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Items Table
        items_table_data = [['PRODUCT', 'CATEGORY', 'QTY', 'COST/UNIT', 'TOTAL COST']]
        
        for item in inventory_data:
            product_name = item.product_name
            category = item.category
            quantity = item.quantity
            cost_per_unit = float(item.cost_price)
            total_cost_item = cost_per_unit * quantity
            
            items_table_data.append([
                product_name,
                category,
                str(quantity),
                f"Rs {cost_per_unit:,.2f}",
                f"Rs {total_cost_item:,.2f}"
            ])
        
        # Add empty rows if needed
        while len(items_table_data) < 5:
            items_table_data.append(['', '', '', '', ''])
        
        items_table = Table(items_table_data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1.5*inch, 1.5*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#AEB877')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Summary Section
        summary_data = [
            ['TOTAL COST:', f"Rs {total_cost:,.2f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(KeepTogether(summary_table))
        story.append(Spacer(1, 0.5*inch))
        
        # Footer
        story.append(Paragraph("Thank you for your business!", self.styles['Heading3']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer

export_service = ExportService()
