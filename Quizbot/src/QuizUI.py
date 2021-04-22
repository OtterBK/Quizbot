#필요 라이브러리 
from typing import OrderedDict
import discord
from discord import player
from discord.ext import commands
from discord.utils import get
import os
import time
import asyncio
import soundfile as sf
import random
import math   
import Config
import sys, traceback
import json
import collections

#공용
global bot  # 봇 객체 
bot = None
global fun_startQuiz #퀴즈 시작 함수
fun_startQuiz = None
global isSet
isSet = True

LIST_PER_PAGE = 5
selectorMap = dict() #퀴즈 선택 UI
quizUIMap = dict() #퀴즈 UI 
optionMap = dict() #각 길드의 옵션들
rankMap = dict() #각 길드의 랭크 데이터

matchingCategory = dict() #카테고리별 매칭 대기열 
MULTIPLAY_RANKNAME = "multiplay"

class SelectorData:
    def __init__(self, selectorMessage):
        self._selectorMessage = selectorMessage #퀴즈 선택 embed 메시지
        self._frameStack = [] #프레임 스택
        self._option = getOption(selectorMessage.guild)

class OPTION_TYPE(enumerate): #옵션 타입
    HINT_TYPE = 0
    SKIP_TYPE = 1
    TRIM_LENGTH = 2
    REPEAT_COUNT = 3

class NET_MESSAGE_TYPE(enumerate):
    REQUEST = 0
    ACK = 1
    CONNECT = 2


class NetMessage:

    def __init__(self, sender, messageTye):
        self._sender = sender
        self._NET_MESSAGE_TYPE = messageTye


class QOption(): #옵션
    
    def __init__(self, guildID):
        self._guildID = guildID
        self._hintType = 0 #0=투표, 1=주최자, 2=자동
        self._skipType = 0 #0=투표, 1=주최자
        self._trimLength = 40 #오디오 자르기 길이, 최대 60, 최저 5
        self._repeatCount = 1 #오디오 반복, 최저1, 최대5

        self.load() #설정값 로드

    def load(self):
        optionFile = Config.OPTION_PATH + str(self._guildID) + ".json"  #길드 id이름으로 된 옵션값 경로

        if os.path.isfile(optionFile):

            with open(optionFile, "r", encoding="utf-8") as json_file:
                optionData = json.load(json_file)[0]

                self._hintType = int(optionData["hintType"])
                self._skipType = int(optionData["skipType"])
                self._trimLength = int(optionData["trimLength"])
                self._repeatCount = int(optionData["repeatCount"])

    def save(self):
        optionFile = Config.OPTION_PATH + str(self._guildID) + ".json"  #길드 id이름으로 된 옵션값 경로

        data = []
        data.append({
            "hintType": self._hintType,
            "skipType": self._skipType,
            "trimLength": self._trimLength,
            "repeatCount": self._repeatCount,
        })

        with open(optionFile, 'w', encoding="utf-8") as outfile:
            json.dump(data, outfile, indent=4)

    
class PlayerStat(): #플레이어 스탯 정보

    def __init__(self, playerName):
        self._playerName = playerName #플레이어 이름
        self._playCount = 0 #플레이 횟수
        self._topScore = 0 #최고점



class MultiplayStat(): #멀티 플레이 스탯 정보, 카테고리마다 다름

    def __init__(self, guildID, guildName):
        self._guildID = guildID
        self._guildName = guildName #플레이어 이름
        self._multiStat_win = 0 #멀티 승리
        self._multiStat_defeat = 0 #멀티 패배
        self._multiStat_play = 0 #멀티 플레이 수


class Scoreboard(): #순위표

    def __init__(self, guildID, quizName):
        self._guildID = guildID #길드id
        self._quizName = quizName #퀴즈명
        self._score = dict()

    def loadScore(self): #순위 불러오기
        rankFile = Config.RANK_PATH + str(self._guildID) + "/" + self._quizName + ".json"  #길드 id, 퀴즈명이름으로 된 순위표 경로
        if os.path.isfile(rankFile):

            with open(rankFile, "r", encoding="utf-8") as json_file:
                scoreData = json.load(json_file)

                for playerName in scoreData.keys():

                    playerStat = PlayerStat(playerName)

                    playerStat._playCount = int(scoreData[playerName][0]["플레이횟수"])
                    playerStat._topScore = int(scoreData[playerName][0]["최고점수"])

                    self._score[playerName] = playerStat #순위표에 넣기

        self.sort() #정렬한번

    def saveScore(self): #순위표 저장
        rankFile = Config.RANK_PATH + str(self._guildID) + "/" + self._quizName + ".json"  #길드 id, 퀴즈명이름으로 된 순위표 경로

        data = {}
        for playerName in self._score.keys():

            playerStat = self._score[playerName] #플레이어 스탯 가져오기

            data[playerName] = []
            data[playerName].append({
                "이름": playerStat._playerName,
                "플레이횟수": playerStat._playCount,
                "최고점수": playerStat._topScore
            })

        with open(rankFile, 'w', encoding="utf-8") as outfile:
            json.dump(data, outfile, indent=4)


    
    def mergeScore(self, scoreMap): #순위 병합
        baseScore = self._score

        for player in scoreMap.keys(): #병합할 순위표의 플레이어들에 대해
            playerName = str(player.name)
            playerName += "#"
            playerName += str(player.discriminator) #이름 + 태그 가져오고
            score = scoreMap[player] #점수 가져오고

            playerStat = None 
            if playerName in baseScore: #이미 순위표에 있다면
                playerStat = baseScore[playerName] #스탯 가져오기
            else: #없으면 생성후 넣기
                playerStat = PlayerStat(playerName)
                baseScore[playerName] = playerStat
            
            playerStat._playCount += 1 #플레이 횟수 1증가
            if score > playerStat._topScore: #병합할 점수가 최고점보다 크면
                playerStat._topScore = score #최고점 갱신
        
        self.sort() #정렬

        self.saveScore() #저장

    def sort(self, isDesc=True): #내림차순 정렬
        scoreMap = self._score
        if len(scoreMap) == 0: return

        sortPlayer = []  # 빈 리스트

        for player in scoreMap.keys():  # 정렬
            index = 0  # 인덱스
            stat = scoreMap[player]  # 스탯 객체
            topScore = stat._topScore #최고점
            while index < len(sortPlayer):
                cp = sortPlayer[index]  # 비교대상
                cp_score = scoreMap[cp]._topScore  # 비교대상 점수
                if topScore > cp_score:  # 비교대상보다 점수높으면
                    break  # while 빠져나가기
                index += 1  # 다음 대상으로

            sortPlayer.insert(index, player)  # 삽입 장소에 추가

        tmpMap = dict()
        for player in sortPlayer: #데이터 재삽입
            tmpMap[player] = scoreMap[player]
        
        self._score = tmpMap


class MultiplayScoreboard(Scoreboard):

    def __init__(self, guildID, quizName):
        super().__init__(guildID, quizName)

        self._quizName = quizName #퀴즈명
        self._score = dict()


    def loadScore(self): #순위 불러오기
        rankFile = Config.RANK_PATH + str(self._guildID) + "/" + self._quizName + ".json"  #길드 id, 퀴즈명이름으로 된 순위표 경로
        if os.path.isfile(rankFile):

            with open(rankFile, "r", encoding="utf-8") as json_file:
                scoreData = json.load(json_file)

                for guildID in scoreData.keys():

                    guildName = scoreData[guildID][0]["길드명"]

                    multiplayStat = MultiplayStat(guildID, guildName)

                    multiplayStat._multiStat_win = int(scoreData[guildID][0]["승리"])
                    multiplayStat._multiStat_defeat = int(scoreData[guildID][0]["패배"])
                    multiplayStat._multiStat_play = int(scoreData[guildID][0]["플레이횟수"])

                    self._score[guildID] = multiplayStat #순위표에 넣기

        self.sort() #정렬 한번

    def saveScore(self): #순위표 저장
        rankFile = Config.RANK_PATH + str(self._guildID) + "/" + self._quizName + ".json"  #길드 id, 퀴즈명이름으로 된 순위표 경로


        data = {}
        for guildID in self._score.keys():

            multiplayStat = self._score[guildID]  # 멀티플레이 스탯 가져오기

            data[guildID] = []
            data[guildID].append({
                "길드id": multiplayStat._guildID,
                "길드명": multiplayStat._guildName,
                "승리": multiplayStat._multiStat_win,
                "패배": multiplayStat._multiStat_defeat,
                "플레이횟수": multiplayStat._multiStat_play
            })

        with open(rankFile, 'w', encoding="utf-8") as outfile:
            json.dump(data, outfile,indent=4)

    
    def mergeScore(self, scoreMap): #순위 병합
        baseScore = self._score

        for guild in scoreMap.keys(): #병합할 순위표의 플레이어들에 대해
            guildID = str(guild.id)
            
            if not guildID in self._score.keys(): #존재 안하면
                tmpStat = MultiplayStat(guild.id, guild.name) #새로 생성
                self._score[guildID] = tmpStat #넣어주기

            multiplayStat = self._score[guildID] #스탯 가져오기
            result = scoreMap[guild]  #대전 결과
            if result == 1: #승리시
                multiplayStat._multiStat_win += 1
            elif result == 0: #패배시
                multiplayStat._multiStat_defeat += 1
            multiplayStat._multiStat_play += 1

        self.sort() #정렬

        self.saveScore() #저장

    def sort(self, isDesc=True): #내림차순 정렬
        scoreMap = self._score
        if len(scoreMap) == 0: return

        sortGuild = []  # 빈 리스트

        for guildID in scoreMap.keys():  # 정렬
            index = 0  # 인덱스
            stat = scoreMap[guildID]  # 스탯 객체
            winCount = int(stat._multiStat_win) #승리수
            while index < len(sortGuild):
                cp = sortGuild[index]  # 비교대상
                cp_win = int(scoreMap[cp]._multiStat_win)  # 비교대상 승리수
                if winCount > cp_win:  # 비교대상보다 승리수높으면
                    break  # while 빠져나가기
                index += 1  # 다음 대상으로

            sortGuild.insert(index, guildID)  # 삽입 장소에 추가

        tmpMap = dict()
        for guildID in sortGuild: #데이터 재삽입
            tmpMap[guildID] = scoreMap[guildID]
        
        self._score = tmpMap

class RankData(): #랭킹 저장용
    
    def __init__(self, guildID):
        self._guildID = guildID
        self._localRank = dict() #로컬 플레이 랭크맵, 퀴즈명 - 순위

        self.loadLocalRank() #데이터 로드

    def loadLocalRank(self): #로컬 순위표 로드
        rankPath = Config.RANK_PATH + str(self._guildID) + "/" #해당 길드의 랭크 저장 폴더

        if not os.path.exists(rankPath): 
            os.makedirs(rankPath) #폴더 생성
            return #데이터 없으니 return


        self._localRank.clear()
        for optionFile in os.listdir(rankPath):
            if optionFile.endswith(".json"): #확장자가 .scoreboard 인 경우에만
                quizName = optionFile.replace(".json", "") #확장자 떼어내기
                scoreboard = Scoreboard(self._guildID, quizName) #순위표 생성
                scoreboard.loadScore() #로드
                self._localRank[quizName] = scoreboard


class MultiplayRankData(RankData): #멀티플레이 랭킹 저장용
    def __init__(self, guildID):
        super().__init__(guildID)

    def loadLocalRank(self): #멀티플레이 순위표 로드
        rankPath = Config.RANK_PATH + str(self._guildID) + "/" #해당 길드의 랭크 저장 폴더

        if not os.path.exists(rankPath): 
            os.makedirs(rankPath) #폴더 생성
            return #데이터 없으니 return


        self._localRank.clear()
        for optionFile in os.listdir(rankPath):
            if optionFile.endswith(".json"): #확장자가 .scoreboard 인 경우에만
                quizName = optionFile.replace(".json", "") #확장자 떼어내기
                scoreboard = MultiplayScoreboard(self._guildID, quizName) #순위표 생성
                scoreboard.loadScore() #로드
                self._localRank[quizName] = scoreboard

#프레임들
class QFrame:
    def __init__(self):

        self._LIST_PER_PAGE = 5 #페이지 마다 표시할 메인 메시지 라인수

        self._title_visible = True #타이틀 표시 여부
        self._title_text = "Title"  #타이틀 메시지

        self._sub_visible = True #서브 타이틀 표시 여부
        self._sub_text = "Sub Title"  # 서브 타이틀 메시지

        self._main_visible = True #메인 메시지 표시 여부
        self._main_text = [] #메인, list 형태로하여 _LIST_PER_PAGE 만큼 표시

        self._notice_visible = True #알림 표시 여부
        self._notice_text = "Notice" #알림

        self._field_visible = True #Field 표시 여부
        self._field_text = dict() #맵에 있는 값을 차례로 표시할 거임

        self._page_visible = True #페이지 표시 옵션
        self._page_nowPage = 0 #현재 페이지 번호

        self._path_visible = True #경로 표시 옵션
        self._path_text = "Path" #경로 메시지

        self._customFooter_visible = False
        self._customFooter_text = ""

        self._image_visible = False #이미지 표시 여부
        self._image_local = False #로컬 이미지 여부
        self._image_url = "" #이미지 url

        self._embedColor = discord.Color.magenta() #색상
        
        self._author = None #작성자 여부 None이면 기본값


        self._myMessage = None

    def addMain(self, singleMsg):
        self._main_text.append(singleMsg)


    def addField(self, fKey, fValue):
        self._field_text[fKey] = fValue

    def paint(self, message): #해당 프레임이 표시될 때 이벤트
        self._myMessage = message

    def destructor(self, message): #해당 프레임이 메시지에서 사라질 때 이벤트
        self._myMessage = message
    
    async def action(self, reaction, user, selectorData): #이벤트
        Config.LOGGER.info(str(user) + ", " + str(reaction.emoji))

        emoji = reaction.emoji # 반응한 이모지 가져오기

        if emoji == Config.EMOJI_ICON.PAGE_NEXT: #다음 페이지면
            self._page_nowPage += 1
            await showTop(reaction.message, selectorData) #페이지 새로고침
        elif emoji == Config.EMOJI_ICON.PAGE_PREV: #이전 페이지면
            self._page_nowPage -= 1 #이전 페이지
            await showTop(reaction.message, selectorData) #페이지 새로고침

    # async def update(self): #프레임 새로고침
    #     try:
    #         setFrame(self._myMessage, self)
    #     except:
    #         print("frame update failed")
        

class MainFrame(QFrame): #메인 화면
    def __init__(self):
        super().__init__() #frame 초기화
        self._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_QUIZBOT +" 퀴즈 봇　　　　]"

        self._sub_visible = False

        matchingCnt = 0
        for matchingQueue in matchingCategory.values():
            matchingCnt += len(matchingQueue)

        self.addMain(Config.EMOJI_ICON.ICON_LOCALPLAY + "** 로컬 플레이**")
        self.addMain(Config.EMOJI_ICON.ICON_MULTIPLAY + "** 멀티 플레이**　[　**"+Config.EMOJI_ICON.ICON_NET+" "+str(matchingCnt)+"**　]")
        self.addMain(Config.EMOJI_ICON.ICON_SETTING + "** 설정**")
        self.addMain(Config.EMOJI_ICON.ICON_PATCHNOTE + "** 패치노트**")
        self.addMain(Config.EMOJI_ICON.ICON_INFO + "** 정보**")

        self._notice_visible = True
        self._notice_text = Config.EMOJI_ICON.PAGE_PREV + " " +Config.EMOJI_ICON.PAGE_NEXT + " 페이지 이동　" + chr(173) + "　" + Config.getEmojiFromNumber(1) + " ~ " + Config.getEmojiFromNumber(5) + " 선택"

        self._field_visible = False

        self._customFooter_visible = True
        self._customFooter_text = Config.EMOJI_ICON.ICON_VERSION + " 버전: " + Config.VERSION

        self._page_visible = False
        
        self._path_visible = False

        self._image_visible = True
        self._image_url = "https://user-images.githubusercontent.com/28488288/106536426-c48d4300-653b-11eb-97ee-445ba6bced9b.jpg"

        self._embedColor = discord.Color.magenta() 

    def paint(self, message):
        super().paint(message)

        self._main_text = []

        matchingCnt = 0
        for matchingQueue in matchingCategory.values():
            matchingCnt += len(matchingQueue)

        self.addMain(Config.EMOJI_ICON.ICON_LOCALPLAY + "** 로컬 플레이**")
        self.addMain(Config.EMOJI_ICON.ICON_MULTIPLAY + "** 멀티 플레이**　[　**"+Config.EMOJI_ICON.ICON_NET+" "+str(matchingCnt)+"**　]")
        self.addMain(Config.EMOJI_ICON.ICON_SETTING + "** 설정**")
        self.addMain(Config.EMOJI_ICON.ICON_PATCHNOTE + "** 패치노트**")
        self.addMain(Config.EMOJI_ICON.ICON_INFO + "** 정보**")


    async def action(self, reaction, user, selectorData): 
        await super().action(reaction, user, selectorData)

        emoji = reaction.emoji
        message = reaction.message
        guild = message.guild

        number = Config.getNumberFromEmoji(emoji) #이모지에 대응하는 정수값 가져옴
        if number != -1: #숫자 이모지라면

            if number == 1: #각 경우에 맞게 행동
                await showFrame(message, CategorySelectFrame(Config.QUIZ_PATH), isPopUp=True) #카테고리 선택창 표시
            elif number == 2: 
                await showFrame(message, MultiplayFrame(Config.MULTI_PATH), isPopUp=True) #멀티 플레이창 표시
            elif number == 3: 
                await showFrame(message, SettingFrame(), isPopUp=True) #설정창 표시
            elif number == 4: 
                await showFrame(message, PathNoteSelectFrame(Config.PATCHNOTE_PATH), isPopUp=True) #패치노트창 표시
            elif number == 5: 
                await showFrame(message, BotInfoFrame(), isPopUp=True) #봇 정보창 표시
                
                
class CategorySelectFrame(QFrame): #카테고리 선택 화면
    def __init__(self, categoryPath):
        super().__init__() #frame 초기화
        self._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_SEARCH +" 카테고리 선택　　　　]"

        self._sub_visible = True
        self._sub_text = Config.EMOJI_ICON.ICON_LIST + " 동일한 서버내 인원끼리 퀴즈를 진행합니다.\n"
        self._sub_text += chr(173)+ "\n" +"**카테고리를 선택해주세요.**"

        self._notice_visible = True

        self._field_visible = False

        self._page_visible = True
        self._page_nowPage = 0
        
        self._path_visible = True

        self._image_visible = False

        self._embedColor = discord.Color.dark_magenta()

        ##추가
        self._myPath = categoryPath #탐색 경로 저장용
        self._absoluteMap = dict() #icon 파싱값 등을 포함한 실제이름
        self.getMainList()

    def getMainList(self):

        viewPath = "" #표시용 패스
        
        allPath = self._myPath #절대 경로

        self._path_text = viewPath #패스 표시

        quizList = os.listdir(allPath) #해당 경로의 모든 퀴즈 가져오기

        self._main_text = [] #메인 텍스트 초기화
        self._absoluteMap = dict()

        for tmpFile in quizList: #쓸모없는 파일은 무시
            if not os.path.isdir(allPath+tmpFile): #폴더가 아니면 패스
                continue #다음 파일로
            icon = Config.EMOJI_ICON.ICON_QUIZ_DEFAULT #아이콘, 기본은 물음표 모양
            icon = getIcon(tmpFile) #파일명으로 아이콘 가져와보기
            fileName = tmpFile.split("&")[0] #실제 파일명만 긁어오기
            showText = icon+" "+fileName #표시할 항목명
            self._absoluteMap[showText] = tmpFile #절대 이름 설정
            self.addMain(showText) #메인 텍스트에 추가

        self._notice_text = Config.EMOJI_ICON.ICON_BOX+ "　항목 수 : **" + str(len(self._absoluteMap.keys())) + "개**"

    async def action(self, reaction, user, selectorData): 
        await super().action(reaction, user, selectorData)

        emoji = reaction.emoji
        message = reaction.message
        guild = message.guild

        number = Config.getNumberFromEmoji(emoji) #이모지에 대응하는 정수값 가져옴
        if number != -1: #숫자 이모지라면
            
            fileIndex = self._page_nowPage * LIST_PER_PAGE #선택한 목록의 인덱스를 가져옴
            fileIndex += number - 1

            if fileIndex >= len(self._main_text):
                return

            selectName = self._main_text[fileIndex] #선택한 항목의 표시 이름
            absoluteName = self._absoluteMap[selectName] #실제 이름 가져옴

            newPath = self._myPath + absoluteName + "/" #새로운 탐색 절대 경로
            await showFrame(message, QuizSelectFrame(newPath), isPopUp=True) #퀴즈 선택 프레임 열기


class QuizSelectFrame(QFrame): #퀴즈 선택 화면
    def __init__(self, quizListPath):
        super().__init__() #frame 초기화

        self._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_SEARCH +" 퀴즈 선택　　　　]"

        self._sub_visible = True
        self._sub_text = "**진행할 퀴즈를 선택해주세요.**"

        self._notice_visible = True

        self._field_visible = False

        self._page_visible = True
        self._page_nowPage = 0
        
        self._path_visible = True

        self._image_visible = False

        self._embedColor = discord.Color.dark_orange()

        ##추가
        self._myPath = quizListPath #탐색 경로 저장용
        self._absoluteMap = dict() #icon 파싱값 등을 포함한 절대적이름
        self.getMainList()

    def getMainList(self):

        allPath = self._myPath #현재 절대 경로

        viewPath = getViewPath(allPath)

        self._path_text = viewPath #패스 설정

        quizList = os.listdir(allPath) #현재 경로의 모든 퀴즈 가져오기

        self._main_text = [] #메인 텍스트 초기화
        self._absoluteMap.clear()

        for tmpFile in quizList: #쓸모없는 파일은 무시
            if not os.path.isdir(allPath+tmpFile): #폴더가 아니면 패스
                continue #다음 파일로
            icon = getIcon(tmpFile) #파일명으로 아이콘 가져와보기
            fileName = tmpFile.split("&")[0] #실제 파일명만 긁어오기
            showText = icon+" "+fileName #표시할 항목명
            self._absoluteMap[showText] = tmpFile #절대 이름 설정
            self.addMain(showText) #메인 텍스트에 추가

        self._notice_text = Config.EMOJI_ICON.ICON_BOX+ "　항목 수 : **" + str(len(self._absoluteMap.keys())) + "개**"

    async def action(self, reaction, user, selectorData): 
        await super().action(reaction, user, selectorData)

        emoji = reaction.emoji
        message = reaction.message
        guild = message.guild

        number = Config.getNumberFromEmoji(emoji) #이모지에 대응하는 정수값 가져옴
        if number != -1: #숫자 이모지라면
            
            fileIndex = self._page_nowPage * LIST_PER_PAGE #선택한 항목의 인덱스를 가져옴
            fileIndex += number - 1
            selectName = self._main_text[fileIndex] #선택한 항목의 표시 이름
            absoluteName = self._absoluteMap[selectName] #실제 이름 가져옴

            newPath = self._myPath + absoluteName + "/" #새로운 탐색 절대 경로
            option = getOption(self._myMessage.guild)
            await showFrame(message, QuizInfoFrame(newPath, option), isPopUp=True) #퀴즈 선택 프레임 열기


class QuizInfoFrame(QFrame):

    def __init__(self, quizPath, option):
        super().__init__() #frame 초기화

        tmpStr = quizPath.split("/")
        quizFileName = tmpStr[len(tmpStr)-2] #퀴즈 이름
        icon = getIcon(quizFileName) # 아이콘 가져오기
        quizName = quizFileName.split("&")[0] #실제 퀴즈명만 긁어오기

        self._title_text = chr(173)+"[　　　　"+ icon + " " + quizName + "　　　　]"

        self._sub_visible = True
        self._sub_text = "퀴즈 정보를 불러올 수 없습니다."

        self._notice_visible = True
        self._notice_text = Config.EMOJI_ICON.ICON_WARN + " 퀴즈 도중에는 설정을 변경하실 수 없습니다."

        self._field_visible = False

        self._page_visible = False

        self._path_visible = True
        self._path_text = getViewPath(quizPath)

        self._image_visible = False

        self.addMain("퀴즈 시작")
        self.addMain("순위 확인")
        self.addMain("설정으로 이동")

        self._embedColor = discord.Color.orange()

        ##추가
        self._option = option
        self._myPath = quizPath
        self._quizPath = quizPath
        self._quizName = quizName #퀴즈명
        self._quizIcon = icon #퀴즈 아이콘
        self._quizTypeName = ""
        self._quizCnt = len(os.listdir(self._myPath)) - 1
        self._quizDesc = ""
        self._quizRepeatCnt = 1 #소리 반복 횟수 기본 1
        self._quizTopNickname = "" #1등 별명

        self._started = False

        self.loadQuizInfo()
    
    def loadQuizInfo(self): #퀴즈 정보 로드
        infoPath = self._myPath + "info.txt"

        infoText = chr(173)+"\n"+Config.EMOJI_ICON.ICON_LIST + " **퀴즈 설명**:\n"
        try:
            f = open(infoPath, 'r', encoding="utf-8" )
            while True:
                line = f.readline()
                if not line: break

                if line.startswith("&repeatCnt: "):
                    repeatCnt = line.replace("&repeatCnt: ", "").strip()
                    self._quizRepeatCnt = int(repeatCnt)
                elif line.startswith("&topNickname: "):
                    topNickname = line.replace("&topNickname: ", "").strip()
                    self._quizTopNickname = topNickname
                elif line.startswith("&typeName: "):
                    typeName = line.replace("&typeName: ", "").strip()
                    self._quizTypeName = typeName
                elif line.startswith("&quizCount: "):
                    quizCount = line.replace("&quizCount: ", "").strip()
                    self._quizCnt = int(quizCount)
                else:
                    infoText += line
            f.close()
        except:
            Config.LOGGER.error("파일 로드 에러, "+infoPath)
            Config.LOGGER.error(traceback.format_exc())
            infoText = "퀴즈 정보를 불러올 수 없습니다."
            
        
        self._quizDesc = infoText

        subText = Config.EMOJI_ICON.ICON_TYPE + "　퀴즈 유형:　**" + self._quizTypeName + "**" + "\n"
        subText += Config.EMOJI_ICON.ICON_BOX + "　문제 수　:　**" + str(self._quizCnt) + "개**" + "\n"
        subText += chr(173)+"\n"+"" + self._quizDesc + "\n" +chr(173) + "\n"
        
        self._sub_text = subText

    def paint(self, message):
        super().paint(message)
        subText = Config.EMOJI_ICON.ICON_TYPE + "　퀴즈 유형:　**" + self._quizTypeName + "**" + "\n"
        subText += Config.EMOJI_ICON.ICON_BOX + "　문제 수　:　**" + str(self._quizCnt) + "개**" + "\n"
        subText += chr(173)+"\n"+"" + self._quizDesc + "\n" +chr(173) + "\n"

        option = self._option
        hintTypeDisplay = getDisplayOption(OPTION_TYPE.HINT_TYPE, option._hintType)
        skipTypeDisplay = getDisplayOption(OPTION_TYPE.SKIP_TYPE, option._skipType)
        trimLengthDisplay = getDisplayOption(OPTION_TYPE.TRIM_LENGTH, option._trimLength)
        repeatCountDisplay = getDisplayOption(OPTION_TYPE.REPEAT_COUNT, option._repeatCount)

        subText +=  chr(173) + "\n"
        subText += Config.EMOJI_ICON.ICON_SETTING+ "　**현재 설정 값**\n" + chr(173) + "\n"
        subText += Config.EMOJI_ICON.ICON_HINT + "　힌트 방식　**"+ chr(173) + chr(173) + chr(173) + chr(173) + chr(173) + "　"+ str(hintTypeDisplay[0]) +"**\n"
        subText += Config.EMOJI_ICON.ICON_SKIP + "　스킵 방식　**"+ chr(173) + chr(173) + chr(173) + chr(173) + chr(173)  + "　"+ str(skipTypeDisplay[0]) +"**\n"
        subText += Config.EMOJI_ICON.ICON_SONG + "　노래 길이　**"+ chr(173) + chr(173) + chr(173) + chr(173) + chr(173) + "　"+ str(trimLengthDisplay[0]) +"**\n"
        subText += Config.EMOJI_ICON.ICON_REPEAT + "　반복 재생　**"+ chr(173) + chr(173) + chr(173) + chr(173) + chr(173) + "　"+ str(repeatCountDisplay[0]) +"**\n"

        self._sub_text = subText

    async def action(self, reaction, user, selectorData): 
        await super().action(reaction, user, selectorData)

        emoji = reaction.emoji
        message = reaction.message
        guild = message.guild

        number = Config.getNumberFromEmoji(emoji) #이모지에 대응하는 정수값 가져옴
        if number != -1: #숫자 이모지라면
            if number == 1: #1번은 퀴즈 시작
                if not self._started:
                    self._started = True
                    await fun_startQuiz(self, user)
            elif number == 2: #2번은 순위 확인
                scoreboard = getScoreboard(guild.id, self._quizName)
                await showFrame(message, ScoreboardFrame(scoreboard), isPopUp=True) #순위 확인창 표시
            elif number == 3: #3번은 설정
                await showFrame(message, SettingFrame(), isPopUp=True) #설정창 표시

class QuizUIFrame(QFrame): #퀴즈 ui 프레임

    def __init__(self, quizPath, channel):
        super().__init__() #frame 초기화

        tmpStr = quizPath.split("/")
        quizFileName = tmpStr[len(tmpStr)-2] #퀴즈 이름
        icon = getIcon(quizFileName) # 아이콘 가져오기
        quizName = quizFileName.split("&")[0] #실제 퀴즈명만 긁어오기

        self._title_text = chr(173)+"[　　　　"+ icon + " " + quizName + "　　　　]"

        self._sub_visible = True #남은시간 표시할 곳
        self._sub_text = ""

        self._main_visible = False

        self._notice_visible = True
        self._notice_text = "" #텍스트 기반 퀴즈용

        self._field_visible = True #점수판

        self._customFooter_visible = True #남은 문제 수

        self._page_visible = False
        self._path_visible = False

        self._image_visible = False

        self.addMain("")
        self.addMain("")
        self.addMain("")

        self._embedColor = discord.Color.light_grey()

        ##추가
        self._useFormat = False

        self._option = None

        self._myPath = quizPath
        self._quizOwner = bot.user #퀴즈 주최자, 기본값은 봇
        self._quizPath = quizPath
        self._quizName = quizName #퀴즈명
        self._quizIcon = icon #퀴즈 아이콘
        self._quizTypeName = ""
        self._quizCnt = len(os.listdir(self._myPath)) - 1
        self._quizDesc = ""
        self._quizRepeatCnt = 1 #소리 반복 횟수 기본 1
        self._quizTopNickname = "" #1등 별명
        self._quizRound = 0 #현재 라운드

        self._quizLeftTime = 40 #남은 시간
        self._quizMaxTime = 40 #총 시간

        self._vote_hint = [] #현재 힌트 투표한 사람 목록
        self._vote_hint_min = 1 #최저 힌트 투표 수
        self._hint_use = False
        self._fun_requestHint = None

        self._vote_skip = [] #현재 스킵 투표한 사람 목록
        self._vote_skip_min = 1 #최저 스킵 투표 수
        self._skip_use = False
        self._fun_skip = None
        
        self._fun_stop = None
        self._stop_use = False

        self._chatChannel = channel

        self.loadQuizInfo()

    def paint(self, message):
        super().paint(message)
        if self._useFormat:
            self._title_visible = True
            self._title_text = chr(173)+"[　　　　"+ self._quizIcon + " " + self._quizName + "　　　　]"

            self._sub_visible = True
            self._sub_text = getClockIcon(self._quizLeftTime, self._quizMaxTime) +"　남은 시간:　**" + str(int(self._quizLeftTime)) + "초**\n" + chr(173) + "\n"
            self._sub_text += Config.EMOJI_ICON.ICON_TIP + "\n"
            self._sub_text += Config.EMOJI_ICON.ICON_HINT + "　**!힌트** - 힌트 요청\n"
            self._sub_text += Config.EMOJI_ICON.ICON_SKIP + "　**!스킵** - 스킵 요청\n"
            self._sub_text += Config.EMOJI_ICON.ICON_STOP + "　**!중지** - 퀴즈 중지\n"
            self._sub_text += Config.EMOJI_ICON.ICON_INFO + "　또는 하단의 이모지를 클릭해주세요."

            self._customFooter_visible = True
            self._customFooter_text = Config.EMOJI_ICON.ICON_BOX+" 문제: " + str(self._quizRound) + " / "+str(self._quizCnt) +"　|　" 


            hintStr =  getDisplayOption(OPTION_TYPE.HINT_TYPE, self._option._hintType)[0]
            self._customFooter_text += Config.EMOJI_ICON.ICON_HINT+" 힌트: " + hintStr

            self._customFooter_text += "　" + chr(173) + "　"

            skipStr =  getDisplayOption(OPTION_TYPE.SKIP_TYPE, self._option._skipType)[0]
            self._customFooter_text += Config.EMOJI_ICON.ICON_SKIP+" 스킵: " + skipStr

    def loadQuizInfo(self): #퀴즈 정보 로드

        infoPath = self._myPath + "info.txt"

        infoText = ""
        try:
            f = open(infoPath, 'r', encoding="utf-8" )
            while True:
                line = f.readline()
                if not line: break

                if line.startswith("&repeatCnt: "):
                    repeatCnt = line.replace("&repeatCnt: ", "").strip()
                    self._quizRepeatCnt = int(repeatCnt)
                elif line.startswith("&topNickname: "):
                    topNickname = line.replace("&topNickname: ", "").strip()
                    self._quizTopNickname = topNickname
                elif line.startswith("&typeName: "):
                    typeName = line.replace("&typeName: ", "").strip()
                    self._quizTypeName = typeName
                elif line.startswith("&quizCount: "):
                    quizCount = line.replace("&quizCount: ", "").strip()
                    self._quizCnt = int(quizCount)
                else:
                    infoText += line
            f.close()
        except:
            Config.LOGGER.error("파일 로드 에러, "+infoPath)
            Config.LOGGER.error(traceback.format_exc())
            infoText = "퀴즈 정보를 불러올 수 없습니다."
        
        self._quizDesc = infoText

    async def update(self): #새로고침
        isSuc = await showFrame(self._myMessage, self, isPopUp=False)
        if not isSuc:
            Config.LOGGER.error("퀴즈 UI 업데이트 에러, UI 재생성")
            Config.LOGGER.error(traceback.format_exc())
            quizUIEmbed = discord.Embed(title="UI 재생성 중...", url=None, description="잠시만 기다려주세요.\n", color=discord.Color.blue())
            quizUIEmbed.set_author(name=bot.user.name, url="",
                        icon_url=bot.user.avatar_url)
            quizUIEmbed.remove_author()

            quizUIMessage = await self._chatChannel.send(embed=quizUIEmbed)

            asyncio.ensure_future(quizUIMessage.add_reaction(Config.EMOJI_ICON.ICON_HINT)) #힌트
            asyncio.ensure_future(quizUIMessage.add_reaction(Config.EMOJI_ICON.ICON_SKIP)) #스킵
            asyncio.ensure_future(quizUIMessage.add_reaction(Config.EMOJI_ICON.ICON_STOP)) #중지

            await showFrame(quizUIMessage, self, isPopUp=False) #띄우기

    def setFunction(self, fun_requestHint, fun_skip, fun_stop): #함수 설정
        self._fun_requestHint = fun_requestHint #힌트 요청
        self._fun_skip = fun_skip #스킵
        self._fun_stop = fun_stop #중지

    def initRound(self, voiceChannel): #매 라운드 초기화
        voicePeopleCnt = len(voiceChannel.voice_states) #보이스 채널의 현재 인원

        self._vote_hint_use = False
        self._hint_use = False
        self._vote_hint = [] #힌트 투표수
        if self._option._hintType == 0: #투표 유형이면
            self._vote_hint_min = voicePeopleCnt // 2 #최저 힌트 투표 수
        elif self._option._hintType == 1: #주최자 유형이면
            self._vote_hint_min = 1 #주최자 1명이면됨
        elif self._option._hintType == 2: #자동 유형이면
            self._vote_hint_min = 10000 #수동 힌트 요청 못쓰게
        elif self._option._hintType == 4: #멀티형이면
            self._vote_hint_min = 1 #아무나 투표하면 힌트요청

        self._vote_skip_use = False
        self._skip_use = False
        self._vote_skip = []
        self._vote_skip_min = voicePeopleCnt // 2 #최저 스킵 투표 수
        if self._option._skipType == 0: #투표 유형이면
            self._vote_skip_min = voicePeopleCnt // 2 #최저 힌트 투표 수
        elif self._option._skipType == 1: #주최자 유형이면
            self._vote_skip_min = 1 #주최자 1명이면됨
 

    def setOption(self, option):
        self._option = option #옵션 설정

    async def hintAction(self, playerName, message):
        option = self._option

        if self._hint_use:
            return

        if playerName in self._vote_hint: #이미 투표했다면
            return

        if option._hintType == 0: #투표 타입일 시
            self._vote_hint.append(playerName) #투표 처리
            asyncio.ensure_future(message.channel.send("```"+playerName.display_name+" 님이 힌트 요청에 투표하셨습니다.　"+chr(173)+"　"+chr(173)+"　"+Config.EMOJI_ICON.ICON_HINT+"　"+str(len(self._vote_hint))+" / "+str(self._vote_hint_min)+"```"))
        elif option._hintType == 1: #주최자 타입일 시
            if self._quizOwner == playerName: #주최자인 경우에만
                self._vote_hint.append(playerName) #투표 처리
        elif option._hintType == 3: #사용불가일 시
            return
        elif option._hintType == 4: #멀티플레이
            if len(self._vote_hint) == 0: #투표 아무도 안했다면
                self._vote_hint.append(playerName) #투표 처리

        if len(self._vote_hint) >= self._vote_hint_min: #최저 투표수를 넘었다면
            self._hint_use = True
            asyncio.ensure_future(self._fun_requestHint()) #힌트 요청

    async  def skipAction(self, playerName, message):

        option = self._option

        if self._skip_use: return

        if playerName in self._vote_skip: #이미 투표했다면
            return

        if option._skipType == 0: #투표 타입일 시
            self._vote_skip.append(playerName) #투표 처리
            asyncio.ensure_future(message.channel.send("```"+playerName.display_name+" 님이 스킵하기에 투표하셨습니다.　"+chr(173)+"　"+chr(173)+"　"+Config.EMOJI_ICON.ICON_SKIP+"　"+str(len(self._vote_skip))+" / "+str(self._vote_skip_min)+"```"))
        elif option._skipType == 1: #주최자 타입일 시
            if self._quizOwner == playerName: #주최자인 경우에만
                self._vote_skip.append(playerName) #투표 처리
        elif option._skipType == 2: #사용불가일 시
            return

        if len(self._vote_skip) >= self._vote_skip_min: #최저 투표수를 넘었다면
            self._skip_use = True
            asyncio.ensure_future(self._fun_skip()) #스킵

    async def stopAction(self, playerName, message):
        if self._stop_use: return

        if self._quizOwner == playerName: #주최자인 경우에만
            asyncio.ensure_future(self._fun_stop()) #중지

    async def action(self, reaction, user, selectorData): 
        emoji = reaction.emoji
        message = reaction.message
        guild = message.guild
        playerName = user

        if emoji == Config.EMOJI_ICON.ICON_HINT: #각 경우에 맞게 행동
            await self.hintAction(playerName, message) # 힌트 사용

        elif emoji == Config.EMOJI_ICON.ICON_SKIP: 
            await self.skipAction(playerName, message) # 스킵

        elif emoji == Config.EMOJI_ICON.ICON_STOP:
            await self.stopAction(playerName, message) # 중지


class ScoreboardFrame(QFrame): #순위표 표시 화면
    def __init__(self, scoreboard):
        super().__init__() #frame 초기화
        self._title_text = chr(173)+"[　　　　" + Config.getMedalFromNumber(0) + " 순위표" +" 　　　　]"

        self._sub_visible = True
        self._sub_text = Config.EMOJI_ICON.ICON_LIST + " " + str(scoreboard._quizName) + " 퀴즈에 대한 순위표입니다."

        self._notice_visible = True
        #self._notice_text = Config.EMOJI_ICON.ICON_NOTICE+" 순위표는 현재 디스코드 서버내의 유저만 표시됩니다."

        self._field_visible = False

        self._main_visible = True

        self._page_visible = True
        self._page_nowPage = 0
        
        self._path_visible = True
        self._path_text = str(scoreboard._quizName)+"/순위표/"

        self._image_visible = False

        self._embedColor = discord.Color.purple()

        ##추가
        self._scoreboard = scoreboard
        
        self.setScore() #main에 scoreboard 표시

    def setScore(self):
        
        self._main_text.clear()
        scoreMap = self._scoreboard._score

        if len(scoreMap.keys()) == 0: #점수 기록이 없다면
            self.addMain("기록이 존재하지 않습니다.")
        else:
            for playerName in scoreMap.keys():
                stat = scoreMap[playerName]
                self.addMain(playerName + "　**" + chr(173) + "　"+ chr(173) + str(stat._topScore)+ "점**")

    async def action(self, reaction, user, selectorData): 
        await super().action(reaction, user, selectorData)


class MultiplayScoreboardFrame(ScoreboardFrame): #순위표 표시 화면
    def __init__(self, multiplayScoreboard):
        super().__init__(multiplayScoreboard) #frame 초기화
        self._title_text = chr(173)+"[　　　　" + Config.getMedalFromNumber(0) + " 순위표" +" 　　　　]"

        self._sub_visible = True
        self._sub_text = Config.EMOJI_ICON.ICON_LIST + " " + str(multiplayScoreboard._quizName) + " 퀴즈에 대한 순위표입니다."

        self._notice_visible = True
        #self._notice_text = Config.EMOJI_ICON.ICON_NOTICE+" 순위표는 현재 디스코드 서버내의 유저만 표시됩니다."

        self._field_visible = False

        self._main_visible = True

        self._page_visible = True
        self._page_nowPage = 0
        
        self._path_visible = True
        self._path_text = str(multiplayScoreboard._quizName)+"/순위표/"

        self._image_visible = False

        self._embedColor = discord.Color.purple()

        ##추가
        self._scoreboard = multiplayScoreboard
        
        self.setScore() #main에 scoreboard 표시

    def setScore(self):
        
        self._main_text.clear()
        scoreMap = self._scoreboard._score

        if len(scoreMap.keys()) == 0: #점수 기록이 없다면
            self.addMain("기록이 존재하지 않습니다.")
        else:
            for guildID in scoreMap.keys():
                multiplayStat = scoreMap[guildID]
                self.addMain(str(multiplayStat._guildName) + "　**" + chr(173) + "　"+ chr(173) + str(multiplayStat._multiStat_win)+ " 승　|　"+str(multiplayStat._multiStat_defeat)+" 패"+"**")

    async def action(self, reaction, user, selectorData): 
        await super().action(reaction, user, selectorData)



class MultiplayFrame(QFrame): #멀티플레이 화면
    def __init__(self, multiplayPath):
        super().__init__() #frame 초기화
        self._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_MULTIPLAY +" 멀티 플레이　　　　]"

        self._sub_visible = True
        self._sub_text = Config.EMOJI_ICON.ICON_LIST + "**퀴즈봇2 를 사용하는 다른 디스코드 서버와 대결을 할 수 있습니다.**\n"
        self._sub_text += "**자신의 디스코드 서버 인원과 협력하여 전적을 올려보세요!**\n"
        self._sub_text += chr(173)+"\n"+ Config.EMOJI_ICON.ICON_TIP + "　**플레이할 카테고리를 선택해주세요.**\n"

        self._main_visible = True

        self._notice_visible = True
        self._notice_text = ""
    

        self._field_visible = False

        self._customFooter_visible = False

        self._page_visible = True
        
        self._path_visible = True
        self._path_text = "멀티 플레이/"

        self._image_visible = False

        self._embedColor = discord.Color.greyple()

        ##추가
        self._myPath = multiplayPath #탐색 경로 저장용
        self._absoluteMap = dict() #icon 파싱값 등을 포함한 실제이름
        self.getMainList()

    def paint(self, message):
        super().paint(message)
        self._sub_visible = True
        self._sub_text = Config.EMOJI_ICON.ICON_LIST + "**퀴즈봇2 를 사용하는 다른 디스코드 서버와 대결을 할 수 있습니다.**\n"
        self._sub_text += "**자신의 디스코드 서버 인원과 협력하여 전적을 올려보세요!**\n"
        self._sub_text += chr(173)+"\n"+ Config.EMOJI_ICON.ICON_TIP + "　**플레이할 카테고리를 선택해주세요.**\n"
        self.getMainList() #매칭중인 큐 수를 새로고침하기 위해 불러와야함

    def getMainList(self):

        viewPath = "멀티 플레이/" #표시용 패스
        
        allPath = self._myPath #절대 경로

        self._path_text = viewPath #패스 표시

        quizList = os.listdir(allPath) #해당 경로의 모든 퀴즈 가져오기

        self._main_text = [] #메인 텍스트 초기화
        self._absoluteMap.clear()

        for tmpFile in quizList: #쓸모없는 파일은 무시
            if not os.path.isdir(allPath+tmpFile): #폴더가 아니면 패스
                continue #다음 파일로
            icon = Config.EMOJI_ICON.ICON_QUIZ_DEFAULT #아이콘, 기본은 물음표 모양
            icon = getIcon(tmpFile) #파일명으로 아이콘 가져와보기
            fileName = tmpFile.split("&")[0] #실제 파일명만 긁어오기
            showText = icon+" "+fileName #표시할 항목명

            if fileName in matchingCategory: #매칭 카테고리에 있는 항목명이면
                matchingQueue = matchingCategory[fileName] #큐 가져옴
                matchingCnt = len(matchingQueue) #매칭 중인 수
                showText += "　[　**"+Config.EMOJI_ICON.ICON_NET+" "+str(matchingCnt)+"**　]"

            self._absoluteMap[showText] = tmpFile #절대 이름 설정
            self.addMain(showText) #메인 텍스트에 추가

        self._notice_text = Config.EMOJI_ICON.ICON_BOX+ "　항목 수 : **" + str(len(self._absoluteMap.keys())) + "개**"

    async def action(self, reaction, user, selectorData): 
        await super().action(reaction, user, selectorData)

        emoji = reaction.emoji
        message = reaction.message
        guild = message.guild

        number = Config.getNumberFromEmoji(emoji) #이모지에 대응하는 정수값 가져옴
        if number != -1: #숫자 이모지라면

            fileIndex = self._page_nowPage * LIST_PER_PAGE #선택한 목록의 인덱스를 가져옴
            fileIndex += number - 1

            if fileIndex >= len(self._main_text):
                return

            selectName = self._main_text[fileIndex] #선택한 항목의 표시 이름
            absoluteName = self._absoluteMap[selectName] #실제 이름 가져옴

            newPath = self._myPath + absoluteName + "/" #새로운 탐색 절대 경로
            await showFrame(message, MultiplayInfoFrame(newPath), isPopUp=True) #멀티플레이 정보 프레임 열기


class MultiplayInfoFrame(QFrame):

    def __init__(self, quizPath):
        super().__init__() #frame 초기화

        tmpStr = quizPath.split("/")
        quizFileName = tmpStr[len(tmpStr)-2] #퀴즈 이름
        icon = getIcon(quizFileName) # 아이콘 가져오기
        quizName = quizFileName.split("&")[0] #실제 퀴즈명만 긁어오기

        self._title_text = chr(173)+"[　　　　"+ icon + " " + quizName + "　　　　]"

        self._sub_visible = True
        self._sub_text = "퀴즈 정보를 불러올 수 없습니다."

        self._notice_visible = True

        if not quizName in matchingCategory.keys(): #해당 퀴즈에 대해 생성된 매칭큐가 없다면
            matchingCategory[quizName] = [] #새롭게 생성
        matchingQueue = matchingCategory[quizName]

        self._notice_text = Config.EMOJI_ICON.ICON_MULTIPLAY + "　" + quizName +" 카테고리를 매칭중인 서버 **" + str(len(matchingQueue)) + "개**"

        self._field_visible = False

        self._page_visible = False

        self._path_visible = True
        self._path_text = "멀티플레이/" + quizName + "/" #표시용 경로 설정

        self._image_visible = False

        self.addMain("매칭 시작")
        self.addMain("순위 확인")

        self._embedColor = discord.Color.greyple()

        ##추가
        self._option = optionMap["-1"] #멀티용 공용 옵션 가져오기
        self._myPath = quizPath
        self._quizPath = quizPath
        self._quizName = quizName #퀴즈명
        self._quizIcon = icon #퀴즈 아이콘
        self._quizTypeName = ""
        self._quizCnt = 0
        self._quizDesc = ""
        self._quizRepeatCnt = 1 #소리 반복 횟수 기본 1
        self._quizTopNickname = "" #1등 별명
        self._searchPathList = [] #멀티용 퀴즈들 위치

        self._stopFlag = True
        self._receive = [] #받은 메시지 저장용 큐
        self._target = None
        self._guildID = ""
        self._ready = False
        self._waitSec = 0
        self._pathList = []

        self.loadQuizInfo()
    
    def loadQuizInfo(self): #퀴즈 정보 로드
        infoPath = self._myPath + "info.txt"

        infoText = chr(173)+"\n"+Config.EMOJI_ICON.ICON_LIST + " **퀴즈 설명**:\n"
        isPathList = False
        pathList = []
        try:
            f = open(infoPath, 'r', encoding="utf-8" )
            while True:
                line = f.readline()
                if not line: break

                if line.startswith("&repeatCnt: "):
                    repeatCnt = line.replace("&repeatCnt: ", "").strip()
                    self._quizRepeatCnt = int(repeatCnt)
                elif line.startswith("&topNickname: "):
                    topNickname = line.replace("&topNickname: ", "").strip()
                    self._quizTopNickname = topNickname
                elif line.startswith("&typeName: "):
                    typeName = line.replace("&typeName: ", "").strip()
                    self._quizTypeName = typeName
                elif line.startswith("&pathList"):
                    isPathList = True #퀴즈 경로 설정으로
                elif line.startswith("&endPathList"):
                    isPathList = False #퀴즈 경로 설정 중지
                elif line.startswith("&typeName: "):
                    typeName = line.replace("&typeName: ", "").strip()
                    self._quizTypeName = typeName
                else:
                    if isPathList: #퀴즈 경로 설정중이면
                        pathList.append(Config.QUIZ_PATH + line.strip())
                    else:
                        infoText += line
            f.close()
        except:
            Config.LOGGER.error("파일 로드 에러, "+infoPath)
            Config.LOGGER.error(traceback.format_exc())
            infoText = "퀴즈 정보를 불러올 수 없습니다."
            
        self._pathList = pathList
        self._quizDesc = infoText

        subText = Config.EMOJI_ICON.ICON_TYPE + "　퀴즈 유형:　**" + self._quizTypeName + "**" + "\n"
        #subText += Config.EMOJI_ICON.ICON_BOX + "　문제 수　:　**" + str(self._quizCnt) + "개**" + "\n"
        subText += chr(173)+"\n"+"" + self._quizDesc + "\n" +chr(173) + "\n"
        
        self._sub_text = subText

    def paint(self, message):
        super().paint(message)

    def destructor(self, message):
        self.stopMatch()

    def stopMatch(self):
        self._stopFlag = True
        matchingQueue = matchingCategory[self._quizName]
        if self in matchingQueue:
            matchingQueue.remove(self) #큐에서 삭제

    async def update(self): #새로고침
        try:
            isSuc = await showFrame(self._myMessage, self, isPopUp=False)
            if not isSuc:
                self._stopFlag =True
        except:
            self._stopFlag = True
            Config.LOGGER.error("매칭 메시지 에러 발생")
            Config.LOGGER.error(traceback.format_exc())

    async def startMatch(self, owner, selectorData):
        if not self._stopFlag: #이미 매칭중이면
            return

        if owner.voice == None:
            self._notice_text = Config.EMOJI_ICON.ICON_WARN + " 먼저 음성 채널에 참가해주세요."
            await self.update()
            return

        # bot의 해당 길드에서의 음성 대화용 객체
        voice = get(bot.voice_clients, guild=self._myMessage.channel.guild)
        if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
            self._notice_text = Config.EMOJI_ICON.ICON_WARN + "현재 진행중인 퀴즈를 중지해주세요.\n　 "+Config.EMOJI_ICON.ICON_STOP+" 버튼 클릭 또는 !중지"
            await self.update()
            return


        Config.LOGGER.info("매칭 탐색 시작 "+ str(self._quizName) +", " + str(self._myMessage.guild.name))
        self._stopFlag = False
        voiceChannel = owner.voice.channel  # 호출자의 음성 채널 얻기

        voice = get(bot.voice_clients, guild=self._myMessage.channel.guild)
        if voice == None or voice.is_connected():
            voice = await voiceChannel.connect()  # 음성 채널 연결후 해당 객체 반환

        if voice == None: 
            self._notice_text = Config.EMOJI_ICON.ICON_WARN + " 음성 객체를 가져오는데 실패했습니다.."
            await self.update()
            return

        voice.play(discord.FFmpegPCMAudio(Config.BGM_PATH + "MATCHING.mp3"))

        if not self._quizName in matchingCategory.keys(): #해당 퀴즈에 대해 생성된 매칭큐가 없다면
            matchingCategory[self._quizName] = [] #새롭게 생성
        matchingQueue = matchingCategory[self._quizName]
        matchingQueue.append(self) #큐 등록
        self._receive = []
        self._ready = False
        self._guild = self._myMessage.channel.guild #길드 등록

        isConnecting = False #연결 시도 중 여부

        clockCnt = 11
        while True:
            if self._stopFlag: 
                if self in matchingQueue:
                    matchingQueue.remove(self) #큐에서 삭제
                voice = get(bot.voice_clients, guild=self._myMessage.channel.guild)
                if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
                    await voice.disconnect()
                try:
                    self._notice_text = Config.EMOJI_ICON.ICON_MULTIPLAY + "　" + self._quizName +" 카테고리를 매칭중인 서버 **" + str(len(matchingQueue)) + "개**"
                    #await self.update()
                except:
                    Config.LOGGER.error("매칭 취소 메시지 표시 에러")

                return

            if len(selectorData._frameStack) > 0:# 프레임 존재시
                topFrame = selectorData._frameStack[len(selectorData._frameStack) - 1] #최상위 프레임 가져옴
                if topFrame != self: #최상위 프레임이 자신이 아니면
                    self.stopMatch()
                    continue
            else: #프레임 없으면
                self.stopMatch()
                continue

            if owner.voice == None: #큐  돌린사람 보이스채널 나가면
                self._stopFlag = True  #큐 중지
                continue

            self._waitSec += 1
            clockCnt -= 1
            if clockCnt < 0: clockCnt = 11
            self._notice_text = getClockIcon(clockCnt,11) + "　"#아이콘 표시

            if len(self._receive) > 0: #메시지함에 뭐라도 있으면
                netMessage = self._receive[0] #가장 top 메시지 가져옴
                del self._receive[0] #가져오면 삭제
                
                sender = netMessage._sender
                messageType = netMessage._NET_MESSAGE_TYPE

                if messageType == NET_MESSAGE_TYPE.REQUEST: #연결 요청일 경우
                    self.sendNetMessage(sender, NET_MESSAGE_TYPE.ACK) #연결 수락 보냄
                    self._notice_text += "대전 상대를 찾았습니다. 연결 요청 중..."
                    
                elif messageType == NET_MESSAGE_TYPE.ACK: #연결 요청 수락일 경우
                    self.sendNetMessage(sender, NET_MESSAGE_TYPE.CONNECT) #연결 시작 보냄
                    self._notice_text += "대전 상대와 연결 중..."

                elif messageType == NET_MESSAGE_TYPE.CONNECT: #연결 시작일 경우
                    self._notice_text = Config.EMOJI_ICON.ICON_TYPE_MULTIPLAY+"　상대의 응답을 기다리는 중입니다..."
                    self.sendNetMessage(sender, NET_MESSAGE_TYPE.CONNECT) #연결 시작 보냄
                    self._target = sender
                    await self.update()
                    break

            else: #메시지 온게 없다면
                
                myIndex = matchingQueue.index(self)
                if  myIndex < len(matchingQueue) - 1: #자신이 대기열의 마지막이 아니라면
                    if not isConnecting: #이미 연결중이 아니면
                        target = matchingQueue[myIndex + 1] #내 뒤에 있는 객체 가져옴
                        self.sendNetMessage(target, NET_MESSAGE_TYPE.REQUEST) #연결 요청 보냄
                        self._notice_text += "대전 상대를 찾았습니다... 연결 요청 중..."
                        isConnecting = True
                        try:
                            voice.play(discord.FFmpegPCMAudio(Config.BGM_PATH + "MATCH_FIND.mp3"))
                        except:
                            Config.LOGGER.error("BGM play error")
                else:
                    self._notice_text += "대전 상대를 탐색 중... " + str(self._waitSec) + "초"
                    isConnecting = False

            await self.update()
            await asyncio.sleep(1) #1초 대기

        if self._target != None:
            self._ready = True #준비 완료로 변경

            loopCnt = Config.MAX_CONNECTION / Config.SYNC_INTERVAL

            i = 0
            while not self._target._ready: #상대 준비 완료 대기
                await asyncio.sleep(Config.SYNC_INTERVAL) # 0.1초마다 확인
                i += 1
                if i > loopCnt:
                    self._notice_text += "연결 시간 초과"
                    await self.update()
                    break

            if not self._target._ready: #상대 준비 상태가 아니면
                await self.startMatch(owner)
            else:
                self.stopMatch() #매칭 중지
                self._notice_text = Config.EMOJI_ICON.ICON_FIGHT + " 대전 상대: **" + str(self._target._myMessage.guild.name) + "**\n" + chr(173) + "\n"
                self._notice_text += Config.EMOJI_ICON.ICON_CHECK+" 연결 성공! 대전을 시작합니다!"
                await self.update()
                Config.LOGGER.info("멀티플레이 시작 "+ str(self._quizName) +", " + str(self._myMessage.guild.name))
                await asyncio.sleep(3)
                await fun_startQuiz(self, owner, forceStart=True) #퀴즈 시작


    def sendNetMessage(self, target, messageType):
        
        netMessage = NetMessage(self, messageType)
        target._receive.insert(0, netMessage) #메시지 전송

    
    async def action(self, reaction, user, selectorData): 
        await super().action(reaction, user, selectorData)

        emoji = reaction.emoji
        message = reaction.message
        guild = message.guild

        number = Config.getNumberFromEmoji(emoji) #이모지에 대응하는 정수값 가져옴
        if number != -1: #숫자 이모지라면
            if number == 1: #1번은 퀴즈 시작
                await self.startMatch(user, selectorData) #매칭 시작
            elif number == 2: #2번은 순위 확인
                self.stopMatch()
                scoreboard = getMultiplayScoreboard(self._quizName)
                await showFrame(message, MultiplayScoreboardFrame(scoreboard), isPopUp=True) #순위 확인창 표시


class SettingFrame(QFrame): #옵션 화면
    def __init__(self):
        super().__init__() #frame 초기화
        self._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_SETTING +" 설정　　　　]"

        self._sub_visible = True
        self._sub_text = Config.EMOJI_ICON.ICON_LIST + " **퀴즈 옵션을 설정할 수 있습니다.**"

        self._notice_visible = False

        self._field_visible = False

        self._page_visible = True
        self._page_nowPage = 0
        
        self._path_visible = True
        self._path_text = "설정/"

        self._image_visible = False

        self._embedColor = discord.Color.dark_purple()
        self._option = None

    def paint(self, message):
        super().paint(message)
        self.applyCustomSetting(message)

    def applyCustomSetting(self, message): #설정값으로 표시

        guild = message.guild
        option = getOption(guild) #옵션 객체 가져오기
        self._option = option
        
        hintTypeDisplay = getDisplayOption(OPTION_TYPE.HINT_TYPE, option._hintType)
        skipTypeDisplay = getDisplayOption(OPTION_TYPE.SKIP_TYPE, option._skipType)
        trimLengthDisplay = getDisplayOption(OPTION_TYPE.TRIM_LENGTH, option._trimLength)
        repeatCountDisplay = getDisplayOption(OPTION_TYPE.REPEAT_COUNT, option._repeatCount)

        self._main_text = []
        self.addMain(Config.EMOJI_ICON.ICON_HINT + " 힌트 방식　**"+ chr(173) + "　"+ chr(173) + chr(173) + chr(173) + "　"+ chr(173) + "　"+ str(hintTypeDisplay[0]) +"**")
        self.addMain(Config.EMOJI_ICON.ICON_SKIP + " 스킵 방식　**"+ chr(173) +"　"+  chr(173) + chr(173) + chr(173) + "　"+ chr(173)  + "　"+ str(skipTypeDisplay[0]) +"**")
        self.addMain(Config.EMOJI_ICON.ICON_SONG + " 노래 길이　**"+ chr(173) + "　"+ chr(173) + chr(173) + chr(173) + "　"+ chr(173) + "　"+ str(trimLengthDisplay[0]) +"**")
        self.addMain(Config.EMOJI_ICON.ICON_REPEAT + " 반복 재생　**"+ chr(173) + "　"+ chr(173) + chr(173) + chr(173) + "　"+ chr(173) + "　"+ str(repeatCountDisplay[0]) +"**")
        self.addMain(Config.EMOJI_ICON.ICON_RESET + " 설정 초기화")
        self._option.save() #옵션 저장

    async def action(self, reaction, user, selectorData): 
        await super().action(reaction, user, selectorData)

        emoji = reaction.emoji
        message = reaction.message
        guild = message.guild

        number = Config.getNumberFromEmoji(emoji) #이모지에 대응하는 정수값 가져옴
        if number != -1: #숫자 이모지라면

            if number == 1: #각 경우에 맞게 행동
                await showFrame(message, SettingValueFrame(self._option, Config.EMOJI_ICON.ICON_HINT, "힌트 요청 방식", "힌트 방식", OPTION_TYPE.HINT_TYPE, 0, 2, 1), isPopUp=True) #카테고리 선택창 표시
            elif number == 2: 
                await showFrame(message, SettingValueFrame(self._option, Config.EMOJI_ICON.ICON_SKIP, "문제 건너뛰기 방식", "스킵 방식", OPTION_TYPE.SKIP_TYPE, 0, 1, 1), isPopUp=True) #설정창 표시
            elif number == 3: 
                await showFrame(message, SettingValueFrame(self._option, Config.EMOJI_ICON.ICON_SONG, "노래 길이", "노래 길이", OPTION_TYPE.TRIM_LENGTH, 5, 60, 5), isPopUp=True) #설정창 표시
            elif number == 4: 
                await showFrame(message, SettingValueFrame(self._option, Config.EMOJI_ICON.ICON_REPEAT, "노래 반복 재생 횟수", "반복 재생", OPTION_TYPE.REPEAT_COUNT, 1, 7, 1), isPopUp=True) #설정창 표시
            elif number == 5: 
                initOption(self._option) #option 객체 기본값으로
                await showTop(message, selectorData) #새로고침
        

class SettingValueFrame(QFrame): #설정 값 변경 화면
    def __init__(self, option, icon, settingTitle, settingName, OPTION_TYPE, min, max, interval):
        super().__init__() #frame 초기화
        self._title_text = chr(173)+"[　　　　"+ icon +" "+settingTitle+" 설정　　　　]"

        self._sub_visible = True
        self._sub_text = ""

        self._notice_visible = False

        self._field_visible = False

        self._main_visible = False

        self._page_visible = False
        self._page_nowPage = 0
        
        self._path_visible = True
        self._path_text = "설정/" + settingName +"/"

        self._image_visible = False

        self._embedColor = discord.Color.purple()

        ##추가
        self._option = option
        self._icon = icon
        self._settingTitle = settingTitle
        self._settingName = settingName
        self._optionType = OPTION_TYPE #옵션 타입
        self._min = min #최대값
        self._max = max #최저값
        self._interval = interval #값 변경 간격

    def paint(self, message):
        super().paint(message)
        self.applyCustomSetting(message)

    def applyCustomSetting(self, message): #설정값으로 표시
        
        self._sub_visible = True

        display = getDisplayOption(self._optionType, self.getValue())

        self._sub_text = self._icon + " "+(self._settingName)+"　**"+ chr(173) + chr(173) + chr(173) + chr(173) + chr(173) + "　"+ str(display[0]) + "**\n" + chr(173) + "\n"
        self._sub_text += Config.EMOJI_ICON.ICON_LIST + " " + str(display[1]) + "\n" + chr(173) + "\n" #정보 표시 

        self._notice_visible = True

        self._notice_text = Config.EMOJI_ICON.PAGE_PREV + Config.EMOJI_ICON.PAGE_NEXT + " 설정 값 변경　\n" + chr(173)


    def getValue(self):
        value = 0
        if self._optionType == OPTION_TYPE.HINT_TYPE:
            value = self._option._hintType
        elif self._optionType == OPTION_TYPE.SKIP_TYPE:
            value = self._option._skipType
        elif self._optionType == OPTION_TYPE.TRIM_LENGTH:
            value = self._option._trimLength
        elif self._optionType == OPTION_TYPE.REPEAT_COUNT:
            value = self._option._repeatCount
        return value


    async def action(self, reaction, user, selectorData): 
        Config.LOGGER.info(str(user) + ", " + str(reaction.emoji))

        emoji = reaction.emoji # 반응한 이모지 가져오기

        value = self.getValue() #값 가져오기

        isChange = False
        if emoji == Config.EMOJI_ICON.PAGE_NEXT: #다음 페이지면
            value += self._interval
            if value > self._max: value = self._max
            isChange = True
        elif emoji == Config.EMOJI_ICON.PAGE_PREV: #이전 페이지면
            value -= self._interval
            if value < self._min: value = self._min
            isChange = True

        if isChange: #갱신
            if self._optionType == OPTION_TYPE.HINT_TYPE:
                self._option._hintType = value
            elif self._optionType == OPTION_TYPE.SKIP_TYPE:
                self._option._skipType = value
            elif self._optionType == OPTION_TYPE.TRIM_LENGTH:
                self._option._trimLength = value
            elif self._optionType == OPTION_TYPE.REPEAT_COUNT:
                self._option._repeatCount = value
            await showFrame(self._myMessage, self, isPopUp=False) #새로고침



class PathNoteSelectFrame(QFrame): #패치노트 선택 화면
    def __init__(self, pathnotePath):
        super().__init__() #frame 초기화
        self._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_SEARCH +" 패치노트　　　　]"

        self._sub_visible = True
        self._sub_text = "**열람할 패치노트를 선택해주세요.**"

        self._notice_visible = True

        self._field_visible = False

        self._page_visible = True
        self._page_nowPage = 0
        
        self._path_visible = True

        self._image_visible = False

        self._embedColor = discord.Color.dark_teal()

        ##추가
        self._myPath = pathnotePath #탐색 경로 저장용
        self._absoluteMap = dict() #icon 파싱값 등을 포함한 실제이름
        self.getMainList()

    def getMainList(self):

        viewPath = "패치노트/" #표시용 패스
        
        allPath = self._myPath #절대 경로

        self._path_text = viewPath #패스 표시

        quizList = os.listdir(allPath) #해당 경로의 모든 패치노트 가져오기

        self._main_text = [] #메인 텍스트 초기화
        self._absoluteMap = dict()

        tmpList = []
        for tmpFile in quizList: #쓸모없는 파일은 무시
            if not tmpFile.endswith(".patchnote"): #패치노트 확장자 아니면
                continue #다음 파일로
            fileName = tmpFile.split("&")[0] #실제 파일명만 긁어오기
            fileName = tmpFile.replace(".patchnote", "") #확장자 떼어내기
            showText = fileName #표시할 항목명
            self._absoluteMap[showText] = tmpFile #절대 이름 설정
            tmpList.append(showText)
        
        self._main_text = [] #메인 텍스트 초기화
        i = len(tmpList) #역순 나열
        while i > 0:
            i -= 1
            text = tmpList[i]
            self.addMain(text) #메인 텍스트에 추가

        self._notice_text = Config.EMOJI_ICON.ICON_BOX+ "　항목 수 : **" + str(len(self._absoluteMap.keys())) + "개**"

    async def action(self, reaction, user, selectorData): 
        await super().action(reaction, user, selectorData)

        emoji = reaction.emoji
        message = reaction.message
        guild = message.guild

        number = Config.getNumberFromEmoji(emoji) #이모지에 대응하는 정수값 가져옴
        if number != -1: #숫자 이모지라면
            
            fileIndex = self._page_nowPage * LIST_PER_PAGE #선택한 목록의 인덱스를 가져옴
            fileIndex += number - 1

            if fileIndex >= len(self._main_text):
                return
            
            selectName = self._main_text[fileIndex] #선택한 항목의 표시 이름
            absoluteName = self._absoluteMap[selectName] #실제 이름 가져옴

            newPath = self._myPath + absoluteName #패치노트의 절대 경로
            await showFrame(message, PatchNoteInfoFrame(newPath), isPopUp=True) #퀴즈 선택 프레임 열기


class PatchNoteInfoFrame(QFrame):

    def __init__(self, notePath):
        super().__init__() #frame 초기화

        tmpStr = notePath.split("/")
        patchNoteFile = tmpStr[len(tmpStr)-1] #패치노트 파일명 이름
        noteName = patchNoteFile.replace(".patchnote", "") #실제 파일명만 긁어오기

        self._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_NOTE + " " + noteName + "　　　　]"

        self._sub_visible = True
        self._sub_text = "패치노트 내역를 불러올 수 없습니다."

        self._notice_visible = False

        self._field_visible = False

        self._page_visible = False

        self._path_visible = True

        self._path_text = "패치노트/" + noteName

        self._image_visible = False

        self._main_visible = False

        self._embedColor = discord.Color.dark_grey()
        
        ##추가
        self._myPath = notePath
        self.loadNoteInfo()
    
    def loadNoteInfo(self): #패치노트 로드
        infoPath = self._myPath

        infoText = ""
        try:
            f = open(infoPath, 'r', encoding="utf-8" )
            while True:
                line = f.readline()
                if not line: break

                infoText += line
            f.close()
        except:
            Config.LOGGER.error("파일 로드 에러, "+infoPath)
            infoText = "패치 내역를 불러올 수 없습니다."
        
        self._sub_text = infoText


class BotInfoFrame(QFrame): #봇 정보 화면
    def __init__(self):
        super().__init__() #frame 초기화
        self._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_QUIZBOT +" 봇 정보　　　　]"

        self._sub_visible = True
        self._sub_text = Config.EMOJI_ICON.ICON_LIST + "\n"
        self._sub_text += "봇 이름:　**" + "퀴즈봇2**\n"
        self._sub_text += "봇 버전:　**" + Config.VERSION + "**\n"
        self._sub_text += "제작 　:　**제육보끔#1916**\n"
        self._sub_text += "패치일 :　" + Config.LAST_PATCH + "\n"

        self._main_visible = False

        self._notice_visible = True
        self._notice_text = Config.EMOJI_ICON.ICON_PHONE + " **Contact**\n" +chr(173) + "\n"
        self._notice_text += Config.EMOJI_ICON.ICON_MAIL + " 이메일:　" + Config.EMAIL_ADDRESS + "\n"
        self._notice_text += Config.EMOJI_ICON.ICON_QUIZBOT + " 봇 공유링크:　"+Config.BOT_LINK + "\n"
        self._notice_text += Config.EMOJI_ICON.ICON_GIT + " 깃허브　 　:　"+"https://github.com/OtterBK/Quizbot" + "\n"
        #self._notice_text += Config.EMOJI_ICON.ICON_GIT + " Github:　https://github.com/OtterBK/Quizbot.git\n" 
        self._notice_text += chr(173) + "\n" + Config.EMOJI_ICON.ICON_FIX + "버그 제보, 개선점, 건의사항이 있다면 상단 이메일 주소로 알려주세요!\n" + chr(173) + "\n"
    

        self._field_visible = False

        self._customFooter_visible = True
        self._customFooter_text = Config.EMOJI_ICON.ICON_VERSION + " 버전: " + Config.VERSION

        self._page_visible = False
        
        self._path_visible = False

        self._image_visible = False

        self._embedColor = discord.Color.magenta() 

    async def action(self, reaction, user, selectorData): 
        await super().action(reaction, user, selectorData)


#utility
def initializing(_bot, _fun_startQuiz):
    global bot
    bot = _bot
    global fun_startQuiz
    fun_startQuiz = _fun_startQuiz

    loadOption() #옵션 불러오기
    loadRank() #랭크 데이터 불러오기

    global isSet
    isSet = True

def loadOption(): #옵션 파일 로드
    optionMap.clear()

    multiplayOption = QOption("-1") #멀티용
    multiplayOption._hintType = 4 #멀티
    multiplayOption._skipType = 2 #사용불가
    multiplayOption._trimLength = 35 #멀티플레이용 노래는 35초 
    multiplayOption._repeatCount = 1
    optionMap["-1"] = multiplayOption

    for optionFile in os.listdir(Config.OPTION_PATH):
        if optionFile.endswith(".json"): #확장자가 .option 인 경우에만
            optionFile = optionFile.replace(".json", "") #확장자 떼어내기
            option = QOption(optionFile)
            optionMap[optionFile] = option


def loadRank(): #랭크 파일 로드
    rankMap.clear()
    for guildID in os.listdir(Config.RANK_PATH):
        if(os.path.isdir(Config.RANK_PATH + guildID + "/")):  # 폴더인지 확인(폴더만 추출할거임)
            rankData = None
            if guildID.find(MULTIPLAY_RANKNAME) != -1:
                rankData = MultiplayRankData(guildID)
            else:
                rankData = RankData(guildID)
            rankMap[guildID] = rankData


def getOption(guildID): #해당 길드의 옵션파일 가져오기
    if guildID in optionMap: #이미 있다면
        return optionMap[guildID] 
    else:
        option = QOption(guildID) #없다면 생성 및 저장
        option.save()
        optionMap[guildID] = option
        return option


def getScoreboard(guildID, quizName): #순위표 가져오기
    rankData = None
    if not guildID in rankMap.keys(): #랭크 데이터 없다면
        rankData = RankData(guildID) #생성후 넣기
        rankMap[guildID] = rankData 
    else:
        rankData = rankMap[guildID]
    
    localRank = rankData._localRank
    scoreboard = None
    if not quizName in localRank.keys(): #퀴즈에 맞는 순위표가 없다면
        scoreboard = Scoreboard(guildID, quizName) #생성 후 넣어주기
        localRank[quizName] = scoreboard
    else:
        scoreboard = localRank[quizName]

    return scoreboard


def getMultiplayScoreboard(quizName): #멀티용 스코어보드 가져오기
    rankData = None
    if not MULTIPLAY_RANKNAME in rankMap.keys(): #랭크 데이터 없다면
        rankData = MultiplayRankData(MULTIPLAY_RANKNAME) #생성후 넣기
        rankMap[MULTIPLAY_RANKNAME] = rankData 
    else:
        rankData = rankMap[MULTIPLAY_RANKNAME]
    
    localRank = rankData._localRank
    scoreboard = None
    if not quizName in localRank.keys(): #퀴즈에 맞는 순위표가 없다면
        scoreboard = MultiplayScoreboard(MULTIPLAY_RANKNAME, quizName) #생성 후 넣어주기
        localRank[quizName] = scoreboard
    else:
        scoreboard = localRank[quizName]

    return scoreboard

def getDisplayOption(OptionType, value): #옵션 타입과 값에 따라 적절한 표시값과 설명을 반환
    if OptionType == OPTION_TYPE.HINT_TYPE: #힌트 타입일 경우
        if value == 0:
            return "투표", "퀴즈에 참여중인 인원의 절반이 투표할 시 힌트가 요청됩니다."
        elif value == 1:
            return "주최자", "퀴즈를 시작한 주최자만 힌트를 요청할 수 있습니다."
        elif value == 2:
            return "자동", "남은 시간이 절반일 때 자동으로 힌트가 요청됩니다."
        elif value == 3:
            return "사용불가", "힌트 요청이 불가능합니다."
        elif value == 4:
            return "멀티용", "힌트 요청이 불가능합니다."
    elif OptionType == OPTION_TYPE.SKIP_TYPE: #스킵 타입일 경우
        if value == 0:
            return "투표", "퀴즈에 참여중인 인원의 절반이 투표할 시 문제를 건너뜁니다."
        elif value == 1:
            return "주최자", "퀴즈를 시작한 주최자만 문제를 건너뛸 수 있습니다."
        elif value == 2:
            return "사용불가", "문제를 건너뛸 수 없습니다."
    elif OptionType == OPTION_TYPE.TRIM_LENGTH: #노래 길이일 경우
            return str(value)+"초", "문제로 제시되는 음악 파일의 길이를 설정합니다.\n"+chr(173)+"\n"+Config.EMOJI_ICON.ICON_ALARM+"문제로 제시되는 노래의 재생구간은 매번 임의로 정해지는데\n이때 노래의 재생 길이를 변경합니다.\n노래 관련 퀴즈에서만 지원하는 기능입니다."
    elif OptionType == OPTION_TYPE.REPEAT_COUNT: #반복 횟수의 경우
            return str(value)+"회", "문제로 제시되는 음악 파일의 반복 재생 횟수를 설정합니다.\n"+chr(173)+"\n"+Config.EMOJI_ICON.ICON_ALARM+"노래 관련 퀴즈에서만 지원하는 기능입니다."
    
    return "존재하지 않는 설정 타입", "존재하지 않는 설정 값"

def initOption(option): #옵션 초기화
    option._hintType = 0
    option._skipType = 0
    option._trimLength = 40
    option._repeatCount = 1

async def clearChat(chatChannel): #메시지 삭제
    guildID = chatChannel.guild.id #

    excludeMsg = []
    if guildID in selectorMap.keys():
        selectorData = selectorMap[guildID]    
        excludeMsg.append(selectorData._selectorMessage)
    
    if guildID in quizUIMap.keys():
        quizUIFrame = quizUIMap[guildID]
        excludeMsg.append(quizUIFrame._myMessage)
    
    number = 500 #긁어올 메시지 개수
    def check(msg): #UI 메시지는 패스
        return not msg in excludeMsg 

    try:
        asyncio.ensure_future(chatChannel.purge(check=check, limit=number))
    except:
        Config.LOGGER.error("clearchat error")
        Config.LOGGER.error(traceback.format_exc())


def removeQuizUI(guild): #퀴즈 UI 프레임 삭제
    if guild.id in quizUIMap:
        del quizUIMap[guild.id]

def isQuiz(fileName): #퀴즈 폴더인지 확인
    fileName = fileName.lower()
    if fileName.find("&quiz") != -1: 
        return True
    else:
        return False

def getClockIcon(leftTime, maxTime): #시계 아이콘 반환
    if maxTime == 0: 
        return Config.EMOJI_ICON_CLOCK_0
    clockType = int((maxTime-leftTime)/maxTime * 12)
    if clockType == 0:
        return Config.EMOJI_ICON.CLOCK_0
    elif clockType == 1:
        return Config.EMOJI_ICON.CLOCK_1
    elif clockType == 2:
        return Config.EMOJI_ICON.CLOCK_2
    elif clockType == 3:
        return Config.EMOJI_ICON.CLOCK_3
    elif clockType == 4:
        return Config.EMOJI_ICON.CLOCK_4
    elif clockType == 5:
        return Config.EMOJI_ICON.CLOCK_5
    elif clockType == 6:
        return Config.EMOJI_ICON.CLOCK_6
    elif clockType == 7:
        return Config.EMOJI_ICON.CLOCK_7
    elif clockType == 8:
        return Config.EMOJI_ICON.CLOCK_8
    elif clockType == 9:
        return Config.EMOJI_ICON.CLOCK_9
    elif clockType == 10:
        return Config.EMOJI_ICON.CLOCK_10
    elif clockType == 11:
        return Config.EMOJI_ICON.CLOCK_11
    elif clockType == 12:
        return Config.EMOJI_ICON.CLOCK_12
    
    return Config.EMOJI_ICON.CLOCK_0


def getIcon(fileName):
    fileName = fileName.lower()
    tmpText = fileName.split("&icon=")
    icon = Config.EMOJI_ICON.ICON_QUIZ_DEFAULT #기본은 물음표 아이콘
    if len(tmpText) > 1: #&icon= 이라는 문자가 있다면
        icon = tmpText[1] #&icon= 뒤에있는 것이 아이콘 타입임
        icon = icon.split("&")[0] #& 만나기 전까지 파싱, 즉 icon 값만 파싱

    return icon #아이콘 반환


def getViewPath(allPath):
    tmpP = allPath.replace(Config.QUIZ_PATH, "").split("/") #각 폴더명을 가져와야함 , 기본 경로는 제외
    viewPath = "" #초기화
    for folderName in tmpP:
        splitTmp = folderName.split("&")
        tmpName = splitTmp[0] #실제 파일명만 긁어오기
        if len(splitTmp) > 1:
            tmpName += "/"
        viewPath += tmpName
    return viewPath


async def returnToTitle(guild): #해당 서버의 퀴즈 선택 UI를 초기화
    if not guild.id in selectorMap.keys(): 
        return
    selectorData = selectorMap[guild.id]
    selectorData._frameStack = []
    await showFrame(selectorData._selectorMessage, MainFrame(), isPopUp=False)


async def createSelectorUI(channel): #초기 UI생성
    if not isSet: return

    guild = channel.guild 


    quizListEmbed = discord.Embed(
            title="초기화중... 잠시만 기다려주세요.", url=None, description="\n▽", color=discord.Color.dark_magenta())
    quizListEmbed.set_author(name=bot.user.name,
                        icon_url=bot.user.avatar_url)
    quizListEmbed.remove_author()


    quizListMessage = await channel.send(embed=quizListEmbed)

    selectorData = None
    if not guild.id in selectorMap.keys(): #기존 데이터 없다면
        selectorData = SelectorData(quizListMessage) #생성
        selectorMap[guild.id] = selectorData #데이터 등록
    else: #기존 데이터 있다면
        selectorData = selectorMap[guild.id]

    selectorData._frameStack = [] #프레임 스택 초기화

    #버튼 달기
    asyncio.ensure_future(quizListMessage.add_reaction(Config.EMOJI_ICON.PAGE_PREV))
    i = 1
    while i < 6: #1~5번 버튼만
        asyncio.ensure_future(quizListMessage.add_reaction(Config.EMOJI_ICON.NUMBER[i]))
        i += 1
    asyncio.ensure_future(quizListMessage.add_reaction(Config.EMOJI_ICON.PAGE_PARENT))
    asyncio.ensure_future(quizListMessage.add_reaction(Config.EMOJI_ICON.PAGE_NEXT))

    await showFrame(quizListMessage, MainFrame(), isPopUp=False)

    return selectorData


async def createQuizUI(channel, quizPath, owner): #초기 UI생성
    if not isSet: return

    quizUIEmbed = discord.Embed(
            title="곧 퀴즈가 시작됩니다.", url=None, description="\n▽", color=discord.Color.blue())
    quizUIEmbed.set_author(name=bot.user.name, url="",
                        icon_url=bot.user.avatar_url)
    quizUIEmbed.remove_author()


    quizUIMessage = await channel.send(embed=quizUIEmbed)

    asyncio.ensure_future(quizUIMessage.add_reaction(Config.EMOJI_ICON.ICON_HINT)) #힌트
    asyncio.ensure_future(quizUIMessage.add_reaction(Config.EMOJI_ICON.ICON_SKIP))#스킵
    asyncio.ensure_future(quizUIMessage.add_reaction(Config.EMOJI_ICON.ICON_STOP)) #중지

    guildID = channel.guild.id
    quizUIFrame = QuizUIFrame(quizPath, channel)  #UI프레임 생성
    option = getOption(guildID) #옵션 값 로드
    quizUIFrame.setOption(option) #옵션 값 설정

    quizUIMap[guildID] = quizUIFrame #퀴즈 UI 등록

    await showFrame(quizUIMessage, quizUIFrame, isPopUp=False) #띄우기

    return quizUIFrame


async def showTop(message, selectorData):
    topFrame = selectorData._frameStack[len(selectorData._frameStack) - 1]
    await showFrame(message, topFrame, isPopUp=False) #새로운 top 프레임 표시


async def showFrame(message, frame, isPopUp=True): #프레임 표시, isPopUp 가 True면 프레임을 추가로 띄우는 방식으로
    guildID = message.guild.id
    if not guildID in selectorMap.keys(): #등록된 selector데이터가 없다면
        return False

    selectorData = selectorMap[guildID]

    isSuc = await setFrame(message, frame)
    if isPopUp: #팝업 방식이면
        selectorData._frameStack.append(frame) #프레임 스택에 추가
    return isSuc


async def setFrame(message, frame): #메시지에 해당 프레임을 설정
    if not isSet: return False

    if message == None or frame == None:
        return False

    frame.paint(message) #프레임 표시 이벤트
    selectorEmbed = getEmbedFromFrame(frame) 

    try:
        await message.edit(embed=selectorEmbed) # 메시지 객체 업데이트 
        return True
    except:
        Config.LOGGER.warning(traceback.format_exc())
        return False


async def popFrame(channel, frame): #메시지 객체와 함께 프레임 생성
    if not isSet: return

    if channel == None or frame == None:
        return

    embed = getEmbedFromFrame(frame)

    thumbnailFile = None
    if frame._image_visible:
        if frame._image_local: #로컬 이미지라면
            filePath = frame._image_url
            thumbnailFile = discord.File(filePath, filename="quizThumbnail.png")
            embed.set_image(url="attachment://quizThumbnail.png")

    message = None
    try:
        if thumbnailFile != None: #로컬 이미지 사용시
            message = await channel.send(file=thumbnailFile, embed=embed) # 메시지 객체 업데이트 
        else:
            message = await channel.send(embed=embed) # 메시지 객체 업데이트 
    except:
        Config.LOGGER.error("메시지 에러 2")
        Config.LOGGER.error(traceback.format_exc())
    
    frame.paint(message) #프레임 표시 이벤트

def getEmbedFromFrame(frame): #frame으로 embed 생성

    title = frame._title_text
    mainList = frame._main_text
    nowPage = int(frame._page_nowPage) #현재 페이지 가져옴
    maxPage = math.ceil(len(mainList) / LIST_PER_PAGE)  #최대 페이지 설정
    if nowPage > maxPage - 1: #페이지 초과시 max로
        frame._page_nowPage = maxPage - 1
        nowPage = maxPage - 1
    if nowPage < 0: #음수 방지
        frame._page_nowPage = 0
        nowPage = 0


    desc = chr(173)+"\n"

    if frame._sub_visible: #서브 타이틀 
        desc += chr(173)+"\n"+frame._sub_text + "\n"
        desc += chr(173)+"\n" + chr(173) + "\n"
    
    
    if frame._main_visible: #메인 메시지, 스크롤 방식
        pageIndex = nowPage * LIST_PER_PAGE #표시 시작할 인덱스

        i = 0
        while i < frame._LIST_PER_PAGE: #LIST_PER_PAGE 만큼 목록 표시
            fileIndex = pageIndex + i
            if fileIndex >= len(mainList): #마지막 텍스트 도달하면 바로 break
                break
            #print(fileIndex)
            #print(str(mainList))
            text = mainList[fileIndex]
            i += 1
            desc += Config.getEmojiFromNumber(i) + ")　" + str(text) + "\n" + chr(173) + "\n"
        
        desc += chr(173) + "\n"

    if frame._notice_visible: #알림 같은것(에러 메시지 등)
        desc += chr(173) + "\n"
        desc += frame._notice_text
        desc += chr(173)+"\n" + chr(173) + "\n"

    color = frame._embedColor
    selectorEmbed = discord.Embed(title=title, url=None, description=desc, color=color) #embed 설정
    
    if frame._field_visible: #필드부
        for field in frame._field_text.keys():
            fieldValue = frame._field_text[field]
            selectorEmbed.add_field(name=field, value=fieldValue, inline=True)
  
    text_footer = ""

    if frame._customFooter_visible: #footer를 특정 문자열로 지정하기
        text_footer = frame._customFooter_text
    else:
        if frame._page_visible: # 페이지 표시
            text_footer += Config.EMOJI_ICON.ICON_PAGE + " "
            text_footer += str(nowPage + 1) + " / " + str(maxPage)
        
        if frame._path_visible: #패스 표시
            if frame._page_visible: 
                text_footer += "　　|　　"
            text_footer += Config.EMOJI_ICON.ICON_FOLDER + " " + str(frame._path_text)

    if frame._image_visible: #이미지
        if not frame._image_local: #로컬 이미지 사용이 아니면
            selectorEmbed.set_image(url=frame._image_url)

    

    # embed 추가 설정
    if frame._author == None:
        selectorEmbed.set_author(name=bot.user.name, url="",
                        icon_url=bot.user.avatar_url)
        selectorEmbed.remove_author()
    else:
        author = frame._author
        selectorEmbed.set_author(name=author.display_name, url="",
                        icon_url=author.avatar_url)

    selectorEmbed.set_footer(text=text_footer) #footer 설정 

    return selectorEmbed


async def update(message): #해당 메시지 객체로 프레임 업데이트
    guildID = message.guild.id
    if not guildID in selectorMap.keys():
        return
    selectorData = selectorMap[guildID]
    await showTop(message, selectorData)


##이벤트
async def on_reaction_add(reaction, user):
    emoji = reaction.emoji #반응한 이모지
    message = reaction.message #반응한 메시지
    guild = message.guild #반응한 서버
        
    if not guild.id in selectorMap.keys(): #데이터 없다면
        return

    if message.author != None and message.author != bot.user: #봇이 보낸 메시지가 아니면
        return

    selectorData = selectorMap[guild.id]
    if len(selectorData._frameStack) <= 0: #프레임 스택이 비어있다면
        selectorData._frameStack.append(MainFrame()) #메인 화면 프레임 추가

    if emoji == Config.EMOJI_ICON.PAGE_PARENT: #돌아가기 버튼이면
        frameStack = selectorData._frameStack #프레임 스택 가져오기
        if len(frameStack) > 1: #프레임 스택에 mainFrame 말고 뭔가 있다면
            delFrame = frameStack[len(frameStack) - 1] #삭제될 프레임
            delFrame.destructor(message) #소멸자 호출
            del frameStack[len(frameStack) - 1] #top 프레임 삭제
            
            await showTop(message, selectorData) #top 프레임 표시
            return

    if guild.id in quizUIMap: #퀴즈 UI프레임이 있으면 이것두 이벤트 동작
        quizUIFrame = quizUIMap[guild.id]
        await quizUIFrame.action(reaction, user, selectorData)
    
    frame = selectorData._frameStack[len(selectorData._frameStack) - 1] #가장 top 프레임 가져옴
    await frame.action(reaction, user, selectorData) #해당 프레임의 이벤트 동작

