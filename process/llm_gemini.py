import os
import google.generativeai as genai
from dotenv import load_dotenv

# 🎯 환경변수(또는 .env)에서 API_KEY를 불러옵니다!
load_dotenv()
api_key = os.getenv("API_KEY")
if not api_key:
    print("⚠️ API_KEY 환경변수가 설정되지 않았습니다. .env 파일이나 시스템 환경변수를 확인해주세요.")
genai.configure(api_key=api_key)

def correct_script_with_gemini(audio_text, pdf_text):
    print("\n🤖 [AI 팀] Gemini API 교정 작업 시작...")
    print("   > 강의록(PDF) 데이터를 기반으로 음성 스크립트 오타를 수정합니다.")
    
    system_instruction = """당신은 본과 의학 강의 전문 속기사입니다.
    목적: Whisper로 추출된 [음성 스크립트]의 발음 오타를 [강의록(PDF) 텍스트]를 참고하여 교정합니다.

    [엄격한 교정 규칙]
    1. 강의록에 명시된 정확한 의학 용어를 사용하여 오타를 수정하세요.
    2. 강사가 실제로 말하지 않은 새로운 내용을 지어내거나 추가하지 마세요. (환각 금지)
    3. 강사가 말한 내용을 마음대로 요약하지 마세요.
    4. 영어로 된 의학 용어는 그대로 영어로 표현하고, 일반적으로 외래어로 인식되어 한국어로 쓰이는 단어들은 한글로 표현해주세요.
    5. 임상적인 기준이나 표기가 모호한 경우, 반드시 '해리슨 내과학'을 표준 기준으로 삼으세요.
    6. 원본 강의의 흐름은 그대로 유지하세요.
    """
    
    user_prompt = f"""
    [강의록(PDF) 텍스트]
    {pdf_text}
    
    ======================
    
    [음성 스크립트]
    {audio_text}
    
    위 두 자료를 바탕으로 규칙에 맞게 교정된 최종 음성 스크립트만 출력하세요.
    """

    # 텍스트 처리에 빠르고 정확한 gemini-2.5-flash 모델 사용
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview",
        system_instruction=system_instruction
    )
    try:
        response = model.generate_content(
            user_prompt,
            generation_config=genai.GenerationConfig(temperature=0.1) # 팩트 위주 보수적 세팅
        )
        print("✨ [AI 팀] Gemini 교정 완료!")
        return response.text
        
    except Exception as e:
        print(f"❌ Gemini API 처리 오류: {e}")
        return None

def summarize_corrected_text(corrected_text):
    print("🤖 [AI 팀] 교정본 바탕으로 핵심 요약 및 용어 추출 중...")
    prompt = f"""다음은 교정된 의학 강의 스크립트입니다. 이를 바탕으로 요약과 용어를 정리하세요.
    
    [형식]
    [SUMMARY] (강의 핵심 내용 요약)
    [TERMS] (중요 용어와 설명)
    [스크립트]
    {corrected_text}"""
    
    # 텍스트 처리에 빠르고 정확한 gemini-2.5-flash 모델 사용
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview",
        #system_instruction=system_instruction
    )
    response = model.generate_content(prompt)
    content = response.text
    
    # 데이터 파싱
    parts = content.split("[TERMS]")
    summary = parts[0].replace("[SUMMARY]", "").strip()
    terms = parts[1].strip() if len(parts) > 1 else ""
    
    return summary, terms