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


    def init(self):
        self._gameStep = GAME_STEP.START #게임 진행상태
        self._roundIndex = 0 #퀴즈 라운드
        self._answerList = [] #정답 인정 목록
        self._quizList = [] #퀴즈 목록
        self._scoreMap = dict() #점수판
        self._isSkiped = False #스킵 여부
        self._useHint = False #힌트 사용여부

    async def gameRule(self): #각 퀴즈별 설명

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
            quizUIFrame._sub_text += Config.getEmojiFromNumber(3) + "　대소문자는 구분할 필요 없습니다..\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(4) + "　줄임말도 정답으로 인정되긴 하나 정확하지 않습니다.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(5) + "　정답이 영어인 경우에는 발음을 제출해도 정답 인정이 되긴합니다.\n"
            quizUIFrame._sub_text += Config.getEmojiFromNumber(6) + "　여러 시리즈가 있는 경우에는 시리즈명을 포함해야 정답으로 인정됩니다.\n"

        playBGM(voice, BGM_TYPE.PLING)
        await quizUIFrame.update()

        await asyncio.sleep(6)  # 6초 대기
        quizUIFrame._sub_text += chr(173)+"\n" + chr(173)+"\n" + chr(173)+"\n"
        quizUIFrame._sub_text += Config.EMOJI_ICON.ICON_TIP + "**　[　"+ Config.EMOJI_ICON.ICON_ALARM +"주의　]**\n"
        quizUIFrame._sub_text += "노래 음량이 일정하지 않습니다. \n봇의 음량를 조금 더 크게 설정해주세요.　"+  Config.EMOJI_ICON.ICON_SPEAKER_LOW + "　->　" +  Config.EMOJI_ICON.ICON_SPEAKER_HIGH +"\n"
        playBGM(voice, BGM_TYPE.PLING)
        await quizUIFrame.update()

        await asyncio.sleep(6)  # 6초 대기
        quizUIFrame._sub_text += chr(173)+"\n" + chr(173)+"\n" + chr(173)+"\n"
        quizUIFrame._sub_text += Config.EMOJI_ICON.ICON_SOON + " *이제 퀴즈를 시작합니다!*\n"
        playBGM(voice, BGM_TYPE.PLING)
        await quizUIFrame.update()
        await asyncio.sleep(3)  # 6초 대기

    def loadQuiz(self): #문제 로드
        tmpList = os.listdir(self._gamePath)            # 퀴즈 폴더 내 모든 파일 불러오기
        quizList = []  # 빈 리스트 선언

        while len(tmpList) > 0:  # 모든 파일에 대해
            rd = random.randrange(0, len(tmpList))  # 0부터 tmpList 크기 -1 만큼
            quiz = tmpList[rd]  # 무작위 1개 선택
            if(os.path.isdir(self._gamePath + quiz)):  # 폴더인지 확인(폴더만 추출할거임)
                quizList.append(quiz)  # 퀴즈 목록에 추가
            del tmpList[rd]  # 검사한 항목은 삭제

        self._quizList = quizList

        self._maxRound = len(quizList)  # 문제 총 개수
        self._quizUIFrame._quizCnt = self._maxRound #퀴즈UI 총 문제 개수 갱신
        self._roundIndex = 0  # 현재 라운드

    async def prepare(self): #시작전 전처리
        print(self._guild.name+" 에서 " + self._gameName + " 퀴즈 시작")

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

        await ui.clearChat(uiMessage.channel) #채팅 청소
        gameData._roundIndex += 1 #라운드 +1
        quizUIFrame._quizRound = gameData._roundIndex #퀴즈UI 라운드 갱신
        if gameData._roundIndex > gameData._maxRound:  # 더이상문제가없다면
            await self.finishGame()  # 게임 끝내기
            return False

        voice = get(bot.voice_clients, guild=uiMessage.guild)  # 봇의 음성 객체 얻기
        
        for player in self.sortScore(): #점수판 추가
            playerName = player.display_name
            quizUIFrame.addField(playerName,"[ " + str(gameData._scoreMap[player]) + "p" +" ]")


        quizUIFrame._title_visible = True
        quizUIFrame._title_text = chr(173)+"[　　　　"+ quizUIFrame._quizIcon + " " + quizUIFrame._quizName + "　　　　]"

        quizUIFrame._sub_visible = True
        quizUIFrame._sub_text = Config.EMOJI_ICON.ICON_BOX+"　**"+str(gameData._roundIndex) +"번째 문제입니다.**"

        quizUIFrame._main_visible = False
        quizUIFrame._notice_visible = False

        quizUIFrame._field_visible = False

        quizUIFrame._customText_visible = False
        quizUIFrame._page_visible = False
        quizUIFrame._path_visible = False

        quizUIFrame._customFooter_text = ""

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

    def getAudio(self): #노래 파일 가져오기
        gameData = self
        guild = self._guild
        quizPath = self._gamePath + self._nowQuiz + "/"

        for file in os.listdir(quizPath):  # 다운로드 경로 참조, 해당 디렉토리 모든 파일에 대해
            if file.endswith(".png") or file.endswith("jpg"): #사진파일이라면 ,썸네일임
                gameData._thumbnail = quizPath + "/" + file
            elif file.endswith(".wav") or file.endswith(".mp3"):  # 파일 확장자가 .wav 또는 .mp3면, 문제 파일일거임
                question = file  # 기존 파일명
                print(f"guild: {guild.name}, gameName: {gameData._gameName}, questionFile: {question}\n") #정답 표시
                audioName = quizPath + "/" + question #실제 실행할 음악파일 경로
                audioLength = 39 #오디오 길이
                
                if file.endswith(".wav"): #확장자 wav 일때
                    f = sf.SoundFile(audioName) #오디오 파일 로드
                    audioLength = len(f) / f.samplerate #오디오 길이
                    f.close()
                elif file.endswith(".mp3"): #확장자 mp3일때
                    audio = MP3(audioName) 
                    audio_info = audio.info
                    length_in_secs = int(audio_info.length) #음악 총 길이
                    if length_in_secs > gameData._trimLength + 1: #음악이 자를 시간 초과할 시, 자르기 시작
                        song = AudioSegment.from_mp3( audioName ) #오디오 자르기 가져오기
                        if length_in_secs > gameData._trimLength + 20: #노래 길이가 자를 시간 + 20만큼 크면
                            #최적의 자르기 실행
                            startTime = random.randrange(10, (length_in_secs - gameData._trimLength - 10)) #자르기 시작 시간 10초 ~ 총길이 - 자를 길이 - 10
                            endTime = startTime + gameData._trimLength #지정된 길이만큼 자르기
                        else:
                            startTime = random.randrange(0, length_in_secs - gameData._trimLength)
                        startTime *= 1000 #s 를 ms로
                        endTime *= 1000 #s를 ms로

                        extract = song[startTime:endTime] #노래 자르기
                        audioName = Config.TMP_PATH + "/" + str(guild.id) + ".mp3" #실제 실행할 음악파일 임시파일로 변경 

                        extract.export(audioName) #임시 저장
                        audioLength = gameData._trimLength
                    else:
                        audioLength = length_in_secs

                return audioName, audioLength

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
            

        while repartCnt > 0: #반복횟수만큼 반복
            repartCnt -= 1
            

            voice.play(discord.FFmpegPCMAudio(audioName))  # 노래 재생
            await fadeIn(voice) #페이드인
            playTime = 2 #페이드인으로 2초 소비

            while voice.is_playing():  # 재생중이면
                if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                    return #리턴
                await asyncio.sleep(0.72)  # 0.72초후 다시 확인 0.28초는 딜레이있어서 뺌
                playTime += 1 #재생 1초 +
                leftTime = audioLength  - playTime #남은 길이
                quizUIFrame._quizLeftTime = leftTime
                
                if hintType == 2: #힌트 타입이 자동일 떄
                    if playTime > audioLength // 2: #절반 이상 재생됐다면
                        self.requestHint() #힌트 요청


                await quizUIFrame.update()

                if leftTime < 0:
                    leftTime = 0
                    print("fast end")
                    voice.stop()
                    break # 재생시간 초과면 break

    async def showAnswer(self, isWrong=False): #정답 공개, isWrong 은 오답여부
        gameData = self
        quizUIFrame = gameData._quizUIFrame
        voice = self._voice
        channel = self._chatChannel
        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT # 다음 라운드 대기로 변경

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
            answerFrame._title_text = chr(173)+"[　　　　"+ Config.getRandomWrongIcon() +" 정답 공개　　　　]"
            answerFrame._embedColor = discord.Color.red()
        else:
            answerFrame._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_COLLECT +" 정답!　　　　]"
            answerFrame._embedColor = discord.Color.green()

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
            quizUIFrame.addField(playerName,"[ " + str(gameData._scoreMap[player]) + "p" +" ]")

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
        
        await asyncio.sleep(4)

    async def nextRound(self):
        gameData = self

        ###### 라운드 표시
        isContinue = await self.noticeRound()
        if not isContinue: #퀴즈 속행 아니면 return
            return
        roundChecker = gameData._roundIndex  # 현재 라운드 저장

        await asyncio.sleep(2)
        ###### 정답 설정
        if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
            return
        self.parseAnswer()

        ###### 라운드 초기화
        
        gameData._isSkiped = False
        gameData._useHint = False
        gameData._thumbnail = None # 썸네일 초기화
        self._quizUIFrame.initRound(self._voice.channel)


        ###### 문제 출제
        if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
            return
        await self.question()
                                        
        ###### 정답 공개
        if self.checkStop(): return
        if roundChecker != gameData._roundIndex:  # 이미 다음 라운드라면 리턴
            return
        if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER:  # 아직도 정답자 없다면
            await self.showAnswer(isWrong=True) #정답 공개
            await self.nextRound() #다음 라운드 진행 


    def addScore(self, user): #1점 추가
        gameData = self
        if user in gameData._scoreMap:  # 점수 리스트에 정답자 있는지 확인
            gameData._scoreMap[user] += 1  # 있으면 1점 추가
        else:
            gameData._scoreMap[user] = 1  # 없으면 새로 1점 추가


    def checkStop(self): #퀴즈 중지 확인
        if self._voice == None or not self._voice.is_connected():  # 봇 음성 객체가 없다면 퀴즈 종료
            guild = self._guild
            if guild in dataMap:
                dataMap[guild]._gameData = None #퀴즈 데이터 삭제
            ui.removeQuizUI(guild) #ui 데이터 삭제
            return True

        return False


    async def start(self):
        self.init() #초기화
        self.loadQuiz() #문제들 로드
        await self.prepare() #전처리
        await self.nextRound() #다음 라운드 진행


    async def performance(self, user): #정답 맞췄을 때 효과
        roundChecker = self._roundIndex  # 현재 라운드 저장

        quizUIFrame = self._quizUIFrame
        quizUIFrame._title_visible = True
        quizUIFrame._title_text = chr(173)+"[　　　　"+ quizUIFrame._quizIcon + " " + quizUIFrame._quizName + "　　　　]"

        quizUIFrame._sub_visible = True
        quizUIFrame._sub_text = Config.getRandomHumanIcon()+" 정답자　**"+ chr(173) + "　"+str(user.display_name) +"**"

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
        waitCount = 9 #9초 대기할거임

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
        await asyncio.sleep(4)

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
        playBGM(voice, BGM_TYPE.ENDING)
        await quizUIFrame.update()
        await asyncio.sleep(2)
        await voice.disconnect()
        self.checkStop() #데이터 삭제

    async def requestHint(self): #힌트 사용
        
        gameData = self #게임 데이터 불러올거임

        if gameData._gameStep != GAME_STEP.WAIT_FOR_ANSWER and gameData._gameStep != GAME_STEP.WAIT_FOR_NEXT: #정답자 대기중이거나 다음라 대기중이 아니면
            return
        if gameData._useHint == True: #이미 힌트 썻다면
            return
        if gameData._gameType == GAME_TYPE.OX: #OX퀴즈는 힌트 불가능
            gameData._useHint = True #힌트 사용으로 변경
            await gameData._chatChannel.send("``` "+chr(173)+"\n해당 퀴즈는 힌트를 제공하지 않습니다.\n"+chr(173)+" ```")
            return

        #힌트 표시
        gameData._useHint = True #힌트 사용으로 변경
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

            rd = random.randrange(0, answerLen)
            if rd in hintIndex or rd == " ": #이미 인덱스에 있거나 공백이라면
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

        await gameData._chatChannel.send("``` "+chr(173)+"\n""요청에 의해 힌트가 제공됩니다.\n"+chr(173)+"\n"+Config.EMOJI_ICON.ICON_HINT+"글자 힌트\n"+str(hintStr)+"\n"+chr(173)+"```")


    async def skip(self): #스킵 사용
        gameData = self

        if gameData._gameStep != GAME_STEP.WAIT_FOR_ANSWER and gameData._gameStep != GAME_STEP.WAIT_FOR_NEXT: #정답자 대기중이거나 다음라 대기중이 아니면
            return
        if gameData._isSkiped: #이미 스킵중이면
            return

        if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER: #정답 못 맞추고 스킵이면
            gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT  # 다음 라운드 대기로 변경
            gameData._isSkiped = True #스킵중 표시

            await gameData._chatChannel.send("``` "+chr(173)+"\n요청에 의해 문제를 건너뜁니다.\n"+chr(173)+" ```")

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
                if roundChecker == gameData._roundIndex: 
                    await self.nextRound() #다음 라운드 진행 
        

    async def stop(self): #퀴즈 중지
        await self._voice.disconnect()

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

        await self._chatChannel.send("``` "+chr(173)+"\n주최자가 퀴즈 진행을 중지하였습니다.\n"+chr(173)+" ```")

        await quizUIFrame.update()

        self.checkStop()
        

    ##이벤트
    async def action(self, reaction, user): 
        emoji = reaction.emoji
        message = reaction.message
        guild = message.guild

    async def on_message(self, message):
        gameData = self
        inputAnswer = message.content.replace(" ", "").upper() #공백 제거 및 대문자로 변경
        author = message.author
        
        isAnswer = False
        for answer in gameData._answerList: #정답 목록과 비교 
            answer = answer.replace(" ", "").upper() # 공백 제거 및 대문자로 변경
            if answer == inputAnswer:  # 정답과 입력값 비교 후 일치한다면
                isAnswer = True
                break

        if isAnswer: #정답 맞췄다면
            gameData._gameStep = GAME_STEP.WAIT_FOR_NEXT  # 다음 라운드 대기로 변경
            roundChecker = gameData._roundIndex  # 정답 맞춘 라운드 저장

            self.addScore(author)  # 메세지 보낸사람 1점 획득

            if self.checkStop(): return
            await self.showAnswer() #정답 공개

            if self.checkStop(): return
            await self.performance(author) #정답 맞췄을 때 효과

            if self.checkStop(): return
            if(roundChecker == gameData._roundIndex):  # 정답 맞춘 라운드와 현재 라운드 일치시
                await self.nextRound() #다음 라운드로 진행
                


class SongQuiz(Quiz): #노래 퀴즈

    def __init__(self, quizPath, quizUIFrame, voice, owner):
        super().__init__(quizPath, quizUIFrame, voice, owner) #

class PictureQuiz(Quiz): #그림 퀴즈

    def __init__(self, quizPath, quizUIFrame, voice, owner):
        super().__init__(quizPath, quizUIFrame, voice, owner) #

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
                print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {question}\n") #정답 표시
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
                        self.requestHint() #힌트 요청
                    await countdown(gameData, isLong=False)  #카운트 다운

    async def performance(self, user):
        voice = self._voice

        voice.stop() #즉각 보이스 스탑
        playBGM(voice, BGM_TYPE.SUCCESS) #성공 효과음

        roundChecker = self._roundIndex  # 현재 라운드 저장

        quizUIFrame = self._quizUIFrame
        quizUIFrame._title_visible = True
        quizUIFrame._title_text = chr(173)+"[　　　　"+ quizUIFrame._quizIcon + " " + quizUIFrame._quizName + "　　　　]"

        quizUIFrame._sub_visible = True
        quizUIFrame._sub_text = Config.getRandomHumanIcon()+" 정답자　**"+ chr(173) + "　"+str(user.display_name) +"**"

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
                rd = random.randrange(0, len(tmpQuizList))  # 0부터 tmpQuizList 크기 -1 만큼
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
        await message.clear_reaction(Config.EMOJI_ICON.ICON_HINT) #힌트 버튼 삭제
        emoji = Config.EMOJI_ICON.OX[0] #이모지 가져오기,
        await message.add_reaction(emoji=emoji) #이모지 추가,
        emoji = Config.EMOJI_ICON.OX[1] #이모지 가져오기,
        await message.add_reaction(emoji=emoji) #

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

        print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {gameData._nowQuiz}\n") #정답 표시

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

        answerIndex = str(gameData._selectionAnswer) #정답 번호
        answerDesc = gameData._oxQuizObject._answerText

        answerFrame = ui.QFrame()
        answerFrame._sub_visible = True
        answerFrame._sub_text = Config.EMOJI_ICON.ICON_POINT + " 정답: " + str(gameData._selectList[gameData._selectionAnswer])

        answerFrame._main_visible = False

        answerFrame._field_visible = True
        isWrong = True #정답자 존재하는가?
        for player in gameData._selectPlayerMap:
            if str(gameData._selectPlayerMap[player]) == answerIndex: #플레이어가 선택한 답과 정답이 일치하면          
                isWrong = False #정답자 존재!
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

        await asyncio.sleep(4)

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
            

        while repartCnt > 0: #반복횟수만큼 반복
            repartCnt -= 1
            

            voice.play(discord.FFmpegPCMAudio(audioName))  # 노래 재생
            await fadeIn(voice) #페이드인
            playTime = 2 #페이드인으로 2초 소비

            while voice.is_playing():  # 재생중이면
                if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
                    return #리턴
                await asyncio.sleep(0.9)  # 0.9초후 다시 확인
                playTime += 1 #재생 1초 +
                leftTime = audioLength  - playTime #남은 길이
                quizUIFrame._quizLeftTime = leftTime

                if leftTime < 0:
                    leftTime = 0

                await quizUIFrame.update()

            #재생이 끝난 후
            if roundChecker != gameData._roundIndex: return # 이미 다음 라운드라면 리턴

            await asyncio.sleep(1) 
                
            if gameData._gameStep == GAME_STEP.WAIT_FOR_ANSWER: #아직도 정답자 기다리는 중이면
                if hintType == 2: #힌트 타입이 자동일 떄
                    self.requestHint() #힌트 요청
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
        await fadeIn(voice) #페이드인

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
            playBGM(voice, BGM_TYPE.FAIL)
            answerFrame._title_text = chr(173)+"[　　　　"+ Config.getRandomWrongIcon() +" 정답 공개　　　　]"
            answerFrame._embedColor = discord.Color.red()
        else:
            answerFrame._title_text = chr(173)+"[　　　　"+ Config.EMOJI_ICON.ICON_COLLECT +" 정답!　　　　]"
            answerFrame._embedColor = discord.Color.green()

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
            quizUIFrame.addField(playerName,"[ " + str(gameData._scoreMap[player]) + "p" +" ]")

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
                rd = random.randrange(0, len(tmpQuizList))  # 0부터 tmpQuizList 크기 -1 만큼
                quiz = tmpQuizList[rd]  # 무작위 1개 선택
                quizList.append(quiz)  # 퀴즈 목록에 ox 퀴즈 객체 추가
                del tmpQuizList[rd]  # 검사한 항목은 삭제


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

        print(f"guild: {gameData._guild.name}, gameName: {gameData._gameName}, questionFile: {gameData._nowQuiz}\n") #정답 표시

        playBGM(voice, BGM_TYPE.BELL)

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
        quizUIFrame._sub_text = Config.getRandomHumanIcon()+" 정답자　**"+ chr(173) + "　"+str(user.display_name) +"**"

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


dataMap = dict()  # 데이터 저장용 해쉬맵
QUIZ_MAP = dict()  # 퀴즈 정보 저장용

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
    
    while voice.is_playing():  # 카운트다운중이면
        if(roundChecker != gameData._roundIndex): #이미 다음 라운드 넘어갔으면
            voice.stop() #카운트다운 정지
            return #리턴
        await asyncio.sleep(1)  # 1초후 다시 확인

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
            voice.play(discord.FFmpegPCMAudio(Config.BGM_PATH + "pling.mp3"))
        elif(bgmType == BGM_TYPE.ROUND_ALARM):
            voice.play(discord.FFmpegPCMAudio(Config.BGM_PATH + "ROUND_ALARM.mp3"))
        elif(bgmType == BGM_TYPE.SCORE_ALARM):
            voice.play(discord.FFmpegPCMAudio(Config.BGM_PATH + "SCORE_ALARM.mp3"))
        elif(bgmType == BGM_TYPE.ENDING):
            voice.play(discord.FFmpegPCMAudio(Config.BGM_PATH + "ENDING.mp3"))
        elif(bgmType == BGM_TYPE.FAIL):
            voice.play(discord.FFmpegPCMAudio(Config.BGM_PATH + "FAIL.mp3"))
        elif(bgmType == BGM_TYPE.countdown10):
            voice.play(discord.FFmpegPCMAudio(Config.BGM_PATH + "countdown10.wav"))
        elif(bgmType == BGM_TYPE.SUCCESS):
            voice.play(discord.FFmpegPCMAudio(Config.BGM_PATH + "SUCCESS.mp3"))
        elif(bgmType == BGM_TYPE.BELL):
            voice.play(discord.FFmpegPCMAudio(Config.BGM_PATH + "bell.mp3"))
        elif(bgmType == BGM_TYPE.LONGTIMER):
            tmpList = os.listdir(Config.BGM_PATH+"/longTimer/")
            rd = random.randrange(0, len(tmpList))  # 0부터 tmpList 크기 -1 만큼
            rdBgm = tmpList[rd]  # 무작위 1개 선택
            bgmName = Config.BGM_PATH+"/longTimer/"+rdBgm
            voice.play(discord.FFmpegPCMAudio(bgmName))
    except:
        print("error01 - voice is not connect error")


def getQuizTypeFromIcon(icon): #아이콘으로 퀴즈 타입 추측
    if icon == Config.EMOJI_ICON.ICON_TYPE_SONG:
        return GAME_TYPE.SONG
    elif icon == Config.EMOJI_ICON.ICON_TYPE_PICTURE:
        return GAME_TYPE.PICTURE
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
    
    return GAME_TYPE.SONG #디폴트


async def startQuiz(quizInfoFrame, owner): #퀴즈 시작

    message = quizInfoFrame._myMessage

    if owner.voice == None:
        quizInfoFrame._notice_visible = True
        quizInfoFrame._notice_text = Config.EMOJI_ICON.ICON_WARN + " 먼저 음성 채널에 참가해주세요."
        await ui.update(message)
        return

    voiceChannel = owner.voice.channel  # 호출자의 음성 채널 얻기
    chattingChannel = quizInfoFrame._myMessage.channel  # 퀴즈할 채팅 채널 얻기
    guild = message.guild
    guildData = getGuildData(guild)

    # bot의 해당 길드에서의 음성 대화용 객체
    voice = get(bot.voice_clients, guild=guild)
    if voice and voice.is_connected():  # 해당 길드에서 음성 대화가 이미 연결된 상태라면 (즉, 누군가 퀴즈 중)
        quizInfoFrame._notice_visible = True
        quizInfoFrame._notice_text = Config.EMOJI_ICON.ICON_WARN + "현재 진행중인 퀴즈를 중지해주세요.\n　 "+Config.EMOJI_ICON.ICON_STOP+" 버튼 클릭 또는 !중지"
        await ui.update(message)
        return

    #퀴즈 시작

    voice = await voiceChannel.connect()  # 음성 채널 연결후 해당 객체 반환
    playBGM(voice, BGM_TYPE.BELL)

    # 해당 채팅 채널에 선택한 퀴즈에 대한 퀴즈 진행용 UI 생성
    quizUiFrame = await ui.createQuizUI(chattingChannel, quizInfoFrame._quizPath, owner)
    option = quizInfoFrame._option #옵션값
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
    elif gameType == GAME_TYPE.OX: #ox 퀴즈면
        gameData = OXQuiz(quizPath, quizUiFrame, voice, owner)  # 퀴즈데이터 생성   
    elif gameType == GAME_TYPE.INTRO: #인트로 퀴즈면
        gameData = IntroQuiz(quizPath, quizUiFrame, voice, owner)  # 퀴즈데이터 생성   
    else: #그 외에는 기본
        gameData = SongQuiz(quizPath, quizUiFrame, voice, owner)  # 퀴즈데이터 생성

    gameData._gameType = gameType
    gameData._gameName = gameName

    gameData._trimLength = trimLength
    gameData._repeatCount = repeatCnt #옵션 세팅

    gameData._topNickname = topNickname

    quizUiFrame.setFunction(gameData.requestHint, gameData.skip, gameData.stop)

    guildData._gameData = gameData  # 해당 서버의 퀴즈데이터 저장
        
    await ui.returnToTitle(guild) #퀴즈 선택 ui 메인화면으로
    await ui.clearChat(chattingChannel) #채팅 청소

    await gameData.gameRule() #퀴즈 설명 출력
    await asyncio.sleep(2)  # 2초 대기

    if gameData.checkStop(): return #혹시 퀴즈가 중지됐는지 확인

    await gameData.start()


# 봇이 접속(활성화)하면 아래의 함수를 실행하게 된다, 이벤트
@bot.event
async def on_ready():
    print(f'{bot.user} 활성화됨')
    await bot.change_presence(status=discord.Status.online) #온라인
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!퀴즈 | !quiz"))
  
    print("봇 이름:",bot.user.name,"봇 아이디:",bot.user.id,"봇 버전:",discord.__version__)


@bot.command(pass_context=False, aliases=["ping"])  # ping 명령어 입력시
async def pingCommand(ctx):  # ping 테스트
    await ctx.send(f"핑 : {round(bot.latency * 1000)}ms")


@bot.command(pass_context=False, aliases=["quiz", "QUIZ", "퀴즈"])  # quiz 명령어 입력시
async def quizCommand(ctx, gamesrc=None):  # 퀴즈봇 UI 생성
    if gamesrc == None:
        guild = ctx.guild #서버
        guildData = getGuildData(guild) #길드 데이터 없으면 초기화
         
        await ui.createSelectorUI(ctx.channel) #UI 재설정
        guildData._selectorChannelID = ctx.channel.id #버튼 상호작용 채널 설정
       

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
            await message.delete()
            return
        if(gameData._gameStep != GAME_STEP.WAIT_FOR_ANSWER): #정답 대기중 아니면 return
            return

        await gameData.on_message(message) #메세지 이벤트 동작


@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:  # 봇이 입력한거면
        return  # 건너뛰어

    channel = reaction.message.channel  # 반응 추가한 채널
    guildData = getGuildData(reaction.message.guild)
    gameData = guildData._gameData

    isAlreadyRemove = False
    if channel.id == guildData._selectorChannelID: #반응한 채널이 퀴즈선택 메시지 있는 채널이라면
        if not isAlreadyRemove:
            try:
                isAlreadyRemove = True
                await reaction.remove(user)  # 이모지 삭제
            except:
                return
        await ui.on_reaction_add(reaction, user) #이벤트 동작

    if gameData != None and gameData._chatChannel == channel:  # 현재 게임중인 채널이면
        if not isAlreadyRemove:
            try:
                isAlreadyRemove = True
                await reaction.remove(user)  # 이모지 삭제
            except:
                return
        await gameData.action(reaction, user) #이벤트 동작

        


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
    emoji = reaction.emoji
    guildData = getGuildData(reaction.message.guild)

    if channel.id == guildData._selectorChannelID: #반응한 채널이 퀴즈선택 메시지 있는 채널이라면
        await reaction.message.add_reaction(emoji=emoji) #다시 추가
                


#################################

ui.initializing(bot, startQuiz) #QuizSelector 초기화
bot.run(Config.TOKEN)  # 봇 실행
