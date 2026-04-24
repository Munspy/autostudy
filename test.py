print("파이썬 스크립트 시작됨")

import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from extract.pdf_extract import extract_text_from_pdf
from extract.audio_extract import extract_text_from_audio
from process.llm_gemini import correct_script_with_gemini
from process.notion_sync import sync_to_notion

print("라이브러리 import 완료")

# 🎯 감시할 구글 드라이브 로컬 경로 (현재는 테스트용 폴더)
WATCH_PATH = r"G:\내 드라이브\2026-1"

class StudyDataHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        file_name = os.path.basename(file_path)
        extension = os.path.splitext(file_name)[1].lower()
        
        # 파일이 완전히 복사될 때까지 아주 잠시 대기 (용량이 큰 영상 파일 씹힘 방지)
        time.sleep(2)
        
        print(f"\n[{time.strftime('%H:%M:%S')}] 🚨 새 파일 감지됨: {file_name}")
        if "_temp" in file_name or file_name.startswith("~$"):
            print("임시파일이므로 무시합니다.")
            return

        base_name = os.path.splitext(file_name)[0]
        # 영상/음성 파일인 경우 텍스트 추출 파이프라인 시작
        if extension in ['.mp4', '.m4a', '.mp3', '.wav']:
            audio_text = extract_text_from_audio(file_path)
            self.save_result(base_name, audio_text, "음성스크립트")
        # pdf라면 
        if extension == '.pdf':
            pdf_text = extract_text_from_pdf(file_path)
            self.save_result(base_name, pdf_text, "강의자료")

        if extension in ['.mp4', '.m4a', '.mp3', '.wav', '.pdf']:
            self.check_and_start_ai_correction(base_name)

    def save_result(self, base_name, text, suffix):
        save_name = f"{base_name}_{suffix}.txt"
        save_path = os.path.join(WATCH_PATH, save_name)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"💾 저장됨: {save_path}")
        # 앞부분 내용 살짝 미리보기
        preview = text[:20] + "..." if len(text) > 20 else text
        print(f"📝 미리보기: {preview}")

    def check_and_start_ai_correction(self, base_name):
        # 짝꿍 파일들의 예상 경로
        audio_txt_path = os.path.join(WATCH_PATH, f"{base_name}_음성스크립트.txt")
        pdf_txt_path = os.path.join(WATCH_PATH, f"{base_name}_강의자료.txt")
        final_txt_path = os.path.join(WATCH_PATH, f"{base_name}_최종교정본.txt")

        # 이미 최종본이 있다면 중복 실행 방지
        if os.path.exists(final_txt_path):
            return

        # 둘 다 존재한다면? Gemini 출동!
        if os.path.exists(audio_txt_path) and os.path.exists(pdf_txt_path):
            print(f"🔗 [매치 성공] '{base_name}' 자료 쌍을 찾았습니다. AI 교정을 시작합니다.")
            
            with open(audio_txt_path, 'r', encoding='utf-8') as f:
                audio_text = f.read()
            with open(pdf_txt_path, 'r', encoding='utf-8') as f:
                pdf_text = f.read()

            # Gemini 호출
            corrected_text = correct_script_with_gemini(audio_text, pdf_text)
            
            if corrected_text:
                self.save_result(base_name, corrected_text, "최종교정본")
                sync_to_notion(base_name, corrected_text, None, "")
        else:
            print(f"⏳ '{base_name}'의 짝꿍 파일이 아직 없습니다.")


def initial_scan(handler):
    """프로그램 시작 시, 이미 추출된 텍스트 파일이 있으면 노션 업로드를 시작합니다."""
    print("🔍 [초기 스캔] 미처리 텍스트 파일 세트를 찾는 중...")
    
    all_files = os.listdir(WATCH_PATH)
    
    for file_name in all_files:
        if file_name.endswith("_최종교정본.txt"):
            base_name = file_name.replace("_최종교정본.txt", "")
            
            # 1. 파일의 정확한 전체 경로를 만듭니다.
            file_path = os.path.join(WATCH_PATH, file_name)
            
            try:
                # 2. 파일을 파이썬으로 열어서 내용을 모두 읽어옵니다. (이게 핵심!)
                with open(file_path, 'r', encoding='utf-8') as f:
                    corrected_text = f.read()
                
                print(f"🎯 [발견] 교정본 읽기 성공, 노션 업로드를 시작합니다: {base_name}")
                
                # 3. 꺼내온 텍스트를 노션 업로드 함수에 던져줍니다.
                sync_to_notion(base_name, corrected_text, None, "")
                
            except Exception as e:
                print(f"❌ {file_name} 파일 읽기 실패: {e}")


if __name__ == "__main__":

    # 🚀 시작하자마자 밀린 숙제(파일)부터 해결!
    event_handler = StudyDataHandler()
    initial_scan(event_handler)