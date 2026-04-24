import fitz

def extract_text_from_pdf(file_path):
    print(f"📄 PDF OCR 분석 시작합니다.. (경로 : {file_path})")
    try:
        # 1. PDF 문서 열기
        doc = fitz.open(file_path)
        full_text = ""
        
        # 2. 페이지별로 순회하며 텍스트 추출
        for i, page in enumerate(doc):
            text = page.get_text() # 해당 페이지의 모든 텍스트를 그대로 가져옴
            full_text += f"\n--- {i+1} Page ---\n" + text
        
        doc.close()
        print(f"✨ PDF 분석 완료!")
        # 파일 저장은 여기서 하지 않고, 추출된 텍스트를 main.py로 던져줍니다(return).
        return full_text

    except Exception as e:
        print(f"❌ PDF 처리 오류: {e}")