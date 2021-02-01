#필요 라이브러리 
import discord
from discord.ext import commands
from discord.utils import get
import os
import time
import asyncio
import soundfile as sf
import random
import math   
import Config


#공용
global bot  # 봇 객체 
bot = None
global fun_startQuiz #퀴즈 시작 함수
fun_startQuiz = None
global isSet
isSet = True

LIST_PER_PAGE = 5
dataMap = dict()


class SelectorData:
    def __init__(self):
        self._controlChannel = None #버튼 상호작용할 채널
        self._quizSelectorMessage = None #퀴즈 선택 embed 메시지
        self._pageList = None #현재 표시된 선택지
        self._nowPage = 0 #현재 페이지 넘버
        self._maxPage = 0 #최대 페이지
        self._pathPoint = [] #경로 저장용
        self._pageMap = dict() #뒤로가기 시 페이지 복구를 위한 경로별 마지막 페이지 해쉬맵


#프레임들
class QFrame:
    def __init__(self):
        self._title_visible = True #타이틀 표시 여부
        self._title_text = "Title"  #타이틀 메시지

        self._sub_visible = True #서브 타이틀 표시 여부
        self._sub_text = "Sub Title"  # 서브 타이틀 메시지

        self._page_visible = False #페이지 표시 옵션
        self._page_nowPage = 0 #현재 페이지 번호

        self._main_visible = True #메인 메시지 표시 여부
        self._main_text = "Main" #메인 메시지



#utility
def initializing(_bot, _fun_startQuiz):
    global bot
    bot = _bot
    global fun_startQuiz
    fun_startQuiz = _fun_startQuiz
    global isSet
    isSet = True

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


async def createUI(channel): #초기 UI생성
    if not isSet: return

    quizListEmbed = discord.Embed(
            title="[                                                퀴즈 선택                                               ]", url=None, description="\n▽", color=discord.Color.dark_magenta())
    quizListEmbed.set_author(name=bot.user, url="",
                        icon_url=bot.user.avatar_url)


    quizListMessage = await channel.send(embed=quizListEmbed)

    await quizListMessage.add_reaction(Config.EMOJI_ICON.PAGE_PREV)
    i = 1
    while i < 6: #1~5번 버튼만
        await quizListMessage.add_reaction(Config.EMOJI_ICON.NUMBER[i])
        i += 1
    await quizListMessage.add_reaction(Config.EMOJI_ICON.PAGE_PARENT)
    await quizListMessage.add_reaction(Config.EMOJI_ICON.PAGE_NEXT)

    return quizListMessage


async def setFrame(message, frame):


async def updatePage(message, guildData):
    if not isSet: return

    if message == None or guildData == None:
        return

    selectorData = guildData._selectorData #UI데이터 가져오기

    searchPath = "" #현재 경로

    i = 0
    while i < len(selectorData._pathPoint):
        searchPath += selectorData._pathPoint[i] + "/" #퀴즈 경로 표시
        i += 1
    
    allPath = Config.QUIZ_PATH + searchPath #절대 경로

    quizList = os.listdir(allPath) #현재 경로의 모든 퀴즈 가져오기

    desc = "\n"+chr(173)+"\n" #embed에 표시할 메시지, chr(173)은 빈문자
    selectorData.pageList = [] #로컬 저장 목록 초기화

    tmpList = []
    for tmpFile in quizList: #쓸모없는 파일은 무시
        print(tmpFile)
        if not os.path.isdir(allPath+tmpFile): #폴더가 아니면 패스
            continue #다음 파일로
        icon = Config.EMOJI_ICON.ICON_FOLDER #아이콘, 기본은 폴더
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
        desc += Config.EMOJI_ICON.NUMBER[i] + ".　" + str(fileData) + "\n　\n"
    
    selectorEmbed = discord.Embed(
            title="[                                                🔍　퀴즈 선택                                               ]", url=None, description="\n"+desc+"\n"+chr(173), color=discord.Color.dark_magenta())
    selectorEmbed.set_author(name=bot.user, url="",
                        icon_url=bot.user.avatar_url)
    selectorEmbed.set_footer(text=("🅿️　"+str(selectorData._nowPage+1)+" / "+str(selectorData._maxPage)+"　　|　　📂 퀴즈봇/"+searchPath)) #페이지 표시

    selectorData._controlChannel = message.channel.id # 채널 갱신
    selectorData._quizSelectorMessage = await message.edit(embed=selectorEmbed) # 메시지 객체 업데이트 