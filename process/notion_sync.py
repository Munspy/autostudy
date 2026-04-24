import os
from notion_client import Client
from process.llm_gemini import summarize_corrected_text

notion = Client(auth=os.getenv("NOTION_TOKEN"))
parent_page_id = os.getenv("NOTION_PAGE_ID")

def create_rich_text_blocks(text, block_type="paragraph", max_length=2000):
    """줄바꿈(\n)을 기준으로 노션 블록을 생성하며, 2000자 초과 시 안전하게 분할합니다."""
    blocks = []
    
    # 1. 먼저 줄바꿈(엔터)을 기준으로 텍스트를 나눕니다.
    paragraphs = text.split('\n')
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue  # 빈 줄은 무시 (만약 빈 줄도 살리고 싶다면 이 두 줄을 지우세요)
            
        # 2. 한 문단이 2000자를 넘는지 확인하는 안전장치
        if len(para) > max_length:
            chunks = [para[i:i+max_length] for i in range(0, len(para), max_length)]
        else:
            chunks = [para]
            
        # 3. 쪼개진 텍스트(들)를 노션 블록 형식으로 포장
        for chunk in chunks:
            if block_type == "code":
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "language": "markdown",
                        "rich_text": [{"text": {"content": chunk}}]
                    }
                })
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": chunk}}]
                    }
                })
                
    return blocks

def sync_to_notion(base_name, corrected_text, media_url, extension):
    print(f"🚀 [Notion 팀] '{base_name}' 분석 및 업로드 시작...")
    summary, terms = summarize_corrected_text(corrected_text)
    
    is_video = extension in ['.mp4', '.mov']
    block_type = "video" if is_video else "audio"

    # 1. 미디어 블록 준비
    children = []
    if media_url:
        embed_url = media_url.replace("/view?usp=drivesdk", "/preview")
        children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "🎧 강의 다시듣기" if not is_video else "📺 강의 다시보기"}}]}})
        children.append({"object": "block", f"type": {block_type}, block_type: {"type": "external", "external": {"url": embed_url}}})

    # 2. 요약 블록 추가
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📌 강의 핵심 요약"}}]}})
    children.append({"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"text": {"content": summary}}]}})

    # 3. 중요 용어 정리 (2000자 초과 대응)
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📑 중요 용어 정리 (Harrison 21st ed.)"}}]}})
    children.append({"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"text": {"content": terms}}]}})

    # 4. 전체 교정 스크립트 (2000자 초과 대응)
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📝 최종 교정 스크립트"}}]}})
    children.extend(create_rich_text_blocks(corrected_text, block_type="paragraph"))

    try:
        notion.pages.create(
            parent={"page_id": parent_page_id},
            properties={"title": {"title": [{"text": {"content": f"📖 {base_name}"}}]}},
            children=children
        )
        print("✅ 노션 업로드 성공! (긴 텍스트 분할 처리 완료)")
    except Exception as e:
        print(f"❌ 노션 업로드 실패: {e}")