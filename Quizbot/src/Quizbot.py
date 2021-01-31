#필요 라이브러리 
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
import math
from threading import Thread
from mutagen.mp3 import MP3
from pydub import AudioSegment
from shutil import copyfile


# 개발자 페이지에서 봇에 대한 토큰 텍스트를 가져온 뒤, TOKEN에 대입하자
TOKEN = "ODA1MjE1NjU5NjMzOTM0NTE3.YBXphQ.aRZPxSMFofc7F1L1NdzL58o5sxQ"
BOT_PREFIX = "^" #명령어 prefix
QUIZ_PATH = "C:/Users/HOME/Desktop/develop/vscode/workspace/quizbot/resource/quizData/"  # 게임 소스폴더
BGM_PATH = "C:/Users/HOME/Desktop/develop/vscode/workspace/quizbot/resource/bgm/"  # 효과음 폴더
# C드라이브에 다운로드하려고하면 Permission Denied 에러 떠서 다른 폴더로...
SAVE_PATH = "C:/Users/HOME/Desktop/develop/vscode/workspace/quizbot/resource/download/" #유튜브 음악 다운로드 폴더
TMP_PATH = "C:/Users/HOME/Desktop/develop/vscode/workspace/quizbot/resource/tmp/" #임시폴더
DATA_PATH = "C:/Users/HOME/Desktop/develop/vscode/workspace/quizbot/resource/data/" #데이터 저장 폴더

#상수 선언
alphabetList = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q"
                    , "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
emojiNumberList = [ "0️⃣", "1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
emojiOXList = ["⭕", "❌"] #ox퀴즈용
LIST_PER_PAGE = 5

#enum 선언
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
    LONGTIMER = 9


class EMOJI_ICON(enumerate): #이모지
    PAGE_PREV = "🔺"
    PAGE_NEXT = "🔻"
    PAGE_PARENT = "↩️"
    PLAY_LEFT = "⏪"
    PLAY_PAUSE_AND_RESUME = "⏯️"
    PLAY_STOP = "⏹️"
    PLAY_RIGHT = "⏩" 
    PLAY_SUB_FAST = "⬅️" 
    PLAY_SUB_SLOW = "➡️" 
    PLAY_AUDIO_FAST = "◀️" 
    PLAY_AUDIO_SLOW = "▶️" 
    ICON_FOLDER = "📁"

#클래스 선언

#봇이 있는 디스코드 서버 데이터
class GuildData:
    def __init__(self, guild):
        self._guildID = guild.id #서버 id 저장
        self._selectorData = SelectorData() #퀴즈 선택용
        self._gameData = None #진행중인 퀴즈 데이터

class SelectorData:
    def __init__(self):
        self._controlChannel = None #버튼 상호작용할 채널
        self._nowPage = 0 #페이지 넘버
        self._quizSelectorMessage = None #퀴즈 선택 embed 메시지
        self._pageList = None #현재 표시된 퀴즈 목록
        self._maxPage = 0 #최대 페이지
        self._pathPoint = [] #경로 저장용
        self._nowPlaying = "없음" #현재 진행중인 퀴즈
        self._pageMap = dict() #뒤로가기 시 페이지 복구를 위한 경로별 마지막 페이지 해쉬맵

class QUIZ:
    def __init__(self, guild, chatChannel, voiceChannel, gameName, roomOwner):
        self._chatChannel = chatChannel
        self._voiceChannel = voiceChannel
        self._gameType = gameType
        self._gameName = gameName
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
        self._repeatCount = 1 #반복 듣기 횟수

        self._textQuizList = [] # 텍스트 기반 퀴즈일 때 문제 저장 공간
        self._oxQuizObject = None #현재 진행중인 ox퀴즈 객체
        self._useHint = False #힌트 사용여부
        self._thumbnail = None # 썸네일
        self._answerAuido = None #정답용 음악
        self._topNickname = "" #1등 별명

class SongQuiz(QUIZ): #노래 퀴즈

    def __init__(self):
        self._gameType == GAME_TYPE.SONG
        
class SelectQuiz(QUIZ): #객관식 퀴즈

    def __init__(self):
        self._gameType = GAME_TYPE.SELECT
        self._selectList = [] #객관식 보기
        self._selectionAnswer = 0 #객관식 정답
        self._selectPlayerMap = dict() #사람들 선택한 답


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

########################


bot = commands.Bot(command_prefix=BOT_PREFIX)  # 봇 커맨드 설정

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


async def clearAll(chatChannel):
    await chatChannel.purge(limit=100)


async def clearChat(chatChannel):
    mgs = [] #챗 채널에서 긁어온 메시지 저장 공간
    number = 500 #긁어올 메시지 개수
    async for tmpMsg in Client.logs_from(ctx.message.channel, limit = number):
        mgs.append(tmpMsg)
    await Client.delete_messages(mgs)


async def countdown(gameData): #카운트 다운
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


async def longCountdown(gameData): #15초짜리 카운트 다운
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


def getEmojiNumber(index): #정수값에 알맞은 이모지 반환
    return emojiNumberList[index]


def convert(seconds): #초 값을 시,분,초 로 반환
    hours = seconds // 3600
    seconds %= 3600
    mins = seconds//60
    seconds %= 60

    return hours, mins, seconds


def isQuiz(fileName): #퀴즈 폴더인지 확인
    fileName = fileName.lower()
    if fileName.find("&quiz") != -1: 
        return True
    else:
        return False

def getIcon(fileName):
    fileName = fileName.lower()
    icon = fileName.split("&icon=")[1] #&quiz 뒤에있는 것이 아이콘 타입임
    icon = icon.split("&")[0] #& 만나기 전까지 파싱, 즉 icon 값만 파싱

    return icon #아이콘 반환
    

#사전 정의 함수
def getGuildData(guild):
    if guild in dataMap.keys():  # 서버 데이터 가져오기
        guildData = dataMap[guild]
    else: # 서버 데이터가 없다면
        guildData = GuildData(guild) # 새로운 서버 데이터 생성
        dataMap[guild] = guildData #데이터 해쉬맵에 등록

    return guildData

async def createUI(channel): #UI생성
    quizListEmbed = discord.Embed(
            title="[                                                퀴즈 선택                                               ]", url=None, description="\n▽", color=discord.Color.dark_magenta())
    quizListEmbed.set_author(name=bot.user, url="",
                        icon_url=bot.user.avatar_url)


    quizListMessage = await channel.send(embed=quizListEmbed)

    await quizListMessage.add_reaction(EMOJI_ICON.PAGE_PREV)
    i = 1
    while i < 6: #1~5번 버튼만
        await quizListMessage.add_reaction(emojiNumberList[i])
        i += 1
    await quizListMessage.add_reaction(EMOJI_ICON.PAGE_PARENT)
    await quizListMessage.add_reaction(EMOJI_ICON.PAGE_NEXT)

    return quizListMessage


async def updatePage(message, guildData):
    if message == None or guildData == None:
        return

    selectorData = guildData._selectorData #UI데이터 가져오기

    searchPath = "" #현재 경로

    i = 0
    while i < len(selectorData._pathPoint):
        searchPath += selectorData._pathPoint[i] + "/" #퀴즈 경로 표시
        i += 1
    
    allPath = QUIZ_PATH + searchPath #절대 경로

    quizList = os.listdir(allPath) #현재 경로의 모든 퀴즈 가져오기

    desc = "\n"+chr(173)+"\n" #embed에 표시할 메시지, chr(173)은 빈문자
    selectorData.pageList = [] #로컬 저장 목록 초기화

    tmpList = []
    for tmpFile in quizList: #쓸모없는 파일은 무시
        print(tmpFile)
        if not os.path.isdir(allPath+tmpFile): #폴더가 아니면 패스
            continue #다음 파일로
        icon = EMOJI_ICON.ICON_FOLDER #아이콘, 기본은 폴더
        icon = getIcon(tmpFile) #파일명으로 아이콘 가져와보기
        fileName = tmpFile.split("&")[0] #실제 파일명만 긁어오기
        tmpList.append(icon+" "+fileName) #파일 목록에 추가

    selectorData._maxPage = math.ceil(len(tmpList) / LIST_PER_PAGE)   #최대 페이지 설정
    pageIndex = selectorData._nowPage * LIST_PER_PAGE #표시 시작할 인덱스

    i = 0
    while i < LIST_PER_PAGE: #LIST_PER_PAGE 만큼 목록 표시
        fileIndex = pageIndex + i
        if fileIndex >= len(tmpList): #마지막 파일 도달하면 바로 break
            break
        fileData = tmpList[fileIndex]
        selectorData.pageList.append(fileData) #저장 목록에 추가
        i += 1
        desc += emojiNumberList[i] + ".　" + str(fileData) + "\n　\n"
    
    selectorEmbed = discord.Embed(
            title="[                                                🔍　퀴즈 선택                                               ]", url=None, description="\n"+desc+"\n"+chr(173), color=discord.Color.dark_magenta())
    selectorEmbed.set_author(name=bot.user, url="",
                        icon_url=bot.user.avatar_url)
    selectorEmbed.set_footer(text=("🅿️　"+str(selectorData._nowPage+1)+" / "+str(selectorData._maxPage)+"　　|　　📂 퀴즈봇/"+searchPath)) #페이지 표시

    selectorData._controlChannel = message.channel.id # 채널 갱신
    selectorData._quizSelectorMessage = await message.edit(embed=selectorEmbed) # 메시지 객체 업데이트 


def playBGM(voice, bgmType): #BGM 틀기
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
        print("error01 - voice is not connect error")


async def addScore(message, gameData): #1점 추가
    author = message.author #정답 맞춘 메시지 보낸사람
    if author in gameData._scoreMap:  # 점수 리스트에 정답자 있는지 확인
        gameData._scoreMap[author] += 1  # 있으면 1점 추가
    else:
        gameData._scoreMap[author] = 1  # 없으면 새로 1점 추가


    author = "" #정답 추가 정보(작곡자 등)
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
    await clearAll(gameData._chatChannel)
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
    await clearAll(gameData._chatChannel)
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
    await clearAll(gameData._chatChannel)
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

    gameData._selectList.clearAll() #보기 문항 초기화
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
    gameData._selectPlayerMap.clearAll() #맵 클리어

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
    await clearAll(gameData._chatChannel)
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

    gameData._selectList.clearAll() #보기 문항 초기화
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
    gameData._selectPlayerMap.clearAll() #선택한 정답 맵 클리어

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
    await clearAll(gameData._chatChannel)
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
    await clearAll(gameData._chatChannel)
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
        
    gameData._selectPlayerMap.clearAll() #선택한 정답 맵 클리어

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
    await clearAll(gameData._chatChannel)
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

    await clearAll(gameData._chatChannel)
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
    await clearAll(gameData._chatChannel)
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
    await clearAll(gameData._chatChannel)
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
    #await bot.change_presence(status=discord.Status.online) #온라인
  #await client.change_presence(status=discord.Status.idle) #자리비움
  #await client.change_presence(status=discord.Status.dnd) #다른용무
  #await client.change_presence(status=discord.Status.offline) #오프라인

  #  await bot.change_presence(activity=discord.Game(name="!quiz"))
  #await client.change_presence(activity=discord.Streaming(name="스트림 방송중", url='링크'))
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!퀴즈 | !quiz"))
  #await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="영상 시청중"))
  
    print("봇 이름:",bot.user.name,"봇 아이디:",bot.user.id,"봇 버전:",discord.__version__)


@bot.command(pass_context=False, aliases=["ping"])  # ping 명령어 입력시
async def pingCommand(ctx):  # ping 테스트
    await ctx.send(f"핑 : {round(bot.latency * 1000)}ms")


@bot.command(pass_context=False, aliases=["quiz", "퀴즈"])  # quiz 명령어 입력시
async def quizCommand(ctx, gamesrc=None):  # 퀴즈봇 UI 생성
    if gamesrc == None:
        selectorMessage = await createUI(ctx.channel) #UI생성

        guild = ctx.guild #서버
        guildData = getGuildData(guild)
        
        await updatePage(selectorMessage, guildData) #초기 화면으로 업데이트


    # if gamesrc == None:  # !quiz만 입력했으면
    #     await showQuizCategory(ctx)  # 카테고리목록 보여줌
    #     return

    # gamesrc = gamesrc.upper()
    # isExistData = os.path.isdir(BASE_PATH + gamesrc)  # 하려는 퀴즈가 있는지 확인
    # if(isExistData == False):  # 없다면
    #     #카테고리 목록 확인일 수도 있으니 있는지 확인
    #     if gamesrc in QUIZ_CATEGORI.keys():  # 카테고리 목록에 있다면
    #         await showQuizList(ctx, gamesrc)  # 카테고리에 속하는 퀴즈목록 표시
    #     else:  # 카테고리 목록에도 없다면
    #         await ctx.send(gamesrc + " 퀴즈는 존재하지 않습니다.")
    #     return

    # if ctx.message.author.voice == None:
    #     await ctx.send("음성 대화채널에 참가한 후 시도하세요.")
    #     return

    # channel = ctx.message.author.voice.channel  # 호출자의 음성 채널 얻기
    # chattingChannel = ctx.message.channel  # 호출자의 채팅 채널 얻기

    # # bot의 해당 길드에서의 음성 대화용 객체
    # voice = get(bot.voice_clients, guild=ctx.guild)
    # if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
    #     await ctx.send("이미 퀴즈가 진행되고 있습니다. 먼저 연결을 끊거나 !gamestop 을 입력하여 종료하세요.")
    # else:  # 퀴즈 진행중이 아니라면
    #     voice = await channel.connect()  # 음성 채널 연결후 해당 객체 반환
    #     tmpQuizData = QUIZ_MAP[gamesrc]
    #     gameType = tmpQuizData._gameType  # 퀴즈 타입 가져오기
    #     gameName = gamesrc  # 퀴즈 이름
    #     gameData = GameData(ctx.guild, chattingChannel,
    #                             voice, gameName, gameType, ctx.message.author)  # 퀴즈데이터 생성
    #     gameData._repeatCount = QUIZ_MAP[gamesrc]._repeatCount  # 반복 횟수 설정
    #     gameData._voice = voice  # voice 객체 설정
    #     gameData._topNickname = tmpQuizData._topNickname #1등 별명 설정
    #     dataMap[ctx.guild] = gameData  # 해당 서버의 퀴즈데이터 저장

    #     await clearAll(gameData._chatChannel)
    #     await ctx.send(gamesrc + " 퀴즈를 시작합니다. 데이터 저장중...")
    #     await playBGM(voice, BGM_TYPE.PLING)
    #     await asyncio.sleep(2)  # 2초 대기
    #     await printGameRule(ctx, voice, gameType)
    #     await asyncio.sleep(2)  # 2초 대기
    #     await checkGameStop(gameData)
    #     embed = discord.Embed(title="자! 이제 "+gameData._gameName+" 퀴즈를 시작합니다!",
    #                               url=None, description="\n", color=discord.Color.blue())
    #     await ctx.send(embed=embed)
    #     await playBGM(voice, BGM_TYPE.PLING)
    #     await asyncio.sleep(4)  # 2초 대기
    #     await gameLoop(ctx, gameData)


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
    if user == bot.user:  # 봇이 입력한거면
        return  # 건너뛰어

    channel = reaction.message.channel  # 반응 추가한 채널

    guildData = getGuildData(reaction.message.guild)
    selectorData = guildData._selectorData
    gameData = guildData._gameData

    if selectorData._quizSelectorMessage == None:  # 퀴즈 선택 메시지 객체가 없다면
        print("no")
        return  # !quiz 입력하라는 뜻으로 그냥 return
    elif selectorData._controlChannel == channel.id:  # 퀴즈 선택 메시지 있는 채널이면
        emoji = reaction.emoji  # 반응한 이모지 가져오기
        print(str(user) + ", " + str(emoji))  # 로그
        try:
            await reaction.remove(user)  # 이모지 삭제
        except:
            return

        isControl = True
        index = 0
        while index < len(emojiNumberList):  # 번호 이모지인지 확인
            if emojiNumberList[index] == emoji:
                await somethingSelected(index)  # 번호 이미지면 행동
                isControl = False
                break
            index += 1

        if emoji == EMOJI_ICON.PAGE_NEXT:  # 다음 페이지면
            isControl = False
            if selectorData.nowPage < selectorData.maxPage:  # 최대 페이지 미만이면
                selectorData.nowPage += 1  # 다음 페이지
        elif emoji == EMOJI_ICON.PAGE_PREV:  # 이전 페이지면
            isControl = False
            if selectorData.nowPage > 0:  # 0보다 크면
                selectorData.nowPage -= 1  # 이전 페이지
        elif emoji == EMOJI_ICON.PAGE_PARENT:  # 되돌아가기면
            isControl = False
            if len(selectorData.pathPoint) > 0:  # 부모 폴더가 있다면
                # 최하위 경로를 삭제함으로서 1단계 위로
                del selectorData.pathPoint[len(selectorData.pathPoint) - 1]

        if isControl:  # 만약 컨트롤 버튼이면
            await control(emoji)  # 리모콘 동작

        await updatePage(reaction.message, guildData)

    if gameData != None and gameData._chatChannel == channel:  # 현재 게임중인 채널이면
        if gameData._gameType == GAME_TYPE.SELECT or gameData._gameType == GAME_TYPE.GLOWLING:  # 객관식 퀴즈 진행중이면
            emoji = reaction.emoji  # 반응한 이모지 가져오기
            #isInSelectEmoji = False #반응한 이모지가 선택용 이모지인지 확인하기

            index = 0

            while index < len(emojiNumberList):
                if emojiNumberList[index] == emoji:
                    # 선택한 번호 저장하기
                    gameData._selectPlayerMap[user.name] = index
                    break
                index += 1
            try:
                await reaction.remove(user)  # 이모지 삭제
            except:
                return
        elif gameData._gameType == GAME_TYPE.OX:  # ox퀴즈의 경우
            emoji = reaction.emoji  # 반응한 이모지 가져오기

            index = 0

            while index < len(emojiOXList):
                if emojiOXList[index] == emoji:
                    # 선택한 번호 저장하기
                    gameData._selectPlayerMap[user.name] = index
                    break
                index += 1


@bot.event
async def on_reaction_remove(reaction, user):
    if user == bot.user: #봇이 삭제한거면
        return #건너뛰어

    channel = reaction.message.channel #반응 삭제한 채널
    emoji = reaction.emoji # 삭제한 이모지 가져오기

    for guildData in dataMap.values(): #모든 서버 데이터에 대해
        selectorData = guildData._selectorData #퀴즈 선택 메시지
        gameData = guildData._gameData # 게임 데이터

        if selectorData != None: #퀴즈 선택 메시지가 null이 아니면
            if selectorData._quizSelectorMessage == reaction.message: # 각 메시지 비교 후 일치시
                await reaction.message.add_reaction(emoji=emoji) #다시 추가

        if gameData != None and gameData._chatChannel == channel: #게임 진행중인 채널이면
            if gameData._:  # 객관식 퀴즈 진행중이면
                await reaction.message.add_reaction(emoji=emoji)  # 다시 추가
                
    


#################################

bot.run(TOKEN)  # 봇 실행
