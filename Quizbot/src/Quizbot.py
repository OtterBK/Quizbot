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
import math
from threading import Thread
from mutagen.mp3 import MP3
from shutil import copyfile
import sys, traceback
import datetime
from discord.ext.commands import CommandNotFound
import koreanbots


random.seed() #시드 설정


import Config
import QuizUI as ui

#기본 ENUM 상수, 수정X
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
    MULTIPLAY = 11 #멀티플레이
    PICTURE_LONG = 12 #타이머 긴 사진 퀴즈


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


class NET_STEP(enumerate):
    GET_TARGET = 1  # 상대 게임 데이터 객체중
    NEXTROUND = 2  # 다음 라운드 알림 대기중
    QUESTION = 3  # 퀴즈낼 대기중
    QUESTION_READY = 4  # 문제 내기 직전
    SHOWANSWER = 5  # 문제정답 공개
    SHOWSCORE = 6  # 순위 공개


#클래스 선언
class GuildData: #봇이 있는 디스코드 서버 데이터
    def __init__(self, guild):
        self._guildID = guild.id #서버 id 저장
        self._selectorChannelID = 0 #퀴즈 선택 객체가 있는 채팅 채널 id
        self._gameData = None #진행중인 퀴즈 데이터


class TextQuizData:
    def __init__(self, answer):
        self._answer = answer
        self._questionText = ""
        self._answerText = "" #추가 설명

class Quiz:
    def __init__(self, quizPath, quizUIFrame, voice, owner):
        ##필수 설정
        self._quizUIFrame = quizUIFrame #퀴즈 진행용 UI
        self._voice = voice #봇 보이스 객체
        self._owner = owner #주최자
        self._chatChannel = quizUIFrame._myMessage.channel
        self._guild = self._chatChannel.guild
        self._gamePath = quizPath #퀴즈 경로
        self._gameType = GAME_TYPE.SONG #게임 타입
        self._gameName = "" #게임 이름
        self._topNickname = "" #1등 별명
        self._maxRound = 40 #최대 라운드 수

        ##퀴즈 옵션, 불변
        self._repeatCount = 1 #반복 듣기 횟수
        self._trimLength = 40 #오디오 파일 자를 크기
        self._waitAfterAnswer = 10 #정답 맞춘 후 대기시간

        ##퀴즈 데이터
        self._gameStep = GAME_STEP.START #게임 진행상태
        self._roundIndex = 0 #퀴즈 라운드
        self._answerList = [] #정답 인정 목록
        self._quizList = [] #퀴즈 목록
        self._scoreMap = dict() #점수판
        self._isSkiped = False #스킵 여부
        self._useHint = False #힌트 사용여부

        self._textQuizList = [] # 텍스트 기반 퀴즈일 때 문제 저장 공간
        self._oxQuizObject = None #현재 진행중인 ox퀴즈 객체
        self._thumbnail = None # 썸네일
        self._answerAuido = None #정답용 음악

        self._answerPlayer  = None #정답자

    def init(self):
        self._gameStep = GAME_STEP.START #게임 진행상태
        self._roundIndex = 0 #퀴즈 라운드
        self._answerList = [] #정답 인정 목록
        self._quizList = [] #퀴즈 목록
        self._scoreMap = dict() #점수판
        self._isSkiped = False #스킵 여부
        self._useHint = False #힌트 사용여부
        self._answerPlayer = None #정답자

    async def gameRule(self): #각 퀴즈별 설명

        await ui.clearChat(self._chatChannel) #채팅 청소

        quizUIFrame = self._quizUIFrame
        voice = self._voice
        gameData = self
        quizUIFrame._title_visible = True
        quizUIFrame._title_text = Config.EMOJI_ICON.ICON_RULE + "　퀴즈 설명"
        quizUIFrame._sub_visible = True
        quizUIFrame._main_visible = False
        quizUIFrame._notice_visible = False
        quizUIFrame._customFooter_visible = False

        quizUIFrame._path_visible = False
        quizUIFrame._page_visible = False

        gameType = gameData._gameType

        quizUIFrame._sub_text = ""

        if gameData.checkStop(): return # 게임 중지 확인
        if gameType == GAME_TYPE.MULTIPLAY: #멀티플레이 퀴즈면
            quizUIFrame._sub_text += Config.EMOJI_ICON.ICON_TIP+ "**　[ "+ Config.EMOJI_ICON.ICON_MULTIPLAY +" 멀티플레이 ]**\n" + chr(173) + "\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(1) + "　기본적인 진행 방식은 일반 퀴즈와 동일하나\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(2) + "　점수가 개별 유저로 계산되지 않고 **서버별로 합산돼 계산**됩니다.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(3) + "　또한 얼마나 **정답을 빠르게 맞추는지에 따라 얻는 점수가 다릅니다**.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(4) + "　**!챗** 명령어를 사용해 **서버간 채팅**이 가능합니다.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(5) + "　예시)　**!챗 안녕하세요.** \n"
            quizUIFrame._sub_text += chr(173)+"\n" + chr(173)+"\n" + chr(173)+"\n"
            playBGM(voice, BGM_TYPE.PLING)
            await quizUIFrame.update()
            await asyncio.sleep(8)  # 8초 대기

        if gameData.checkStop(): return # 게임 중지 확인
        #정답 작성 요령 설명
        if gameType == GAME_TYPE.GLOWLING or gameType == GAME_TYPE.SELECT: #객관식인 경우
            quizUIFrame._sub_text += Config.EMOJI_ICON.ICON_TIP + "**　[ "+ Config.EMOJI_ICON.ICON_SELECTOR +" 객관식 퀴즈 정답 선택 요령 ]**\n" + chr(173) + "\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(1) + "　제시된 문제에 대한 정답을 "+ Config.getEmojiFromNumber(0) +"~ "+ Config.getEmojiFromNumber(10) +" 숫자 아이콘 중에서 선택해주세요.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(2) + "　이미 정답을 선택했어도 변경이 가능합니다.\n"
        elif gameType == GAME_TYPE.OX: #OX퀴즈의  경우
            quizUIFrame._sub_text += Config.EMOJI_ICON.ICON_TIP + "**　[ "+ Config.EMOJI_ICON.ICON_OXQUIZ +" 퀴즈 정답 선택 요령 ]**\n" + chr(173) + "\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(1) + "　제시된 문제에 대한 정답을 " + Config.EMOJI_ICON.OX[0] + " 또는 " + Config.EMOJI_ICON.OX[1] + " 아이콘 중에서 선택해주세요.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(2) + "　이미 정답을 선택했어도 변경이 가능합니다.\n"
        else:
            quizUIFrame._sub_text += Config.EMOJI_ICON.ICON_TIP + "**　[ "+ Config.EMOJI_ICON.ICON_KEYBOARD +" 주관식 퀴즈 정답 작성 요령 ]**\n" + chr(173) + "\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(1) + "　정답은 공백 없이 입력하여도 상관 없습니다.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(2) + "　특수문자는 입력하지마세요.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(3) + "　대소문자는 구분할 필요 없습니다.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(4) + "　줄임말도 정답으로 인정되긴 하나 정확하지 않습니다.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(5) + "　정답이 영어인 경우에는 발음을 제출해도 정답 인정이 되긴합니다.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(6) + "　여러 시리즈가 있는 경우에는 시리즈명을 포함해야 정답으로 인정됩니다.\n"

        playBGM(voice, BGM_TYPE.PLING)
        await quizUIFrame.update()

        if gameData.checkStop(): return # 게임 중지 확인
        await asyncio.sleep(6)  # 6초 대기
        quizUIFrame._sub_text += chr(173)+"\n" + chr(173)+"\n" + chr(173)+"\n"
        quizUIFrame._sub_text += Config.EMOJI_ICON.ICON_TIP + "**　[　"+ Config.EMOJI_ICON.ICON_ALARM +"주의　]**\n"
        quizUIFrame._sub_text += "노래 음량이 일정하지 않습니다. \n봇의 음량를 조금 더 크게 설정해주세요.　"+  Config.EMOJI_ICON.ICON_SPEAKER_LOW + "　->　" +  Config.EMOJI_ICON.ICON_SPEAKER_HIGH +"\n"
        playBGM(voice, BGM_TYPE.PLING)
        await quizUIFrame.update()

        if gameData.checkStop(): return # 게임 중지 확인
        await asyncio.sleep(6)  # 6초 대기
        quizUIFrame._sub_text += chr(173)+"\n" + chr(173)+"\n" + chr(173)+"\n"
        quizUIFrame._sub_text += Config.EMOJI_ICON.ICON_SOON + " *이제 퀴즈를 시작합니다!*\n"
        playBGM(voice, BGM_TYPE.PLING)
        await quizUIFrame.update()
        await asyncio.sleep(4)  # 4초 대기

        if gameData.checkStop(): return #혹시 퀴즈가 중지됐는지 확인

    def loadQuiz(self): #문제 로드
        tmpList = os.listdir(self._gamePath)            # 퀴즈 폴더 내 모든 파일 불러오기
        quizList = []  # 빈 리스트 선언

        while len(tmpList) > 0:  # 모든 파일에 대해
            rd = random.randint(0, len(tmpList) - 1)  # 0부터 tmpList 크기 -1 만큼
            quiz = tmpList[rd]  # 무작위 1개 선택
            if(os.path.isdir(self._gamePath + quiz)):  # 폴더인지 확인(폴더만 추출할거임)
                quizList.append(quiz)  # 퀴즈 목록에 추가
            del tmpList[rd]  # 검사한 항목은 삭제

        self._quizList = quizList

        self._maxRound = len(quizList)  # 문제 총 개수
        self._quizUIFrame._quizCnt = self._maxRound #퀴즈UI 총 문제 개수 갱신
        self._roundIndex = 0  # 현재 라운드

    async def prepare(self): #시작전 전처리
        self.loadQuiz() #퀴즈로드
        Config.LOGGER.info(self._guild.name+" 에서 " + self._gameName + " 퀴즈 시작")


    def sortScore(self):#정렬된 점수 맵 반환
        gameData = self

        sortPlayer = []  # 빈 리스트
        for player in gameData._scoreMap.keys():  # 정렬
            index = 0  # 인덱스
            score = gameData._scoreMap[player]  # 점수
            while index < len(sortPlayer):
                cp = sortPlayer[index]  # 비교대상
                cp_score = gameData._scoreMap[cp]  # 비교대상 점수
                if score > cp_score:  # 비교대상보다 점수높으면
                    break  # while 빠져나가기
                index += 1  # 다음 대상으로

            sortPlayer.insert(index, player)  # 삽입 장소에 추가

        return sortPlayer

    async def noticeRound(self):
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        uiMessage = quizUIFrame._myMessage #UI 메시지

        try:
            asyncio.ensure_future(showNotice(self._chatChannel, noticeIndex=2)) #점검 있으면 표시
        except:
            pass

        await ui.clearChat(uiMessage.channel) #채팅 청소
        gameData._roundIndex += 1 #라운드 +1
        quizUIFrame._quizRound = gameData._roundIndex #퀴즈UI 라운드 갱신
        if gameData._roundIndex > gameData._maxRound:  # 더이상문제가없다면
            try:
                await self.finishGame()  # 게임 끝내기
            except:
                Config.LOGGER.error("게임 종료 에러")
                Config.LOGGER.error(traceback.format_exc())
                return False

            return False

        voice = get(bot.voice_clients, guild=uiMessage.guild)  # 봇의 음성 객체 얻기

        # quizUIFrame._field_visible = True
        # for player in self.sortScore(): #점수판 추가
        #     playerName = player.display_name
        #     quizUIFrame.addField(playerName,"[ " + str(gameData._scoreMap[player]) + "p" +" ]")
        quizUIFrame._field_text.clear()

        quizUIFrame._title_visible = True
        quizUIFrame._title_text = chr(173)+"[　　　　"+ quizUIFrame._quizIcon + " " + quizUIFrame._quizName + "　　　　]"

        quizUIFrame._sub_visible = True
        quizUIFrame._sub_text = Config.EMOJI_ICON.ICON_BOX+"　**"+str(gameData._roundIndex) +"번째 문제입니다.**"

        quizUIFrame._main_visible = False
        quizUIFrame._notice_visible = True

        quizUIFrame._customText_visible = False
        quizUIFrame._page_visible = False
        quizUIFrame._path_visible = False

        quizUIFrame._customFooter_visible = True
        quizUIFrame._customFooter_text = Config.EMOJI_ICON.ICON_BOX+" 문제: " + str(quizUIFrame._quizRound) + " / "+str(quizUIFrame._quizCnt)

        quizUIFrame._useFormat = False

        playBGM(voice, BGM_TYPE.ROUND_ALARM)
        await quizUIFrame.update() #몇번째 문제인지 알려줌
        return True

    def parseAnswer(self): #정답 인정 목록 추출
        quizTitle = self._quizList[self._roundIndex - 1]  # 현재 진행중인 문제 가져오기
        self._nowQuiz = quizTitle  # 퀴즈 정답 등록
        answer = []  # 빈 리스트 선언
        title = quizTitle.split("&^")[0] #먼저 제목만 뽑기

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

        self._answerList = answer #정답 인정 목록 설정


    async def question(self): #문제 내기
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        guild = self._guild
        quizPath = self._gamePath + self._nowQuiz + "/"
        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER

        isTrimed = False #자르기 옵션 적용됐는지 여부

        for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
            if file.endswith(".png") or file.endswith("jpg"): #사진파일이라면 ,썸네일임
                gameData._thumbnail = quizPath + "/" + file
            elif file.endswith(".wav") or file.endswith(".mp3"):  # 파일 확장자가 .wav 또는 .mp3면, 문제 파일일거임
                question = file  # 기존 파일명
                Config.LOGGER.info(f"guild: {guild.name}, gameName: {gameData._gameName}, questionFile: {question}\n") #정답 표시
                audioName = quizPath + "/" + question #실제 실행할 음악파일 경로
                audioLength = 39 #오디오 길이

                try:
                    if file.endswith(".wav"): #확장자 wav 일때
                        f = sf.SoundFile(audioName) #오디오 파일 로드
                        length_in_secs = len(f) / f.samplerate #오디오 길이
                        f.close()
                    elif file.endswith(".mp3"): #확장자 mp3일때
                        audio = MP3(audioName)
                        audio_info = audio.info

                        length_in_secs = int(audio_info.length) #음악 총 길이
                        # 음악 길이 가져오기 완료
                    if length_in_secs > gameData._trimLength + 1: #음악이 자를 시간 초과할 시, 자르기 시작
                        length_in_secs = int(length_in_secs)
                        if length_in_secs > gameData._trimLength + 20: #노래 길이가 자를 시간 + 20만큼 크면
                            #최적의 자르기 실행
                            startTime = random.randint(10, (length_in_secs - gameData._trimLength - 10) - 1) #자르기 시작 시간 10초 ~ 총길이 - 자를 길이 - 10
                        else:
                            startTime = random.randint(0, length_in_secs - gameData._trimLength - 1)

                        endTime = startTime + gameData._trimLength #지정된 길이만큼 자르기

                        startTime = toTimestamp(startTime)
                        endTime = toTimestamp(endTime)

                        isTrimed = True
                        audioLength = gameData._trimLength

                        # print(startTime + " | " + endTime)
                    else:
                        audioLength = length_in_secs
                except:
                    Config.LOGGER.error("오디오 열기 에러, "+str(file))
                    Config.LOGGER.error(traceback.format_exc())
                    return False

        repartCnt = gameData._repeatCount #반복횟수
        quizUIFrame._quizMaxTime = audioLength #노래 길이

        quizUIFrame._useFormat = True #정해진 포맷 사용

        hintType = gameData._quizUIFrame._option._hintType # 힌트 타입 가져오기

        limit = 0

        while repartCnt > 0: #반복횟수만큼 반복
            repartCnt -= 1

            voice.stop() #우선 보이스 중지

            if isTrimed: #자르기 옵션이 적용돼 있다면
                voice.play(discord.FFmpegPCMAudio(audioName, before_options="-ss " + startTime + " -to " + endTime))  # 노래 재생
            else:
                voice.play(discord.FFmpegPCMAudio(audioName))

            asyncio.ensure_future(fadeIn(voice)) #페이드인
            playTime = 0

            while voice.is_playing():  # 재생중이면
                if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                    return #리턴
                await asyncio.sleep(0.71) #딜레이 계산해서
                playTime += 1 #재생 1초 +
                leftTime = audioLength  - playTime #남은 길이
                quizUIFrame._quizLeftTime = leftTime

                if hintType == 2: #힌트 타입이 자동일 떄
                    if playTime > audioLength // 2: #절반 이상 재생됐다면
                        asyncio.ensure_future(self.requestHint()) #힌트 요청

                limit += 1
                if limit > 1000: return
                await quizUIFrame.update()

                if leftTime < 0:
                    leftTime = 0
                    Config.LOGGER.debug("fast end")
                    voice.stop()
                    break # 재생시간 초과면 break

        return True

    def setScoreField(self, uiFrame):
        for player in self.sortScore(): #점수판 추가
            playerName = player.display_name
            uiFrame.addField(playerName,"[ " + str(self._scoreMap[player]) + "p" +" ]")

    async def showAnswer(self, isWrong=False): #정답 공개, isWrong 은 오답여부
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        channel = self._chatChannel
        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT # 다음 라운드 대기로 변경

        author = ""
        tmpSp = gameData._nowQuiz.split("&^")
        if len(tmpSp) >= 2: #만약 작곡자가 적혀있다면
            i = 1
            while i < len(tmpSp):
                author += tmpSp[i] #작곡자 저장
                i += 1

        answerStr = "" #정답 공개용 문자열
        for tmpStr in gameData._answerList:
            answerStr += tmpStr + "\n" #정답 문자열 생성

        answerFrame = ui.QFrame()

        answerFrame._sub_visible = True
        answerFrame._sub_text = ""

        answerFrame._title_visible = True
        if isWrong: #오답일 시
            if not voice.is_playing():
                playBGM(voice, BGM_TYPE.FAIL)
            answerFrame._title_text = chr(173)+"[　　　　"+ Config.getRandomWrongIcon() +" 정답 공개　　　　]"
            answerFrame._embedColor = discord.Color.red()
        else:
            answerFrame._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_COLLECT +" 정답!　　　　]"
            answerFrame._embedColor = discord.Color.green()

        if gameData._answerPlayer != None: #정답자 적혀있다면
            answerFrame._sub_text = chr(173)+"\n" + Config.getRandomHumanIcon()+" 정답자　**["+ "　"+str(gameData._answerPlayer.display_name) +"　]**" + "\n"

        answerFrame._author = gameData._answerPlayer

        answerFrame._sub_text += Config.EMOJI_ICON.ICON_LIST + " **정답 목록**\n"+ chr(173) + "\n"+answerStr

        answerFrame._main_visible = False

        if author != "": #추가 설명이 있다면
            answerFrame._notice_visible = True
            answerFrame._notice_text = Config.EMOJI_ICON.ICON_PEN + " *" + author + "*"
        else:
            answerFrame._notice_visible = False



        answerFrame._field_visible = True
        self.setScoreField(answerFrame)

        if gameData._thumbnail != None:
            answerFrame._image_visible = True
            answerFrame._image_local = True
            answerFrame._image_url = gameData._thumbnail


        answerFrame._page_visible = False
        answerFrame._path_visible = False

        answerFrame._customFooter_visible = True
        if(gameData._roundIndex < gameData._maxRound):  # 이 문제가 마지막 문제가 아니었다면
            answerFrame._customFooter_text = Config.EMOJI_ICON.ICON_NOTICE + " 곧 다음 문제로 진행됩니다."
        else:
            answerFrame._customFooter_text = Config.EMOJI_ICON.ICON_NOTICE + " 이제 순위가 공개됩니다."

        await ui.popFrame(channel, answerFrame)

    async def nextRound(self):
        gameData = self

        ###### 라운드 표시
        isError = False
        try:
            isContinue = await self.noticeRound()
            if not isContinue: #퀴즈 속행 아니면 return
                return
        except:
            Config.LOGGER.error("noticeRound error")
            isError = True
            Config.LOGGER.error(traceback.format_exc())

        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        await asyncio.sleep(2)
        ###### 정답 설정
        if self.checkStop(): return
        if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
            return
        try:
            self.parseAnswer()
        except:
            Config.LOGGER.error("parseAnswer error")
            isError = True
            Config.LOGGER.error(traceback.format_exc())

        ###### 라운드 초기화

        gameData._isSkiped = False
        gameData._useHint = False
        gameData._thumbnail = None # 썸네일 초기화
        gameData._answerPlayer = None #정답자 초기화
        self._quizUIFrame.initRound(self._voice.channel)


        ###### 문제 출제
        if self.checkStop(): return
        if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
            return
        try:
            await self.question()
        except:
            Config.LOGGER.error("question error")
            isError = True
            Config.LOGGER.error(traceback.format_exc())

        ###### 정답 공개
        if self.checkStop(): return
        if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
            return
        if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER or isError:  # 아직도 정답자 없거나 문제 발생시
            isError = False
            try:
                await self.showAnswer(isWrong=True) #정답 공개
                await asyncio.sleep(3) #초대기
            except:
                Config.LOGGER.error("showAnswer error")
                Config.LOGGER.error(traceback.format_exc())

            try:
                await self.nextRound() #다음 라운드 진행
            except:
                Config.LOGGER.error("nextRound error")
                Config.LOGGER.error(traceback.format_exc())


    def addScore(self, user): #1점 추가
        gameData = self
        if user in gameData._scoreMap:  # 점수 리스트에 정답자 있는지 확인
            gameData._scoreMap[user] += 1  # 있으면 1점 추가
        else:
            gameData._scoreMap[user] = 1  # 없으면 새로 1점 추가


    def checkStop(self): #퀴즈 중지 확인

        guild = self._guild
        channel = self._chatChannel

        quizChannel = guild.get_channel(channel.id)

        if quizChannel == None or self._voice == None or not self._voice.is_connected():  # 봇 음성 객체가 없다면 퀴즈 종료, 채널이 None일때도
            guild = self._guild
            if guild in dataMap:
                dataMap[guild]._gameData = None #퀴즈 데이터 삭제
            ui.removeQuizUI(guild) #ui 데이터 삭제

            if self._gameStep != GAME_STEP.END: #퀴즈가 정상적으로 끝난게 아니면
                try:
                    asyncio.ensure_future(self.forceEnd())
                except:
                    Config.LOGGER.error(traceback.format_exc())

            return True

        return False

    async def forceEnd(self): #강제 종료시
        if self._gameStep == GAME_STEP.END: return
        self._gameStep = GAME_STEP.END
        Config.LOGGER.info(str(self._guild.name) + "에서 "+str(self._gameName)+"퀴즈 강제종료")

    async def start(self):
        self.init() #초기화
        await self.gameRule()
        if self.checkStop(): return #게임 중지 체크
        await self.prepare() #전처리
        if self.checkStop(): return #게임 중지 체크
        await self.nextRound() #다음 라운드 진행


    async def performance(self, user): #정답 맞췄을 때 효과
        roundChecker = self._roundIndex  # 현재 라운드 저장

        quizUIFrame = self._quizUIFrame
        quizUIFrame._title_visible = True
        quizUIFrame._title_text = chr(173)+"[　　　　"+ quizUIFrame._quizIcon + " " + quizUIFrame._quizName + "　　　　]"

        quizUIFrame._sub_visible = True
        quizUIFrame._sub_text = Config.getRandomHumanIcon()+" 정답자　**["+ "　"+str(user.display_name) +"　]**"

        quizUIFrame._main_visible = False
        quizUIFrame._notice_visible = False

        quizUIFrame._field_visible = False

        quizUIFrame._customText_visible = False
        quizUIFrame._page_visible = False
        quizUIFrame._path_visible = False

        quizUIFrame._customFooter_text = ""

        quizUIFrame._useFormat = False
        await quizUIFrame.update()

        voice = self._voice
        waitCount = 8 #9초 대기할거임

        while voice.is_playing(): #재생중이면
            waitCount -= 1
            await asyncio.sleep(1)  # 1초 대기
            if waitCount <= 0: #9초 대기했다면
                break #대기 탈출

        if roundChecker != self._roundIndex:  # 이미 다음 라운드라면 리턴
            return
        await fadeOut(voice)

    async def finishGame(self): #퀴즈 종료
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        channel = self._chatChannel

        gameData._gameStep = GAME_STEP.END
        voice.stop()

        quizUIFrame._useFormat = False

        quizUIFrame._title_visible = True
        quizUIFrame._title_text = chr(173)+"[　　　　"+ Config.getMedalFromNumber(0) + " " + "순위 발표" + "　　　　]"

        quizUIFrame._sub_visible = True
        quizUIFrame._sub_text = "퀴즈명:　"+ chr(173) + quizUIFrame._quizIcon + " " + quizUIFrame._quizName

        quizUIFrame._notice_visible = False

        quizUIFrame._embedColor = discord.Color.gold() #색상 선택

        quizUIFrame._customText_visible = False
        quizUIFrame._customFooter_text = ""

        quizUIFrame._page_visible = False
        quizUIFrame._path_visible = False

        playBGM(voice, BGM_TYPE.BELL)
        await quizUIFrame.update()
        await asyncio.sleep(3)

        quizUIFrame._notice_visible = True
        quizUIFrame._notice_text = "" #점수 표시할 곳

        if len(self._scoreMap.keys()) == 0: #정답자 아무도 없다면
            playBGM(voice, BGM_TYPE.FAIL)
            quizUIFrame._notice_text = "**헉! 😅 정답자가 아무도 없습니다... \n많이 어려우셨나요...? 😢**" #점수 표시할 곳
            await quizUIFrame.update()
        else:
            i = 1
            for player in self.sortScore(): #점수판 추가
                playerName = player.display_name
                quizUIFrame._notice_text += str(Config.getMedalFromNumber(i)) + " " + playerName + "　"+ chr(173) + "　" + str(gameData._scoreMap[player]) + "점　" + chr(173)

                if i == 1: #1등이면
                    quizUIFrame._notice_text += Config.EMOJI_ICON.ICON_POINT_TO_LEFT + "　**최고의 " + str(self._topNickname) + "**\n"

                quizUIFrame._notice_text += chr(173) + "\n"

                if i <= 3: #3등까지는 한 개씩 보여줌
                    playBGM(voice, BGM_TYPE.SCORE_ALARM)
                    await quizUIFrame.update()
                    await asyncio.sleep(2)

                i += 1

            if len(gameData._scoreMap) > 3: #4명이상 플레이 했다면
                playBGM(voice, BGM_TYPE.SCORE_ALARM) #나머지 발표
                await quizUIFrame.update()

            scoreboard = ui.getScoreboard(self._guild.id, self._gameName)  #길드, 퀴즈명으로 순위표  가져오기
            scoreboard.mergeScore(gameData._scoreMap) #현재 한 퀴즈 결과에 대한 순위표와 병합


        await asyncio.sleep(4)

        quizUIFrame._customText_visible = True
        quizUIFrame._customFooter_text = Config.EMOJI_ICON.ICON_NOTICE + " 퀴즈가 종료되었습니다."
        Config.LOGGER.info(self._guild.name+" 에서 " + self._gameName + " 퀴즈 종료")
        playBGM(voice, BGM_TYPE.ENDING)
        await quizUIFrame.update()
        await asyncio.sleep(2)
        await voice.disconnect()
        self.checkStop() #데이터 삭제

    async def requestHint(self): #힌트 사용

        gameData = self #게임 데이터 불러올거임

        if gameData._gameStep != GAME_STEP.WAIT_FOR_ANSWER: #정답자 대기중이 아니면
            return
        if gameData._useHint == True: #이미 힌트 썻다면
            return
        if gameData._gameType == GAME_TYPE.OX or gameData._gameType == GAME_TYPE.MULTIPLAY: #OX퀴즈, 멀티는 힌트 불가능
            gameData._useHint = True #힌트 사용으로 변경
            asyncio.ensure_future(gameData._chatChannel.send("``` "+chr(173)+"\n해당 퀴즈는 힌트를 제공하지 않습니다.\n"+chr(173)+" ```"))
            return

        #힌트 표시
        gameData._useHint = True #힌트 사용으로 변경
        answer = gameData._answerList[0] #정답 가져오기
        answer = answer.upper() #대문자로
        #answer = answer.replace(" ", "") #공백 제거
        answerLen = len(answer) #문자 길이
        hintLen = math.ceil(answerLen / 4)#표시할 힌트 글자수
        hintStr = "" #힌트 문자열

        hintIndex = []
        index = 0
        limit = 0
        while index < hintLen: #인덱스 설정
            limit += 1
            if  limit > 1000: #시도 한계 설정
                break

            rd = random.randint(0, answerLen - 1)
            if rd in hintIndex or answer[rd] == " ": #이미 인덱스에 있거나 공백이라면
                continue
            else:
                hintIndex.append(rd)
                index += 1

        index = 0
        while index < answerLen:
            if index in hintIndex: #만약 해당 글자가 표시인덱스에 있다면
                hintStr += answer[index] #해당 글자는 표시하기
            elif answer[index] == " ": #공백도 표시
                hintStr += answer[index]
            else:
                hintStr += Config.EMOJI_ICON.ICON_BLIND
            index += 1

        asyncio.ensure_future(gameData._chatChannel.send("```markdown\n"+chr(173)+"\n""## 요청에 의해 힌트가 제공됩니다.\n"+chr(173)+"\n"+Config.EMOJI_ICON.ICON_HINT+" <힌트>　"+chr(173)+" "+str(hintStr)+"\n"+chr(173)+"```"))


    async def skip(self): #스킵 사용
        gameData = self

        if gameData._gameStep != GAME_STEP.WAIT_FOR_ANSWER and gameData._gameStep != GAME_STEP.WAIT_FOR_NEXT: #정답자 대기중이거나 다음라 대기중이 아니면
            return
        if gameData._isSkiped: #이미 스킵중이면
            return
        if gameData._gameType == GAME_TYPE.MULTIPLAY: #멀티는 스킵 불가능
            gameData._isSkiped = True #힌트 사용으로 변경
            asyncio.ensure_future(gameData._chatChannel.send("``` "+chr(173)+"\n해당 퀴즈는 건너뛰기를 제공하지 않습니다.\n"+chr(173)+" ```"))
            return

        if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER: #정답 못 맞추고 스킵이면
            gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT  # 다음 라운드 대기로 변경
            gameData._isSkiped = True #스킵중 표시

            asyncio.ensure_future(gameData._chatChannel.send("```markdown\n"+chr(173)+"\n## 요청에 의해 문제를 건너뜁니다.\n"+chr(173)+" ```"))

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
                await self.showAnswer(isWrong=True) #정답 공개
                await asyncio.sleep(3)
                if roundChecker == gameData._roundIndex:
                    await self.nextRound() #다음 라운드 진행


    async def stop(self): #퀴즈 중지
        await self._voice.disconnect()

        if self._gameStep == GAME_STEP.END: return

        self._roundIndex = self._maxRound

        quizUIFrame = self._quizUIFrame

        quizUIFrame._title_visible = True
        quizUIFrame._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_STOP + " " + "중지" + "　　　　]"

        quizUIFrame._sub_visible = True
        quizUIFrame._sub_text = "**퀴즈 주최자 "+str(self._owner.name) +"님께서 퀴즈 진행을 중지하였습니다.**"

        quizUIFrame._main_visible = False
        quizUIFrame._notice_visible = False

        quizUIFrame._field_visible = False

        quizUIFrame._customText_visible = False
        quizUIFrame._page_visible = False
        quizUIFrame._path_visible = False

        quizUIFrame._customFooter_text = ""

        quizUIFrame._useFormat = False

        asyncio.ensure_future(self._chatChannel.send("``` "+chr(173)+"\n주최자가 퀴즈 진행을 중지하였습니다.\n"+chr(173)+" ```"))

        await quizUIFrame.update()

        self.checkStop()


    async def onAnswer(self, author, isWrong=False):
        gameData = self
        roundChecker = gameData._roundIndex  # 정답 맞춘 라운드 저장

        gameData._answerPlayer = author #정답자 설정

        if self.checkStop(): return
        await self.showAnswer(isWrong) #정답 공개

        if self.checkStop(): return
        await self.performance(author) #정답 맞췄을 때 효과

        if self.checkStop(): return
        if(roundChecker == gameData._roundIndex):  # 정답 맞춘 라운드와 현재 라운드 일치시
            await self.nextRound() #다음 라운드로 진행

    ##이벤트
    async def action(self, reaction, user):
        emoji = reaction.emoji
        message = reaction.message
        guild = message.guild

    async def on_message(self, message):
        gameData = self
        author = message.author

        if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER: #정답자 대기중이면
            inputAnswer = message.content.replace(" ", "").upper() #공백 제거 및 대문자로 변경
            isAnswer = False
            for answer in gameData._answerList: #정답 목록과 비교
                answer = answer.replace(" ", "").upper() # 공백 제거 및 대문자로 변경
                if answer == inputAnswer:  # 정답과 입력값 비교 후 일치한다면
                    isAnswer = True
                    break

            if isAnswer: #정답 맞췄다면
                gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT  # 다음 라운드 대기로 변경

                self.addScore(author)  # 메세지 보낸사람 1점 획득

                asyncio.ensure_future(self.onAnswer(author))


class SongQuiz(Quiz): #노래 퀴즈

    def __init__(self, quizPath, quizUIFrame, voice, owner):
        super().__init__(quizPath, quizUIFrame, voice, owner) #

class PictureQuiz(Quiz): #그림 퀴즈

    def __init__(self, quizPath, quizUIFrame, voice, owner):
        super().__init__(quizPath, quizUIFrame, voice, owner) #

        self._isLongCount = False #긴 타이머인지

    async def question(self): #문제 내기
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        quizPath = gameData._gamePath + gameData._nowQuiz + "/"

        hintType = gameData._quizUIFrame._option._hintType # 힌트 타입 가져오기

        for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
            if isImage(file):  # 파일 확장자가 사진 파일이라면
                question = file  # 기존 파일명
                Config.LOGGER.info(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {question}\n") #정답 표시
                if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
                    gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
                    roundChecker = gameData._roundIndex  # 현재 라운드 저장

                    imageName = quizPath + "/" + question #이미지 파일 경로, 초기화

                    await gameData._chatChannel.send(file=discord.File(imageName)) #이미지 표시
                    await asyncio.sleep(1) #사진 업로드 대기시간

                    #사진 표시 끝난후
                    if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
                        return
                    if hintType == 2: #힌트 타입이 자동일 떄
                        await self.requestHint() #힌트 요청
                    await countdown(gameData, self._isLongCount)  #카운트 다운

    async def performance(self, user):
        voice = self._voice

        voice.stop() #즉각 보이스 스탑
        playBGM(voice, BGM_TYPE.SUCCESS) #성공 효과음

        roundChecker = self._roundIndex  # 현재 라운드 저장

        quizUIFrame = self._quizUIFrame
        quizUIFrame._title_visible = True
        quizUIFrame._title_text = chr(173)+"[　　　　"+ quizUIFrame._quizIcon + " " + quizUIFrame._quizName + "　　　　]"

        quizUIFrame._sub_visible = True
        quizUIFrame._sub_text = Config.getRandomHumanIcon()+" 정답자　**["+ "　"+str(user.display_name) +"　]**"

        quizUIFrame._main_visible = False
        quizUIFrame._notice_visible = False

        quizUIFrame._field_visible = False

        quizUIFrame._customText_visible = False
        quizUIFrame._page_visible = False
        quizUIFrame._path_visible = False

        quizUIFrame._customFooter_text = ""

        quizUIFrame._useFormat = False
        await quizUIFrame.update()

        await asyncio.sleep(2)  # 2초 대기

class OXQuiz(Quiz): #OX 퀴즈

    def __init__(self, quizPath, quizUIFrame, voice, owner):
        super().__init__(quizPath, quizUIFrame, voice, owner) #

        self._textQuizList = []
        self._selectList = [] #보기
        self._selectionAnswer = 0 #객관식 정답
        self._selectPlayerMap = dict() #사람들 선택한 답
        self._nowOXQuiz = None


    def loadQuiz(self):

        if(os.path.isfile(self._gamePath + "/" + "quiz.txt")):  # 퀴즈 파일 로드

            tmpQuizList = [] #임시 ox퀴즈 객체  저장공간
            addIndex = -1 #현재 작업중인 ox 퀴즈 객체 인덱스
            tmpOXQuiz = None

            f = open(self._gamePath + "/" + "quiz.txt", "r", encoding="utf-8" )
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
                rd = random.randint(0, len(tmpQuizList) - 1)  # 0부터 tmpQuizList 크기 -1 만큼
                quiz = tmpQuizList[rd]  # 무작위 1개 선택
                quizList.append(quiz)  # 퀴즈 목록에 ox 퀴즈 객체 추가
                del tmpQuizList[rd]  # 검사한 항목은 삭제

            self._textQuizList = quizList #ox 퀴즈 리스트 설정

            self._maxRound = len(quizList)  # 문제 총 개수
            self._quizUIFrame._quizCnt = self._maxRound #퀴즈UI 총 문제 개수 갱신
            self._roundIndex = 0  # 현재 라운드

    async def prepare(self):
        await super().prepare()

        message = self._quizUIFrame._myMessage
        asyncio.ensure_future(message.clear_reaction(Config.EMOJI_ICON.ICON_HINT) )#힌트 버튼 삭제
        emoji = Config.EMOJI_ICON.OX[0] #이모지 가져오기,
        asyncio.ensure_future(message.add_reaction(emoji=emoji)) #이모지 추가,
        emoji = Config.EMOJI_ICON.OX[1] #이모지 가져오기,
        asyncio.ensure_future(message.add_reaction(emoji=emoji)) #

    def parseAnswer(self):
        gameData = self

        oxQuiz = gameData._textQuizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
        gameData._nowQuiz = oxQuiz._answer  # 퀴즈 정답 등록

        gameData._selectList.append(Config.EMOJI_ICON.OX[0]) # 보기에 넣기
        gameData._selectList.append(Config.EMOJI_ICON.OX[1])

        if oxQuiz._answer == "O":
            gameData._selectionAnswer = 0 #정답 번호 등록
        else:
            gameData._selectionAnswer = 1

        gameData._selectPlayerMap.clear() #선택한 정답 맵 클리어

    async def question(self): #문제 내기
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        oxQuiz = gameData._textQuizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
        gameData._oxQuizObject = oxQuiz
        questionText = oxQuiz._questionText #문제 str

        quizUIFrame._useFormat = True
        quizUIFrame._notice_visible = True
        quizUIFrame._notice_text = Config.EMOJI_ICON.ICON_QUIZ_DEFAULT + "　**문제**\n" + chr(173) + "\n"
        quizUIFrame._notice_text += questionText + "\n"

        Config.LOGGER.info(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {gameData._nowQuiz}\n") #정답 표시

        playBGM(voice, BGM_TYPE.BELL)

        await asyncio.sleep(1.0) #1초 대기 후

        gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
        if roundChecker != gameData._roundIndex:  return # 이미 다음 라운드라면 리턴
        await countdown(gameData, isLong=True)  #카운트 다운

    async def showAnswer(self, isWrong=False):
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        channel = self._chatChannel
        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT
        #await asyncio.sleep(0.5)

        quizUIFrame._notice_text = "" #문제 없애기

        answerIndex = str(gameData._selectionAnswer) #정답 번호
        answerDesc = gameData._oxQuizObject._answerText

        answerFrame = ui.QFrame()
        answerFrame._sub_visible = True
        answerFrame._sub_text = Config.EMOJI_ICON.ICON_POINT + " 정답: " + str(gameData._selectList[gameData._selectionAnswer])

        answerFrame._main_visible = False

        answerFrame._field_visible = True
        isWrong = True #정답자 존재하는가?
        answerPlayers = ""
        for player in gameData._selectPlayerMap:
            if str(gameData._selectPlayerMap[player]) == answerIndex: #플레이어가 선택한 답과 정답이 일치하면
                isWrong = False #정답자 존재!
                answerPlayers += player.display_name + "\n"
                answerFrame.addField(player.display_name, Config.EMOJI_ICON.ICON_GOOD)
                self.addScore(player)

        answerFrame._title_visible = True
        if isWrong: #오답일 시
            playBGM(voice, BGM_TYPE.FAIL)
            answerFrame._title_text = chr(173)+"[　　　　"+ Config.getRandomWrongIcon() +" 정답 공개　　　　]"
            answerFrame._embedColor = discord.Color.red()
            answerFrame.addField("정답자 없음", "😢")
        else:
            playBGM(gameData._voice, BGM_TYPE.SUCCESS) #성공 효과음
            answerFrame._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_COLLECT +" 정답!　　　　]"
            answerFrame._sub_text = chr(173)+"\n" + Config.getRandomHumanIcon()+" 정답자　\n**"+ "　"+str(answerPlayers) +"　**" + "\n"
            answerFrame._embedColor = discord.Color.green()

        if answerDesc != "": #추가 설명이 있다면
            answerFrame._notice_visible = True
            answerFrame._notice_text = Config.EMOJI_ICON.ICON_PEN + " *" + answerDesc + "*"
        else:
            answerFrame._notice_visible = False

        if gameData._thumbnail != None:
            answerFrame._image_visible = True
            answerFrame._image_local = True
            answerFrame._image_url = gameData._thumbnail

        answerFrame._page_visible = False
        answerFrame._path_visible = False

        answerFrame._customFooter_visible = True
        if(gameData._roundIndex < gameData._maxRound):  # 이 문제가 마지막 문제가 아니었다면
            answerFrame._customFooter_text = Config.EMOJI_ICON.ICON_NOTICE + " 곧 다음 문제로 진행됩니다."
        else:
            answerFrame._customFooter_text = Config.EMOJI_ICON.ICON_NOTICE + " 이제 순위가 공개됩니다."

        await ui.popFrame(channel, answerFrame)

        await asyncio.sleep(3)

    ##이벤트
    async def action(self, reaction, user):
        emoji = reaction.emoji # 반응한 이모지 가져오기

        index = 0

        while index < len(Config.EMOJI_ICON.OX[index]):
            if Config.EMOJI_ICON.OX[index] == emoji:
                self._selectPlayerMap[user] = index #선택한 번호 저장하기
                break
            index += 1



class IntroQuiz(Quiz): #인트로 퀴즈

    def __init__(self, quizPath, quizUIFrame, voice, owner):
        super().__init__(quizPath, quizUIFrame, voice, owner) #
        self._questionFile = ""
        self._answerFile = ""

    def getAudio(self): #노래 파일 가져오기
        gameData = self
        quizPath = self._gamePath + self._nowQuiz + "/"

        audioLength = 0
        for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
            if file.startswith("q"):  # q로 시작하는게 문제파일
                gameData._questionFile = quizPath + "/" + file  # 문제 설정
                if file.endswith(".wav"): #확장자 wav 일때
                    f = sf.SoundFile(gameData._questionFile) #오디오 파일 로드
                    audioLength = len(f) / f.samplerate #오디오 길이
                    f.close()
                elif file.endswith(".mp3"): #확장자 mp3일때
                    audio = MP3(gameData._questionFile)
                    audio_info = audio.info
                    audioLength = int(audio_info.length) #음악 총 길이

            elif file.startswith("a"): #a로 시작하는게 정답파일
                gameData._answerFile = quizPath + "/" + file  # 정답 설정

            if isImage(file): #사진파일이라면 ,썸네일임
                gameData._thumbnail = quizPath + "/" + file

        return gameData._questionFile, audioLength

    async def question(self): #문제 내기
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER

        audioData = self.getAudio()
        audioName = audioData[0]
        audioLength = audioData[1]

        repartCnt = gameData._repeatCount #반복횟수
        quizUIFrame._quizMaxTime = audioLength #노래 길이

        quizUIFrame._useFormat = True #정해진 포맷 사용

        hintType = gameData._quizUIFrame._option._hintType # 힌트 타입 가져오기


        limit = 0

        while repartCnt > 0: #반복횟수만큼 반복
            repartCnt -= 1

            voice.stop() #우선 보이스 중지
            voice.play(discord.FFmpegPCMAudio(audioName))  # 노래 재생
            asyncio.ensure_future(fadeIn(voice)) #페이드인
            playTime = 0

            while voice.is_playing():  # 재생중이면
                if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                    return #리턴
                await asyncio.sleep(0.9)  # 0.9초후 다시 확인
                playTime += 1 #재생 1초 +
                leftTime = audioLength  - playTime #남은 길이
                quizUIFrame._quizLeftTime = leftTime

                if leftTime < 0:
                    leftTime = 0

                limit += 1
                if limit > 1000: return

                await quizUIFrame.update()

            #재생이 끝난 후
            if roundChecker != gameData._roundIndex: return # 이미 다음 라운드라면 리턴

            await asyncio.sleep(1)

            if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER: #아직도 정답자 기다리는 중이면
                if hintType == 2: #힌트 타입이 자동일 떄
                    await self.requestHint() #힌트 요청
                await countdown(self, isLong=False)

                #카운트다운 끝난 후
                if roundChecker != gameData._roundIndex: return # 이미 다음 라운드라면 리턴
                if self.checkStop(): return #게임 중지됐으면 return

    async def showAnswer(self, isWrong=False): #정답 공개, isWrong 은 오답여부
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        channel = self._chatChannel
        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT # 다음 라운드 대기로 변경

        voice.stop() #즉각 보이스 스탑
        voice.play(discord.FFmpegPCMAudio(gameData._answerFile))  # 정답 재생
        asyncio.ensure_future(fadeIn(voice)) #페이드인
        playTime = 0

        author = ""
        tmpSp = gameData._nowQuiz.split("&^")
        if len(tmpSp) == 2: #만약 작곡자가 적혀있다면
            author = tmpSp[1] #작곡자 저장

        answerStr = "" #정답 공개용 문자열
        for tmpStr in gameData._answerList:
            answerStr += tmpStr + "\n" #정답 문자열 생성

        answerFrame = ui.QFrame()

        answerFrame._sub_visible = True
        answerFrame._sub_text = ""

        answerFrame._title_visible = True
        if isWrong: #오답일 시
            #playBGM(voice, BGM_TYPE.FAIL)
            answerFrame._title_text = chr(173)+"[　　　　"+ Config.getRandomWrongIcon() +" 정답 공개　　　　]"
            answerFrame._embedColor = discord.Color.red()
        else:
            answerFrame._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_COLLECT +" 정답!　　　　]"
            answerFrame._sub_text = chr(173)+"\n" + Config.getRandomHumanIcon()+" 정답자　**["+ "　"+str(gameData._answerPlayer.display_name) +" ]**" + "\n"
            answerFrame._embedColor = discord.Color.green()

        answerFrame._author = gameData._answerPlayer

        answerFrame._sub_text += Config.EMOJI_ICON.ICON_LIST + " **정답 목록**\n"+ chr(173) + "\n"+answerStr

        answerFrame._main_visible = False

        if author != "": #추가 설명이 있다면
            answerFrame._notice_visible = True
            answerFrame._notice_text = Config.EMOJI_ICON.ICON_PEN + " *" + author + "*"
        else:
            answerFrame._notice_visible = False



        answerFrame._field_visible = True
        for player in self.sortScore(): #점수판 추가
            playerName = player.display_name
            answerFrame.addField(playerName,"[ " + str(gameData._scoreMap[player]) + "p" +" ]")

        if gameData._thumbnail != None:
            answerFrame._image_visible = True
            answerFrame._image_local = True
            answerFrame._image_url = gameData._thumbnail


        answerFrame._page_visible = False
        answerFrame._path_visible = False

        answerFrame._customFooter_visible = True
        if(gameData._roundIndex < gameData._maxRound):  # 이 문제가 마지막 문제가 아니었다면
            answerFrame._customFooter_text = Config.EMOJI_ICON.ICON_NOTICE + " 곧 다음 문제로 진행됩니다."
        else:
            answerFrame._customFooter_text = Config.EMOJI_ICON.ICON_NOTICE + " 이제 순위가 공개됩니다."

        await ui.popFrame(channel, answerFrame)

        while voice.is_playing():  # 정답 파일 재생중이면
            if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                voice.stop() #재생 중지
            await asyncio.sleep(0.5)  # 0.5초후 다시 확인


class TextQuiz(Quiz): #QNA 텍스트 퀴즈

    def __init__(self, quizPath, quizUIFrame, voice, owner):
        super().__init__(quizPath, quizUIFrame, voice, owner) #

        self._textQuizList = [] #텍스트 퀴즈들
        self._isLongCount = False

    def loadQuiz(self):
        gameData = self

        if(os.path.isfile(gameData._gamePath + "/" + "quiz.txt")):  # 퀴즈 파일 로드

            tmpQuizList = [] #임시 ox퀴즈 객체  저장공간
            addIndex = -1 #현재 작업중인 ox 퀴즈 객체 인덱스
            tmpOXQuiz = None

            f = open(gameData._gamePath + "/" + "quiz.txt", "r", encoding="utf-8" )
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
                rd = random.randint(0, len(tmpQuizList) - 1)  # 0부터 tmpQuizList 크기 -1 만큼
                quiz = tmpQuizList[rd]  # 무작위 1개 선택
                quizList.append(quiz)  # 퀴즈 목록에 ox 퀴즈 객체 추가
                del tmpQuizList[rd]  # 검사한 항목은 삭제

            self._textQuizList = quizList #텍스트 퀴즈들

            self._maxRound = len(quizList)  # 문제 총 개수
            self._quizUIFrame._quizCnt = self._maxRound #퀴즈UI 총 문제 개수 갱신
            self._roundIndex = 0  # 현재 라운드

    def parseAnswer(self):
        gameData = self

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


    async def question(self): #문제 내기
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        textQuiz = gameData._textQuizList[gameData._roundIndex]  # 현재 진행중인 문제 가져오기
        questionText = textQuiz._questionText #문제 str

        quizUIFrame._useFormat = True
        quizUIFrame._notice_visible = True
        quizUIFrame._notice_text = Config.EMOJI_ICON.ICON_QUIZ_DEFAULT + "　**문제**\n" + chr(173) + "\n"
        quizUIFrame._notice_text += questionText + "\n"

        Config.LOGGER.info(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {gameData._nowQuiz}\n") #정답 표시

        playBGM(voice, BGM_TYPE.BELL)
        await quizUIFrame.update()

        await asyncio.sleep(1.0) #1초 대기 후

        gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER
        if roundChecker != gameData._roundIndex:  return # 이미 다음 라운드라면 리턴
        await countdown(gameData, isLong=self._isLongCount)  #카운트 다운


    async def performance(self, user):
        voice = self._voice

        voice.stop() #즉각 보이스 스탑
        playBGM(voice, BGM_TYPE.SUCCESS) #성공 효과음

        roundChecker = self._roundIndex  # 현재 라운드 저장

        quizUIFrame = self._quizUIFrame
        quizUIFrame._title_visible = True
        quizUIFrame._title_text = chr(173)+"[　　　　"+ quizUIFrame._quizIcon + " " + quizUIFrame._quizName + "　　　　]"

        quizUIFrame._sub_visible = True
        quizUIFrame._sub_text = Config.getRandomHumanIcon()+" 정답자　**["+ "　"+str(user.display_name) +"　]**"

        quizUIFrame._main_visible = False
        quizUIFrame._notice_visible = False

        quizUIFrame._field_visible = False

        quizUIFrame._customText_visible = False
        quizUIFrame._page_visible = False
        quizUIFrame._path_visible = False

        quizUIFrame._customFooter_text = ""

        quizUIFrame._useFormat = False
        await quizUIFrame.update()

        await asyncio.sleep(2)  # 2초 대기


class MultiplayQuiz(Quiz): #멀티플레이 퀴즈

    def __init__(self, quizPath, quizUIFrame, voice, owner, targetGuild, pathList):
        super().__init__(quizPath, quizUIFrame, voice, owner) #

        self._targetGuild = targetGuild #상대 서버
        self._targetData = None #상대 게임 데이터
        self._pathList = pathList #퀴즈 데이터 불러올 경로 목록
        self._netStep = NET_STEP.GET_TARGET #동기화용 스탭
        self._multiplayScoreMap = dict()
        self._multiOwner = None #퀴즈 주도자
        self._maxTime = 30
        self._leftTime = 30
        self._leftRepeatCnt = 1
        self._audioData = None
        self._voiceSync = True


    ##멀티 전용
    async def sync(self, isSyncRound=False): #동기화, isSyncRound 는 라운드 강제 동기 여부
        try:
            targetData = self._targetData
            syncMessage = None

            loopCnt = Config.MAX_CONNECTION / Config.SYNC_INTERVAL
            i = 0
            while self._netStep != targetData._netStep: #단계 같아질때까지
                await asyncio.sleep(Config.SYNC_INTERVAL) # 확인 딜레이
                if targetData._gameStep == GAME_STEP.END: #상대가 게임 끝났다면
                    return #동기화 중지

                    # #now = datetime.datetime.now() #동기 성공 시간 표시
                    # #print(str(self._netStep)+", "+str(now))

                i += 1
                if i > loopCnt:
                    asyncio.ensure_future(self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" 연결 시간 초과\n"+chr(173)+" ```"))
                    await self.connectionTimeout()
                    return False
                elif i > loopCnt / 5: #일정 시간 경과하면 동기화중이라는 메시지 표시
                    if syncMessage == None:
                        syncMessage = await self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" 동기화 중... 잠시만 기다려주세요.\n"+chr(173)+" ```")
        except:
            Config.LOGGER.error("동기화 에러")
            Config.LOGGER.error(traceback.format_exc())
            return False

        if isSyncRound:
            if self._roundIndex != targetData._roundIndex: #라운드 강제 동기
                if self._roundIndex > targetData._roundIndex:
                    targetData._roundIndex = self._roundIndex
                else:
                    self._roundIndex = targetData._roundIndex

        try:
            if syncMessage != None:
                asyncio.ensure_future(syncMessage.delete()) #동기화 메시지 삭제
        except:
            Config.LOGGER.error("동기 메시지 삭제 에러")
            Config.LOGGER.error(traceback.format_exc())

        await asyncio.sleep(1) #상대도 동기할 수 있도록 1초 대기
        return True


    async def toggleVoiceSync(self): #보이스 객체 재연결 여부
        if self._voiceSync:
            self._voiceSync = False
            asyncio.ensure_future(self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.OX[1]+" 보이스 동기화가 비활성화 됐습니다.\n"
                                         +"노래가 시작될때 보이스 재연결을 하지 않습니다.\n상대 서버보다 노래가 1초~2초 정도 늦게 들릴 수 있습니다."+chr(173)+" ```"))
        else:
            self._voiceSync = True
            asyncio.ensure_future(self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.OX[0]+" 보이스 동기화가 활성화 됐습니다.\n"
                                         +"노래가 시작될때 보이스 재연결을 진행합니다.\n상대 서버와 노래가 동시가 송출됩니다."+chr(173)+" ```"))


    def submitScoreboard(self, winner):
        sendScoreMap = dict()

        for guild in self._multiplayScoreMap.keys():
            if guild == winner: #승리자면
                sendScoreMap[guild] = 1 #승리 점수
            else:
                sendScoreMap[guild] = 0  #패배 점수

        scoreboard = ui.getMultiplayScoreboard(self._gameName)  #퀴즈명으로 멀티용 순위표  가져오기
        scoreboard.mergeScore(sendScoreMap) #현재 한 퀴즈 결과에 대한 순위표와 병합

    async def sendMultiplayMessage(self, author, chatMessage):
        targetData = self._targetData
        if targetData == None: return

        sendMsg = "```markdown\n##"+Config.EMOJI_ICON.ICON_CHAT+" [" + str(self._guild.name) + "]  에서 메세지를 보냈습니다. \n" + Config.getRandomHumanIcon() + " [" + str(author.display_name) + "] ( " + chatMessage + ")\n```"

        asyncio.ensure_future(self._chatChannel.send(sendMsg))
        asyncio.ensure_future(targetData._chatChannel.send(sendMsg))

    ##오버라이딩
    def loadQuiz(self): #문제 로드

        quizList = []  # 빈 리스트 선언
        for quizPath in self._pathList: #정해진 각 퀴즈 경로에 대해
            tmpList = os.listdir(quizPath)            # 퀴즈 폴더 내 모든 파일 불러오기
            for tmpQuiz in tmpList:
                abPath = quizPath + "/" + tmpQuiz
                if(os.path.isdir(abPath)):  # 폴더인지 확인(폴더만 추출할거임)
                    quizList.append(abPath) #퀴즈 목록에 추가, 절대 경로를 추가함

        Config.LOGGER.debug(str(len(quizList)) + "개")
        for i in range(0, 50): #50문제만 뽑을거임
            rd = random.randint(0, len(quizList) - 1)  # 0부터 tmpList 크기 -1 만큼
            quiz = quizList[rd]  # 무작위 1개 선택
            self._quizList.append(quiz)  # 실제 목록에 추가
            del quizList[rd]  # 추출한 항목은 삭제

        self._maxRound = len(self._quizList)  # 문제 총 개수
        self._quizUIFrame._quizCnt = self._maxRound #퀴즈UI 총 문제 개수 갱신
        self._roundIndex = 0  # 현재 라운드


    def sortScore(self):#정렬된 점수 맵 반환
        gameData = self
        targetData = self._targetData

        tmpMap = dict()  # 빈 점수 맵
        myScore = 0 #내 점수
        for score in gameData._scoreMap.values():  # 정렬
            myScore += score #점수 합산

        myGuild = self._guild
        tmpMap[myGuild] = myScore

        targetScore = 0 #상대 점수
        for score in targetData._scoreMap.values():  # 정렬
            targetScore += score #점수 합산

        targetGuild = targetData._guild
        tmpMap[targetGuild] = targetScore

        sortGuild = []
        for guild in tmpMap.keys():  # 정렬
            index = 0  # 인덱스
            score = tmpMap[guild]  # 점수
            while index < len(sortGuild):
                cp = sortGuild[index]  # 비교대상
                cp_score = tmpMap[cp]  # 비교대상 점수
                if score > cp_score:  # 비교대상보다 점수높으면
                    break  # while 빠져나가기
                index += 1  # 다음 대상으로
            sortGuild.insert(index, guild)  # 삽입 장소에 추가

        self._multiplayScoreMap.clear()
        for guild in sortGuild: #데이터 재삽입
            self._multiplayScoreMap[guild] = tmpMap[guild]

        return self._multiplayScoreMap

    def setScoreField(self, uiFrame):
        multiplayScoreMap = self.sortScore()
        for guild in multiplayScoreMap.keys(): #점수판 추가
            guildName = guild.name
            uiFrame.addField(guildName, "[ " + str(multiplayScoreMap[guild]) + "점 ]")

    def parseAnswer(self): #정답 인정 목록 추출
        quizPath = self._quizList[self._roundIndex - 1]  # 현재 진행중인 문제 가져오기
        self._nowQuiz = quizPath  # 퀴즈 전체 경로 저장
        answer = []  # 빈 리스트 선언
        tmpSplit = quizPath.split("/")
        quizTitle = tmpSplit[len(tmpSplit) - 1] #파일 전체 이름 가져오기
        title = quizTitle.split("&^")[0] #먼저 제목만 뽑기

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

        self._answerList = answer #정답 인정 목록 설정


    def getAudioData(self): #노래 파일 가져오기
        gameData = self
        guild = self._guild
        quizPath = self._nowQuiz + "/"

        isTrimed = False
        audioStart = 0
        audioEnd = 0

        for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
            if file.endswith(".png") or file.endswith("jpg"): #사진파일이라면 ,썸네일임
                gameData._thumbnail = quizPath + "/" + file
            elif file.endswith(".wav") or file.endswith(".mp3"):  # 파일 확장자가 .wav 또는 .mp3면, 문제 파일일거임
                question = file  # 기존 파일명
                audioName = quizPath + "/" + question #실제 실행할 음악파일 경로
                audioLength = 39 #오디오 길이
                Config.LOGGER.info(f"guild: {gameData._guild.name}, target: {gameData._targetData._guild.name}, gameName: {gameData._gameName}, questionFile: {audioName}\n") #정답 표시
                try:
                    if file.endswith(".wav"): #확장자 wav 일때
                        f = sf.SoundFile(audioName) #오디오 파일 로드
                        length_in_secs = len(f) / f.samplerate #오디오 길이
                        f.close()
                    elif file.endswith(".mp3"): #확장자 mp3일때
                        audio = MP3(audioName)
                        audio_info = audio.info
                        length_in_secs = int(audio_info.length) #음악 총 길이

                    if length_in_secs > gameData._trimLength + 1: #음악이 자를 시간 초과할 시, 자르기 시작
                        length_in_secs = int(length_in_secs)
                        if length_in_secs > gameData._trimLength + 20: #노래 길이가 자를 시간 + 20만큼 크면
                            #최적의 자르기 실행
                            startTime = random.randint(10, (length_in_secs - gameData._trimLength - 10) - 1) #자르기 시작 시간 10초 ~ 총길이 - 자를 길이 - 10
                        else:
                            startTime = random.randint(0, length_in_secs - gameData._trimLength - 1)

                        endTime = startTime + gameData._trimLength #지정된 길이만큼 자르기

                        audioStart = toTimestamp(startTime)
                        audioEnd = toTimestamp(endTime)

                        isTrimed = True
                        audioLength = gameData._trimLength
                    else:
                        audioLength = length_in_secs
                except:
                    Config.LOGGER.error("오디오 열기 에러, "+str(file))
                    Config.LOGGER.error(traceback.format_exc())
                    return None

                return audioName, audioLength, isTrimed ,audioStart, audioEnd


    async def question(self): #문제 내기
        gameData = self
        targetData = self._targetData
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        gameData._gameStep = GAME_STEP.WAIT_FOR_ANSWER

        if self._multiOwner == self: #자신이 멀티 플레이 주도자라면
            self._audioData = self.getAudioData() #오디오 정보 얻기
            targetData._audioData = self._audioData #오디오 동기화

        syncMessage = None
        loopCnt = Config.MAX_CONNECTION / Config.SYNC_INTERVAL
        i = 0
        while self._audioData == None or self._audioData != targetData._audioData: #퀴즈 목록 동기화 될 때까지
            await asyncio.sleep(Config.SYNC_INTERVAL) # 0.1초마다 확인

            i += 1
            if i > loopCnt:
                asyncio.ensure_future(self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" 연결 시간 초과\n"+chr(173)+" ```"))
                await self.connectionTimeout()
                return
            elif i > loopCnt / 5:
                if syncMessage == None:
                    syncMessage = await self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" 오디오 동기화 중... 잠시만 기다려주세요.\n"+chr(173)+" ```")

            try:
                if syncMessage != None:
                    asyncio.ensure_future(syncMessage.delete()) #동기화 메시지 삭제
            except:
                Config.LOGGER.error("동기 메시지 삭제 에러")
                Config.LOGGER.error(traceback.format_exc())

        if self._audioData == None or self._audioData != targetData._audioData: #동기 실패시
            return False

        audioData = self._audioData
        audioName = audioData[0]
        audioLength = audioData[1]
        isTrimed = audioData[2]
        startTime = audioData[3]
        endTime = audioData[4]


        repartCnt = gameData._repeatCount #반복횟수

        self._maxTime = audioLength * repartCnt
        self._leftTime = self._maxTime

        quizUIFrame._quizMaxTime = audioLength #노래 길이

        quizUIFrame._useFormat = True #정해진 포맷 사용

        hintType = gameData._quizUIFrame._option._hintType # 힌트 타입 가져오기

        await asyncio.sleep(1) #동기화 체킹을 위해 1초 대기


        while repartCnt > 0: #반복횟수만큼 반복
            repartCnt -= 1

            if voice.source != None:
                voice.source.cleanup()

            voice.stop() #우선 보이스 중지

            if self._voiceSync: #보이스 동기화 사용중이면
                voiceChannel = voice.channel #이러면 노래 동시에 나옴
                await voice.disconnect()
                self._voice = await voiceChannel.connect()
                if self._voice == None or not self._voice.is_connected():
                    await asyncio.sleep(0.5)
                    try:
                        self._voice = await voiceChannel.connect()
                    except:
                        Config.LOGGER.error("voice reconnect error")
                voice = self._voice

            await asyncio.sleep(2)

            # voice.resume() #다시 재생, 버퍼 초기화
            # while voice.is_playing():  # 재생중이면
            #     await asyncio.sleep(1) #다 재생되길 대기
            # try:
            #     voice.source = None
            # except:
            #     pass

            self._netStep = NET_STEP.QUESTION_READY
            #interval = Config.SYNC_INTERVAL/10 # 0.01초마다 확인, 문제 출제는 중요한 부분이라 0.01단위
            interval = 0.01
            loopCnt = Config.MAX_CONNECTION / interval
            i = 0
            while self._netStep != NET_STEP.QUESTION_READY or self._targetData._netStep != NET_STEP.QUESTION_READY: #오디오 준비 동기화 될 때까지
                await asyncio.sleep(interval) #딜레이

                i += 1
                if i > loopCnt:
                    asyncio.ensure_future(self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" 연결 시간 초과\n"+chr(173)+" ```"))
                    await self.connectionTimeout()
                    break

            limit = 0


            if isTrimed: #자르기 옵션이 적용돼 있다면
                voice.play(discord.FFmpegPCMAudio(audioName, before_options="-ss " + startTime + " -to " + endTime))  # 노래 재생
            else:
                voice.play(discord.FFmpegPCMAudio(audioName))

            asyncio.ensure_future(fadeIn(voice)) #페이드인
            playTime = 0

            while voice.is_playing():  # 재생중이면
                if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                    return #리턴
                await asyncio.sleep(0.71)  # 0.71초후 다시 확인 0.29초는 딜레이있어서 뺌
                playTime += 1 #재생 1초 +
                self._leftTime -= 1
                leftTime = audioLength  - playTime #남은 길이
                quizUIFrame._quizLeftTime = leftTime

                if hintType == 2: #힌트 타입이 자동일 떄
                    if playTime > audioLength // 2: #절반 이상 재생됐다면
                        asyncio.ensure_future(self.requestHint()) #힌트 요청

                limit += 1
                if limit > 1000: return

                await quizUIFrame.update()

                if leftTime < 0:
                    leftTime = 0
                    Config.LOGGER.error("fast end")
                    voice.stop()
                    break # 재생시간 초과면 break

        return True


    async def nextRound(self):
        gameData = self

        # rdWait = random.randint(1,5)
        # print(str(self._guild.name)+ str(rdWait) +" 초")
        # await asyncio.sleep(rdWait)

        #인원 수 표시 재설정
        try:
            self._quizUIFrame._notice_visible = True
            self._quizUIFrame._notice_text = Config.EMOJI_ICON.ICON_FIGHT + " 대전 상대: **" + str(self._targetData._guild.name) + " / "+ str(len(self._targetData._voice.channel.voice_states)-1) + "명"+"**\n" + chr(173) + "\n"
            self._quizUIFrame._notice_text += Config.EMOJI_ICON.ICON_CHAT+" !챗 <메세지>　"+chr(173)+" - 　서버간 메시지를 전송합니다.\n" + chr(173) + "\n"
            self._quizUIFrame._notice_text += Config.EMOJI_ICON.ICON_SPEAKER_HIGH+" !보이스동기화　"+chr(173)+"-　노래 싱크 동기화 기능을 활성/비활성 합니다.\n"
            self._quizUIFrame._notice_text += Config.EMOJI_ICON.ICON_WARN+" 기본값은 활성이며 비활성시 보이스 재연결을 하지 않습니다.\n재연결 알림소리가 거슬리면 비활성화 해주세요.\n"
        except:
            pass

        ###### 라운드 표시
        if self.checkStop(): return
        self._netStep = NET_STEP.NEXTROUND
        if not await self.sync(isSyncRound=True): return #동기화
        isError = False
        try:
            isContinue = await self.noticeRound()
            if not isContinue: #퀴즈 속행 아니면 return
                return
        except:
            Config.LOGGER.error("noticeRound error")
            isError = True
            Config.LOGGER.error(traceback.format_exc())

        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        ###### 정답 설정
        if self.checkStop(): return
        if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
            return
        try:
            self.parseAnswer()
        except:
            Config.LOGGER.error("parseAnswer error")
            isError = True
            Config.LOGGER.error(traceback.format_exc())

        ###### 라운드 초기화

        gameData._isSkiped = False
        gameData._useHint = False
        gameData._thumbnail = None # 썸네일 초기화
        gameData._answerPlayer = None #정답자 초기화
        self._maxTime = 30
        self._leftTime = 30
        self._leftRepeatCnt = 1
        self._audioData = None
        self._quizUIFrame.initRound(self._voice.channel)

        await asyncio.sleep(1.5) #상대도 동기할 수 있도록 1초 대기
        ###### 문제 출제
        if self.checkStop(): return
        self._netStep = NET_STEP.QUESTION
        if not await self.sync(isSyncRound=False): return #동기화
        if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
            return
        try:

            await self.question()
        except:
            Config.LOGGER.error("question error")
            isError = True
            Config.LOGGER.error(traceback.format_exc())


        ###### 정답 공개
        if self.checkStop(): return
        if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
            return
        if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER or isError:  # 아직도 정답자 없거나 문제 발생시
            isError = False
            try:
                # self._netStep = NET_STEP.SHOWANSWER #뭔가 문제 있는 듯, 필수 사항은 아니니 pass
                # if not await self.sync(isSyncRound=False): return #동기화
                await self.showAnswer(isWrong=True) #정답 공개
                await asyncio.sleep(3)
            except:
                Config.LOGGER.error("showAnswer error")
                Config.LOGGER.error(traceback.format_exc())

            try:
                await self.nextRound() #다음 라운드 진행
            except:
                Config.LOGGER.error("nextRound error")
                Config.LOGGER.error(traceback.format_exc())



    def addScore(self, user): #점수 추가
        gameData = self

        score = math.ceil((self._leftTime / self._maxTime) * 10)  #남은 시간 비례 점수 계산

        if user in gameData._scoreMap:  # 점수 리스트에 정답자 있는지 확인
            gameData._scoreMap[user] += score  # 있으면 점수 추가
        else:
            gameData._scoreMap[user] = score  # 없으면 새로 점수 추가

    async def forceEnd(self): #멀티용 강제종료
        if self._gameStep == GAME_STEP.END: return
        self._gameStep = GAME_STEP.END
        targetData = self._targetData
        targetData._gameStep = GAME_STEP.END #상대는 정상적으로 끝난거로 하기

        asyncio.ensure_future(self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" 대전 도중 퀴즈를 종료하였습니다.\n대전은 "
                                     +str(targetData._guild.name)+" 서버의 승리로 기록됩니다."+chr(173)+" ```"))

        asyncio.ensure_future(targetData._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" "+str(self._guild.name)
                                           +" 서버가 퀴즈를 종료하였습니다.\n대전은 "+str(targetData._guild.name)+" 서버의 승리로 기록됩니다."+chr(173)+" ```"))

        await targetData._voice.disconnect()
        self.submitScoreboard(targetData._guild) #상대의 승리 처리
        targetData.checkStop()


    async def connectionTimeout(self, isDraw=False): #멀티용 연결 끊김
        if self._gameStep == GAME_STEP.END: return
        self._gameStep = GAME_STEP.END

        if isDraw:
            targetData = self._targetData
            asyncio.ensure_future(self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" "+str(targetData._guild.name)
                                         +" 서버의 연결이 끊김.\n대전은 무승부로 기록됩니다.\n"+chr(173)+" \n```"))

            await self._voice.disconnect()
            self.checkStop()
        else:
            targetData = self._targetData
            asyncio.ensure_future(self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" "+str(targetData._guild.name)
                                         +" 서버의 연결이 끊김.\n대전은 "+str(self._guild.name)+" 서버의 승리로 기록됩니다.\n"+chr(173)+" ```"))

            await self._voice.disconnect()
            self.checkStop()
            self.submitScoreboard(self._guild) #자신의 승리 처리


    async def prepare(self):
        syncMessage = await self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" 객체 동기화 중... 잠시만 기다려주세요.\n"+chr(173)+" ```")
        loopCnt = Config.MAX_CONNECTION / Config.SYNC_INTERVAL
        i = 0
        while self._targetData == None: #상대 객체 얻을때까지
            await asyncio.sleep(Config.SYNC_INTERVAL) # 0.1초마다 확인

            if self._targetGuild in dataMap.keys():
                target_gameData = dataMap[self._targetGuild]._gameData #상대방 게임 데이터 객체 가져옴
                if target_gameData == None: #퀴즈 객체가 없다면
                    continue #계속 탐색

                self._targetData = target_gameData #저장

                try:
                    asyncio.ensure_future(syncMessage.delete()) #동기화 메시지 삭제
                except:
                    Config.LOGGER.error("동기 메시지 삭제 에러")
                    Config.LOGGER.error(traceback.format_exc())
                continue

            i += 1
            if i > loopCnt:
                asyncio.ensure_future(self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" 연결 시간 초과\n"+chr(173)+" ```"))
                await self.connectionTimeout(isDraw=True)
                break

        syncMessage = await self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" 퀴즈 목록 동기화 중... 잠시만 기다려주세요.\n"+chr(173)+" ```")
        loopCnt = Config.MAX_CONNECTION / Config.SYNC_INTERVAL
        i = 0
        while len(self._quizList) == 0 or len(self._targetData._quizList) == 0 or self._quizList != self._targetData._quizList: #퀴즈 목록 받아올때까지
            await asyncio.sleep(Config.SYNC_INTERVAL) # 0.1초마다 확인

            targetData = self._targetData

            if self._multiOwner == None and targetData._multiOwner == None: #주도자가 아직 정해지지 않았다면
                self._multiOwner = self #주도자를 자신으로 설정
                targetData._multiOwner = self
                self.loadQuiz() #퀴즈 로드
                self._targetData._quizList = self._quizList #퀴즈 리스트 동기
            else: #주도자가 정해졌다면
                multiOwner = None
                if self._multiOwner != None:
                    multiOwner = self._multiOwner
                else:
                    multiOwner = targetData._multiOwner
                if multiOwner != None:
                    self._quizList == multiOwner._quizList #주도자한테 퀴즈 받아옴

            i += 1
            if i > loopCnt:
                asyncio.ensure_future(self._chatChannel.send("``` "+chr(173)+"\n"+Config.EMOJI_ICON.ICON_MULTIPLAY+" 퀴즈 목록 동기화 실패, 대전을 중지합니다.\n"+chr(173)+" ```"))
                await self.connectionTimeout(isDraw=True)
                return

        try:
            asyncio.ensure_future(syncMessage.delete()) #동기화 메시지 삭제
        except:
            Config.LOGGER.error("동기 메시지 삭제 에러")
            Config.LOGGER.error(traceback.format_exc())


        self._maxRound = len(self._quizList)  # 문제 총 개수
        self._quizUIFrame._quizCnt = self._maxRound #퀴즈UI 총 문제 개수 갱신
        self._roundIndex = 0  # 현재 라운드


    async def finishGame(self): #퀴즈 종료
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        channel = self._chatChannel

        voice.stop()

        # rdWait = random.randint(3,20)
        # print(str(self._guild.name)+ str(rdWait) +" 초")
        # await asyncio.sleep(rdWait)

        self._netStep = NET_STEP.SHOWSCORE
        if not await self.sync(isSyncRound=False): return #동기화

        gameData._gameStep = GAME_STEP.END

        quizUIFrame._useFormat = False

        quizUIFrame._title_visible = True
        quizUIFrame._title_text = chr(173)+"[　　　　"+ Config.getMedalFromNumber(0) + " " + "순위 발표" + "　　　　]"

        quizUIFrame._sub_visible = True
        quizUIFrame._sub_text = "퀴즈명:　"+ chr(173) + quizUIFrame._quizIcon + " " + quizUIFrame._quizName + " / " + "멀티플레이"

        quizUIFrame._notice_visible = False

        quizUIFrame._embedColor = discord.Color.gold() #색상 선택

        quizUIFrame._customText_visible = False
        quizUIFrame._customFooter_text = ""

        quizUIFrame._page_visible = False
        quizUIFrame._path_visible = False

        playBGM(voice, BGM_TYPE.BELL)
        await quizUIFrame.update()
        await asyncio.sleep(3)

        quizUIFrame._notice_visible = True
        quizUIFrame._notice_text = "" #점수 표시할 곳

        multiplayScoreMap = self.sortScore()

        if len(multiplayScoreMap.keys()) == 0: #정답자 아무도 없다면
            playBGM(voice, BGM_TYPE.FAIL)
            quizUIFrame._notice_text = "**헉! 😅 정답자가 아무도 없습니다... \n많이 어려우셨나요...? 😢**" #점수 표시할 곳
            await quizUIFrame.update()
        else:
            i = 1
            for guild in multiplayScoreMap.keys(): #점수판 추가
                guildName = guild.name
                quizUIFrame._notice_text += str(Config.getMedalFromNumber(i)) + " " + guildName + "　"+ chr(173) + "　" + str(multiplayScoreMap[guild]) + "점　" + chr(173)

                if i == 1: #1등이면
                    quizUIFrame._notice_text += Config.EMOJI_ICON.ICON_POINT_TO_LEFT + "　**최고의 " + str(self._topNickname) + "**\n"

                quizUIFrame._notice_text += chr(173) + "\n"

                if i <= 3: #3등까지는 한 개씩 보여줌
                    playBGM(voice, BGM_TYPE.SCORE_ALARM)
                    await quizUIFrame.update()
                    await asyncio.sleep(2)

                i += 1

            if len(gameData._scoreMap) > 3: #4명이상 플레이 했다면
                playBGM(voice, BGM_TYPE.SCORE_ALARM) #나머지 발표
                await quizUIFrame.update()

            if self._multiOwner == self: #주도자가 자신일 때
                keys = list(multiplayScoreMap.keys())
                winner = keys[0]
                if multiplayScoreMap[winner] != 0: #1등이 0점 아니면
                    self.submitScoreboard(winner)

        mvpUser = None
        bestScore = 0

        for user in gameData._scoreMap.keys():
            score = gameData._scoreMap[user]
            if score > bestScore:
                bestScore = score
                mvpUser = user

        targetData = self._targetData
        for user in targetData._scoreMap.keys():
            score = targetData._scoreMap[user]
            if score > bestScore:
                bestScore = score
                mvpUser = user

        if mvpUser != None:
            quizUIFrame._notice_text += chr(173)+"\n"+str(Config.EMOJI_ICON.ICON_TROPHY) + " " + "MVP　[ " + str(mvpUser.display_name) + " ], " + str(bestScore) + "점 획득" + chr(173)
            playBGM(voice, BGM_TYPE.SUCCESS) #mvp발표
            await quizUIFrame.update()


        await asyncio.sleep(4)

        quizUIFrame._customText_visible = True
        quizUIFrame._customFooter_text = Config.EMOJI_ICON.ICON_NOTICE + " 퀴즈가 종료되었습니다."
        Config.LOGGER.info(self._guild.name+" 에서 " + self._gameName + " 퀴즈 종료")
        playBGM(voice, BGM_TYPE.ENDING)
        await quizUIFrame.update()
        await asyncio.sleep(2)
        await voice.disconnect()
        self.checkStop() #데이터 삭제

    async def requestHint(self): #힌트 사용
        gameData = self #게임 데이터 불러올거임
        targetData = self._targetData

        gameData._useHint = True #힌트 사용으로 변경
        asyncio.ensure_future(gameData._chatChannel.send("```"+str(gameData._guild.name)+" 서버가 힌트 요청에 투표하셨습니다.　"+chr(173)+"　"+chr(173)+"　"+"```"))
        asyncio.ensure_future(targetData._chatChannel.send("```"+str(gameData._guild.name)+" 서버가 힌트 요청에 투표하셨습니다.　"+chr(173)+"　"+chr(173)+"　"+"```"))

        if not targetData._useHint: #상대가 힌트 사용 상태가 아니면
            return

        #상대가 힌트 사용 상태인데 해당 객체가 힌트 요청했다면

        #힌트 표시
        answer = gameData._answerList[0] #정답 가져오기
        answer = answer.upper() #대문자로
        #answer = answer.replace(" ", "") #공백 제거
        answerLen = len(answer) #문자 길이
        hintLen = math.ceil(answerLen / 4) #표시할 힌트 글자수
        hintStr = "" #힌트 문자열

        hintIndex = []
        index = 0
        limit = 0
        while index < hintLen: #인덱스 설정
            limit += 1
            if  limit > 1000: #시도 한계 설정
                break

            rd = random.randint(0, answerLen - 1)
            if rd in hintIndex or answer[rd] == " ": #이미 인덱스에 있거나 공백이라면
                continue
            else:
                hintIndex.append(rd)
                index += 1

        index = 0
        while index < answerLen:
            if index in hintIndex: #만약 해당 글자가 표시인덱스에 있다면
                hintStr += answer[index] #해당 글자는 표시하기
            elif answer[index] == " ": #공백도 표시
                hintStr += answer[index]
            else:
                hintStr += Config.EMOJI_ICON.ICON_BLIND
            index += 1

        asyncio.ensure_future(gameData._chatChannel.send("```markdown\n"+chr(173)+"\n""## 요청에 의해 힌트가 제공됩니다.\n"+chr(173)+"\n"+Config.EMOJI_ICON.ICON_HINT+" <힌트>　"+chr(173)+"* "+str(hintStr)+"\n"+chr(173)+"```"))
        asyncio.ensure_future(targetData._chatChannel.send("```markdown\n"+chr(173)+"\n""## 요청에 의해 힌트가 제공됩니다.\n"+chr(173)+"\n"+Config.EMOJI_ICON.ICON_HINT+" <힌트>　"+chr(173)+"* "+str(hintStr)+"\n"+chr(173)+"```"))


    ##이벤트
    async def on_message(self, message):
        gameData = self
        author = message.author

        if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER: #정답자 대기중이면
            inputAnswer = message.content.replace(" ", "").upper() #공백 제거 및 대문자로 변경
            isAnswer = False
            for answer in gameData._answerList: #정답 목록과 비교
                answer = answer.replace(" ", "").upper() # 공백 제거 및 대문자로 변경
                if answer == inputAnswer:  # 정답과 입력값 비교 후 일치한다면
                    isAnswer = True
                    break

            if isAnswer: #정답 맞췄다면
                if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER: #아직도 정답 대기자라면, 멀티에서만 확인 필요
                    targetData = self._targetData

                    targetData._gameStep = GAME_STEP.WAIT_FOR_NEXT  # 상대 퀴즈 객체 다음 라운드 대기로 변경
                    gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT  # 다음 라운드 대기로 변경

                    self.addScore(author)  # 메세지 보낸사람 1점 획득

                    asyncio.ensure_future(self.onAnswer(author)) #자신은 정답
                    asyncio.ensure_future(targetData.onAnswer(author, isWrong=True)) #상대는 오답



dataMap = dict()  # 데이터 저장용 해쉬맵
QUIZ_MAP = dict()  # 퀴즈 정보 저장용
newGuilds = []

########################


bot = commands.Bot(command_prefix=Config.BOT_PREFIX)  # 봇 커맨드 설정

#Utility
async def fadeIn(voice):
    if not voice.is_playing(): #보이스 재생중아니면
        return # 즉각 리턴

    try:
        voice.source = discord.PCMVolumeTransformer(voice.source)
        volume = 0.05  # 초기볼륨
        voice.source.volume = volume  # 볼륨 설정
        while volume < 1.0:  # 페이드 인
            volume += 0.05
            voice.source.volume = volume  # 볼륨 설정
            await asyncio.sleep(0.10)
    except:
        Config.LOGGER.error("fade In error")
        Config.LOGGER.error(traceback.format_exc())



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
        Config.LOGGER.error("fade out error")
        Config.LOGGER.error(traceback.format_exc())


async def clearAll(chatChannel):
    asyncio.ensure_future(chatChannel.purge(limit=100))


async def countdown(gameData, isLong=False): #카운트 다운
    leftSec = 15 if isLong else 7 #남은 초
    voice = gameData._voice
    quizUIFrame = gameData._quizUIFrame

    roundChecker = gameData._roundIndex

    quizUIFrame._useFormat = True #정해진 포맷 사용
    quizUIFrame._quizMaxTime = leftSec #최대 시간

    if isLong: #긴 타이머면
        playBGM(voice, BGM_TYPE.LONGTIMER) #카운트 다운 브금
    else:
        playBGM(voice, BGM_TYPE.countdown10) #카운트 다운 브금
    voice.source = discord.PCMVolumeTransformer(voice.source)
    volume = 1.0 # 초기볼륨
    voice.source.volume = volume

    limit = 0
    while voice.is_playing():  # 카운트다운중이면
        if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
            voice.stop() #카운트다운 정지
            return #리턴
        await asyncio.sleep(1)  # 1초후 다시 확인

        limit += 1
        if limit > 100: return
        leftSec -= 1 #남은 초 -1
        if leftSec < 0: leftSec = 0
        quizUIFrame._quizLeftTime = leftSec
        await quizUIFrame.update()


#사전 정의 함수
def convert(seconds): #초 값을 시,분,초 로 반환
    hours = seconds // 3600
    seconds %= 3600
    mins = seconds//60
    seconds %= 60

    return hours, mins, seconds

def toTimestamp(second): #초 단위 값을 timestamp(HH:MM:SS) 형식으로 변경
    hour = second // 3600
    if hour > 99: #최대 99
        hour = str(99)
    elif hour < 10: #최저 2자리수로
        hour = "0" + str(hour)
    else: #문자열로
        hour = str(hour)
    second %= 3600

    min = second // 60
    if min < 10:
        min = "0" + str(min)
    else:
        min = str(min)

    second %= 60
    if second < 10:
        second = "0" + str(second)
    else:
        second = str(second)

    return str(hour + ":" + min + ":" + second)

def korean_to_be_single(korean_word):
    """
    한글 단어를 입력받아서 초성/중성/종성을 구분하여 리턴해줍니다.
    """
    ####################################
    # 초성 리스트. 00 ~ 18
    CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    # 중성 리스트. 00 ~ 20
    JUNGSUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
    # 종성 리스트. 00 ~ 27 + 1(1개 없음)
    JONGSUNG_LIST = [' ', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    ####################################
    r_lst = []
    for w in list(korean_word.strip()):
        if '가'<=w<='힣':
            ch1 = (ord(w) - ord('가'))//588
            ch2 = ((ord(w) - ord('가')) - (588*ch1)) // 28
            ch3 = (ord(w) - ord('가')) - (588*ch1) - 28*ch2
            r_lst.append([CHOSUNG_LIST[ch1], JUNGSUNG_LIST[ch2], JONGSUNG_LIST[ch3]])
        else:
            r_lst.append([w])
    return r_lst

def isImage(file):
    if file.endswith(".png") or file.endswith(".jpg") or file.endswith(".gif") or file.endswith(".PNG") or file.endswith(".webp"):
        return True
    else:
        return False

def getGuildData(guild):
    if guild in dataMap.keys():  # 서버 데이터 가져오기
        guildData = dataMap[guild]
    else: # 서버 데이터가 없다면
        guildData = GuildData(guild) # 새로운 서버 데이터 생성
        dataMap[guild] = guildData #데이터 해쉬맵에 등록

    return guildData

def playBGM(voice, bgmType): #BGM 틀기
    try:
        if(bgmType == BGM_TYPE.PLING):
            source = discord.FFmpegPCMAudio(Config.BGM_PATH + "pling.mp3")
        elif(bgmType == BGM_TYPE.ROUND_ALARM):
            source = discord.FFmpegPCMAudio(Config.BGM_PATH + "ROUND_ALARM.mp3")
        elif(bgmType == BGM_TYPE.SCORE_ALARM):
            source = discord.FFmpegPCMAudio(Config.BGM_PATH + "SCORE_ALARM.mp3")
        elif(bgmType == BGM_TYPE.ENDING):
            source = discord.FFmpegPCMAudio(Config.BGM_PATH + "ENDING.mp3")
        elif(bgmType == BGM_TYPE.FAIL):
            source = discord.FFmpegPCMAudio(Config.BGM_PATH + "FAIL.mp3")
        elif(bgmType == BGM_TYPE.countdown10):
            source = discord.FFmpegPCMAudio(Config.BGM_PATH + "countdown10.wav")
        elif(bgmType == BGM_TYPE.SUCCESS):
            source = discord.FFmpegPCMAudio(Config.BGM_PATH + "SUCCESS.mp3")
        elif(bgmType == BGM_TYPE.BELL):
            source = discord.FFmpegPCMAudio(Config.BGM_PATH + "bell.mp3")
        elif(bgmType == BGM_TYPE.LONGTIMER):
            tmpList = os.listdir(Config.BGM_PATH+"/longTimer/")
            rd = random.randint(0, len(tmpList) - 1)  # 0부터 tmpList 크기 -1 만큼
            rdBgm = tmpList[rd]  # 무작위 1개 선택
            bgmName = Config.BGM_PATH+"/longTimer/"+rdBgm
            source = discord.FFmpegPCMAudio(bgmName)

        voice.play(source)
    except:
        Config.LOGGER.error("error01 - voice is not connect error")
        Config.LOGGER.error(traceback.format_exc())


def getQuizTypeFromIcon(icon): #아이콘으로 퀴즈 타입 추측
    if icon == Config.EMOJI_ICON.ICON_TYPE_SONG:
        return GAME_TYPE.SONG
    elif icon == Config.EMOJI_ICON.ICON_TYPE_PICTURE:
        return GAME_TYPE.PICTURE
    elif icon == Config.EMOJI_ICON.ICON_TYPE_PICTURE_LONG:
        return GAME_TYPE.PICTURE_LONG
    elif icon == Config.EMOJI_ICON.ICON_TYPE_OX:
        return GAME_TYPE.OX
    elif icon == Config.EMOJI_ICON.ICON_TYPE_INTRO:
        return GAME_TYPE.INTRO
    elif icon == Config.EMOJI_ICON.ICON_TYPE_QNA:
        return GAME_TYPE.QNA
    elif icon == Config.EMOJI_ICON.ICON_TYPE_SCRIPT:
        return GAME_TYPE.SCRIPT
    elif icon == Config.EMOJI_ICON.ICON_TYPE_SELECT:
        return GAME_TYPE.SELECT
    elif icon == Config.EMOJI_ICON.ICON_TYPE_MULTIPLAY:
        return GAME_TYPE.MULTIPLAY

    return GAME_TYPE.SONG #디폴트


async def startQuiz(quizInfoFrame, owner, forceStart=False): #퀴즈 시작

    message = quizInfoFrame._myMessage
    chattingChannel = quizInfoFrame._myMessage.channel  # 퀴즈할 채팅 채널 얻기
    guild = message.guild
    guildData = getGuildData(guild)
    voiceChannel = None

    if not forceStart: #강제 시작 아니면 적법한 절차 거침
        if owner.voice == None:
            quizInfoFrame._notice_visible = True
            quizInfoFrame._notice_text = Config.EMOJI_ICON.ICON_WARN + " 먼저 음성 채널에 참가해주세요."
            quizInfoFrame._started = False
            await ui.update(message)
            return

        voiceChannel = owner.voice.channel  # 호출자의 음성 채널 얻기

        # bot의 해당 길드에서의 음성 대화용 객체
        voice = get(bot.voice_clients, guild=guild)
        if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
            quizInfoFrame._notice_visible = True
            quizInfoFrame._notice_text = Config.EMOJI_ICON.ICON_WARN + "현재 진행중인 퀴즈를 중지해주세요.\n　 "+Config.EMOJI_ICON.ICON_STOP+" 버튼 클릭 또는 !중지"
            await ui.update(message)
            return
    else: #강제 시작이면
        voiceChannel = owner.voice.channel  # 호출자의 음성 채널 얻기


    if guildData._gameData != None: #이미 진행중인 퀴즈 중지
        await guildData._gameData.stop() #중지

    if voiceChannel == None:
        quizInfoFrame._notice_text = Config.EMOJI_ICON.ICON_WARN + " 음성 채널을 찾을 수 없음, 다시 시도해보세요."

    if guild.id in newGuilds:
        newGuilds.remove(guild.id)

    isSuccess = False
    #퀴즈 시작
    voice = get(bot.voice_clients, guild=guild)
    if voice == None or not voice.is_connected():  # 음성 연결 안됐다면
        try:
            voice = await voiceChannel.connect()  # 음성 채널 연결후 해당 객체 반환
            isSuccess = True
        except: #보통 Already voice connected 문제 발생시
            isSuccess = False
            Config.LOGGER.error(traceback.format_exc())
            asyncio.ensure_future(chattingChannel.send("❗ 예기치 못한 문제가 발생하였습니다. 재시도해주세요. \n해당 문제가 지속적으로 발생할 시 \n💌 [ "+Config.EMAIL_ADDRESS+" ] 으로 문의바랍니다.\n"))
            if voice == None:
                asyncio.ensure_future(chattingChannel.send("voice == None"))
            elif voice.is_connected():
                asyncio.ensure_future(chattingChannel.send("voice is connected"))
            #await voice.move_to(voiceChannel)
            await asyncio.sleep(1)
            print("error disconnect")
            await voice.disconnect() #보이스 강제로 연결끊기

    if not isSuccess and not forceStart:
        tmpVoice = get(bot.voice_clients, channel=voiceChannel)
        print("error disconnect2")
        await tmpVoice.disconnect()

    quizInfoFrame._started = False

    playBGM(voice, BGM_TYPE.BELL)

    # 해당 채팅 채널에 선택한 퀴즈에 대한 퀴즈 진행용 UI 생성
    quizUiFrame = await ui.createQuizUI(chattingChannel, quizInfoFrame._quizPath, owner)
    quizUiFrame._option = quizInfoFrame._option #옵션값
    option = quizUiFrame._option #옵션값
    quizUiFrame._quizOwner = owner #주최자 설정
    quizUiFrame._customFooter_visible = True
    quizUiFrame._customFooter_text = Config.EMOJI_ICON.ICON_WARN + "　퀴즈 진행을 위해 해당 채팅 채널의 최근 메시지를 삭제합니다. \n"+Config.EMOJI_ICON.ICON_POINT+"　잠시만 기다려주세요."
    #playBGM(voice, BGM_TYPE.PLING)
    await quizUiFrame.update()

    quizPath = quizInfoFrame._quizPath
    gameIcon = quizUiFrame._quizIcon  # 퀴즈 아이콘 가져오기
    gameType = getQuizTypeFromIcon(gameIcon)  # 아이콘으로 퀴즈 타입 추측
    gameName = quizUiFrame._quizName  # 퀴즈 이름

    #옵션 설정
    trimLength = option._trimLength #노래 길이
    repeatCnt = option._repeatCount  # 반복 횟수 가져오기
    topNickname = quizUiFrame._quizTopNickname  # 1등 별명 가져오기

    gameData = None
    if gameType == GAME_TYPE.PICTURE: #사진 퀴즈면
        gameData = PictureQuiz(quizPath, quizUiFrame, voice, owner)  # 퀴즈데이터 생성
    elif gameType == GAME_TYPE.PICTURE_LONG: #타이머 긴 사진 퀴즈면
        gameData = PictureQuiz(quizPath, quizUiFrame, voice, owner)  # 퀴즈데이터 생성
        gameData._isLongCount = True #롱 타이머 활성화
    elif gameType == GAME_TYPE.OX: #ox 퀴즈면
        gameData = OXQuiz(quizPath, quizUiFrame, voice, owner)  # 퀴즈데이터 생성
    elif gameType == GAME_TYPE.INTRO: #인트로 퀴즈면
        gameData = IntroQuiz(quizPath, quizUiFrame, voice, owner)  # 퀴즈데이터 생성
    elif gameType == GAME_TYPE.QNA: #텍스트 퀴즈면
        gameData = TextQuiz(quizPath, quizUiFrame, voice, owner)  # 퀴즈데이터 생성
    elif gameType == GAME_TYPE.MULTIPLAY: #멀티플레이 퀴즈면
        targetGuild = quizInfoFrame._target._guild
        pathList = quizInfoFrame._pathList
        gameData = MultiplayQuiz(quizPath, quizUiFrame, voice, owner, targetGuild, pathList)  # 퀴즈데이터 생성
    else: #그 외에는 기본
        gameData = SongQuiz(quizPath, quizUiFrame, voice, owner)  # 퀴즈데이터 생성

    gameData._gameType = gameType
    gameData._gameName = gameName

    gameData._trimLength = trimLength
    gameData._repeatCount = repeatCnt #옵션 세팅

    gameData._topNickname = topNickname

    quizUiFrame.setFunction(gameData.requestHint, gameData.skip, gameData.stop)

    guildData._gameData = gameData  # 해당 서버의 퀴즈데이터 저장

    asyncio.ensure_future(ui.returnToTitle(guild)) #퀴즈 선택 ui 메인화면으로

    await asyncio.sleep(1)
    await gameData.start()


async def test(ctx): #비동기 함수 한번에 여러개 실행방법

    async def startCor(ctx):
        await asyncio.wait([
            test2(ctx),
            test3(ctx)
        ])

    asyncio.run(await startCor(ctx))

async def test2(ctx):
    while True:
        Config.LOGGER.debug("텟1")
        await asyncio.sleep(1)

async def test3(ctx):
    while True:
        Config.LOGGER.debug("텟2")
        await asyncio.sleep(1)

async def test4(ctx): #비동기 함수 실행하고 잊기 fire and forget
    asyncio.ensure_future(test2(ctx))  # fire and forget async_foo()
    asyncio.ensure_future(test3(ctx))  # fire and forget async_foo()

async def helpMessage(ctx): #도움말
    sendStr = Config.EMOJI_ICON.ICON_TIP + "[ 도움말 ]\n" + chr(173) + "\n"
    sendStr += Config.EMOJI_ICON.ICON_BOOK_RED + " !퀴즈 - 퀴즈 선택창을 생성합니다.　, (!ㅋㅈ, !quiz, !QUIZ 도 가능)\n"
    sendStr += Config.EMOJI_ICON.ICON_BOOK_RED + " !중지 - 퀴즈를 강제로 중지합니다.\n"
    sendStr += Config.EMOJI_ICON.ICON_BOOK_RED + " !현황 - 퀴즈별 진행중인 서버수를 확인합니다.\n"
    sendStr += Config.EMOJI_ICON.ICON_BOOK_RED + " !챗 <메세지> - 멀티플레이 퀴즈에서 상대방에게 메세지를 전송합니다.\n"
    sendStr += Config.EMOJI_ICON.ICON_BOOK_RED + " !보이스동기화 - 멀티플레이 퀴즈에서 보이스 동기화를 ON/OFF 합니다.\n"

    sendStr += chr(173) + "\n"

    sendStr += "봇 이름:　" + "퀴즈봇2\n"
    sendStr += "봇 버전:　" + Config.VERSION + "\n"
    sendStr += "제작 　:　제육보끔#1916\n"
    sendStr += "패치일 :　" + Config.LAST_PATCH + "\n"

    sendStr += chr(173) + "\n"

    sendStr += Config.EMOJI_ICON.ICON_PHONE + " Contact\n" +chr(173) + "\n"
    sendStr += Config.EMOJI_ICON.ICON_MAIL + " 이메일:　" + Config.EMAIL_ADDRESS + "\n"
    sendStr += Config.EMOJI_ICON.ICON_QUIZBOT + " 봇 공유링크:　"+Config.BOT_LINK + "\n"
    sendStr += Config.EMOJI_ICON.ICON_GIT + " 깃허브　 　:　"+"https://github.com/OtterBK/Quizbot" + "\n"
    sendStr += chr(173) + "\n" + Config.EMOJI_ICON.ICON_FIX + "버그 제보, 개선점, 건의사항이 있다면 상단 이메일 주소로 알려주세요!\n" + chr(173) + "\n"

    asyncio.ensure_future(ctx.send("```" + chr(173) +"\n" + str(sendStr) + "\n```"))


async def showNotice(channel, noticeIndex=1): #공지 표시, noticeIndex 는 공지사항 번호
    if channel == None: return
    notice = ""

    try:
        f = open(Config.DATA_PATH+"notice"+str(noticeIndex)+".txt", 'r', encoding="utf-8" ) #공지
        while True:
            line = f.readline()
            if not line:
                break

            notice += line
        f.close()
    except:
        Config.LOGGER.error("공지사항 로드 에러")

    if notice != "":#공지가 있다면
        asyncio.ensure_future(channel.send("```"+ chr(173) + "\n" +str(notice) +"\n"+ chr(173) + "\n"+"```"))




# 봇이 접속(활성화)하면 아래의 함수를 실행하게 된다, 이벤트
@bot.event
async def on_ready():
    Config.LOGGER.info(f'{bot.user} 활성화됨')
    await bot.change_presence(status=discord.Status.online) #온라인
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!퀴즈 | !quiz"))

    print("봇 이름:" + str(bot.user.name) + ", 봇 아이디:" + str(bot.user.name) + ", 봇 버전:" + discord.__version__)
    for guild in bot.guilds:
        print(guild.name)
    Config.LOGGER.info(str(len(bot.guilds)) + "개의 서버 연결됨")


@bot.command(pass_context=False, aliases=["ping"])  # ping 명령어 입력시
async def pingCommand(ctx):  # ping 테스트
    asyncio.ensure_future(ctx.send(f"핑 : {round(bot.latency * 1000)}ms"))


@bot.command(pass_context=False, aliases=["도움", "도움말","명령어", "commands"])  # ping 명령어 입력시
async def helpCommand(ctx):  # 도움말
    asyncio.ensure_future(helpMessage(ctx))


@bot.command(pass_context=False, aliases=["hellothisisverification"])  # ping 명령어 입력시
async def checkAuthurCommand(ctx):  # 제작자 표시
    await ctx.send("제육보끔#1916")


@bot.command(pass_context=False, aliases=["중지"])  # 중지 명령어 입력시
async def stopCommand(ctx):  # ping 테스트
    guildData = getGuildData(ctx.guild) #길드 데이터 없으면 초기화
    if guildData._gameData != None:
        gameData = guildData._gameData
        if gameData._owner == ctx.message.author: #주최자라면
            await gameData.stop()
        else:
            asyncio.ensure_future(ctx.message.channel.send("```" + "퀴즈 중지는 주최자만이 가능합니다.\n음성 채널 관리 권한이 있다면 [ 봇 우클릭 -> 연결 끊기 ] 를 눌러도 종료가 가능합니다." + "```"))
    else:
        voice = get(bot.voice_clients, guild=ctx.guild)
        if voice and voice.is_connected():  # 음성대화 연결된 상태면
            await voice.disconnect() #끊기

@bot.command(pass_context=False, aliases=["현황"])  # 중지 명령어 입력시
async def quizStatusCommand(ctx):  # 퀴즈현황
    localCnt = 0
    multiCnt = 0
    for guildData in dataMap.values():
        if guildData._gameData != None:
            if guildData._gameData._gameType == GAME_TYPE.MULTIPLAY:
                multiCnt += 1
            else:
                localCnt += 1

    matchingCnt = 0
    for matchingQueue in ui.matchingCategory.values():
        matchingCnt += len(matchingQueue)

    asyncio.ensure_future(ctx.send("```" + chr(173) +"\n"+ str(len(bot.guilds)) +"개의 서버 중\n로컬 플레이: "+ str(localCnt) + "\n" + "멀티플레이: " + str(multiCnt) + "\n" + "매칭 중: " + str(matchingCnt) + "\n플레이하고 있습니다.\n" + chr(173) +"```"))

@bot.command(pass_context=False, aliases=["챗"])  # 중지 명령어 입력시
async def multiplayChatCommand(ctx, *args):  # 멀티플레이 채팅
    chat = ""
    for tmpStr in args:
        chat += tmpStr + " "
    if chat != "":
        message = ctx.message
        guldData = getGuildData(message.guild)
        gameData = guldData._gameData  # 데이터 맵에서 해당 길드의 게임 데이터 가져오기
        if(gameData == None):  # 게임데이터가 없으면 return
            return
        if gameData._gameType == GAME_TYPE.MULTIPLAY: #멀티 플레이 게임중이면
            asyncio.ensure_future(message.delete())
            asyncio.ensure_future(gameData.sendMultiplayMessage(ctx.message.author, chat))
        elif(gameData._gameStep == GAME_STEP.START or gameData._gameStep == GAME_STEP.END):  # 룰 설명중, 엔딩중이면
            asyncio.ensure_future(message.delete())


@bot.command(pass_context=False, aliases=["보이스동기화"])  # 보이스동기화 명령어 입력시
async def multiplayVoiceSyncCommand(ctx):  # 멀티플레이 채팅

    message = ctx.message
    guldData = getGuildData(message.guild)
    gameData = guldData._gameData  # 데이터 맵에서 해당 길드의 게임 데이터 가져오기
    if(gameData == None):  # 게임데이터가 없으면 return
        return
    if(gameData._gameStep == GAME_STEP.START or gameData._gameStep == GAME_STEP.END):  # 룰 설명중, 엔딩중이면
        asyncio.ensure_future(message.delete())
    if gameData._gameType == GAME_TYPE.MULTIPLAY: #멀티 플레이 게임중이면
        await gameData.toggleVoiceSync()

@bot.command(pass_context=False, aliases=["힌트", "hint", "HINT"])  # 수동 힌트 명령어 입력시
async def hintCommand(ctx):  # 수동 힌트
    guildData = getGuildData(ctx.guild) #길드 데이터 없으면 초기화
    if guildData._gameData != None:
        gameData = guildData._gameData
        await gameData._quizUIFrame.hintAction(ctx.message.author, ctx.message)

@bot.command(pass_context=False, aliases=["스킵", "skip", "SKIP"])  # 수동  스킵 명령어 입력시
async def skipCommand(ctx):  # 수동 힌트
    guildData = getGuildData(ctx.guild) #길드 데이터 없으면 초기화
    if guildData._gameData != None:
        gameData = guildData._gameData
        await gameData._quizUIFrame.skipAction(ctx.message.author, ctx.message)


@bot.command(pass_context=False, aliases=["quiz", "QUIZ", "퀴즈", "ㅋㅈ"])  # quiz 명령어 입력시
async def quizCommand(ctx, gamesrc=None):  # 퀴즈봇 UI 생성
    if gamesrc == None:
        guild = ctx.guild #서버
        guildData = getGuildData(guild) #길드 데이터 없으면 초기화

        try:
            asyncio.ensure_future(showNotice(ctx.message.channel))
        except:
            pass

        if guildData._gameData == None:
            voice = get(bot.voice_clients, guild=ctx.guild)
            if voice and voice.is_connected():  # 음성대화 연결된 상태면
                await voice.disconnect() #끊기

        await ui.createSelectorUI(ctx.channel) #UI 재설정
        guildData._selectorChannelID = ctx.channel.id #버튼 상호작용 채널 설정

        if guild.id in newGuilds:

            await ctx.send("> 🛑 어라? 퀴즈봇을 추가하고 **새로운 채널**을 생성하지 않으신 것 같은데 괜찮으세요?\n> ❗ 퀴즈가 진행되는 채널은 **채팅 청소**를 진행하여 ***모든 메시지가 사라집니다!***\n "+
                           "> 😃 퀴즈봇 전용 채팅 채널을 생성 후 진행하는 것을 추천드려요!\n" + chr(173) + "\n" + "> 📔 이 메세지는 퀴즈를 한 번이라도 시작하면 더 이상 표시되지 않습니다.\n")


@bot.event
async def on_guild_join(guild): #서버 참가시
    newGuilds.append(guild.id)


@bot.event
async def on_guild_channel_create(channel): #채팅 채널 생성시
    guild = channel.guild

    if guild.id in newGuilds:
        newGuilds.remove(guild.id)

@bot.event
async def on_message(message):
    # 봇이 입력한 메시지라면 무시하고 넘어간다.
    if message.author == bot.user:
        return
    elif message.content.startswith(Config.BOT_PREFIX):  # 명령어면 return
        await bot.process_commands(message)
        return
    elif message.guild not in dataMap:  # 게임 데이터 없으면 건너뛰기
        return
    else:
        guldData = getGuildData(message.guild)
        gameData = guldData._gameData  # 데이터 맵에서 해당 길드의 게임 데이터 가져오기
        if(gameData == None):  # 게임데이터가 없으면 return
            return
        if message.channel != gameData._chatChannel: #채팅 채널이 게임데이터에 저장된 채팅채널과 일치하지 않으면
            return
        if(gameData._gameStep == GAME_STEP.START or gameData._gameStep == GAME_STEP.END):  # 룰 설명중, 엔딩중이면
            asyncio.ensure_future(message.delete())
            #await message.delete()
            return
        if(gameData._gameStep != GAME_STEP.WAIT_FOR_ANSWER): #정답 대기중 아니면 return
            return

        asyncio.ensure_future(gameData.on_message(message)) #메세지 이벤트 동작


@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:  # 봇이 입력한거면
        return  # 건너뛰어

    guild = reaction.message.guild # 반응한 서버
    channel = reaction.message.channel  # 반응 추가한 채널
    message = reaction.message
    guildData = getGuildData(reaction.message.guild)
    gameData = guildData._gameData

    # if message.author != None and message.author != bot.user: #봇이 보낸 메시지가 아니면
    #     return

    isAlreadyRemove = False
    if channel.id == guildData._selectorChannelID: #반응한 서버가 퀴즈선택 메시지 있는 서버라면
        if not isAlreadyRemove:
            try:
                isAlreadyRemove = True
                asyncio.ensure_future(reaction.remove(user))  # 이모지 삭제, 버튼 반응 속도 개선
            except:
                asyncio.ensure_future(hannel.send("```" + chr(173) + "\n" + Config.EMOJI_ICON.ICON_WARN + " 권한이 부족합니다.\n퀴즈봇 사용을 위해서는 관리자 권한이 필요합니다.\n관리자 권한을 가진 유저에게 퀴즈봇을 추가해달라고 요청하세요.\n" + chr(173) + "```" ))
                asyncio.ensure_future(channel.send(Config.BOT_LINK))
                Config.LOGGER.error(traceback.format_exc())
                return
        asyncio.ensure_future(ui.on_reaction_add(reaction, user)) #이벤트 동작

    if gameData != None and guild.id == guildData._guildID:  # 현재 게임중인 서버라면
        if channel.name == gameData._chatChannel.name:
            if not isAlreadyRemove:
                try:
                    isAlreadyRemove = True
                    asyncio.ensure_future(reaction.remove(user))  # 이모지 삭제, 버튼 반응 속도 개선
                except:
                    await channel.send("```" + chr(173) + "\n" + Config.EMOJI_ICON.ICON_WARN + " 권한이 부족합니다.\n퀴즈봇 사용을 위해서는 관리자 권한이 필요합니다.\n관리자 권한을 가진 유저에게 퀴즈봇을 추가해달라고 요청하세요.\n" + chr(173) + "```" )
                    await channel.send(Config.BOT_LINK)
                    Config.LOGGER.error(traceback.format_exc())
                    return
            asyncio.ensure_future(gameData.action(reaction, user) )#이벤트 동작




# @bot.event #봇이 삭제하는 것도 막기 때문에 못씀
# async def on_reaction_clear_emoji(reaction):
#     channel = reaction.message.channel  # 반응 삭제한 채널
#     emoji = reaction.emoji
#     guildData = getGuildData(reaction.message.guild)

#     if channel.id == guildData._selectorChannelID: #반응한 채널이 퀴즈선택 메시지 있는 채널이라면
#         await reaction.message.add_reaction(emoji=emoji) #다시 추가


@bot.event
async def on_reaction_remove(reaction, user):
    if user == bot.user: #봇이 삭제한거면
        return #건너뛰어

    channel = reaction.message.channel  # 반응 삭제한 채널
    message = reaction.message
    emoji = reaction.emoji
    guildData = getGuildData(reaction.message.guild)

    # if message.author != None and message.author != bot.user: #봇이 보낸 메시지가 아니면
    #     return

    if channel.id == guildData._selectorChannelID: #반응한 채널이 퀴즈선택 메시지 있는 채널이라면
        asyncio.ensure_future(reaction.message.add_reaction(emoji=emoji)) #다시 추가, 버튼 반응 속도 개선


#커맨드 에러 핸들링
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        return
    raise error


#################################

ui.initializing(bot, startQuiz) #QuizSelector 초기화
#한국 봇 서버 업데이트
if Config.KOREA_BOT_TOKEN != "":
    koreaBot = koreanbots.Client(bot, Config.KOREA_BOT_TOKEN)
else:
    Config.LOGGER.warning("한국 봇 서버 토큰 누락")

if Config.TOKEN != "":
    bot.run(Config.TOKEN)  # 봇 실행
else:
    Config.LOGGER.critical("디스코드 봇 토큰 누락")

