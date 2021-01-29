import discord
from discord.ext import commands
from discord.utils import get
import youtube_dl
import os
import time
import asyncio
import soundfile as sf
import random
import SelectionList
from threading import Thread
from mutagen.mp3 import MP3
from pydub import AudioSegment
from shutil import copyfile


# 개발자 페이지에서 봇에 대한 토큰 텍스트를 가져온 뒤, TOKEN에 대입하자
TOKEN = "Nzg4MDYwODMxNjYwMTE0MDEy.X9eA1w.n1ojFFe1evV4uxnmmwxFqLubhVY"
BOT_PREFIX = "!"
BASE_PATH = "F:/quizbot/gameData/"  # 게임 소스폴더
BGM_PATH = "F:/quizbot/bgm/"  # 효과음 폴더
# C드라이브에 다운로드하려고하면 Permission Denied 에러 떠서 다른 폴더로...
SAVE_PATH = "F:/quizbot/download/"
TMP_PATH = "F:/quizbot/tmp/" #임시폴더

#상수 선언
alphabetList = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q"
                    , "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
emojiNumberList = [ "0️⃣", "1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
emojiOXList = ["⭕", "❌"]

bot = commands.Bot(command_prefix=BOT_PREFIX)  # 봇 커맨드 설정

#이넘 선언
class GAME_STEP(enumerate):
    START = 1  # 오프닝 중
    WAIT_FOR_ANSWER = 2  # 정답자 기다리는 중
    WAIT_FOR_NEXT = 3  # 다음 단계 기다리는중
    END = 4  # 엔딩 중
    FINISH = 5  # 끝


class GAME_TYPE(enumerate):
    SONG = 1 #노래
    SCRIPT = 2 #대사
    SELECT = 3 #객관식
    TTS = 4 #TTS 사용방식
    GLOWLING = 5 #포켓몬 울음소리
    PICTURE = 6 #사진
    OX = 7 #OX퀴즈
    QNA = 8 #텍스트 기반 qna
    FAST_QNA = 9 #텍스트 기반 qna, 타이머 짧음
    INTRO = 10 #인트로 맞추기


class BGM_TYPE(enumerate):
    PLING = 1
    ROUND_ALARM = 2
    SCORE_ALARM = 3
    ENDING = 4
    FAIL = 5
    countdown10 = 6
    SUCCESS = 7
    BELL = 8
    LONGTIMER = 8


#클래스 선언
class GameData:

    def __init__(self, guild, chatChannel, voiceChannel, gameName, gameType, roomOwner):
        self._chatChannel = chatChannel
        self._voiceChannel = voiceChannel
        self._gameType = gameType
        self._gameName = gameName
        self._gameRank = dict()
        self._nowQuiz = ""
        self._answerList = []
        self._roundIndex = 0
        self._roundDelay = 40000
        self._gameStep = GAME_STEP.START
        self._maxRound = 0
        self._guild = guild
        self._quizList = []
        self._scoreMap = dict()
        self._voice = None
        self._roomOwner = roomOwner
        self._isSkiped = False
        self._selectList = [] #객관식 보기
        self._selectionAnswer = 0 #객관식 정답
        self._selectPlayerMap = dict() #사람들 선택한 답
        self._repeatCount = 1
        self._textQuizList = [] # 텍스트 기반 퀴즈일 때 문제 저장 공간
        self._oxQuizObject = None #현재 진행중인 ox퀴즈 객체
        self._useHint = False #힌트 사용여부
        self._thumbnail = None # 썸네일
        self._answerAuido = None #정답용 음악
        self._topNickname = "" #1등 별명

#Ox, 일반 퀴즈용 퀴즈 데이터
class TextQuizData: 
    def __init__(self, answer):
        self._answer = answer
        self._questionText = ""
        self._answerText = "" #추가 설명


class QuizData:
    def __init__(self, gameType, gameDiff, quizCnt, desc, topNickname):
        self._gameType = gameType
        self._gameDiff = gameDiff
        self._quizCnt = quizCnt
        self._desc = desc
        self._repeatCount = 1
        self._topNickname = topNickname #1위에게 붙일 닉네임


dataMap = dict()  # 데이터 저장용 해쉬맵
QUIZ_MAP = dict()  # 퀴즈 정보 저장용

#애니
QUIZ_MAP["애니송1"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 120, "모든 장르를 포함하는 애니송", "덕후")
QUIZ_MAP["애니송2"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 81, "상당히 어렵습니다.", "덕후")
QUIZ_MAP["애니송3"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 81, "상당히 어렵습니다.", "덕후")
QUIZ_MAP["애니송4"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 81, "상당히 어렵습니다.", "덕후")
QUIZ_MAP["애니송5"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 81, "상당히 어렵습니다.", "덕후")
QUIZ_MAP["애니송6"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 81, "상당히 어렵습니다.", "덕후")
QUIZ_MAP["애니송7"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 81, "상당히 어렵습니다.", "덕후")
QUIZ_MAP["애니송8"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 81, "상당히 어렵습니다.", "덕후")
QUIZ_MAP["애니송9"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 81, "상당히 어렵습니다.", "덕후")
QUIZ_MAP["애니더빙곡1"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 81, "국내 방영 애니 더빙곡", "덕후")
QUIZ_MAP["애니더빙곡2"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 82, "국내 방영 애니 더빙곡", "덕후")
QUIZ_MAP["애니인트로1"] = QuizData(GAME_TYPE.INTRO, "★★★★★", 50, "애니 오프닝 인트로 듣고 제목 맞추기, 어려움", "덕후")
QUIZ_MAP["애니인트로2"] = QuizData(GAME_TYPE.INTRO, "★★★★★", 50, "애니 오프닝 인트로 듣고 제목 맞추기, 어려움", "덕후")
QUIZ_MAP["애니인트로3"] = QuizData(GAME_TYPE.INTRO, "★★★★★", 50, "애니 오프닝 인트로 듣고 제목 맞추기, 어려움", "덕후")

#영화
QUIZ_MAP["영화대사1"] = QuizData(GAME_TYPE.SCRIPT, "★★★★☆", 53, "영화 명대사(장면)들만 모은 첫 영화대사", "영화 마니아")
QUIZ_MAP["영화OST1"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 84, "영화 ost듣고 제목 맞추기", "영화 감상가")

#가요
QUIZ_MAP["국내가요1"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 70, "2017~2018년, 인기가요", "한국인")
QUIZ_MAP["국내가요2"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 65, "2017~2018년, 인기가요", "한국인")
QUIZ_MAP["2019년히트가요"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 95, "2019년, 인기가요", "인싸")
QUIZ_MAP["걸그룹1"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 75, "걸그룹 노래", "걸그룹 덕후")
QUIZ_MAP["걸그룹2"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 80, "걸그룹 노래", "걸그룹 덕후")
QUIZ_MAP["걸그룹3"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 75, "걸그룹 노래", "걸그룹 덕후")
QUIZ_MAP["가수10cm노래"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 38, "가수 10cm 의 노래", "10cm 덕후")
QUIZ_MAP["2020년히트가요"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 97, "2020년 히트가요", "인싸")
QUIZ_MAP["국내가요3"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 90, "2005~2016년, 인기가요", "틀")
QUIZ_MAP["국내가요4"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 85, "2005~2016년, 인기가요", "노인네")
QUIZ_MAP["국내가요5"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 86, "2005~2016년, 인기가요", "어르신")
QUIZ_MAP["한국힙합1"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 60, "비교적 최신 한국 힙합", "래퍼")
QUIZ_MAP["한국힙합2"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 60, "비교적 최신 한국 힙합", "힙합마스터")
QUIZ_MAP["한국힙합3"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 60, "비교적 최신 한국 힙합", "인싸")

#게임
QUIZ_MAP["메이플스토리BGM_1"] = QuizData(GAME_TYPE.SELECT, "★★★★☆", 70, "객관식, 메이플스토리 BGM", "메덕")
QUIZ_MAP["메이플스토리BGM_2"] = QuizData(GAME_TYPE.SELECT, "★★★★☆", 60, "객관식, 메이플스토리 BGM", "메덕")
QUIZ_MAP["메이플스토리BGM_3"] = QuizData(GAME_TYPE.SELECT, "★★★★☆", 60, "객관식, 메이플스토리 BGM", "메덕")
QUIZ_MAP["메이플스토리BGM_4"] = QuizData(GAME_TYPE.SELECT, "★★★★☆", 60, "객관식, 메이플스토리 BGM", "메덕")
QUIZ_MAP["메이플스토리BGM_5"] = QuizData(GAME_TYPE.SELECT, "★★★★☆", 60, "객관식, 메이플스토리 BGM", "메덕")
QUIZ_MAP["메이플스토리BGM_6"] = QuizData(GAME_TYPE.SELECT, "★★★★☆", 60, "객관식, 메이플스토리 BGM", "메덕")
QUIZ_MAP["메이플스토리BGM_7"] = QuizData(GAME_TYPE.SELECT, "★★★★☆", 65, "객관식, 메이플스토리 BGM", "메덕")
QUIZ_MAP["메이플스토리BGM_8"] = QuizData(GAME_TYPE.SELECT, "★★★★☆", 65, "객관식, 메이플스토리 BGM", "메덕")
QUIZ_MAP["메이플스토리BGM_9"] = QuizData(GAME_TYPE.SELECT, "★★★★☆", 70, "객관식, 메이플스토리 BGM", "메덕")
QUIZ_MAP["게임1"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 76, "OST를 듣고 게임 제목 맞추기", "게이머")
QUIZ_MAP["스타크래프트1"] = QuizData(GAME_TYPE.PICTURE, "★★☆☆☆", 100, "스타크래프트1에 등장하는 유닛, 건물 맞추기", "스타크래프트 게이머")


#포켓몬
QUIZ_MAP["포켓몬소리_1세대_1"] = QuizData(GAME_TYPE.GLOWLING, "★★★★☆", 75, "포켓몬 울음소리 맞추기 1세대", "포켓몬 마스터")
QUIZ_MAP["포켓몬소리_1세대_2"] = QuizData(GAME_TYPE.GLOWLING, "★★★★☆", 75, "포켓몬 울음소리 맞추기 1세대", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림1"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림2"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림3"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림4"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림5"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림6"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림7"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림8"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림9"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림10"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림11"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림12"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림13"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림14"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림15"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림16"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림17"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 마스터")
QUIZ_MAP["포켓몬그림18"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "오박사")
QUIZ_MAP["포켓몬그림19"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "김박사")
QUIZ_MAP["포켓몬그림20"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포켓몬 챔피언")
QUIZ_MAP["포켓몬그림21"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "포켓몬 또는 아이템 그림 보고 맞추기", "포덕")

#POP송
QUIZ_MAP["팝송1"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 50, "유명 팝송", "팝송 마니아")
QUIZ_MAP["팝송2"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 46, "유명 팝송", "팝송 덕후")

#드라마
QUIZ_MAP["드라마1"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 61, "2000~2020 드라마 ost 듣고 제목 맞추기", "드라마 마니아")
QUIZ_MAP["드라마2"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 61, "2000~2020 드라마 ost 듣고 제목 맞추기", "드라마 덕후")

#인물퀴즈
QUIZ_MAP["한국인물1"] = QuizData(GAME_TYPE.PICTURE, "★★☆☆☆", 50, "한국 유명인물 맞추기", "인싸")
QUIZ_MAP["한국인물2"] = QuizData(GAME_TYPE.PICTURE, "★★☆☆☆", 50, "한국 유명인물 맞추기", "인싸")
QUIZ_MAP["한국인물3"] = QuizData(GAME_TYPE.PICTURE, "★★☆☆☆", 50, "한국 유명인물 맞추기", "인싸")
QUIZ_MAP["한국인물4"] = QuizData(GAME_TYPE.PICTURE, "★★☆☆☆", 50, "한국 유명인물 맞추기", "인싸")
QUIZ_MAP["애니캐릭터1"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 50, "애니메이션 캐릭터 이름 맞추기", "덕후")
QUIZ_MAP["애니캐릭터2"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 50, "애니메이션 캐릭터 이름 맞추기", "덕")
QUIZ_MAP["애니캐릭터3"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 60, "애니메이션 캐릭터 이름 맞추기", "오타쿠")
QUIZ_MAP["국내아이돌1"] = QuizData(GAME_TYPE.PICTURE, "★★★★☆", 62, "한국 아이돌 그룹명 맞추기", "군인")
QUIZ_MAP["국내아이돌2"] = QuizData(GAME_TYPE.PICTURE, "★★★★☆", 62, "한국 아이돌 그룹명 맞추기", "말년 병장")
QUIZ_MAP["국내아이돌3"] = QuizData(GAME_TYPE.PICTURE, "★★★★☆", 62, "한국 아이돌 그룹명 맞추기", "걸그룹 팬")

#마인크래프트
QUIZ_MAP["마인크래프트그림1"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 62, "마인크래프트 게임 아이템 및 블록 이름 맞추기", "스티브")
QUIZ_MAP["마인크래프트그림2"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 62, "마인크래프트 게임 아이템 및 블록 이름 맞추기", "스티브")
QUIZ_MAP["마인크래프트그림3"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 62, "마인크래프트 게임 아이템 및 블록 이름 맞추기", "알렉스")
QUIZ_MAP["마인크래프트그림4"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 62, "마인크래프트 게임 아이템 및 블록 이름 맞추기", "알렉스")
QUIZ_MAP["마인크래프트그림5"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 62, "마인크래프트 게임 아이템 및 블록 이름 맞추기", "노치")
QUIZ_MAP["마인크래프트그림6"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 62, "마인크래프트 게임 아이템 및 블록 이름 맞추기", "노치")
QUIZ_MAP["마인크래프트그림7"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 62, "마인크래프트 게임 아이템 및 블록 이름 맞추기", "마크 게이머")
QUIZ_MAP["마인크래프트OX1"] = QuizData(GAME_TYPE.OX, "★★★☆☆", 60, "마인크래프트 관련 OX 퀴즈", "마크 게이머")
QUIZ_MAP["마인크래프트OX2"] = QuizData(GAME_TYPE.OX, "★★★☆☆", 60, "마인크래프트 관련 OX 퀴즈", "크리퍼")

#잡학
QUIZ_MAP["넌센스1"] = QuizData(GAME_TYPE.QNA, "★★★☆☆", 15, "넌센스 퀴즈", "부장님")
QUIZ_MAP["역사상식1"] = QuizData(GAME_TYPE.QNA, "★★★☆☆", 50, "역사 상식 퀴즈, 주로 한국사 종종 세계사도 껴있음", "사학자")
QUIZ_MAP["역사상식2"] = QuizData(GAME_TYPE.QNA, "★★★☆☆", 50, "역사 상식 퀴즈, 주로 한국사 종종 세계사도 껴있음", "역사가")
QUIZ_MAP["역사상식3"] = QuizData(GAME_TYPE.QNA, "★★★☆☆", 50, "역사 상식 퀴즈, 주로 한국사 종종 세계사도 껴있음", "역사가")
QUIZ_MAP["역사상식4"] = QuizData(GAME_TYPE.QNA, "★★★☆☆", 50, "역사 상식 퀴즈, 주로 한국사 종종 세계사도 껴있음", "역사가")
QUIZ_MAP["상식OX1"] = QuizData(GAME_TYPE.OX, "★★★☆☆", 50, "상식 ox 퀴즈", "상식인")
QUIZ_MAP["상식OX2"] = QuizData(GAME_TYPE.OX, "★★★☆☆", 40, "상식 ox 퀴즈", "상식인")
QUIZ_MAP["상식OX3"] = QuizData(GAME_TYPE.OX, "★★★☆☆", 40, "상식 ox 퀴즈", "정상인")
QUIZ_MAP["상식OX4"] = QuizData(GAME_TYPE.OX, "★★★☆☆", 40, "상식 ox 퀴즈", "상식왕")
QUIZ_MAP["상식OX5"] = QuizData(GAME_TYPE.OX, "★★★☆☆", 40, "상식 ox 퀴즈", "지식왕")
QUIZ_MAP["상식OX6"] = QuizData(GAME_TYPE.OX, "★★★☆☆", 40, "상식 ox 퀴즈", "지식인")
QUIZ_MAP["속담1"] = QuizData(GAME_TYPE.FAST_QNA, "★★★☆☆", 100, "속담 맞추기 퀴즈", "한국인")


#기타
QUIZ_MAP["국기1"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 77, "각 나라의 국기를 보고 국가명 맞추기", "지식인")
QUIZ_MAP["국기2"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 77, "각 나라의 국기를 보고 국가명 맞추기", "지식인")
QUIZ_MAP["국기3"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 77, "각 나라의 국기를 보고 국가명 맞추기", "지식인")
QUIZ_MAP["기타국기1"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 68, "자치령, 기구 국기를보고 해당 기구 맞추기", "잡지식인")
QUIZ_MAP["랜드마크1"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 50, "전 세계의 명소, 유산 맞추기", "여행가")
QUIZ_MAP["랜드마크2"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 50, "전 세계의 명소, 유산 맞추기", "여행가")
QUIZ_MAP["랜드마크3"] = QuizData(GAME_TYPE.PICTURE, "★★★☆☆", 50, "전 세계의 명소, 유산 맞추기", "여행가")
QUIZ_MAP["군대"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 28, "한국군 군가, BGM 맞추기", "일병")
QUIZ_MAP["음악교과서1"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 61, "학교 음악시간에 배울법한 노래들...", "음악가")
QUIZ_MAP["음악교과서2"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 61, "학교 음악시간에 배울법한 노래들...", "음악가")
QUIZ_MAP["음악교과서3"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 61, "학교 음악시간에 배울법한 노래들...", "음악가")
QUIZ_MAP["음악교과서4"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 61, "학교 음악시간에 배울법한 노래들...", "음악 선생님")
QUIZ_MAP["음악교과서5"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 61, "학교 음악시간에 배울법한 노래들...", "음악 선생님")
QUIZ_MAP["음악교과서6"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 61, "학교 음악시간에 배울법한 노래들...", "음악 선생님")
QUIZ_MAP["동요1"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 60, "동요", "육아 마스터")
QUIZ_MAP["동요2"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 60, "동요", "유치원 선생님")

#개인요청
QUIZ_MAP["보끔플레이리스트1"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 103, "제작자 플레이 리스트", "보끔 잘알")
QUIZ_MAP["고민플레이리스트"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 52, "고민's 플레이 리스트", "고민 잘알")
QUIZ_MAP["나비플레이리스트(일본판)"] = QuizData(GAME_TYPE.SONG, "★★★★★", 56, "나비's JPOP플레이 리스트", "씹덕")
QUIZ_MAP["토마플레이리스트"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 75, "토마의 플레이 리스트", "토마토")
QUIZ_MAP["베찌애니플레이리스트"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 38, "베찌's 애니 플레이리스트", "니버")
QUIZ_MAP["부추빵플레이리스트"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 49, "부추빵's 여러가지 섞인 플레이리스트", "시옷")
QUIZ_MAP["설플레이리스트"] = QuizData(GAME_TYPE.SONG, "★★★★☆", 50, "설이's 플레이리스트", "설잘알")
QUIZ_MAP["나이스플레이리스트"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 30, "나이스's 플레이리스트", "나이스 요놈")
QUIZ_MAP["빙그레플레이리스트"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 25, "빙그레's 플레이리스트, 노래제목을 맞춰야합니다", "메로나")
QUIZ_MAP["히온플레이리스트"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 46, "히온's 플레이리스트", "니이버")
QUIZ_MAP["언몽레플레이리스트1"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 56, "언몽레's 플레이리스트, 엄청 어려움", "혼모노")
QUIZ_MAP["언몽레플레이리스트2"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 56, "언몽레's 플레이리스트, 엄청 어려움", "찐덕후")
QUIZ_MAP["언몽레플레이리스트3"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 68, "언몽레's 플레이리스트", "덕")
QUIZ_MAP["언몽레플레이리스트4"] = QuizData(GAME_TYPE.SONG, "★★☆☆☆", 68, "언몽레's 플레이리스트", "후")


#QUIZ_MAP["속담맞추기1탄"] = QuizData(GAME_TYPE.TTS, "★★★☆☆", 50, "속담 맞추기")

#미완
#QUIZ_MAP["가사맞추기1"] = QuizData(GAME_TYPE.SONG, "★★★☆☆", 20, "2020년 인기가요")

#퀴즈 카테고리들
CATEGORI_KPOP = [] #K-POP 카테고리
CATEGORI_KPOP.append("국내가요1")
CATEGORI_KPOP.append("국내가요2")
CATEGORI_KPOP.append("2019년히트가요")
CATEGORI_KPOP.append("걸그룹1")
CATEGORI_KPOP.append("걸그룹2")
CATEGORI_KPOP.append("걸그룹3")
CATEGORI_KPOP.append("가수10cm노래")
CATEGORI_KPOP.append("2020년히트가요")
CATEGORI_KPOP.append("국내가요3")
CATEGORI_KPOP.append("국내가요4")
CATEGORI_KPOP.append("국내가요5")
CATEGORI_KPOP.append("한국힙합1")
CATEGORI_KPOP.append("한국힙합2")
CATEGORI_KPOP.append("한국힙합3")

CATEGORI_ANIMATION = [] #애니메이션 카테고리
CATEGORI_ANIMATION.append("애니송1")
CATEGORI_ANIMATION.append("애니송2")
CATEGORI_ANIMATION.append("애니송3")
CATEGORI_ANIMATION.append("애니송4")
CATEGORI_ANIMATION.append("애니송5")
CATEGORI_ANIMATION.append("애니송6")
CATEGORI_ANIMATION.append("애니송7")
CATEGORI_ANIMATION.append("애니송8")
CATEGORI_ANIMATION.append("애니송9")
CATEGORI_ANIMATION.append("애니더빙곡1")
CATEGORI_ANIMATION.append("애니더빙곡2")
CATEGORI_ANIMATION.append("애니인트로1")
CATEGORI_ANIMATION.append("애니인트로2")
CATEGORI_ANIMATION.append("애니인트로3")

CATEGORI_MOVIE = [] #영화 카테고리
CATEGORI_MOVIE.append("영화대사1")
CATEGORI_MOVIE.append("영화OST1")

CATEGORI_GAME = [] #게임 카테고리
CATEGORI_GAME.append("메이플스토리BGM_1")
CATEGORI_GAME.append("메이플스토리BGM_2")
CATEGORI_GAME.append("메이플스토리BGM_3")
CATEGORI_GAME.append("메이플스토리BGM_4")
CATEGORI_GAME.append("메이플스토리BGM_5")
CATEGORI_GAME.append("메이플스토리BGM_6")
CATEGORI_GAME.append("메이플스토리BGM_7")
CATEGORI_GAME.append("메이플스토리BGM_8")
CATEGORI_GAME.append("메이플스토리BGM_9")
CATEGORI_GAME.append("게임1")
CATEGORI_GAME.append("스타크래프트1")

CATEGORI_POKEMON = [] #포켓몬 전용 카테고리
CATEGORI_POKEMON.append("포켓몬소리_1세대_1")
CATEGORI_POKEMON.append("포켓몬소리_1세대_2")
CATEGORI_POKEMON.append("포켓몬그림1")
CATEGORI_POKEMON.append("포켓몬그림2")
CATEGORI_POKEMON.append("포켓몬그림3")
CATEGORI_POKEMON.append("포켓몬그림4")
CATEGORI_POKEMON.append("포켓몬그림5")
CATEGORI_POKEMON.append("포켓몬그림6")
CATEGORI_POKEMON.append("포켓몬그림7")
CATEGORI_POKEMON.append("포켓몬그림8")
CATEGORI_POKEMON.append("포켓몬그림9")
CATEGORI_POKEMON.append("포켓몬그림10")
CATEGORI_POKEMON.append("포켓몬그림11")
CATEGORI_POKEMON.append("포켓몬그림12")
CATEGORI_POKEMON.append("포켓몬그림13")
CATEGORI_POKEMON.append("포켓몬그림14")
CATEGORI_POKEMON.append("포켓몬그림15")
CATEGORI_POKEMON.append("포켓몬그림16")
CATEGORI_POKEMON.append("포켓몬그림17")
CATEGORI_POKEMON.append("포켓몬그림18")
CATEGORI_POKEMON.append("포켓몬그림19")
CATEGORI_POKEMON.append("포켓몬그림20")
CATEGORI_POKEMON.append("포켓몬그림21")

CATEGORI_POP = [] #팝송 카테고리
CATEGORI_POP.append("팝송1")
CATEGORI_POP.append("팝송2")

CATEGORI_DRAMA = [] #드라마 카테고리
CATEGORI_DRAMA.append("드라마1")
CATEGORI_DRAMA.append("드라마2")

CATEGORI_PICTURE = [] #사진퀴즈 카테고리
CATEGORI_PICTURE.append("한국인물1")
CATEGORI_PICTURE.append("한국인물2")
CATEGORI_PICTURE.append("한국인물3")
CATEGORI_PICTURE.append("한국인물4")
CATEGORI_PICTURE.append("애니캐릭터1")
CATEGORI_PICTURE.append("애니캐릭터2")
CATEGORI_PICTURE.append("애니캐릭터3")
CATEGORI_PICTURE.append("국내아이돌1")
CATEGORI_PICTURE.append("국내아이돌2")
CATEGORI_PICTURE.append("국내아이돌3")

CATEGORI_MINECRAFT = [] #마인크래프트 카테고리
CATEGORI_MINECRAFT.append("마인크래프트그림1")
CATEGORI_MINECRAFT.append("마인크래프트그림2")
CATEGORI_MINECRAFT.append("마인크래프트그림3")
CATEGORI_MINECRAFT.append("마인크래프트그림4")
CATEGORI_MINECRAFT.append("마인크래프트그림5")
CATEGORI_MINECRAFT.append("마인크래프트그림6")
CATEGORI_MINECRAFT.append("마인크래프트그림7")
CATEGORI_MINECRAFT.append("마인크래프트OX1")
CATEGORI_MINECRAFT.append("마인크래프트OX2")

CATEGORI_TRIVIA = [] #잡학 퀴즈 카테고리
CATEGORI_TRIVIA.append("넌센스1")
CATEGORI_TRIVIA.append("역사상식1")
CATEGORI_TRIVIA.append("역사상식2")
CATEGORI_TRIVIA.append("역사상식3")
CATEGORI_TRIVIA.append("역사상식4")
CATEGORI_TRIVIA.append("상식OX1")
CATEGORI_TRIVIA.append("상식OX2")
CATEGORI_TRIVIA.append("상식OX3")
CATEGORI_TRIVIA.append("상식OX4")
CATEGORI_TRIVIA.append("상식OX5")
CATEGORI_TRIVIA.append("상식OX6")
CATEGORI_TRIVIA.append("속담1")

CATEGORI_OTHERS = [] #기타 카테고리
CATEGORI_OTHERS.append("국기1")
CATEGORI_OTHERS.append("국기2")
CATEGORI_OTHERS.append("국기3")
CATEGORI_OTHERS.append("기타국기1")
CATEGORI_OTHERS.append("랜드마크1")
CATEGORI_OTHERS.append("랜드마크2")
CATEGORI_OTHERS.append("랜드마크3")
CATEGORI_OTHERS.append("군대")
CATEGORI_OTHERS.append("음악교과서1")
CATEGORI_OTHERS.append("음악교과서2")
CATEGORI_OTHERS.append("음악교과서3")
CATEGORI_OTHERS.append("음악교과서4")
CATEGORI_OTHERS.append("음악교과서5")
CATEGORI_OTHERS.append("음악교과서6")
CATEGORI_OTHERS.append("동요1")
CATEGORI_OTHERS.append("동요2")


CATEGORI_PERSONAL = [] #개인 카테고리
CATEGORI_PERSONAL.append("보끔플레이리스트1")
#CATEGORI_OTHERS.append("단어맞추기1탄") 버그마늠
CATEGORI_PERSONAL.append("고민플레이리스트")
CATEGORI_PERSONAL.append("나비플레이리스트(일본판)")
CATEGORI_PERSONAL.append("토마플레이리스트")
CATEGORI_PERSONAL.append("베찌애니플레이리스트")
CATEGORI_PERSONAL.append("부추빵플레이리스트")
CATEGORI_PERSONAL.append("설플레이리스트")
CATEGORI_PERSONAL.append("나이스플레이리스트")
CATEGORI_PERSONAL.append("빙그레플레이리스트")
CATEGORI_PERSONAL.append("히온플레이리스트")
CATEGORI_PERSONAL.append("언몽레플레이리스트1")
CATEGORI_PERSONAL.append("언몽레플레이리스트2")
CATEGORI_PERSONAL.append("언몽레플레이리스트3")
CATEGORI_PERSONAL.append("언몽레플레이리스트4")


QUIZ_CATEGORI = dict() #카테고리 담을 곳
QUIZ_CATEGORI["케이팝"] = CATEGORI_KPOP #카테고리 목록에 KPOP 추가
QUIZ_CATEGORI["애니메이션"] = CATEGORI_ANIMATION #카테고리 목록에 애니 추가
QUIZ_CATEGORI["영화"] = CATEGORI_MOVIE #카테고리 목록에 영화 추가
QUIZ_CATEGORI["게임"] = CATEGORI_GAME #카테고리 목록에 게임 추가
QUIZ_CATEGORI["포켓몬"] = CATEGORI_POKEMON #카테고리 목록에 포켓몬 추가
QUIZ_CATEGORI["팝"] = CATEGORI_POP #카테고리 목록에 팝 추가
QUIZ_CATEGORI["드라마"] = CATEGORI_DRAMA #카테고리 목록에 드라마 추가
QUIZ_CATEGORI["인물퀴즈"] = CATEGORI_PICTURE #카테고리 목록에 인물퀴즈 추가
QUIZ_CATEGORI["마인크래프트"] = CATEGORI_MINECRAFT #카테고리 목록에 마인크래프트 추가
QUIZ_CATEGORI["잡학"] = CATEGORI_TRIVIA #카테고리 목록에 잡학 추가
QUIZ_CATEGORI["개인요청"] = CATEGORI_PERSONAL #카테고리 목록에 기타 추가
QUIZ_CATEGORI["기타"] = CATEGORI_OTHERS #카테고리 목록에 기타 추가


#반복 횟수 설정
#QUIZ_MAP["가사맞추기1"]._repeatCount = 3
QUIZ_MAP["포켓몬소리_1세대_1"]._repeatCount = 3
QUIZ_MAP["포켓몬소리_1세대_2"]._repeatCount = 3

selectList_maplestory = SelectionList.selectList_maplestory #메이플 스토리 객관식 리스트
selectList_pokemon1 = SelectionList.selectList_pokemon1 #포켓몬 1세대 객관식 리스트


selectMap = dict() #객관식 맵
selectMap["메이플스토리BGM_1"] = selectList_maplestory #객관식 답지 설정
selectMap["메이플스토리BGM_2"] = selectList_maplestory
selectMap["메이플스토리BGM_3"] = selectList_maplestory
selectMap["메이플스토리BGM_4"] = selectList_maplestory
selectMap["메이플스토리BGM_5"] = selectList_maplestory
selectMap["메이플스토리BGM_6"] = selectList_maplestory
selectMap["메이플스토리BGM_7"] = selectList_maplestory
selectMap["메이플스토리BGM_8"] = selectList_maplestory
selectMap["메이플스토리BGM_9"] = selectList_maplestory

selectMap["포켓몬소리_1세대_1"] = selectList_pokemon1
selectMap["포켓몬소리_1세대_2"] = selectList_pokemon1

#Utility
async def fadeIn(voice):
    if not voice.is_playing(): #보이스 재생중아니면
        return # 즉각 리턴

    try:
        voice.source = discord.PCMVolumeTransformer(voice.source)
        volume = 0.005  # 초기볼륨
        voice.source.volume = volume  # 볼륨 설정
        while volume < 1.0:  # 페이드 인
            volume += 0.05
            voice.source.volume = volume  # 볼륨 설정
            await asyncio.sleep(0.10)   
    except:
        print("fade In error")



async def fadeOut(voice):
    if not voice.is_playing(): #보이스 재생중아니면
        return # 즉각 리턴

    try:
        volume = voice.source.volume
        while volume > 0:  # 페이드 아웃
            volume -= 0.05
            voice.source.volume = volume  # 볼륨 설정
            await asyncio.sleep(0.10)
        
        voice.stop()  # 노래 중지
    except:
        print("fade out error")


async def clear(chatChannel):
    await chatChannel.purge(limit=100)


async def countdown(gameData):
    leftSec = 7 #남은 초

    voice = gameData._voice

    roundChecker = gameData._roundIndex

    playBarEmbed = discord.Embed(title="남은 시간", url="", description=("■"*7)+"\n", color=discord.Color.blue()) #재생바
    countdownBarMessage = await gameData._chatChannel.send(embed=playBarEmbed)
    await playBGM(voice, BGM_TYPE.countdown10) #카운트 다운
    voice.source = discord.PCMVolumeTransformer(voice.source)
    volume = 1.0 # 초기볼륨
    voice.source.volume = volume
    while voice.is_playing():  # 카운트다운중이면
        if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
            voice.stop() #카운트다운 정지
            return #리턴
        await asyncio.sleep(1)  # 1초후 다시 확인

        leftSec -= 1 #남은 초 -1
        index = 0
        showStr = "" #표시할 바

        while index < leftSec:
            index += 1
            showStr += "■"
        playBarEmbed = discord.Embed(title="남은 시간", url="", description=showStr+"\n", color=discord.Color.blue()) #재생바
        try: #메세지 객체 없어질수도있으니 try
            await countdownBarMessage.edit(embed=playBarEmbed)# 재생 끝날때까지 반복
        except:
            return
            #print("No message object error, playbar")

async def longCountdown(gameData):
    leftSec = 15 #남은 초

    tmpList = os.listdir(BGM_PATH+"/longTimer/")
    rd = random.randrange(0, len(tmpList))  # 0부터 tmpList 크기 -1 만큼
    rdBgm = tmpList[rd]  # 무작위 1개 선택
    
    bgmName = BGM_PATH+"/longTimer/"+rdBgm
    #print(bgmName)

    voice = gameData._voice

    roundChecker = gameData._roundIndex

    playBarEmbed = discord.Embed(title="남은 시간", url="", description=("■"*leftSec)+"\n", color=discord.Color.blue()) #재생바
    countdownBarMessage = await gameData._chatChannel.send(embed=playBarEmbed)

    voice.play(discord.FFmpegPCMAudio(bgmName))

    await fadeIn(voice) #페이드인
    
    while voice.is_playing():  # 카운트다운중이면
        if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
            voice.stop() #카운트다운 정지
            return #리턴
        await asyncio.sleep(1)  # 1초후 다시 확인

        leftSec -= 1 #남은 초 -1
        index = 0
        showStr = "" #표시할 바

        while index < leftSec:
            index += 1
            showStr += "■"

        playBarEmbed = discord.Embed(title="남은 시간", url="", description=showStr+"\n", color=discord.Color.blue()) #재생바
        try: #메세지 객체 없어질수도있으니 try
            await countdownBarMessage.edit(embed=playBarEmbed)# 재생 끝날때까지 반복
        except:
            return
            #print("No message object error, playbar")

def getAlphabetFromIndex(index):
    return alphabetList[index]

def getEmojiNumber(index):
    return emojiNumberList[index]

def convert(seconds):
    hours = seconds // 3600
    seconds %= 3600
    mins = seconds//60
    seconds %= 60

    return hours, mins, seconds

#사전 정의 함수

async def playBGM(voice, bgmType):
    try:
        if(bgmType == BGM_TYPE.PLING):
            voice.play(discord.FFmpegPCMAudio(BGM_PATH + "pling.mp3"))
        elif(bgmType == BGM_TYPE.ROUND_ALARM):
            voice.play(discord.FFmpegPCMAudio(BGM_PATH + "ROUND_ALARM.mp3"))
        elif(bgmType == BGM_TYPE.SCORE_ALARM):
            voice.play(discord.FFmpegPCMAudio(BGM_PATH + "SCORE_ALARM.mp3"))
        elif(bgmType == BGM_TYPE.ENDING):
            voice.play(discord.FFmpegPCMAudio(BGM_PATH + "ENDING.mp3"))
        elif(bgmType == BGM_TYPE.FAIL):
            voice.play(discord.FFmpegPCMAudio(BGM_PATH + "FAIL.mp3"))
        elif(bgmType == BGM_TYPE.countdown10):
            voice.play(discord.FFmpegPCMAudio(BGM_PATH + "countdown10.wav"))
        elif(bgmType == BGM_TYPE.SUCCESS):
            voice.play(discord.FFmpegPCMAudio(BGM_PATH + "SUCCESS.mp3"))
        elif(bgmType == BGM_TYPE.BELL):
            voice.play(discord.FFmpegPCMAudio(BGM_PATH + "bell.mp3"))

    except:
        print("voice is not connect error")


async def addScore(message, gameData):

    author = message.author
    if author in gameData._scoreMap:  # 점수 리스트에 정답자 있는지 확인
        gameData._scoreMap[author] += 1  # 있으면 1점 추가
    else:
        gameData._scoreMap[author] = 1  # 없으면 새로 1점 추가


    author = ""
    tmpSp = gameData._nowQuiz.split("&^")
    if len(tmpSp) == 2: #만약 작곡자가 적혀있다면
        author = tmpSp[1] #작곡자 저장

    answerStr = "" #정답 공개용 문자열
    for tmpStr in gameData._answerList:
        answerStr += tmpStr + "\n" #정답 문자열 생성

    if author == "": #작곡자가 적혀있지 않다면 그냥 공개
        embed = discord.Embed(
            title="[                              정답!!!                              ]", url=None, description=answerStr+"\n▽", color=discord.Color.blue())
        embed.set_author(name=message.author, url="",
                        icon_url=message.author.avatar_url)
    else: #작곡자 있다면
        embed = discord.Embed(
            title="[                              정답!!!                              ]", url=None, description=answerStr+"\n( "+str(author)+" )\n▽", color=discord.Color.blue())
        embed.set_author(name=message.author, url="",
                        icon_url=message.author.avatar_url)

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        embed.add_field(
            name=player, value="[ " + str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    embed.set_footer(text="\n남은 퀴즈 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개")

    thumbnailFile = None #썸네일 설정
    if gameData._thumbnail != None:
        thumbnailFile = discord.File(str(gameData._thumbnail), filename="quizThumbnail.png")

    if thumbnailFile == None:
        await gameData._chatChannel.send(embed=embed)
    else:
        embed.set_image(url="attachment://quizThumbnail.png")
        await gameData._chatChannel.send(file=thumbnailFile, embed=embed)

async def checkGameStop(gameData):
    if gameData._voice == None or not gameData._voice.is_connected:  # 봇 음성 객체가 없다면 퀴즈 종료
        del dataMap[gameData._guild]

        
async def showQuizCategory(ctx): #카테고리 목록 출력

    embed = discord.Embed(title="[ "+"퀴즈 카테고리 목록"+" ]\n", url=None,
        description=str("!quiz <카테고리명> \n입력시 해당 카테고리의 퀴즈 목록을 확인할 수 있습니다.\n▼ 총 퀴즈 개수 \n["+str(len(QUIZ_MAP.keys()))+" 개]"), color=discord.Color.blue())
    
    for categoryName in QUIZ_CATEGORI.keys():
        tmpCategoryData = QUIZ_CATEGORI[categoryName]
        embed.add_field(
            name=str(categoryName), value=" [ "+str(len(tmpCategoryData)) + "개 ]", inline=False)  # 카테고리 

    await ctx.send(embed=embed)

async def showQuizList(ctx, categoryName): #퀴즈 목록 출력

    embed = discord.Embed(title="[ "+str(categoryName)+"퀴즈 목록"+" ]\n", url=None,
        description=str("!quiz <플레이할 퀴즈명> \n입력시 해당 퀴즈를 시작합니다"), color=discord.Color.blue())
    
    for quizName in QUIZ_CATEGORI[categoryName]:
        tmpQuizData = QUIZ_MAP[quizName]
        embed.add_field(
            name=str(quizName), value=" [ ("+str(tmpQuizData._quizCnt) + "문제), " + str(tmpQuizData._desc) + " ]", inline=False)  # 난이도 필드로 추가

    await ctx.send(embed=embed)


async def printGameRule(ctx, voice, gameType): #각 퀴즈별 설명
    embed = discord.Embed(title="Tip", url=None,
                              description="게임 주최자는 [!skip] 으로 문제를 건너뛸 수 있습니다.\n 게임 주최자는 [!gamestop] 으로 퀴즈를 중지할 수 있습니다\n 게임 주최자는 [!hint] 로 힌트를 요청할 수 있습니다.", color=discord.Color.blue())
    await ctx.send(embed=embed)
    await playBGM(voice, BGM_TYPE.PLING)

    await asyncio.sleep(4)  # 3초 대기
    if gameType == GAME_TYPE.SONG:  # 게임 타입이 SONG 일 경우
        embed = discord.Embed(title="주의!", url=None,
                              description="봇의 음악 소리가 큽니다. 적절히 봇의 소리크기를 줄여두세요.", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법1", url=None,
                              description="정답은 공백없이도 입력 가능합니다. \n특수문자는 입력하지마세요. \n예): 시간을 달리는 소녀 -> 시간을달리는소녀\n이와 같은 표현도 가능합니다. \n예:) 시간을 달리는 소녀 -> 시달소, 개구리 중사 케로로 -> 개중케, 케로로\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법2", url=None,
                              description="시리즈명까지 다 입력해야합니다. \n예:) xyz, dp 등등...\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법3", url=None,
                              description="음악 길이는 대부분 40초로 정답을 맞출 때까지 계속 재생됩니다. \n정답을 맞추더라도 10초간은 지속 재생됩니다.\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
    elif gameType == GAME_TYPE.SCRIPT: #SCRIPT 일 경우
        embed = discord.Embed(title="플레이 방법1", url=None,
                              description="정답은 공백없이도 입력 가능합니다.", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법2", url=None,
                              description="시리즈명까지 다 입력해야합니다. \n예:) 해리포터마법사의돌\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법3", url=None,
                              description="대사 길이가 짧기 때문에 잘 듣고 맞춰주세요. \n대사가 끝나도 10초의 시간이 더 주어집니다.\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
    elif gameType == GAME_TYPE.SELECT: #객관식 일 경우
        embed = discord.Embed(title="플레이 방법1", url=None,
                              description="객관식 문제는 제시된 보기 중에서 선택하여 정답을 맞추는 방식입니다.\n채팅은 자제해주세요 ㅜㅜ 렉걸립니다.", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법2", url=None,
                              description="음악은 30초정도 재생되며 동시에 보기 메시지에 반응이 추가됩니다.\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법3", url=None,
                              description="보기 메시지에 추가된 반응 중 선택할 항목의 번호를 눌러 답을 제출할 수 있습니다.\n답을 바꾸고 싶다면 새롭게 선택할 번호를 누르시면됩니다.\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
    elif gameType == GAME_TYPE.GLOWLING: #포켓몬 울음소리일 경우
        embed = discord.Embed(title="플레이 방법1", url=None,
                                description="포켓몬 맞추기 문제는 제시된 보기 중에서 선택하여 정답을 맞추는 방식입니다.\n채팅은 자제해주세요 ㅜㅜ 렉걸립니다.", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법2", url=None,
                                description="울음소리는 3번정도 재생되며 동시에 보기 메시지에 반응이 추가됩니다.\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법3", url=None,
                                description="보기 메시지에 추가된 반응 중 선택할 항목의 번호를 눌러 답을 제출할 수 있습니다.\n답을 바꾸고 싶다면 새롭게 선택할 번호를 누르시면됩니다.\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
    elif gameType == GAME_TYPE.PICTURE: #사진퀴즈일경우
        embed = discord.Embed(title="플레이 방법1", url=None,
                                description="사진퀴즈는 제시된 사진에 해당하는 인물, 캐릭터, 물체명을 먼저 입력한 사람이 점수를 획득합니다.", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법2", url=None,
                                description="사진이 제공된 후 7초간의 시간이 주어지며 해당 시간안에 정답을 입력해야합니다.\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
    elif gameType == GAME_TYPE.OX: #ox퀴즈일경우
        embed = discord.Embed(title="플레이 방법1", url=None,
                                description="매 라운드마다 문제가 제시됩니다. 또한 제시된 문제에는 O, X 버튼이 달려있습니다.", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법2", url=None,
                                description="문제를 읽고 주어진 시간내에 해당 문제에 대한 대답을 선택하시면 됩니다.\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
    elif gameType == GAME_TYPE.QNA or gameType == GAME_TYPE.FAST_QNA: #텍스트 퀴즈일경우
        embed = discord.Embed(title="플레이 방법1", url=None,
                                description="제시된 문제에 대한 정답을 입력하시면 됩니다.", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
    elif gameType == GAME_TYPE.INTRO: #인트로 퀴즈
        embed = discord.Embed(title="플레이 방법1", url=None,
                                description="애니메이션 오프닝의 인트로를 듣고 해당 애니메이션의 제목을 맞추면됩니다.", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법2", url=None,
                                description="문제로 제시되는 인트로 노래가 짧기 때문에 주의해서 들으세요.", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기
        embed = discord.Embed(title="플레이 방법3", url=None,
                                description="난이도가 매우 어렵기 때문에 애니메이션 잘 모르면 시도조차 안하시는게 좋습니다.", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 3초 대기

async def gameLoop(ctx, gameData):
    if(gameData._gameType == GAME_TYPE.SONG):
        # 퀴즈 폴더 내 모든 파일 불러오기
        tmpList = os.listdir(BASE_PATH+gameData._gameName)
        quizList = []  # 빈 리스트 선언

        while len(tmpList) > 0:  # 모든 파일에 대해
            rd = random.randrange(0, len(tmpList))  # 0부터 tmpList 크기 -1 만큼
            quiz = tmpList[rd]  # 무작위 1개 선택
            if(os.path.isdir(BASE_PATH + gameData._gameName + "/" + quiz)):  # 폴더인지 확인(폴더만 추출할거임)
                quizList.append(quiz)  # 퀴즈 목록에 추가
            del tmpList[rd]  # 검사한 항목은 삭제

        gameData._quizList = quizList
        gameData._maxRound = len(quizList)  # 문제 총 개수
        gameData._roundIndex = -1  # 현재 라운드, -1로 해야 편함
        # while gameData._roundIndex < gameData._maxRound: #모든 문제 할 떄까지
        await startQuiz(gameData)
    elif(gameData._gameType == GAME_TYPE.SCRIPT):
        # 퀴즈 폴더 내 모든 파일 불러오기
        tmpList = os.listdir(BASE_PATH+gameData._gameName)
        quizList = []  # 빈 리스트 선언

        while len(tmpList) > 0:  # 모든 파일에 대해
            rd = random.randrange(0, len(tmpList))  # 0부터 tmpList 크기 -1 만큼
            quiz = tmpList[rd]  # 무작위 1개 선택
            if(os.path.isdir(BASE_PATH + gameData._gameName + "/" + quiz)):  # 폴더인지 확인(폴더만 추출할거임)
                quizList.append(quiz)  # 퀴즈 목록에 추가
            del tmpList[rd]  # 검사한 항목은 삭제

        gameData._quizList = quizList
        gameData._maxRound = len(quizList)  # 문제 총 개수
        gameData._roundIndex = -1  # 현재 라운드, -1로 해야 편함
        # while gameData._roundIndex < gameData._maxRound: #모든 문제 할 떄까지
        await startQuiz(gameData)
    elif(gameData._gameType == GAME_TYPE.SELECT):
        # 퀴즈 폴더 내 모든 파일 불러오기
        tmpList = os.listdir(BASE_PATH+gameData._gameName)
        quizList = []  # 빈 리스트 선언

        while len(tmpList) > 0:  # 모든 파일에 대해
            rd = random.randrange(0, len(tmpList))  # 0부터 tmpList 크기 -1 만큼
            quiz = tmpList[rd]  # 무작위 1개 선택
            if(os.path.isdir(BASE_PATH + gameData._gameName + "/" + quiz)):  # 폴더인지 확인(폴더만 추출할거임)
                quizList.append(quiz)  # 퀴즈 목록에 추가
            del tmpList[rd]  # 검사한 항목은 삭제

        gameData._quizList = quizList
        gameData._maxRound = len(quizList)  # 문제 총 개수
        gameData._roundIndex = -1  # 현재 라운드, -1로 해야 편함
        # while gameData._roundIndex < gameData._maxRound: #모든 문제 할 떄까지
        await startQuiz(gameData)
    elif(gameData._gameType == GAME_TYPE.GLOWLING):
        # 퀴즈 폴더 내 모든 파일 불러오기
        tmpList = os.listdir(BASE_PATH+gameData._gameName)
        quizList = []  # 빈 리스트 선언

        while len(tmpList) > 0:  # 모든 파일에 대해
            rd = random.randrange(0, len(tmpList))  # 0부터 tmpList 크기 -1 만큼
            quiz = tmpList[rd]  # 무작위 1개 선택
            if(os.path.isdir(BASE_PATH + gameData._gameName + "/" + quiz)):  # 폴더인지 확인(폴더만 추출할거임)
                quizList.append(quiz)  # 퀴즈 목록에 추가
            del tmpList[rd]  # 검사한 항목은 삭제

        gameData._quizList = quizList
        gameData._maxRound = len(quizList)  # 문제 총 개수
        gameData._roundIndex = -1  # 현재 라운드, -1로 해야 편함
        # while gameData._roundIndex < gameData._maxRound: #모든 문제 할 떄까지
        await startQuiz(gameData)
    elif(gameData._gameType == GAME_TYPE.PICTURE):
        # 퀴즈 폴더 내 모든 파일 불러오기
        tmpList = os.listdir(BASE_PATH+gameData._gameName)
        quizList = []  # 빈 리스트 선언

        while len(tmpList) > 0:  # 모든 파일에 대해
            rd = random.randrange(0, len(tmpList))  # 0부터 tmpList 크기 -1 만큼
            quiz = tmpList[rd]  # 무작위 1개 선택
            if(os.path.isdir(BASE_PATH + gameData._gameName + "/" + quiz)):  # 폴더인지 확인(폴더만 추출할거임)
                quizList.append(quiz)  # 퀴즈 목록에 추가
            del tmpList[rd]  # 검사한 항목은 삭제

        gameData._quizList = quizList
        gameData._maxRound = len(quizList)  # 문제 총 개수
        gameData._roundIndex = -1  # 현재 라운드, -1로 해야 편함
        # while gameData._roundIndex < gameData._maxRound: #모든 문제 할 떄까지
        await startQuiz(gameData)
    elif(gameData._gameType == GAME_TYPE.OX): #OX퀴즈일때
        if(os.path.isfile(BASE_PATH + gameData._gameName + "/" + "quiz.txt")):  # 퀴즈 파일 로드

            tmpQuizList = [] #임시 ox퀴즈 객체  저장공간
            addIndex = -1 #현재 작업중인 ox 퀴즈 객체 인덱스
            tmpOXQuiz = None

            f = open(BASE_PATH + gameData._gameName + "/" + "quiz.txt", "r", encoding="utf-8" )
            while True:
                line = f.readline() #1줄씩 읽기
                if not line: break #다 읽으면 break;
                if line == "\r\n": continue #개행이면 그냥 continue
                tmpLine = line.replace("quiz_answer: ", "") # 앞에 부분 다 떼어내
                if tmpLine != line: #정답 문자열 있다면
                    answer = tmpLine[0:0+1].upper() #o인지 x인지 가져오기
                    tmpOXQuiz = TextQuizData(answer) #ox 퀴즈 객체 생성
                    tmpQuizList.append(tmpOXQuiz) #해당 객체 list에 추가
                    addIndex += 1 #작업중인 ox 퀴즈 인덱스 재설정
                else: #정답 문자열 없으면
                    tmpLine = line.replace("desc:", "") # desc 확인
                    if tmpLine != line: #desc 가 있다면
                        if(tmpOXQuiz != None): # 작업중인 ox 문제 객체가 있다면
                            tmpOXQuiz._answerText += tmpLine # line 추가
                    else: #desc도 없다면, 문제 문장일거임
                        if(tmpOXQuiz != None): # 작업중인 ox 문제 객체가 있다면
                            tmpOXQuiz._questionText += line # line 추가
                
            f.close()

            quizList = []  # 빈 리스트 선언
            while len(tmpQuizList) > 0:  # 모든 퀴즈 객체에 대해
                rd = random.randrange(0, len(tmpQuizList))  # 0부터 tmpQuizList 크기 -1 만큼
                quiz = tmpQuizList[rd]  # 무작위 1개 선택
                quizList.append(quiz)  # 퀴즈 목록에 ox 퀴즈 객체 추가
                del tmpQuizList[rd]  # 검사한 항목은 삭제

            gameData._textQuizList = quizList #ox 퀴즈 리스트 설정
            gameData._maxRound = len(quizList)  # 문제 총 개수
            gameData._roundIndex = -1  # 현재 라운드, -1로 해야 편함
            # while gameData._roundIndex < gameData._maxRound: #모든 문제 할 떄까지
            await startQuiz(gameData)
        else: #퀴즈 파일 없으면 return
            return
    elif(gameData._gameType == GAME_TYPE.QNA or gameData._gameType == GAME_TYPE.FAST_QNA): #QNA퀴즈일때
        if(os.path.isfile(BASE_PATH + gameData._gameName + "/" + "quiz.txt")):  # 퀴즈 파일 로드

            tmpQuizList = [] #임시 ox퀴즈 객체  저장공간
            addIndex = -1 #현재 작업중인 ox 퀴즈 객체 인덱스
            tmpOXQuiz = None

            f = open(BASE_PATH + gameData._gameName + "/" + "quiz.txt", "r", encoding="utf-8" )
            while True:
                line = f.readline() #1줄씩 읽기
                if not line: break #다 읽으면 break;
                if line == "\r\n": continue #개행이면 그냥 continue
                tmpLine = line.replace("quiz_answer: ", "") # 앞에 부분 다 떼어내
                if tmpLine != line: #정답 문자열 있다면
                    answer = tmpLine[0:len(tmpLine)].strip().upper() #답 가져오기
                    tmpOXQuiz = TextQuizData(answer) #ox 퀴즈 객체 생성
                    tmpQuizList.append(tmpOXQuiz) #해당 객체 list에 추가
                    addIndex += 1 #작업중인 ox 퀴즈 인덱스 재설정
                else: #정답 문자열 없으면
                    tmpLine = line.replace("desc:", "") # desc 확인
                    if tmpLine != line: #desc 가 있다면
                        if(tmpOXQuiz != None): # 작업중인 ox 문제 객체가 있다면
                            tmpOXQuiz._answerText += tmpLine # line 추가
                    else: #desc도 없다면, 문제 문장일거임
                        if(tmpOXQuiz != None): # 작업중인 ox 문제 객체가 있다면
                            tmpOXQuiz._questionText += line # line 추가
                
            f.close()

            quizList = []  # 빈 리스트 선언
            while len(tmpQuizList) > 0:  # 모든 퀴즈 객체에 대해
                rd = random.randrange(0, len(tmpQuizList))  # 0부터 tmpQuizList 크기 -1 만큼
                quiz = tmpQuizList[rd]  # 무작위 1개 선택
                quizList.append(quiz)  # 퀴즈 목록에 ox 퀴즈 객체 추가
                del tmpQuizList[rd]  # 검사한 항목은 삭제

            gameData._textQuizList = quizList #ox 퀴즈 리스트 설정
            gameData._maxRound = len(quizList)  # 문제 총 개수
            gameData._roundIndex = -1  # 현재 라운드, -1로 해야 편함
            # while gameData._roundIndex < gameData._maxRound: #모든 문제 할 떄까지
            await startQuiz(gameData)
        else: #퀴즈 파일 없으면 return
            return
    elif(gameData._gameType == GAME_TYPE.INTRO):
        # 퀴즈 폴더 내 모든 파일 불러오기
        tmpList = os.listdir(BASE_PATH+gameData._gameName)
        quizList = []  # 빈 리스트 선언

        while len(tmpList) > 0:  # 모든 파일에 대해
            rd = random.randrange(0, len(tmpList))  # 0부터 tmpList 크기 -1 만큼
            quiz = tmpList[rd]  # 무작위 1개 선택
            if(os.path.isdir(BASE_PATH + gameData._gameName + "/" + quiz)):  # 폴더인지 확인(폴더만 추출할거임)
                quizList.append(quiz)  # 퀴즈 목록에 추가
            del tmpList[rd]  # 검사한 항목은 삭제

        gameData._quizList = quizList
        gameData._maxRound = len(quizList)  # 문제 총 개수
        gameData._roundIndex = -1  # 현재 라운드, -1로 해야 편함
        # while gameData._roundIndex < gameData._maxRound: #모든 문제 할 떄까지
        await startQuiz(gameData)

async def startQuiz(gameData):
    await nextRound(gameData)


async def nextRound(gameData):
    gameData._isSkiped = False
    gameData._useHint = False
    if gameData._gameType == GAME_TYPE.SONG:
        await quiz_song(gameData)  # 다음 라운드 호출, 재귀
    elif gameData._gameType == GAME_TYPE.SCRIPT:
        await quiz_script(gameData)  # 다음 라운드 호출, 재귀
    elif gameData._gameType == GAME_TYPE.SELECT:
        await quiz_select(gameData)  # 다음 라운드 호출, 재귀
    elif gameData._gameType == GAME_TYPE.GLOWLING:
        await quiz_glowling(gameData)  # 다음 라운드 호출, 재귀
    elif gameData._gameType == GAME_TYPE.PICTURE:
        await quiz_picture(gameData)  # 다음 라운드 호출, 재귀
    elif gameData._gameType == GAME_TYPE.OX:
        await quiz_ox(gameData)  # 다음 라운드 호출, 재귀
    elif gameData._gameType == GAME_TYPE.QNA:
        await quiz_qna(gameData)  # 다음 라운드 호출, 재귀
    elif gameData._gameType == GAME_TYPE.FAST_QNA:
        await quiz_fastqna(gameData)  # 다음 라운드 호출, 재귀
    elif gameData._gameType == GAME_TYPE.INTRO:
        await quiz_intro(gameData)  # 다음 라운드 호출, 재귀

async def quiz_song(gameData):  # 재귀 사용, 노래 퀴즈용
    await clear(gameData._chatChannel)
    gameData._roundIndex += 1

    if gameData._roundIndex == gameData._maxRound:  # 더이상문제가없다면
        await finishGame(gameData)  # 게임 끝내기
        return

    voice = get(bot.voice_clients, guild=gameData._guild)  # 봇의 음성 객체 얻기

    questionEmbed = discord.Embed(title=str(gameData._roundIndex+1)+"번째 문제입니다.",
                          url="", description="\n▽", color=discord.Color.blue())

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        questionEmbed.add_field(
            name=player, value=" [ "+str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    questionEmbed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    await gameData._chatChannel.send(embed=questionEmbed)
    await playBGM(voice, BGM_TYPE.ROUND_ALARM)
    await asyncio.sleep(2)
    quiz = gameData._quizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
    gameData._nowQuiz = quiz  # 퀴즈 정답 등록
    answer = []  # 빈 리스트 선언

    title = gameData._nowQuiz.split("&^")[0] #먼저 제목만 뽑기

    fullAnswer = title.split("&#")  # 지정한 특수문자로 split하여 여러 제목 가져오기
    for tmpStr in fullAnswer:  # 추가
        answer.append(tmpStr)  # 정답에 추가

    for tmpStr in fullAnswer:
        tmpA = tmpStr.split(" ")  # 공백으로 split
        answer2 = ""
        for tmpStr in tmpA:
            if len(tmpStr) >= 1: #어떤 문자든 있다면
                answer2 += tmpStr[0]  # 첫글자만 추가
        if len(answer2) >= 2:  # 문자열 길이가 2보다 클때
            answer.append(answer2)  # 정답 목록에 추가

    gameData._answerList = answer  # 정답 목록 설정
    gameData._thumbnail = None # 썸네일 초기화

    quizPath = BASE_PATH + gameData._gameName + "/" + quiz
    for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
        if file.endswith(".png") or file.endswith("jpg"): #사진파일이라면 ,썸네일임
            gameData._thumbnail = quizPath + "/" +file
        elif file.endswith(".wav") or file.endswith(".mp3"):  # 파일 확장자가 .wav 또는 .mp3면, 문제 파일일거임
            question = file  # 기존 파일명
            print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {question}\n") #정답 표시
            if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
                gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
                roundChecker = gameData._roundIndex  # 현재 라운드 저장

                audioName = quizPath + "/" + question #실제 실행할 음악파일 경로, 초기화

                audioLength = 39 #초기화 ,기본 39

                if file.endswith(".wav"): #확장자 wav 일때
                    f = sf.SoundFile(audioName) #오디오 파일 로드
                    audioLength = len(f) / f.samplerate #오디오 길이
                    f.close()
                elif file.endswith(".mp3"): #확장자 mp3일때, 1분이상곡은 자르기 옵션 제공 ㅎㅎ
                    audio = MP3(audioName) 
                    audio_info = audio.info
                    length_in_secs = int(audio_info.length) #음악 총 길이
                    if length_in_secs > 80: #음악이 80초 초과할 시, 자르기 시작
                        song = AudioSegment.from_mp3( audioName ) #오디오 자르기 가져오기
                        startTime = random.randrange(20, (length_in_secs-19-39)) #자르기 시작 시간 5 ~ 끝-19-(노래길이)
                        endTime = startTime + 39 #39초만큼 자를거라

                        #print(str(startTime) + " ~ " + str(endTime))

                        startTime *= 1000 #s 를 ms로
                        endTime *= 1000 #s를 ms로

                        extract = song[startTime:endTime]
                        
                        audioName = TMP_PATH + "/" + str(gameData._guild.id) + ".mp3" #실제 실행할 음악파일 임시파일로 변경

                        extract.export(audioName) #임시 저장
                    else:
                        audioLength = length_in_secs
                
                repartCnt = gameData._repeatCount #반복횟수

                while repartCnt > 0: #반복횟수만큼 반복
                    repartCnt -= 1

                    playSec = 0 #현재 재생한 초

                    playBarEmbed = discord.Embed(title="음악 재생 현황", url="", description="\n", color=discord.Color.blue()) #재생바
                    playBarMessage = await gameData._chatChannel.send(embed=playBarEmbed)
                    voice.play(discord.FFmpegPCMAudio(audioName))  # 재생


                    await fadeIn(voice) #페이드인

                    while voice.is_playing():  # 재생중이면
                        if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                            return #리턴
                        await asyncio.sleep(1)  # 1초후 다시 확인
                        playSec += 1 #재생 1초 +
                        notPlayed = (audioLength - 9) - playSec #남은 길이
                        index = 0
                        showStr = "" #표시할 바

                        while index < playSec:
                            index += 1
                            showStr += "■"
                        
                        index = 0
                        while index < notPlayed:
                            index += 1
                            showStr += "□"

                        playBarEmbed = discord.Embed(title="음악 재생 현황", url="", description=showStr+"\n", color=discord.Color.blue()) #재생바
                        try: #메세지 객체 없어질수도있으니 try
                            await playBarMessage.edit(embed=playBarEmbed)# 재생 끝날때까지 반복
                        except:
                            print("No message object error, playbar")

                        if notPlayed < 0: 
                            voice.stop()
                            break # 재생시간 초과면 break
                            
                if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
                    return
                await checkGameStop(gameData)
                if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER:  # 아직도 정답자 없다면
                    await showAnswer(roundChecker, gameData)  # 정답 공개!
                    return
                break  # for 빠지기


async def quiz_script(gameData):  # 재귀 사용, 대사 퀴즈용
    await clear(gameData._chatChannel)
    gameData._roundIndex += 1

    if gameData._roundIndex == gameData._maxRound:  # 더이상문제가없다면
        await finishGame(gameData)  # 게임 끝내기
        return

    voice = get(bot.voice_clients, guild=gameData._guild)  # 봇의 음성 객체 얻기

    questionEmbed = discord.Embed(title=str(gameData._roundIndex+1)+"번째 문제입니다.",
                          url="", description="\n▽", color=discord.Color.blue())

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        questionEmbed.add_field(
            name=player, value=" [ "+str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    questionEmbed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    await gameData._chatChannel.send(embed=questionEmbed)
    await playBGM(voice, BGM_TYPE.ROUND_ALARM)
    await asyncio.sleep(2)
    quiz = gameData._quizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
    gameData._nowQuiz = quiz  # 퀴즈 정답 등록
    answer = []  # 빈 리스트 선언

    title = gameData._nowQuiz.split("&^")[0] #먼저 제목만 뽑기

    fullAnswer = title.split("&#")  # 지정한 특수문자로 split하여 여러 제목 가져오기
    for tmpStr in fullAnswer:  # 추가
        answer.append(tmpStr)  # 정답에 추가

    for tmpStr in fullAnswer:
        tmpA = tmpStr.split(" ")  # 공백으로 split
        answer2 = ""
        for tmpStr in tmpA:
            if len(tmpStr) >= 1: #어떤 문자든 있다면
                answer2 += tmpStr[0]  # 첫글자만 추가
        if len(answer2) >= 2:  # 문자열 길이가 2보다 같거나 클때
            answer.append(answer2)  # 정답 목록에 추가

    gameData._answerList = answer  # 정답 목록 설정

    quizPath = BASE_PATH + gameData._gameName + "/" + quiz
    for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
        if file.endswith(".wav"):  # 파일 확장자가 .mp3면, 문제 파일일거임
            question = file  # 기존 파일명
            print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {question}\n") #정답 표시
            if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
                gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
                roundChecker = gameData._roundIndex  # 현재 라운드 저장

                f = sf.SoundFile(quizPath + "/" + question) #오디오 파일 로드
                audioLength = len(f) / f.samplerate #오디오 길이
                f.close()

                repartCnt = gameData._repeatCount #반복횟수

                while repartCnt > 0: #반복횟수만큼 반복
                    repartCnt -= 1

                    playSec = 0 #현재 재생한 초

                    playBarEmbed = discord.Embed(title="대사", url="", description="\n", color=discord.Color.blue()) #재생바
                    playBarMessage = await gameData._chatChannel.send(embed=playBarEmbed)
                    voice.play(discord.FFmpegPCMAudio(quizPath + "/" + question))  # 재생
                    voice.source = discord.PCMVolumeTransformer(voice.source)
                    volume = 1.0 # 초기볼륨
                    voice.source.volume = volume


                    while voice.is_playing():  # 재생중이면
                        if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                            voice.stop()
                            return #리턴
                        await asyncio.sleep(1)  # 1초후 다시 확인
                        playSec += 1 #재생 1초 +
                        notPlayed = (audioLength - 3) - playSec #남은 길이, -14하는 이유는 초기에 7초만큼 페이드인하느라 시간씀, 연산 레깅
                        index = 0
                        showStr = "" #표시할 바

                        while index < playSec:
                            index += 1
                            showStr += "■"
                        
                        index = 0
                        while index < notPlayed:
                            index += 1
                            showStr += "□"

                        playBarEmbed = discord.Embed(title="대사", url="", description=showStr+"\n", color=discord.Color.blue()) #재생바
                        try: #메세지 객체 없어질수도있으니 try
                            await playBarMessage.edit(embed=playBarEmbed)# 재생 끝날때까지 반복
                        except:
                            print("No message object error, playbar")

                #재생이 끝난 후
                if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER: #아직도 정답자 기다리는 중이면
                    countdown(gameData)

                #카운트 다운 끝난 후

                if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
                    return
                await checkGameStop(gameData)
                if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER:  # 아직도 정답자 없다면
                    await showAnswer(roundChecker, gameData)  # 정답 공개!
                    return
                break  # for 빠지기



async def quiz_select(gameData):  # 재귀 사용, 객관식 퀴즈용
    await clear(gameData._chatChannel)
    gameData._roundIndex += 1

    if gameData._roundIndex == gameData._maxRound:  # 더이상문제가없다면
        await finishGame(gameData)  # 게임 끝내기
        return

    voice = get(bot.voice_clients, guild=gameData._guild)  # 봇의 음성 객체 얻기

    questionEmbed = discord.Embed(title=str(gameData._roundIndex+1)+"번째 문제입니다.",
                          url="", description="\n▽", color=discord.Color.blue())

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        questionEmbed.add_field(
            name=player, value=" [ "+str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    questionEmbed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    await gameData._chatChannel.send(embed=questionEmbed)
    await playBGM(voice, BGM_TYPE.ROUND_ALARM)
    await asyncio.sleep(2)
    quiz = gameData._quizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
    gameData._nowQuiz = quiz  # 퀴즈 정답 등록

    gameData._selectList.clear() #보기 문항 초기화
    notRandomList = [] #아직 안 섞은 리스트
    title = gameData._nowQuiz[0:len(gameData._nowQuiz)-5] #먼저 객관식 제목만 뽑기
    notRandomList.append(title) #정답 먼저 추가
    for i in range(0,10): #보기 10개만 가져올거임
        notRandomList.append(random.choice(selectMap[gameData._gameName])) #보기 추가

    #보기 설정완료(총11개)

    index = 0
    while len(notRandomList) > 0: #리스트 비울 때까지 계속 반복
        rd = random.randrange(0, len(notRandomList)) #리스트에서 무작위로 1개
        rdTmp = notRandomList[rd] #보기 문항 가져오기
        if len(gameData._selectList) > 0: #보기 목록에 뭐라도 있다면
            for compareStr in gameData._selectList: #보기 목록 모든 항목에 대해
                if compareStr == rdTmp: # 만약 중복이라면
                    del notRandomList[rd] #뽑아낸 보기 삭제
                    notRandomList.append(random.choice(selectMap[gameData._gameName])) #다른 보기 추가
                    continue #계속~
        gameData._selectList.append(notRandomList[rd]) # 보기에 넣기  
        del notRandomList[rd] #뽑아낸 보기 삭제

    gameData._selectionAnswer = gameData._selectList.index(title) #정답 번호

    selectListStr = "\n▽\n" #보기 str
    index = 0
    for tmpStr in gameData._selectList: #모든 보기에서 가져오기
        selectListStr += "[ "+ str(index) +"번 ]. " + tmpStr + "\n" #str 추가
        index += 1

    selectionEmbed = discord.Embed(title="----- 보기 -----",
                          url="", description=selectListStr, color=discord.Color.blue())

    selectionMsg = await gameData._chatChannel.send(embed=selectionEmbed) #보기 보내기
    gameData._selectPlayerMap.clear() #맵 클리어

    quizPath = BASE_PATH + gameData._gameName + "/" + quiz
    for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
        if file.endswith(".wav") or file.endswith(".mp3"):  # 파일 확장자가 .mp3면, 문제 파일일거임
            question = file  # 기존 파일명
            print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {question}\n") #정답 표시
            if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
                gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
                roundChecker = gameData._roundIndex  # 현재 라운드 저장
                
                audioLength = 20 #객관식은 오디오길이 15초로 고정

                repartCnt = gameData._repeatCount #반복횟수

                while repartCnt > 0: #반복횟수만큼 반복
                    repartCnt -= 1

                    playSec = 0 #현재 재생한 초

                    playBarEmbed = discord.Embed(title="음악 재생 현황", url="", description="\n", color=discord.Color.blue()) #재생바
                    playBarMessage = await gameData._chatChannel.send(embed=playBarEmbed)
                    voice.play(discord.FFmpegPCMAudio(quizPath + "/" + question))  # 재생

                    await fadeIn(voice) #페이드인        

                    emojiIndex = 0
                    
                    while voice.is_playing():  # 재생중이면
                        if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                            return #리턴
                        await asyncio.sleep(1)  # 1초후 다시 확인
                        playSec += 1 #재생 1초 +
                        notPlayed = (audioLength) - playSec #남은 길이,
                        index = 0
                        showStr = "" #���시할 바

                        while index < playSec:
                            index += 1
                            showStr += "■"
                        
                        index = 0
                        while index <= notPlayed: #같거나 작다루...
                            index += 1
                            showStr += "□"

                        playBarEmbed = discord.Embed(title="음악 재생 현황", url="", description=showStr+"\n", color=discord.Color.blue()) #재생바
                        
                        try: #메세지 객체 없어질수도있으니 try
                            if emojiIndex < len(gameData._selectList): #보기 문항만큼 이모지 추가 안했다면
                                emoji = getEmojiNumber(emojiIndex) #이모지 가져오기,
                                emojiIndex += 1
                                await selectionMsg.add_reaction(emoji=emoji) #이모지 추가, 렉걸려서 여기에다 넣었음...재생하면서 작동하라구...
                            await playBarMessage.edit(embed=playBarEmbed)# 재생 끝날때까지 반복
                        except:
                            print("No message object error, playbar")

                        if notPlayed < 0: break # 만약 20초 지났다면 break
                    
                    if repartCnt > 0: #아직 반복횟수 남아있다면
                        await asyncio.sleep(2) #1초대기

                if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
                    return
                                
                await fadeOut(voice) #노래 끄기

                await checkGameStop(gameData)
                if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER:  # 사실상 그냥 올 수 있는 부분
                    await showAnswer_select(roundChecker, gameData)  # 정답 공개!(객관식용)
                    return
                break  # for 빠지기


async def quiz_glowling(gameData):  # 재귀 사용, 객관식 울음소리(포켓몬)
    await clear(gameData._chatChannel)
    gameData._roundIndex += 1

    if gameData._roundIndex == gameData._maxRound:  # 더이상문제가없다면
        await finishGame(gameData)  # 게임 끝내기
        return

    voice = get(bot.voice_clients, guild=gameData._guild)  # 봇의 음성 객체 얻기

    questionEmbed = discord.Embed(title=str(gameData._roundIndex+1)+"번째 문제입니다.",
                          url="", description="\n▽", color=discord.Color.blue())

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        questionEmbed.add_field(
            name=player, value=" [ "+str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    questionEmbed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    await gameData._chatChannel.send(embed=questionEmbed)
    await playBGM(voice, BGM_TYPE.ROUND_ALARM)
    await asyncio.sleep(2)
    quiz = gameData._quizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
    gameData._nowQuiz = quiz  # 퀴즈 정답 등록

    gameData._selectList.clear() #보기 문항 초기화
    notRandomList = [] #아직 안 섞은 리스트
    title = gameData._nowQuiz #먼저 포켓몬 정답만 뽑기
    notRandomList.append(title) #정답 먼저 추가
    for i in range(0,10): #보기 10개만 가져올거임
        notRandomList.append(random.choice(selectMap[gameData._gameName])) #보기 추가

    #보기 설정완료(총11개)

    index = 0
    while len(notRandomList) > 0: #리스트 비울 때까지 계속 반복
        rd = random.randrange(0, len(notRandomList)) #리스트에서 무작위로 1개
        rdTmp = notRandomList[rd] #보기 문항 가져오기
        if len(gameData._selectList) > 0: #보기 목록에 뭐라도 있다면
            for compareStr in gameData._selectList: #보기 목록 모든 항목에 대해
                if compareStr == rdTmp: # 만약 중복이라면
                    del notRandomList[rd] #뽑아낸 보기 삭제
                    notRandomList.append(random.choice(selectMap[gameData._gameName])) #다른 보기 추가
                    continue #계속~
        gameData._selectList.append(notRandomList[rd]) # 보기에 넣기  
        del notRandomList[rd] #뽑아낸 보기 삭제

    gameData._selectionAnswer = gameData._selectList.index(title) #정답 번호
    gameData._selectPlayerMap.clear() #선택한 정답 맵 클리어

    selectListStr = "\n▽\n" #보기 str
    index = 0
    for tmpStr in gameData._selectList: #모든 보기에서 가져오기
        selectListStr += "[ "+ str(index) +"번 ]. " + tmpStr + "\n" #str 추가
        index += 1

    selectionEmbed = discord.Embed(title="----- 보기 -----",
                          url="", description=selectListStr, color=discord.Color.blue())

    selectionMsg = await gameData._chatChannel.send(embed=selectionEmbed) #보기 보내기

    
    emojiIndex = 0
                    
    while True: #선택항목 다 띄우기
        try: #메세지 객체 없어질수도있으니 try
            if emojiIndex < len(gameData._selectList): #보기 문항만큼 이모지 추가 안했다면
                emoji = getEmojiNumber(emojiIndex) #이모지 가져오기,
                emojiIndex += 1
                await selectionMsg.add_reaction(emoji=emoji) #이모지 추가, 렉걸려서 여기에다 넣었음...재생하면서 작동하라구...
            else:
                break
        except:
            print("No message object error, playbar")

    quizPath = BASE_PATH + gameData._gameName + "/" + quiz
    for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
        if file.endswith(".wav") or file.endswith(".mp3") or file.endswith(".ogg"):  # 파일 확장자가 .mp3, ogg, wav면, 문제 파일일거임
            question = file  # 기존 파일명
            print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {question}\n") #정답 표시
            if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
                gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
                roundChecker = gameData._roundIndex  # 현재 라운드 저장

                repartCnt = gameData._repeatCount #반복횟수
                playBarEmbed = discord.Embed(title="남은 듣기 횟수", url="", description="■■■\n", color=discord.Color.blue()) #재생바
                playBarMessage = await gameData._chatChannel.send(embed=playBarEmbed)

                while repartCnt > 0: #반복횟수만큼 반복
                    repartCnt -= 1

                    playSec = 0 #현재 재생한 횟수

                    voice.play(discord.FFmpegPCMAudio(quizPath + "/" + question))  # 재생   
                    
                    while voice.is_playing():  # 재생중이면
                        if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                            return #리턴
                        await asyncio.sleep(1)  # 0.5초후 다시 확인
                        playSec += 1 #재생 1 +
                        notPlayed = repartCnt - playSec #남은 길이,

                        showStr = "" #표시할 바
                        index = 0
                        while index <= notPlayed: #같거나 작다루...
                            index += 1
                            showStr += "■"

                        index = 0

                        while index < playSec:
                            index += 1
                            showStr += "□"
                        

                        playBarEmbed = discord.Embed(title="남은 듣기 횟수", url="", description=showStr+"\n", color=discord.Color.blue()) #재생바
                        
                        try: #메세지 객체 없어질수도있으니 try
                            await playBarMessage.edit(embed=playBarEmbed)# 재생 끝날때까지 반복
                        except:
                            print("No message object error, playbar")

                        if notPlayed < 0: break # 만약 20초 지났다면 break
                    
                    if repartCnt > 0: #아직 반복횟수 남아있다면
                        await asyncio.sleep(2.5) #2.5초대기

                    if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
                        return

                #재생이 끝난 후
                await countdown(gameData) 
                while voice.is_playing():  # 재생중이면, 즉, 카운트 다운 대기
                    await asyncio.sleep(0.3) #0.3초 대기 후 다시 체크

                #카운트 다운 끝난 후

                await checkGameStop(gameData)
                if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER:  # 사실상 그냥 올 수 있는 부분
                    await showAnswer_select(roundChecker, gameData)  # 정답 공개!(객관식용)
                    return
                break  # for 빠지기


async def quiz_picture(gameData):  # 재귀 사용, 사진보고 맞추기
    await clear(gameData._chatChannel)
    gameData._roundIndex += 1

    if gameData._roundIndex == gameData._maxRound:  # 더이상문제가없다면
        await finishGame(gameData)  # 게임 끝내기
        return

    voice = get(bot.voice_clients, guild=gameData._guild)  # 봇의 음성 객체 얻기

    questionEmbed = discord.Embed(title=str(gameData._roundIndex+1)+"번째 문제입니다.",
                          url="", description="\n▽", color=discord.Color.blue())

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        questionEmbed.add_field(
            name=player, value=" [ "+str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    questionEmbed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    await gameData._chatChannel.send(embed=questionEmbed)
    await playBGM(voice, BGM_TYPE.ROUND_ALARM)
    await asyncio.sleep(2)
    quiz = gameData._quizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
    gameData._nowQuiz = quiz  # 퀴즈 정답 등록

    answer = []  # 빈 리스트 선언

    title = gameData._nowQuiz.split("&^")[0] #먼저 제목만 뽑기

    fullAnswer = title.split("&#")  # 지정한 특수문자로 split하여 여러 제목 가져오기
    for tmpStr in fullAnswer:  # 추가
        answer.append(tmpStr)  # 정답에 추가

    for tmpStr in fullAnswer:
        tmpA = tmpStr.split(" ")  # 공백으로 split
        answer2 = ""
        for tmpStr in tmpA:
            if len(tmpStr) >= 1: #어떤 문자든 있다면
                answer2 += tmpStr[0]  # 첫글자만 추가
        if len(answer2) >= 2:  # 문자열 길이가 2보다 같거나 클때
            answer.append(answer2)  # 정답 목록에 추가

    gameData._answerList = answer  # 정답 목록 설정
                    

    quizPath = BASE_PATH + gameData._gameName + "/" + quiz
    for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
        if file.endswith(".png") or file.endswith(".jpg") or file.endswith(".gif") or file.endswith(".PNG") or file.endswith(".webp") :  # 파일 확장자가 사진 파일이라면
            question = file  # 기존 파일명
            print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {question}\n") #정답 표시
            if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
                gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
                roundChecker = gameData._roundIndex  # 현재 라운드 저장

                imageName = quizPath + "/" + question #이미지 파일 경로, 초기화

                await gameData._chatChannel.send(file=discord.File(imageName)) #이미지 표시
                await asyncio.sleep(1) #사진 업로드 대기시간

                #사진 표시 끝난후
                await countdown(gameData) 
                while voice.is_playing():  # 재생중이면, 즉, 카운트 다운 대기
                    await asyncio.sleep(0.3) #0.3초 대기 후 다시 체크

                #카운트 다운 끝난 후

                await checkGameStop(gameData)
                if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER:  # 아직도 정답대기중이면
                    await showAnswer(roundChecker, gameData)  # 정답 공개!(객관식용)
                    return
                break  # for 빠지기



async def quiz_ox(gameData):  # 재귀 사용, OX퀴즈
    await clear(gameData._chatChannel)
    gameData._roundIndex += 1

    if gameData._roundIndex == gameData._maxRound:  # 더이상문제가없다면
        await finishGame(gameData)  # 게임 끝내기
        return

    voice = get(bot.voice_clients, guild=gameData._guild)  # 봇의 음성 객체 얻기

    questionEmbed = discord.Embed(title=str(gameData._roundIndex+1)+"번째 문제입니다.",
                          url="", description="\n▽", color=discord.Color.blue())

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        questionEmbed.add_field(
            name=player, value=" [ "+str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    questionEmbed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    await gameData._chatChannel.send(embed=questionEmbed)
    await playBGM(voice, BGM_TYPE.ROUND_ALARM)
    await asyncio.sleep(2)
    oxQuiz = gameData._textQuizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
    gameData._nowQuiz = oxQuiz._answer  # 퀴즈 정답 등록

    gameData._selectList.append(emojiOXList[0]) # 보기에 넣기  
    gameData._selectList.append(emojiOXList[1]) 

    if oxQuiz._answer == "O":
        gameData._selectionAnswer = 0 #정답 번호 등록
    else:
        gameData._selectionAnswer = 1
        
    gameData._selectPlayerMap.clear() #선택한 정답 맵 클리어

    questionText = oxQuiz._questionText #문제 str

    selectionEmbed = discord.Embed(title="---------- [ 문제 ] ----------",
                          url="", description=questionText, color=discord.Color.blue())

    questionMsg = await gameData._chatChannel.send(embed=selectionEmbed) #문제 보내기
    gameData._oxQuizObject = oxQuiz
    print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {gameData._nowQuiz}\n") #정답 표시
    await playBGM(voice, BGM_TYPE.BELL)
                    
    try: #메세지 객체 없어질수도있으니 try
        emoji = emojiOXList[0] #이모지 가져오기,
        await questionMsg.add_reaction(emoji=emoji) #이모지 추가,
        emoji = emojiOXList[1] #이모지 가져오기,
        await questionMsg.add_reaction(emoji=emoji) #
    except:
        print("No message object error, playbar")

    await asyncio.sleep(1.0) #1.5초 대기 후 다시 체크

    gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
    roundChecker = gameData._roundIndex  # 현재 라운드 저장

    await longCountdown(gameData) 
    while voice.is_playing():  # 재생중이면, 즉, 카운트 다운 대기
        await asyncio.sleep(0.3) #0.3초 대기 후 다시 체크

    #카운트 다운 끝난 후

    await checkGameStop(gameData)
    if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER:  # 사실상 그냥 올 수 있는 부분
        await showAnswer_ox(roundChecker, gameData)  # 정답 공개!(객관식용)
        return


async def quiz_qna(gameData):  # 재귀 사용, 텍스트퀴즈
    await clear(gameData._chatChannel)
    gameData._roundIndex += 1

    if gameData._roundIndex == gameData._maxRound:  # 더이상문제가없다면
        await finishGame(gameData)  # 게임 끝내기
        return

    voice = get(bot.voice_clients, guild=gameData._guild)  # 봇의 음성 객체 얻기

    questionEmbed = discord.Embed(title=str(gameData._roundIndex+1)+"번째 문제입니다.",
                          url="", description="\n▽", color=discord.Color.blue())

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        questionEmbed.add_field(
            name=player, value=" [ "+str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    questionEmbed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    await gameData._chatChannel.send(embed=questionEmbed)
    await playBGM(voice, BGM_TYPE.ROUND_ALARM)
    await asyncio.sleep(2)
    textQuiz = gameData._textQuizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
    gameData._nowQuiz = textQuiz._answer  # 퀴즈 정답 등록

    answer = []  # 빈 리스트 선언

    title = gameData._nowQuiz.split("&^")[0] #먼저 제목만 뽑기

    fullAnswer = title.split("&#")  # 지정한 특수문자로 split하여 여러 제목 가져오기
    for tmpStr in fullAnswer:  # 추가
        answer.append(tmpStr)  # 정답에 추가

    for tmpStr in fullAnswer:
        tmpA = tmpStr.split(" ")  # 공백으로 split
        answer2 = ""
        for tmpStr in tmpA:
            if len(tmpStr) >= 1: #어떤 문자든 있다면
                answer2 += tmpStr[0]  # 첫글자만 추가
        if len(answer2) >= 2:  # 문자열 길이가 2보다 같거나 클때
            answer.append(answer2)  # 정답 목록에 추가

    gameData._answerList = answer  # 정답 목록 설정

    questionText = textQuiz._questionText #문제 str

    print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {gameData._nowQuiz}\n") #정답 표시
    selectionEmbed = discord.Embed(title="---------- [ 문제 ] ----------",
                          url="", description=questionText, color=discord.Color.blue())

    questionMsg = await gameData._chatChannel.send(embed=selectionEmbed) #문제 보내기
    gameData._textQuizObject = textQuiz
    await playBGM(voice, BGM_TYPE.BELL)

    gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
    roundChecker = gameData._roundIndex  # 현재 라운드 저장

    await asyncio.sleep(1.5)
    await longCountdown(gameData) 
    while voice.is_playing():  # 재생중이면, 즉, 카운트 다운 대기
        await asyncio.sleep(0.3) #0.3초 대기 후 다시 체크

    #카운트 다운 끝난 후

    await checkGameStop(gameData)
    if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER:  # 사실상 그냥 올 수 있는 부분
        await showAnswer(roundChecker, gameData)  # 정답 공개!(객관식용)
        return

async def quiz_fastqna(gameData):  # 재귀 사용, 텍스트퀴즈, 타이머 짧음

    await clear(gameData._chatChannel)
    gameData._roundIndex += 1

    if gameData._roundIndex == gameData._maxRound:  # 더이상문제가없다면
        await finishGame(gameData)  # 게임 끝내기
        return

    voice = get(bot.voice_clients, guild=gameData._guild)  # 봇의 음성 객체 얻기

    questionEmbed = discord.Embed(title=str(gameData._roundIndex+1)+"번째 문제입니다.",
                          url="", description="\n▽", color=discord.Color.blue())

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        questionEmbed.add_field(
            name=player, value=" [ "+str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    questionEmbed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")


    await gameData._chatChannel.send(embed=questionEmbed)
    await playBGM(voice, BGM_TYPE.ROUND_ALARM)
    await asyncio.sleep(2)
    textQuiz = gameData._textQuizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
    gameData._nowQuiz = textQuiz._answer  # 퀴즈 정답 등록

    answer = []  # 빈 리스트 선언

    title = gameData._nowQuiz.split("&^")[0] #먼저 제목만 뽑기

    fullAnswer = title.split("&#")  # 지정한 특수문자로 split하여 여러 제목 가져오기
    for tmpStr in fullAnswer:  # 추가
        answer.append(tmpStr)  # 정답에 추가

    for tmpStr in fullAnswer:
        tmpA = tmpStr.split(" ")  # 공백으로 split
        answer2 = ""
        for tmpStr in tmpA:
            if len(tmpStr) >= 1: #어떤 문자든 있다면
                answer2 += tmpStr[0]  # 첫글자만 추가
        if len(answer2) >= 2:  # 문자열 길이가 2보다 같거나 클때
            answer.append(answer2)  # 정답 목록에 추가

    gameData._answerList = answer  # 정답 목록 설정

    questionText = textQuiz._questionText #문제 str

    print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {gameData._nowQuiz}\n") #정답 표시
    selectionEmbed = discord.Embed(title="---------- [ 문제 ] ----------",
                          url="", description=questionText, color=discord.Color.blue())

    questionMsg = await gameData._chatChannel.send(embed=selectionEmbed) #문제 보내기
    gameData._textQuizObject = textQuiz
    await playBGM(voice, BGM_TYPE.BELL)

    gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
    roundChecker = gameData._roundIndex  # 현재 라운드 저장

    await asyncio.sleep(1.5)
    await countdown(gameData) 
    while voice.is_playing():  # 재생중이면, 즉, 카운트 다운 대기
        await asyncio.sleep(0.3) #0.3초 대기 후 다시 체크

    #카운트 다운 끝난 후

    await checkGameStop(gameData)
    if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER:  # 사실상 그냥 올 수 있는 부분
        await showAnswer(roundChecker, gameData)  # 정답 공개!(객관식용)
        return


async def quiz_intro(gameData):  # 재귀 사용, 인트로 퀴즈용
    await clear(gameData._chatChannel)
    gameData._roundIndex += 1

    if gameData._roundIndex == gameData._maxRound:  # 더이상문제가없다면
        await finishGame(gameData)  # 게임 끝내기
        return

    voice = get(bot.voice_clients, guild=gameData._guild)  # 봇의 음성 객체 얻기

    questionEmbed = discord.Embed(title=str(gameData._roundIndex+1)+"번째 문제입니다.",
                          url="", description="\n▽", color=discord.Color.blue())

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        questionEmbed.add_field(
            name=player, value=" [ "+str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    questionEmbed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    await gameData._chatChannel.send(embed=questionEmbed)
    await playBGM(voice, BGM_TYPE.ROUND_ALARM)
    await asyncio.sleep(2)
    quiz = gameData._quizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
    gameData._nowQuiz = quiz  # 퀴즈 정답 등록
    answer = []  # 빈 리스트 선언

    title = gameData._nowQuiz.split("&^")[0] #먼저 제목만 뽑기

    fullAnswer = title.split("&#")  # 지정한 특수문자로 split하여 여러 제목 가져오기
    for tmpStr in fullAnswer:  # 추가
        answer.append(tmpStr)  # 정답에 추가

    for tmpStr in fullAnswer:
        tmpA = tmpStr.split(" ")  # 공백으로 split
        answer2 = ""
        for tmpStr in tmpA:
            if len(tmpStr) >= 1: #어떤 문자든 있다면
                answer2 += tmpStr[0]  # 첫글자만 추가
        if len(answer2) >= 2:  # 문자열 길이가 2보다 클때
            answer.append(answer2)  # 정답 목록에 추가

    gameData._answerList = answer  # 정답 목록 설정
    gameData._thumbnail = None # 썸네일 초기화

    questionFile = None #문제파일
    answerFile = None #정답 공개용 파일
    questionFileName = ""

    print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {str(gameData._nowQuiz)}\n") #정답 표시

    quizPath = BASE_PATH + gameData._gameName + "/" + quiz
    for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
        if file.endswith(".png") or file.endswith("jpg"): #사진파일이라면 ,썸네일임
            gameData._thumbnail = quizPath + "/" + file #썸네일 지정해주고
        elif file.startswith("q"):  # q로 시작하는게 문제파일
            questionFile = quizPath + "/" + file  # 문제 설정
            questionFileName = file
        elif file.startswith("a"): #a로 시작하는게 정답파일
            answerFile = quizPath + "/" + file  # 정답 설정
            
    if questionFile == None or answerFile == None: #파일이 온전하지 않다면
        nextRound(gameData) #다음 문제
    else: #파일이 온전하면
        if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
            gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
            roundChecker = gameData._roundIndex  # 현재 라운드 저장

            audioName = questionFile #실제 실행할 음악파일 경로, 초기화
            gameData._answerAuido = answerFile #정답 오디오 설정

            audioLength = 39 #초기화 ,기본 39

            if questionFileName.endswith(".wav"): #확장자 wav 일때
                f = sf.SoundFile(audioName) #오디오 파일 로드
                audioLength = len(f) / f.samplerate #오디오 길이
                f.close()
            elif questionFileName.endswith(".mp3"): #확장자 mp3일때, 1분이상곡은 자르기 옵션 제공 ㅎㅎ
                audio = MP3(audioName) 
                audio_info = audio.info
                length_in_secs = int(audio_info.length) #음악 총 길이
                if length_in_secs > 80: #음악이 80초 초과할 시, 자르기 시작
                    song = AudioSegment.from_mp3( audioName ) #오디오 자르기 가져오기
                    startTime = random.randrange(20, (length_in_secs-19-39)) #자르기 시작 시간 5 ~ 끝-19-(노래길이)
                    endTime = startTime + 39 #39초만큼 자를거라

                    #print(str(startTime) + " ~ " + str(endTime))

                    startTime *= 1000 #s 를 ms로
                    endTime *= 1000 #s를 ms로

                    extract = song[startTime:endTime]
                        
                    audioName = TMP_PATH + "/" + str(gameData._guild.id) + ".mp3" #실제 실행할 음악파일 임시파일로 변경

                    extract.export(audioName) #임시 저장
                else:
                    audioLength = length_in_secs
                
            repartCnt = gameData._repeatCount #반복횟수

            while repartCnt > 0: #반복횟수만큼 반복
                repartCnt -= 1

                playSec = 0 #현재 재생한 초

                playBarEmbed = discord.Embed(title="음악 재생 현황", url="", description="\n", color=discord.Color.blue()) #재생바
                playBarMessage = await gameData._chatChannel.send(embed=playBarEmbed)
                voice.play(discord.FFmpegPCMAudio(audioName))  # 재생
                 
                #인트로 퀴즈는 페이드인 없음

                timeChecker = 0
                while voice.is_playing():  # 재생중이면
                    timeChecker += 1
                    if(timeChecker % 2 != 0): continue #.5초 간격은 패스
                    if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                        return #리턴
                    await asyncio.sleep(1)  # 1초후 다시 확인
                    playSec += 1 #재생 1초 +
                    notPlayed = (audioLength-1) - playSec #남은 길이
                    index = 0
                    showStr = "" #표시할 바

                    while index < playSec:
                        index += 1
                        showStr += "■"
                        
                    index = 0
                    while index < notPlayed:
                        index += 1
                        showStr += "□"

                    playBarEmbed = discord.Embed(title="음악 재생 현황", url="", description=showStr+"\n", color=discord.Color.blue()) #재생바
                    try: #메세지 객체 없어질수도있으니 try
                        await playBarMessage.edit(embed=playBarEmbed)# 재생 끝날때까지 반복
                    except:
                        print("No message object error, playbar")

                    # if notPlayed < 0: 
                    #     voice.stop()
                    #     break # 재생시간 초과면 break

            #재생이 끝난 후
            if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
                return

            if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER: #아직도 정답자 기다리는 중이면
                await countdown(gameData)

            #카운트 다운 끝난 후
                            
            if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
                return
            await checkGameStop(gameData)
            if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER:  # 아직도 정답자 없다면
                await showAnswer(roundChecker, gameData)  # 정답 공개!
                return


async def quiz_tts(gameData):  # 재귀 사용, tts 퀴즈용
    await clear(gameData._chatChannel)
    gameData._roundIndex += 1

    if gameData._roundIndex == gameData._maxRound:  # 더이상문제가없다면
        await finishGame(gameData)  # 게임 끝내기
        return

    voice = get(bot.voice_clients, guild=gameData._guild)  # 봇의 음성 객체 얻기

    questionEmbed = discord.Embed(title=str(gameData._roundIndex+1)+"번째 문제입니다.",
                          url="", description="\n▽", color=discord.Color.blue())

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        questionEmbed.add_field(
            name=player, value=" [ "+str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    questionEmbed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    await gameData._chatChannel.send(embed=questionEmbed)
    await playBGM(voice, BGM_TYPE.ROUND_ALARM)
    await asyncio.sleep(2)
    quiz = gameData._quizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
    gameData._nowQuiz = quiz  # 퀴즈 정답 등록
    answer = []  # 빈 리스트 선언

    title = gameData._nowQuiz #먼저 전체 답 뽑기

    fullAnswer = title.split("&#")  # 지정한 특수문자로 split하여 여러 답 가져오기
    for tmpStr in fullAnswer:  # 추가
        answer.append(tmpStr)  # 정답에 추가

    for tmpStr in fullAnswer:
        tmpA = tmpStr.split(" ")  # 공백으로 split
        answer2 = ""
        for tmpStr in tmpA:
            if len(tmpStr) >= 1: #어떤 문자든 있다면
                answer2 += tmpStr[0]  # 첫글자만 추가
        if len(answer2) >= 2:  # 문자열 길이가 2보다 같거나 클때
            answer.append(answer2)  # 정답 목록에 추가

    gameData._answerList = answer  # 정답 목록 설정

    quizPath = BASE_PATH + gameData._gameName + "/" + quiz
    for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
        if file.endswith(".wav"):  # 파일 확장자가 .mp3면, 문제 파일일거임
            question = file  # 기존 파일명
            print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {question}\n") #정답 표시
            if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
                gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
                roundChecker = gameData._roundIndex  # 현재 라운드 저장

                f = sf.SoundFile(quizPath + "/" + question) #오디오 파일 로드
                audioLength = len(f) / f.samplerate #오디오 길이
                f.close()

                repartCnt = gameData._repeatCount #반복횟수

                while repartCnt > 0: #반복횟수만큼 반복
                    repartCnt -= 1

                    playSec = 0 #현재 재생한 초

                    playBarEmbed = discord.Embed(title="대사", url="", description="\n", color=discord.Color.blue()) #재생바
                    playBarMessage = await gameData._chatChannel.send(embed=playBarEmbed)
                    voice.play(discord.FFmpegPCMAudio(quizPath + "/" + question))  # 재생
                    voice.source = discord.PCMVolumeTransformer(voice.source)
                    volume = 1.0 # 초기볼륨
                    voice.source.volume = volume


                    while voice.is_playing():  # 재생중이면
                        if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                            voice.stop()
                            return #리턴
                        await asyncio.sleep(1)  # 1초후 다시 확인
                        playSec += 1 #재생 1초 +
                        notPlayed = (audioLength - 3) - playSec #남은 길이, -14하는 이유는 초기에 7초만큼 페이드인하느라 시간씀, 연산 레깅
                        index = 0
                        showStr = "" #표시할 바

                        while index < playSec:
                            index += 1
                            showStr += "■"
                        
                        index = 0
                        while index < notPlayed:
                            index += 1
                            showStr += "□"

                        playBarEmbed = discord.Embed(title="대사", url="", description=showStr+"\n", color=discord.Color.blue()) #재생바
                        try: #메세지 객체 없어질수도있으니 try
                            await playBarMessage.edit(embed=playBarEmbed)# 재생 끝날때까지 반복
                        except:
                            print("No message object error, playbar")

                #재생이 끝난 후
                if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER: #아직도 정답자 기다리는 중이면
                    await countdown(gameData)

                #카운트 다운 끝난 후

                if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
                    return
                await checkGameStop(gameData)
                if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER:  # 아직도 정답자 없다면
                    await showAnswer(roundChecker, gameData)  # 정답 공개!
                    return
                break  # for 빠지기



async def finishGame(gameData):
    gameData._gameStep = GAME_STEP.END
    await asyncio.sleep(2)
    await gameData._chatChannel.send("=========== 모든 문제를 풀었습니다. ===========\n점수 계산 중....\n\n\n\n\n\n")
    await gameData._chatChannel.send("▷\n▷\n▷")
    await playBGM(gameData._voice, BGM_TYPE.PLING)

    sortPlayer = []  # 빈 리스트
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    await asyncio.sleep(3)
    await gameData._chatChannel.send("\n\n\n\n\n★★★★★★★★ 순위표 ★★★★★★★★\n")
    await gameData._chatChannel.send("▷")
    await playBGM(gameData._voice, BGM_TYPE.ROUND_ALARM)
    await asyncio.sleep(2)
    
    leftList = ""
    sIndex = 0
    for player in sortPlayer: #정렬된 플레이어표시
        playerView = str(player) + " : [ "+ str(gameData._scoreMap[player]) +"점 ]"  #표시할 텍스트
        if sIndex < 3: #3위까지는 천천히 보여줌
            sIndex += 1
            if sIndex == 1: #1등은 특별하게
                playerView = "🥇" + playerView + "  👈  " + "최고의 " + str(gameData._topNickname) 
            elif sIndex == 2:
                playerView = "🥈" + playerView
            elif sIndex == 3:
                playerView = "🥉" + playerView
            playerView = playerView + "\n"
            await playBGM(gameData._voice, BGM_TYPE.SCORE_ALARM)
            await gameData._chatChannel.send(playerView)
            await asyncio.sleep(2)
        else:
            leftList += "▶ "+ playerView + "\n"

    if(leftList != ""): #left 리스트에 뭐라도 있으면
        await playBGM(gameData._voice, BGM_TYPE.SCORE_ALARM)
        await gameData._chatChannel.send(leftList) #나머지 점수 발표 
        await asyncio.sleep(4)

    await gameData._chatChannel.send(gameData._gameName+" 퀴즈가 종료됐습니다.")
    await playBGM(gameData._voice, BGM_TYPE.ENDING)
    await asyncio.sleep(2)
    await gameData._voice.disconnect()
    del dataMap[gameData._guild] #데이터삭제


async def showAnswer(roundChecker, gameData):
    if gameData._gameStep == GAME_STEP.WAIT_FOR_NEXT:  # 이미 정답 맞춘 상태면
        if not gameData._isSkiped: # 그리고 스킵상태도 아니면
            return  # 리턴

    if(roundChecker != gameData._roundIndex):  # 현재 라운드와 이 함수를 호출한 play 함수의 라운드가 같지 않다면
        return
    gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT
    #await asyncio.sleep(0.5)

    author = ""
    tmpSp = gameData._nowQuiz.split("&^")
    if len(tmpSp) == 2: #만약 작곡자가 적혀있다면
        author = tmpSp[1] #작곡자 저장

    answerStr = "" #정답 공개용 문자열
    for tmpStr in gameData._answerList:
        answerStr += tmpStr + "\n" #정답 문자열 생성

    if author == "": #작곡자 적혀있지 않으면 그냥 공개
        embed = discord.Embed(title="정답 공개", url=None,
                          description=str(answerStr)+"\n▽", color=discord.Color.blue()) #정답 공개
    else: #작곡자 적혀있으면 공개
        embed = discord.Embed(title="정답 공개", url=None,
                          description=str(answerStr)+"\n( "+str(author)+" )\n▽", color=discord.Color.blue()) #저자까지 정답 공개
    sortPlayer = []  # 빈 리스트
    
    for player in gameData._scoreMap:  # 정렬
        index = 0  # 인덱스
        score = gameData._scoreMap[player]  # 점수
        while index < len(sortPlayer):
            cp = sortPlayer[index]  # 비교대상
            cp_score = gameData._scoreMap[cp]  # 비교대상 점수
            if score > cp_score:  # 비교대상보다 점수높으면
                break  # while 빠져나가기
            index += 1  # 다음 대상으로

        sortPlayer.insert(index, player)  # 삽입 장소에 추가

    for player in sortPlayer:
        embed.add_field(
            name=player, value="[ " + str(gameData._scoreMap[player]) + "점 ]", inline=True)  # 필드로 추가

    embed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    thumbnailFile = None #썸네일 설정
    if gameData._thumbnail != None:
        thumbnailFile = discord.File(str(gameData._thumbnail), filename="quizThumbnail.png")

    voice = gameData._voice
    if gameData._gameType == GAME_TYPE.INTRO: #인트로 퀴즈라면 성공 노래 틀어줌
        voice.stop() #즉각 보이스 스탑
        voice.play(discord.FFmpegPCMAudio(gameData._answerAuido))  # 정답 재생
        await fadeIn(voice) #페이드인

        if thumbnailFile == None:
            await gameData._chatChannel.send(embed=embed)
        else:
            embed.set_image(url="attachment://quizThumbnail.png")
            await gameData._chatChannel.send(file=thumbnailFile, embed=embed) #음악 재생하면서 메시지 보내라는 뜻에서 여기에 넣음

        while voice.is_playing():  # 카운트다운중이면
            if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                voice.stop() #카운트다운 정지
            await asyncio.sleep(0.5)  # 0.5초후 다시 확인
    else:
        await playBGM(voice, BGM_TYPE.FAIL)
        if thumbnailFile == None:
            await gameData._chatChannel.send(embed=embed)
        else:
            embed.set_image(url="attachment://quizThumbnail.png")
            await gameData._chatChannel.send(file=thumbnailFile, embed=embed)
            
        await asyncio.sleep(2.5)

    if(gameData._roundIndex+1 < gameData._maxRound):  # 이 문제가 마지막 문제가 아니었다면
        embed = discord.Embed(title="다음 라운드로 진행됩니다.", url=None,
                              description="", color=discord.Color.blue())
        await gameData._chatChannel.send(embed=embed)
        await playBGM(gameData._voice, BGM_TYPE.PLING)
        await asyncio.sleep(2)
    await nextRound(gameData)


async def showAnswer_select(roundChecker, gameData):
    if gameData._gameStep == GAME_STEP.WAIT_FOR_NEXT:  # 이미 정답 맞춘 상태면
        if not gameData._isSkiped: # 그리고 스킵상태도 아니면
            return  # 리턴

    if(roundChecker != gameData._roundIndex):  # 현재 라운드와 이 함수를 호출한 play 함수의 라운드가 같지 않다면
        return
    gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT
    #await asyncio.sleep(0.5)

    answerIndex = str(gameData._selectionAnswer) #정답 번호

    embed = discord.Embed(title="정답 공개", url=None,
                          description="[ "+ answerIndex + "번 ]. " + str(gameData._selectList[gameData._selectionAnswer]) +"\n▽", color=discord.Color.blue()) #정답 공개

    isAnswerPlayer = False #정답자 존재하는가?
    for player in gameData._selectPlayerMap:
        if str(gameData._selectPlayerMap[player]) == answerIndex: #플레이어가 선택한 답과 정답이 일치하면          
            isAnswerPlayer = True #정답자 존재!
            embed.add_field(
                name=player, value="[ 정답! ]", inline=True)  # 필드로 추가
            if player in gameData._scoreMap:  # 점수 리스트에 정답자 있는지 확인
                gameData._scoreMap[player] += 1  # 있으면 1점 추가
            else:
                gameData._scoreMap[player] = 1  # 없으면 새로 1점 추가
    
    if isAnswerPlayer == False: #정답자 없다면
        embed.add_field(
                name="정답자 없음", value="...", inline=True)  # 필드로 추가
        await playBGM(gameData._voice, BGM_TYPE.FAIL)
    else: #정답자 있다면
        await playBGM(gameData._voice, BGM_TYPE.SUCCESS) #성공 효과음

    embed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    await gameData._chatChannel.send(embed=embed)
    await asyncio.sleep(3)

    if(gameData._roundIndex+1 < gameData._maxRound):  # 이 문제가 마지막 문제가 아니었다면
        embed = discord.Embed(title="다음 라운드로 진행됩니다.", url=None,
                              description="", color=discord.Color.blue())
        await gameData._chatChannel.send(embed=embed)
        await playBGM(gameData._voice, BGM_TYPE.PLING)
        await asyncio.sleep(2)
    await nextRound(gameData)


async def showAnswer_ox(roundChecker, gameData): #ox 퀴즈 정답 공개용
    if gameData._gameStep == GAME_STEP.WAIT_FOR_NEXT:  # 이미 정답 맞춘 상태면
        if not gameData._isSkiped: # 그리고 스킵상태도 아니면
            return  # 리턴

    if(roundChecker != gameData._roundIndex):  # 현재 라운드와 이 함수를 호출한 play 함수의 라운드가 같지 않다면
        return
    gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT
    #await asyncio.sleep(0.5)

    answerIndex = str(gameData._selectionAnswer) #정답 번호
    answerDesc = gameData._oxQuizObject._answerText
    embed = discord.Embed(title="정답 공개", url=None,
                          description="[ "+ str(gameData._selectList[gameData._selectionAnswer]) + " ]\n("+ str(answerDesc) + ")\n▽", color=discord.Color.blue()) #정답 공개

    isAnswerPlayer = False #정답자 존재하는가?
    for player in gameData._selectPlayerMap:
        if str(gameData._selectPlayerMap[player]) == answerIndex: #플레이어가 선택한 답과 정답이 일치하면          
            isAnswerPlayer = True #정답자 존재!
            embed.add_field(
                name=player, value="[ 정답! ]", inline=True)  # 필드로 추가
            if player in gameData._scoreMap:  # 점수 리스트에 정답자 있는지 확인
                gameData._scoreMap[player] += 1  # 있으면 1점 추가
            else:
                gameData._scoreMap[player] = 1  # 없으면 새로 1점 추가
    
    if isAnswerPlayer == False: #정답자 없다면
        embed.add_field(
                name="정답자 없음", value="...", inline=True)  # 필드로 추가
        await playBGM(gameData._voice, BGM_TYPE.FAIL)
    else: #정답자 있다면
        await playBGM(gameData._voice, BGM_TYPE.SUCCESS) #성공 효과음

    embed.set_footer(text="\n남은 문제 수 : " +
                     str(gameData._maxRound - gameData._roundIndex - 1)+"개\n")

    await gameData._chatChannel.send(embed=embed)
    await asyncio.sleep(3)

    if(gameData._roundIndex+1 < gameData._maxRound):  # 이 문제가 마지막 문제가 아니었다면
        embed = discord.Embed(title="다음 라운드로 진행됩니다.", url=None,
                              description="", color=discord.Color.blue())
        await gameData._chatChannel.send(embed=embed)
        await playBGM(gameData._voice, BGM_TYPE.PLING)
        await asyncio.sleep(2)
    await nextRound(gameData)


# 봇이 접속(활성화)하면 아래의 함수를 실행하게 된다, 이벤트
@bot.event
async def on_ready():
    print(f'{bot.user} 활성화됨')
    await bot.change_presence(status=discord.Status.online) #온라인
  #await client.change_presence(status=discord.Status.idle) #자리비움
  #await client.change_presence(status=discord.Status.dnd) #다른용무
  #await client.change_presence(status=discord.Status.offline) #오프라인

    await bot.change_presence(activity=discord.Game(name="!quiz 를 입력하여 게임시작"))
  #await client.change_presence(activity=discord.Streaming(name="스트림 방송중", url='링크'))
  #await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="노래 듣는중"))
  #await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="영상 시청중"))
  
    print("봇 이름:",bot.user.name,"봇 아이디:",bot.user.id,"봇 버전:",discord.__version__)


@bot.command(pass_context=False, aliases=["ping"])  # ping 명령어 입력시
async def pingCommand(ctx):  # ping 테스트
    await ctx.send(f"핑 : {round(bot.latency * 1000)}ms")


@bot.command(pass_context=False, aliases=["quiz"])  # quiz 명령어 입력시
async def quizCommand(ctx, gamesrc=None):  # 퀴즈 시작

    if gamesrc == None:  # !quiz만 입력했으면
        await showQuizCategory(ctx)  # 카테고리목록 보여줌
        return

    gamesrc = gamesrc.upper()
    isExistData = os.path.isdir(BASE_PATH + gamesrc)  # 하려는 퀴즈가 있는지 확인
    if(isExistData == False):  # 없다면
        #카테고리 목록 확인일 수도 있으니 있는지 확인
        if gamesrc in QUIZ_CATEGORI.keys():  # 카테고리 목록에 있다면
            await showQuizList(ctx, gamesrc)  # 카테고리에 속하는 퀴즈목록 표시
        else:  # 카테고리 목록에도 없다면
            await ctx.send(gamesrc + " 퀴즈는 존재하지 않습니다.")
        return

    if ctx.message.author.voice == None:
        await ctx.send("음성 대화채널에 참가한 후 시도하세요.")
        return

    channel = ctx.message.author.voice.channel  # 호출자의 음성 채널 얻기
    chattingChannel = ctx.message.channel  # 호출자의 채팅 채널 얻기

    # bot의 해당 길드에서의 음성 대화용 객체
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
        await ctx.send("이미 퀴즈가 진행되고 있습니다. 먼저 연결을 끊거나 !gamestop 을 입력하여 종료하세요.")
    else:  # 퀴즈 진행중이 아니라면
        voice = await channel.connect()  # 음성 채널 연결후 해당 객체 반환
        tmpQuizData = QUIZ_MAP[gamesrc]
        gameType = tmpQuizData._gameType  # 퀴즈 타입 가져오기
        gameName = gamesrc  # 퀴즈 이름
        gameData = GameData(ctx.guild, chattingChannel,
                                voice, gameName, gameType, ctx.message.author)  # 퀴즈데이터 생성
        gameData._repeatCount = QUIZ_MAP[gamesrc]._repeatCount  # 반복 횟수 설정
        gameData._voice = voice  # voice 객체 설정
        gameData._topNickname = tmpQuizData._topNickname #1등 별명 설정
        dataMap[ctx.guild] = gameData  # 해당 서버의 퀴즈데이터 저장

        await clear(gameData._chatChannel)
        await ctx.send(gamesrc + " 퀴즈를 시작합니다. 데이터 저장중...")
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(2)  # 2초 대기
        await printGameRule(ctx, voice, gameType)
        await asyncio.sleep(2)  # 2초 대기
        await checkGameStop(gameData)
        embed = discord.Embed(title="자! 이제 "+gameData._gameName+" 퀴즈를 시작합니다!",
                                  url=None, description="\n", color=discord.Color.blue())
        await ctx.send(embed=embed)
        await playBGM(voice, BGM_TYPE.PLING)
        await asyncio.sleep(4)  # 2초 대기
        await gameLoop(ctx, gameData)


@bot.command(pass_context=False, aliases=["hint"])  # hint 명령어 입력시
async def hintQuiz(ctx):  # 퀴즈 힌트
        gameData = None #게임 데이터 불러올거임
        for tmpData in dataMap.values(): #모든 게임 데이터에 대해
            if tmpData._roomOwner == ctx.message.author: #스킵 입력한 사람과 게임 데이터의 방장이 동일하면
                gameData = tmpData #게임 데이터 가져오기

        if gameData == None: #게임 데이터를 못찾았다면
            return
        if gameData._gameStep != GAME_STEP.WAIT_FOR_ANSWER and gameData._gameStep != GAME_STEP.WAIT_FOR_NEXT: #정답자 대기중이거나 다음라 대기중이 아니면
            return
        if gameData._useHint == True: #이미 힌트 썻다면
            embed = discord.Embed(title="[     힌트    ]", url=None,
                                description="이미 힌트를 사용했습니다.", color=discord.Color.blue())
            await ctx.send(embed=embed)
            return

        #힌트 표시
        gameData._useHint = True #힌트 사용으로 변경
        answer = gameData._answerList[0] #정답 가져오기
        answer = answer.replace(" ", "") #공백 제거
        answer = answer.upper() #대문자로
        answerLen = len(answer) #문자 길이
        hintLen = (answerLen // 5) + 1 #표시할 힌트 글자수
        hintStr = "" #힌트 문자열

        hintIndex = []
        index = 0

        limit = 0


        while index < hintLen: #인덱스 설정
            limit += 1
            if  limit > 1000: #시도 한계 설정
                break

            rd = random.randrange(0, answerLen)
            if rd in hintIndex: #이미 인덱스에 있다면
                continue
            else:
                hintIndex.append(rd)
                index += 1

        index = 0 
        while index < answerLen:
            if index in hintIndex: #만약 해당 글자가 표시인덱스에 있다면
                hintStr += answer[index] #해당 글자는 표시하기
            else:
                hintStr += "○"
            index += 1

        embed = discord.Embed(title="[     힌트    ]", url=None,
                                description="퀴즈 주최자 "+ str(gameData._roomOwner) + "님께서 힌트를 요청했습니다.\n글자 힌트: "+hintStr, color=discord.Color.blue())
        await ctx.send(embed=embed)


@bot.command(pass_context=False, aliases=["skip"])  # skip 명령어 입력시
async def skipQuiz(ctx):  # 퀴즈 스킵
        gameData = None #게임 데이터 불러올거임
        for tmpData in dataMap.values(): #모든 게임 데이터에 대해
            if tmpData._roomOwner == ctx.message.author: #스킵 입력한 사람과 게임 데이터의 방장이 동일하면
                gameData = tmpData #게임 데이터 가져오기

        if gameData == None: #게임 데이터를 못찾았다면
            return
        if gameData._gameStep != GAME_STEP.WAIT_FOR_ANSWER and gameData._gameStep != GAME_STEP.WAIT_FOR_NEXT: #정답자 대기중이거나 다음라 대기중이 아니면
            return
        if gameData._isSkiped: #이미 스킵중이면
            return

        if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER: #정답 못 맞추고 스킵이면
            gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT  # 다음 라운드 대기로 변경
            gameData._isSkiped = True #스킵중 표시

            embed = discord.Embed(title="[     스킵     ]", url=None,
                                description="퀴즈 주최자 "+ str(gameData._roomOwner) + "님께서 문제를 건너뛰기 했습니다.", color=discord.Color.blue())
            await ctx.send(embed=embed)

            voice = gameData._voice
            roundChecker = gameData._roundIndex  # 스킵한 라운드 저장
            voice.source = discord.PCMVolumeTransformer(voice.source)
                    
            waitCount = 3 #3초 대기할거임
            while voice.is_playing(): #재생중이면
                waitCount -= 1
                await asyncio.sleep(1)  # 1초 대기
                if waitCount <= 0: #3초 대기했다면
                    break #대기 탈출

            if(roundChecker == gameData._roundIndex):  # 스킵한 라운드와 현재 라운드 일치시
                await fadeOut(voice)
                await showAnswer(roundChecker, gameData) #정답 공개

        elif gameData._gameStep == GAME_STEP.WAIT_FOR_NEXT: #정답 맞추고 스킵이면
            return #못하게 막기 버그가있어...
            embed = discord.Embed(title="[     스킵     ]", url=None,
                                description="퀴즈 주최자 "+ str(gameData._roomOwner) + "님께서 스킵하였습니다.", color=discord.Color.blue())
            await ctx.send(embed=embed)

            voice = gameData._voice
            roundChecker = gameData._roundIndex  # 스킵한 라운드 저장
            voice.source = discord.PCMVolumeTransformer(voice.source)

            waitCount = 3 #3초 대기할거임
            while voice.is_playing(): #재생중이면
                waitCount -= 1
                await asyncio.sleep(1)  # 1초 대기
                if waitCount <= 0: #3초 대기했다면
                    break #대기 탈출

            if(roundChecker == gameData._roundIndex):  # 스킵한 라운드와 현재 라운드 일치시
                await fadeOut(voice) #페이드 아웃
                if gameData._isSkiped: #아직도 스킵 상태면(다른곳에서 nextround 호출할 시 false 일거임)
                    await nextRound(gameData) #다음라운드로


@bot.command(pass_context=False, aliases=["gamestop"])  # gamestop 명령어 입력시
async def stopQuiz(ctx):  # 퀴즈 스탑
    gameData = None #게임 데이터 불러올거임
    for tmpData in dataMap.values(): #모든 게임 데이터에 대해
        if tmpData._roomOwner == ctx.message.author: #스킵 입력한 사람과 게임 데이터의 방장이 동일하면
            gameData = tmpData #게임 데이터 가져오기

    if gameData == None: #게임 데이터를 못찾았다면
        stopEmbed = discord.Embed(title="[     경고     ]", url=None,
            description="퀴즈 주최자만이 게임을 중지할 수 있습니다.", color=discord.Color.blue())
        await ctx.send(embed = stopEmbed)
        return


    await gameData._voice.disconnect()
    del dataMap[gameData._guild] #데이터삭제
            

    embed = discord.Embed(title="[     중지     ]", url=None, description="퀴즈 주최자 "+ str(gameData._roomOwner) + "님께서 게임을 중지했습니다.", color=discord.Color.blue())
    await ctx.send(embed=embed)
       

@bot.event
async def on_message(message):
    # 봇이 입력한 메시지라면 무시하고 넘어간다.
    if message.author == bot.user:
        #print("m - self")
        return
    elif message.content.startswith(BOT_PREFIX):  # 명령어면 return
        #print("m - its command")
        await bot.process_commands(message)
        return
    elif message.guild not in dataMap:  # 게임 데이터 없으면 건너뛰기
        #print("m - no gamedata")
        return
    else:
        gameData = dataMap[message.guild]  # 데이터 맵에서 해당 길드의 게임 데이터 가져오기
        if(gameData == None):  # 게임데이터가 없거나 정답 대기중이 아니면 return
            return
        if message.channel != gameData._chatChannel: #채팅 채널이 게임데이터에 저장된 채팅채널과 일치하지 않으면
            return #건너뛰어
        if(gameData._gameStep == GAME_STEP.START or gameData._gameStep == GAME_STEP.END):  # 룰 설명중, 엔딩중이면
            await message.delete()
            return
        if(gameData._gameStep != GAME_STEP.WAIT_FOR_ANSWER):
            return
        if(gameData._gameType == GAME_TYPE.SELECT or gameData._gameType == GAME_TYPE.OX or gameData._gameType == GAME_TYPE.GLOWLING): #객관식 진행중이면
            if(gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER): #문제 풀기 시간이면
                await message.delete()
                return

        inputAnswer = message.content.replace(" ", "")
        inputAnswer = inputAnswer.upper() #대문자로 변경
        for answer in gameData._answerList:
            #print(answer)      
            answer = answer.replace(" ", "")  # 공백 제거
            answer = answer.upper() # 비교를 위해 대문자로
            if answer == inputAnswer:  # 정답과 입력값 비교
                gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT  # 다음 라운드 대기로 변경

                await addScore(message, gameData)  # 메세지 보낸사람 1점 획득

                # await message.channel.send(message.author.name + " 님께서 정답을 맞추셨습니다!")
                voice = get(bot.voice_clients, guild=message.guild)  # 봇의 음성 객체 얻기
                roundChecker = gameData._roundIndex  # 정답 맞춘 라운드 저장
                voice.source = discord.PCMVolumeTransformer(voice.source)
                
                if gameData._gameType == GAME_TYPE.PICTURE or gameData._gameType == GAME_TYPE.QNA or gameData._gameType == GAME_TYPE.FAST_QNA or gameData._gameType == GAME_TYPE.SCRIPT: #사진퀴즈, 텍스트,. 대사 퀴즈라면
                    voice.stop() #즉각 보이스 스탑
                    await playBGM(voice, BGM_TYPE.SUCCESS) #성공 효과음
                    await asyncio.sleep(2.5)  # 2초 대기
                elif gameData._gameType == GAME_TYPE.INTRO:
                    voice.stop() #즉각 보이스 스탑
                    #await playBGM(voice, BGM_TYPE.SUCCESS) #성공 효과음
                    #await asyncio.sleep(2)  # 2초 대기
                    try:
                        voice.play(discord.FFmpegPCMAudio(gameData._answerAuido))  # 정답 재생
                        await fadeIn(voice) #페이드인
                        while voice.is_playing():  # 카운트다운중이면
                            if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                                voice.stop() #카운트다운 정지
                            await asyncio.sleep(0.5)  # 0.5초후 다시 확인
                    except:
                        print("오디오 이미 실행")
                else: #그 외의 퀴즈면
                    waitCount = 11 #11초 대기할거임
                    while voice.is_playing(): #재생중이면
                        waitCount -= 1
                        await asyncio.sleep(1)  # 1초 대기
                        if waitCount <= 0: #11초 대기했다면
                            break #대기 탈출

                if(roundChecker == gameData._roundIndex):  # 정답 맞춘 라운드와 현재 라운드 일치시
                        await fadeOut(gameData._voice)
                        await nextRound(gameData)  # 다음 라운드
                return  # 정답시 리턴

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user: #봇이 입력한거면
        return #건너뛰어

    channel = reaction.message.channel #반응 추가한 채널

    for gameData in dataMap.values(): #모든 게임 데이터에 대해
        if gameData._chatChannel == channel: #게임 중인 채널이면
            if gameData._gameType == GAME_TYPE.SELECT or gameData._gameType == GAME_TYPE.GLOWLING: #객관식 퀴즈 진행중이면
                emoji = reaction.emoji # 반응한 이모지 가져오기
                #isInSelectEmoji = False #반응한 이모지가 선택용 이모지인지 확인하기

                index = 0

                while index < len(emojiNumberList):
                    if emojiNumberList[index] == emoji:
                        gameData._selectPlayerMap[user.name] = index #선택한 번호 저장하기
                        break
                    index += 1
                try:
                    await reaction.remove(user) #이모지 삭제
                except:
                    return
            elif gameData._gameType == GAME_TYPE.OX: #ox퀴즈의 경우
                emoji = reaction.emoji # 반응한 이모지 가져오기

                index = 0

                while index < len(emojiOXList):
                    if emojiOXList[index] == emoji:
                        gameData._selectPlayerMap[user.name] = index #선택한 번호 저장하기
                        break
                    index += 1

                try:
                    await reaction.remove(user) #이모지 삭제
                except:
                    return
            break #더이상 다음 게임 데이터를 찾을 이유가 없음

@bot.event
async def on_reaction_remove(reaction, user):
    if user == bot.user: #봇이 삭제한거면
        return #건너뛰어

    channel = reaction.message.channel #반응 삭제한 채널

    for gameData in dataMap.values(): #모든 게임 데이터에 대해
        if gameData._chatChannel == channel: #게임 중인 채널이면
            if gameData._gameType == GAME_TYPE.SELECT or gameData._gameType == GAME_TYPE.GLOWLING: #객관식 퀴즈 진행중이면
                emoji = reaction.emoji # 반응한 이모지 가져오기
                await reaction.message.add_reaction(emoji=emoji) #다시 추가...
                         
                
##

bot.run(TOKEN)  # 봇 실행

#연습용, 유튜브 다운용

# @bot.command(pass_context=False, aliases=["myj"]) #j 또는 joi 입력 시
# async def join(ctx):
#     global voice #음성 대화용 객체
#     channel = ctx.message.author.voice.channel # 호출자의 음성 채널 얻기
#     voice = get(bot.voice_clients, guild=ctx.guild) #bot의 음성 대화용 객체

#     if voice and voice.is_connected(): #음성 대화용 객체가 존재하며 현재 음성 대화용 객체가 연결된 상태라면(이미 다른 음성채널에 있다면)
#         await voice.move_to(channel) #호출자가 있는 음성 채널로 이동
#     else: # 음성 대화용 객체가 비연결 상태라면
#         voice = await channel.connect() #음성 채널 연결후 해당 음성 대화용 객체 반환
#     #위의 과정은 사실상 어떻게든 voice 객체를 얻는 과정

#     await voice.disconnect() #음성 대화용 객체 연결 끊기(음성채널 나가기)
#     #오류 방지

#     if voice and voice.is_connected(): #음성 대화용 객체가 존재하며 현재 음성 대화용 객체가 연결된 상태라면(이미 다른 음성채널에 있다면)
#         await voice.move_to(channel) #호출자가 있는 음성 채널로 이동
#     else: # 음성 대화용 객체가 비연결 상태라면(disconnect 했으니깐 비연결이여야지)
#         voice = await channel.connect() #음성 채널 연결후 해당 음성 대화용 객체 반환
#         print(f"The bot has connected to {channel}\n") #이게 정상

#     await ctx.send(f"Joined {channel}")


# @bot.command(pass_context=False, aliases=["myl"])
# async def leave(ctx):
#     channel = ctx.message.author.voice.channel # 호출자의 음성 채널 얻기
#     voice = get(bot.voice_clients, guild=ctx.guild) #bot의 음성 대화용 객체

#     if voice and voice.is_connected(): #음성 대화 연결된 상태라면
#         await voice.disconnect() # 연결 끊기
#         print(f"The bot has left {channel}")
#         await ctx.send(f"Left {channel}")
#     else: #이미 연결 안된 상태라면(동시에 여러명이 명령어 침)
#         print("Bot was told to leave voice channel, but was not in one")
#         await ctx.send("Don't think I am in a voice channel")

# @bot.command(pass_context=False, aliases=['myss']) #
# async def stop (ctx):
#     voice = get(bot.voice_clients, guild=ctx.guild) #bot의 음성 대화용 객체
#     print("Music stopped") #이미 재생되는 중인 파일같다고 알려줌
#     voice.stop()

# @bot.command(pass_context=False, aliases=['myp']) #
# async def play (ctx, url: str):
#     song_there = os.path.isfile(SAVE_PATH+"song.mp3") #song.mp3 파일의 존재여부
#     try:
#         if song_there: #존재하면
#             os.remove(SAVE_PATH+"song.mp3") #삭제
#             print("Removed old song file")
#     except PermissionError: #권한 부족 에러 발생시
#         print("Tring to delete song file, but it's being played") #이미 재생되는 중인 파일같다고 알려줌
#         await ctx.send("Error: Music playing")
#         return

#     await ctx.send("Getting everything ready now")

#     voice = get(bot.voice_clients, guild=ctx.guild)

#     if voice == None:
#         print("No voice object")
#         return

#     ydl_opta = { #추출 매개변수, 건들지 말자....
#         "format": "bestaudio/best",
#         "postprocessors": [{
#             "key": "FFmpegExtractAudio",
#             "preferredcodec": "mp3",
#             "preferredquality": "192"
#         }],
#         'outtmpl':SAVE_PATH + '%(title)s.%(ext)s', #다운 경로 설정
#     }

#     with youtube_dl.YoutubeDL(ydl_opta) as ydl: #with문을 사용해 파일입출력을 안전하게 as하여 outube_dl.YoutubeDL(ydl_opta) 값을 ydl로
#         ydl.download({url}) #ydl_opta 값을 적용한 유튜브 다운로더를 통해 url에서 파일을 다운로드한다. 경로는 소스경로

#     for file in os.listdir(SAVE_PATH): #다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
#         if file.endswith(".mp3"): #파일 확장자가 .mp3면, 다운로드한 파일일거임
#             name = file #기존 파일명
#             print(f"Renamed File: {file}\n")
#             os.rename(SAVE_PATH+file, SAVE_PATH+"song.mp3") #파일명 변경 song.mp3로

#     voice.play(discord.FFmpegPCMAudio(SAVE_PATH+"song.mp3"), after=lambda e: print(f"{name} has finished playing"))
#     #song.mp3 파일 음성 재생 끝나면 알려줌
#     voice.source = discord.PCMVolumeTransformer(voice.source)
#     voice.source.volume = 0.15 #볼륨 설정

#     nname = name.rsplit("-", 2) #보통 유튜브는 "-" 로 split하여 제목만을 가져올 수 있음
#     await ctx.send(f"Playing {nname}")


# bot.run(TOKEN) #봇 실행 토큰은 웹 상에서 자신의 봇을 특정 짓기위한 키


# 채팅창에 누군가가 메시지를 입력하면 아래의 함수를 실행하게 된다
# @bot.event
# async def on_message(message):
# 봇이 입력한 메시지라면 무시하고 넘어간다.
# if message.author == bot.user:
#    return
# 메시지가 들어온 채팅창에 "그렇군요!" 라고 입력한다.
# await message.channel.send("그렇군요!")

# @bot.command(name="테스트")
# async def playerAudio(ctx):
#     # Gets voice channel of message author
#     voice_channel = ctx.author.channel
#     channel = None
#     if voice_channel != None:
#         channel = voice_channel.name
#         vc = await voice_channel.connect()
#         vc.play(discord.FFmpegPCMAudio(executable="C:/ffmpeg/bin/ffmpeg.exe", source="C:<path_to_file>"))
#         # Sleep while audio is playing.
#         while vc.is_playing():
#             sleep(.1)
#         await vc.disconnect()
#     else:
#          await ctx.send(str(ctx.author.name) + "is not in a channel.")
#     # Delete command after the audio is done playing.
#      await ctx.message.delete()


# 봇을 실행하자
