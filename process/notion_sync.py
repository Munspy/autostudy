import os
import json
from notion_client import Client
#구글드라이브
from upload.google_drive import get_drive_file_url

notion = Client(auth=os.getenv("NOTION_TOKEN"))
database_id = os.getenv("NOTION_DATABASE_ID") 

import re
# 볼드체 처리
def convert_text_to_notion_rich_text(text):
    parts = re.split(r'\*\*(.*?)\*\*', text)
    rich_text_list = []
    
    for i, part in enumerate(parts):
        if not part: 
            continue
            
        is_bold = (i % 2 == 1) # 홀수 인덱스는 ** 로 감싸진 부분
        
        # 만약 볼드체나 일반 텍스트 조각 자체가 2000자를 넘는다면 2000자씩 쪼개기
        for j in range(0, len(part), 2000):
            chunk = part[j:j+2000]
            rt_obj = {
                "type": "text",
                "text": {"content": chunk}
            }
            if is_bold:
                rt_obj["annotations"] = {"bold": True}
            
            rich_text_list.append(rt_obj)
            
    return rich_text_list

# 🌟 수정된 함수 2: 노션 API 제한(객체 100개 & 글자 2000자)을 모두 만족하도록 블록 생성
def create_rich_text_blocks(text, block_type="paragraph", split_by_newline=True):
    blocks = []
    
    # 옵션에 따라 줄바꿈 처리
    if split_by_newline:
        sections = [p.strip() for p in text.split('\n') if p.strip()]
    else:
        sections = [text.strip()] if text.strip() else []

    for section in sections:
        if not section:
            continue
            
        # 1. 텍스트를 통째로 변환 (마크다운 깨짐 방지)
        rich_text_list = convert_text_to_notion_rich_text(section)
        
        current_rich_text = []
        current_length = 0
        
        # 2. 객체를 순회하며 100개 제한 & 2000자 제한에 맞춰 블록 분할
        for rt in rich_text_list:
            content_len = len(rt["text"]["content"])
            
            # [핵심 로직] 현재 배열이 100개가 되거나, 다음 텍스트를 더했을 때 2000자를 넘기면 블록 생성
            if len(current_rich_text) >= 100 or current_length + content_len > 2000:
                blocks.append({
                    "object": "block",
                    "type": block_type,
                    block_type: {
                        "rich_text": current_rich_text
                    }
                })
                current_rich_text = [] # 초기화
                current_length = 0
            
            # 배열에 추가
            current_rich_text.append(rt)
            current_length += content_len
            
        # 3. 마지막에 남은 객체들 처리
        if current_rich_text:
            blocks.append({
                "object": "block",
                "type": block_type,
                block_type: {
                    "rich_text": current_rich_text
                }
            })
            
    return blocks


def trigger_notion_upload(base_name, target_dir):
    
    # 1. JSON 데이터 로드
    result_json_path = os.path.join(target_dir, f"{base_name}_result.json")
    if os.path.exists(result_json_path) is False : 
        return

    print(f"🚀 [Notion 팀] '{base_name}' 노션 업로드 시작...")

    with open(result_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 2. 구글 드라이브 링크 수집 (외부 함수 호출 가정)
    media_url = get_drive_file_url(f"{base_name}.mp4") or get_drive_file_url(f"{base_name}.mp3") or get_drive_file_url(f"{base_name}.m4a")
    pdf_url = get_drive_file_url(f"{base_name}.pdf")
    
    # 3. 미디어 타입 판별
    video_path = os.path.join(target_dir, f"{base_name}.mp4")
    if os.path.exists(video_path) : 
        is_video = True
    else : 
        is_video = False
    block_type = "video" if is_video else "audio"

    # 4. 데이터베이스 속성(Properties) - 노션 DB 컬럼명과 일치해야 함
    properties = {
        "이름": {"title": [{"text": {"content": f"📖 {base_name}"}}]},
        "원본 PDF": {"url": pdf_url if pdf_url else None},
        "강의 영상": {"url": media_url if media_url else None},
        "상태": {"select": {"name": "✅ 완료"}}
    }

    # 5. 페이지 본문(Children) 구성
    children = []
    
    # 미디어 임베드
    if media_url:
        embed_url = media_url.replace("/view?usp=drivesdk", "/preview")
        children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📺 강의 다시보기" if is_video else "🎧 강의 다시듣기"}}]}})
        children.append({"object": "block", "type": block_type, block_type: {"type": "external", "external": {"url": embed_url}}})

    # 요약 (split_by_newline=False를 추가하여 블록이 쪼개지지 않게 방어)
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📌 강의 핵심 요약"}}]}})
    children.extend(create_rich_text_blocks(data["summary"], block_type="bulleted_list_item", split_by_newline=False))
    
    # 용어 (위와 동일)
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📑 중요 용어 정리"}}]}})
    children.extend(create_rich_text_blocks(data["terms"], block_type="bulleted_list_item", split_by_newline=False))

    # 전체 스크립트 (기존처럼 문단마다 블록을 나누기 위해 옵션을 적지 않음)
    children.append({"object": "block", "type": "heading_1", "heading_1": {"rich_text": [{"text": {"content": "📝 최종 교정 스크립트"}}]}})
    children.extend(create_rich_text_blocks(data["corrected_text"], block_type="paragraph", split_by_newline=True))

    try:
        # parent를 database_id로 설정하여 데이터베이스에 한 줄(Row)로 생성
        notion.pages.create(
            parent={"database_id": database_id},
            properties=properties,
            children=children
        )
        print(f"✅ [Notion] '{base_name}' 업로드 성공!")

        
        old_path = os.path.join(target_dir, f"{base_name}_result.json")
        new_path = os.path.join(target_dir, f"{base_name}_done.json")
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
    except Exception as e:
        print(f"❌ [Notion] 업로드 실패: {e}")