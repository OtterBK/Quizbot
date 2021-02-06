<div align=center>

![MainIMG](https://user-images.githubusercontent.com/28488288/106536426-c48d4300-653b-11eb-97ee-445ba6bced9b.jpg)

</div>
<br>
<br>

# 퀴즈 봇 🔔
> #### 🎮 디스코드 서버에서 사용 가능한 퀴즈 봇입니다.
> #### 🎧음악을 듣고 노래 제목을 맞추거나 🖼 그림을 보고 인물을 맞추는 등의 다양한 퀴즈가 있습니다.

<br>

## 💻 봇 추가 방법
> #### 📄 서버에 봇을 추가하기 위해 아래 버튼을 클릭해주세요.
> #### 📌 관리자 권한이 필요합니다.

<br>

<div align=center>
  
[![DISCORD](http://img.shields.io/badge/-Discord-gray?style=for-the-badge&logo=discord&link=https://discord.com/api/oauth2/authorize?client_id=788060831660114012&permissions=0&scope=bot)](https://discord.com/api/oauth2/authorize?client_id=788060831660114012&permissions=0&scope=bot)&nbsp;&nbsp;&nbsp;<br>
☝ 퀴즈봇 추가하기 
</div>
<br>

#### ❔ 버튼을 눌러도 반응이 없다면 아래 링크를 클릭해주세요.
🌐 [퀴즈봇](https://discord.com/api/oauth2/authorize?client_id=788060831660114012&permissions=0&scope=bot "퀴즈봇 추가하기") 추가 링크

<br>

## 📚 명령어
```
!퀴즈 - 퀴즈봇을 조작할 수 있는 UI를 생성합니다.
```

<br>

##  🛠 직접 서버 열기
### 🔩 Config.py 
> #### 토큰 ,UI 아이콘, 퀴즈 경로 등을 설정할 수 있습니다.

#### 🧰 필수 설정 사항
```

TOKEN = "Input your discord bot token" #자신의 디스코드 봇 토큰 입력
BOT_PREFIX = "!" #명령어 접두사

QUIZ_PATH = "F:/quizbot/gameData/"  # 게임 소스폴더
BGM_PATH = "F:/quizbot/bgm/"  # 효과음 폴더, 함께 첨부된 bgm 폴더를 사용하세요.
SAVE_PATH = "F:/quizbot/download/" #다운로드 폴더
TMP_PATH = "F:/quizbot/tmp/" #임시폴더
DATA_PATH = "F:/quizbot/savedata/" #데이터 저장 폴더
OPTION_PATH = DATA_PATH + "option/" #옵션 데이터 저장 폴더
RANK_PATH = DATA_PATH + "rank/" #랭크 데이터 저장 폴더
PATCHNOTE_PATH = DATA_PATH + "patchnote/" #패치노트 폴더

VERSION = "2.0" #봇 버전 
LAST_PATCH = "last patch" #봇의 마지막 패치일자
EMAIL_ADDRESS = "input your email address" #이메일 주소
BOT_LINK = "" #봇 공유 링크

```
#### 👩‍💻 해당 값을 자신의 환경에 맞게 변경하셔야합니다. :memo:

### 🔩 Quizbot.py 
> #### 퀴즈봇을 실행합니다.

### 🔩 QuizUI.py 
> #### 퀴즈 선택 등의 UI를 제공합니다.

<br>

####  ❗ 퀴즈 자료 설정 예시는 함께 첨부된 <u>gameData</u> 📁 폴더를 확인하세요.

<br>

#### :camera: 스냅샷

![quizbot](https://user-images.githubusercontent.com/28488288/107127934-07189c00-68fd-11eb-9342-4a051a310ebd.gif)

