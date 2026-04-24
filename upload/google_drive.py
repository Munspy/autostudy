import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# 1. 연결 통로(서비스) 만들기
def get_drive_service():
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    creds = None
    # 프로젝트 루트 폴더에서 인증 파일을 찾습니다.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # credentials.json 파일이 프로젝트 루트에 있어야 합니다.
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

# 전역 변수로 서비스 미리 선언
drive_service = get_drive_service()

# 2. 파일 이름으로 링크 찾아오기
def get_drive_file_url(file_name):
    try:
        query = f"name = '{file_name}' and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, webViewLink)").execute()
        files = results.get('files', [])
        return files[0].get('webViewLink') if files else None
    except Exception as e:
        print(f"❌ 드라이브 검색 오류: {e}")
        return None