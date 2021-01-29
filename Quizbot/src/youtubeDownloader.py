import youtube_dl
import os
from pynput.keyboard import Listener, Key, KeyCode
import win32api
import pyperclip


# 실행되는 폴더 안에 '영상제목.확장자' 형식으로 다운로드
SAVE_PATH = 'F:/quizbot/작업중/다운로드/'
 
store = set()
 
HOT_KEYS = {
    'ytDownload': set([ Key.alt_l, KeyCode(char='1')] )
    , 'ytListDownload': set([ Key.alt_l, KeyCode(char='2')] )
    , 'open_notepad': set([ Key.alt_l, KeyCode(char='3')] )
}

def ytDownload(): #유튜브 다운로드

    store.clear()

    url = pyperclip.paste() #클립보드에서 가져오기

    ydl_opta = { #추출 매개변수, 건들지 말자....
        "format": "bestaudio/best",
        "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192" #192도 가능
        }],
        'noplaylist': True,
        "ignoreerrors": False ,#오류 발생 무시
        'outtmpl':SAVE_PATH + '%(title)s.%(ext)s', #다운 경로 설정
    }
    #print(url)
    try:
        with youtube_dl.YoutubeDL(ydl_opta) as ydl: #with문을 사용해 파일입출력을 안전하게 as하여 outube_dl.YoutubeDL(ydl_opta) 값을 ydl로
            ydl.download({url}) #ydl_opta 값을 적용한 유튜브 다운로더를 통해 url에서 파일을 다운로드한다. 경로는 소스경로
    except:
        print("error")

    print('다운로드 완료했습니다.')

 
def ytListDownload(): #유튜브 재생목록 다운로드

    url = pyperclip.paste() #클립보드에서 가져오기

    ydl_opta = { #추출 매개변수, 건들지 말자....
        "format": "bestaudio/best",
        "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192"
        }],
        "ignoreerrors": True ,#오류 발생 무시
        'outtmpl':SAVE_PATH + '%(title)s.%(ext)s', #다운 경로 설정
    }
    print(url)

    with youtube_dl.YoutubeDL(ydl_opta) as ydl: #with문을 사용해 파일입출력을 안전하게 as하여 outube_dl.YoutubeDL(ydl_opta) 값을 ydl로
        ydl.download({url}) #ydl_opta 값을 적용한 유튜브 다운로더를 통해 url에서 파일을 다운로드한다. 경로는 소스경로

    print('다운로드 완료했습니다.')

def open_notepad(): #노트 패드 실행
    print('open_notepad')
    try:
        win32api.WinExec('notepad.exe')
    except Exception as err:
        print( err )
 
def handleKeyPress( key, **kwargs ): # 키 눌렀을 때
    store.add( key )
 
def handleKeyRelease( key ): #키 뗐을때
    for action, trigger in HOT_KEYS.items():
        CHECK = all([ True if triggerKey in store else False for triggerKey in trigger ])
 
        if CHECK:
            try:
                action = eval( action )
                if callable( action ):
                    action()
            except NameError as err:
                print( err )
                
    # 종료
    if key == Key.esc:
        return False
    elif key in store:
        store.remove( key )
    
with Listener(on_press=handleKeyPress, on_release=handleKeyRelease) as listener: #이벤트 핸들러 실행
    listener.join()
