import os

class SimplePDFWriter:
    def __init__(self):
        self.objects = []
        
    def add_object(self, content: bytes) -> int:
        self.objects.append(content)
        return len(self.objects)
        
    def build(self) -> bytes:
        header = b'%PDF-1.4\n'
        offsets = {}
        body = b''
        
        current_offset = len(header)
        for i, obj_content in enumerate(self.objects):
            obj_id = i + 1
            offsets[obj_id] = current_offset
            
            obj_bytes = f"{obj_id} 0 obj\n".encode('utf-8') + obj_content + b"\nendobj\n"
            body += obj_bytes
            current_offset += len(obj_bytes)
            
        xref_start = current_offset
        xref = f"xref\n0 {len(self.objects) + 1}\n0000000000 65535 f \n".encode('utf-8')
        for i in range(len(self.objects)):
            obj_id = i + 1
            xref += f"{offsets[obj_id]:010d} 00000 n \n".encode('utf-8')
            
        trailer = f"trailer\n<</Size {len(self.objects) + 1} /Root 1 0 R>>\nstartxref\n{xref_start}\n%%EOF\n".encode('utf-8')
        
        return header + body + xref + trailer

def generate():
    writer = SimplePDFWriter()
    
    # 1. Catalog
    writer.add_object(b'<</Type /Catalog /Pages 2 0 R>>')
    # 2. Pages
    writer.add_object(b'<</Type /Pages /Kids [3 0 R] /Count 1>>')
    # 3. Page
    writer.add_object(b'<</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R /F2 5 0 R>>>> /MediaBox [0 0 595 842] /Contents 6 0 R>>')
    # 4. Font F1
    writer.add_object(b'<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>')
    # 5. Font F2
    writer.add_object(b'<</Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold>>')
    
    # 6. Stream content
    lines = [
        "BT",
        "/F2 16 Tf",
        "50 800 Td",
        "(PredictaGuard Security & Health Report) Tj",
        "ET",
        "BT",
        "/F1 12 Tf",
        "50 780 Td",
        "(Generated on: 2026-07-28 17:00:00) Tj",
        "ET",
        # Draw some lines
        "50 770 m",
        "550 770 l",
        "S"
    ]
    stream_content = "\n".join(lines)
    stream_bytes = stream_content.encode('utf-8')
    
    obj_6_content = f"<</Length {len(stream_bytes)}>>\nstream\n".encode('utf-8') + stream_bytes + b"\nendstream"
    
    writer.add_object(obj_6_content)
    
    pdf_data = writer.build()
    
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dynamic_test.pdf"))
    with open(output_path, "wb") as f:
        f.write(pdf_data)
        
    print(f"Dynamic PDF written to: {output_path}")

if __name__ == "__main__":
    generate()
