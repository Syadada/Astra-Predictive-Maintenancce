import os

OUTPUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_generated.pdf"))

def generate():
    filename = "Weekly_Health_Summary_W24_2026"
    textContent = 'PredictaGuard Report: ' + filename.replace('_', ' ') + ' (07/28/2026)'
    streamContent = 'BT\n/F1 12 Tf\n72 712 Td\n(' + textContent + ') Tj\nET'
    streamLen = len(streamContent)
    
    # Calculate offset
    # 5 0 obj is at 313.
    # Length of "5 0 obj\n<</Length " + len(str(streamLen)) + ">>\nstream\n"
    header_len = len(f"5 0 obj\n<</Length {streamLen}>>\nstream\n")
    stream_end_len = len("\nendstream\nendobj\n")
    xref_offset = 313 + header_len + streamLen + stream_end_len
    
    content = (
        '%PDF-1.4\n' +
        '1 0 obj\n<</Type /Catalog /Pages 2 0 R>>\nendobj\n' +
        '2 0 obj\n<</Type /Pages /Kids [3 0 R] /Count 1>>\nendobj\n' +
        '3 0 obj\n<</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R>>>> /MediaBox [0 0 595 842] /Contents 5 0 R>>\nendobj\n' +
        '4 0 obj\n<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>\nendobj\n' +
        f'5 0 obj\n<</Length {streamLen}>>\nstream\n{streamContent}\nendstream\nendobj\n' +
        'xref\n' +
        '0 6\n' +
        '0000000000 65535 f \n' +
        '0000000009 00000 n \n' +
        '0000000058 00000 n \n' +
        '0000000115 00000 n \n' +
        '0000000244 00000 n \n' +
        '0000000313 00000 n \n' +
        'trailer\n' +
        '<</Size 6 /Root 1 0 R>>\n' +
        'startxref\n' +
        f'{xref_offset}\n' +
        '%%EOF\n'
    )
    
    with open(OUTPUT_PATH, "wb") as f:
        f.write(content.encode('utf-8'))
        
    print(f"Valid PDF written to: {OUTPUT_PATH}")
    print(f"Xref offset: {xref_offset}")

if __name__ == "__main__":
    generate()
