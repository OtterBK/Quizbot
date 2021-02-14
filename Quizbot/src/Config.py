
import random

# 개발자 페이지에서 봇에 대한 토큰 텍스트를 가져온 뒤, TOKEN에 대입하자

BOT_PREFIX = "!" #명령어 prefix

RESOURCE_PATH = "F:/quizbot/"
QUIZ_PATH = RESOURCE_PATH + "gameData/"  # 게임 소스폴더
MULTI_PATH = RESOURCE_PATH + "multiplay/"  # 멀티플레이 소스폴더
BGM_PATH = RESOURCE_PATH + "bgm/"  # 효과음 폴더
SAVE_PATH = RESOURCE_PATH + "download/" 
TMP_PATH = RESOURCE_PATH + "tmp/" #임시폴더
DATA_PATH = RESOURCE_PATH + "savedata/" #데이터 저장 폴더
OPTION_PATH = DATA_PATH + "option/" #옵션 데이터 저장 폴더
RANK_PATH = DATA_PATH + "rank/" #랭크 데이터 저장 폴더
PATCHNOTE_PATH = DATA_PATH + "patchnote/" #패치노트 폴더

VERSION = "2.06"
LAST_PATCH = "21/02/14"
EMAIL_ADDRESS = "otter6975@gmail.com"
BOT_LINK = "https://discord.com/api/oauth2/authorize?client_id=788060831660114012&permissions=8&scope=bot"

TOKEN = ""
NOTICE = ""

#멀티 플레이 관련
SYNC_INTERVAL = 0.01 #동기 체크 딜레이
MAX_CONNECTION = 30

try:
    f = open(DATA_PATH+"token.txt", 'r', encoding="utf-8" )
    TOKEN = f.readline().strip()
    f.close()
except:
    print("토큰 로드 에러")

try:
    f = open(DATA_PATH+"notice.txt", 'r', encoding="utf-8" ) #공지
    while True:
        line = f.readline()
        if not line:
            break

        NOTICE += f.readline()
    f.close()
except:
    print("토큰 로드 에러")

#이모지 아이콘
class EMOJI_ICON(enumerate): #이모지
    PAGE_PREV = "◀️"
    PAGE_NEXT = "▶️"
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
    ICON_SEARCH = "🔍"
    ICON_QUIZBOT = "🔔"
    ICON_LOCALPLAY = "🌠"
    ICON_MULTIPLAY = "🌏"
    ICON_SETTING = "⚙️"
    ICON_INFO = "📒"
    ICON_PAGE = "🅿️"
    ICON_QUIZ_DEFAULT = "❓"
    ICON_WARN = "⚠️"
    ICON_BOX = "📦"
    ICON_HINT = "💡"
    ICON_SKIP = "⏩"
    ICON_STOP = "⏹️"
    ICON_RULE = "📝"
    ICON_TIP = "🔖"
    ICON_SOON = "☑️"
    ICON_SPEAKER_LOW = "🔉"
    ICON_SPEAKER_HIGH = "🔊"
    ICON_KEYBOARD = "⌨️"
    ICON_SELECTOR = "📋"
    ICON_OXQUIZ = "⭕❌"
    ICON_RESET = "⛔"
    ICON_VERSION = "📌"
    ICON_HELP = "❔"
    ICON_POINT = "☝️"
    ICON_COLLECT = "💯"
    ICON_ALARM = "❗"
    ICON_NOTICE = "🔶"
    ICON_LIST = "📄"
    ICON_PEN = "✏️"
    ICON_SONG = "🎵"
    ICON_REPEAT = "🔁"
    ICON_HUMAN = ["👮‍♀️","🕵️‍♀️","🕵️‍♂️","💂‍♂️","💂‍♀️","👷‍♀️","👷‍♂️","👩‍⚕️","👨‍⚕️","👩‍🎓","👨‍🎓","👩‍🏫","👨‍🏫","👩‍⚖️","👨‍⚖️","👩‍🌾","👨‍🌾","👩‍🍳","👨‍🍳","👩‍🔧","👩‍🏭","👨‍🔧","👨‍🏭","👩‍💼","👨‍💼","👩‍🔬","👨‍🔬","👩‍💻","👨‍💻","👩‍🎤","👨‍🎤","👩‍🎨","👨‍🎨","👩‍✈️","👨‍✈️","👩‍🚀","👨‍🚀","👩‍🚒","👨‍🚒","🧕","👰","🤵","🤱","🤰","🦸‍♀️","🦸‍♂️","🦹‍♀️","🦹‍♂️","🧙‍♀️","🧙‍♂️","🧚‍♀️","🧚‍♂️","🧛‍♀️","🧛‍♂️","🧜‍♀️","🧝‍♀️","🧝‍♂️","🧟‍♀️","🧟‍♂️"]
    ICON_POINT_TO_LEFT = "👈"
    ICON_POINT_TO_RIGHT = "👉"
    ICON_WRONG = ["😡","🤮", "😅","🤬","🥵","🥶","😕","☹️","🤨","😐","😦","🤕"]
    ICON_MEDAL = ["🏅", "🥇", "🥈", "🥉"]
    ICON_BLIND = "◼"
    ICON_PHONE = "📱"
    ICON_MAIL = "📧"
    ICON_GIT = "🌐"
    ICON_FIX = "🛠️"
    ICON_GOOD = "👍"
    ICON_PATCHNOTE = "📗"
    ICON_BOOK_RED = "📕"
    ICON_NOTE = "📜"
    ICON_CHECK = "✅"
    ICON_CHAT = "📫"
    ICON_FIGHT = "🥊"
    ICON_TROPHY = "🏆"
    ICON_NET = "🙋‍♂️"
    

    CLOCK_0 = "🕛"
    CLOCK_1 = "🕐"
    CLOCK_2 = "🕑"
    CLOCK_3 = "🕒"
    CLOCK_4 = "🕓"
    CLOCK_5 = "🕔"
    CLOCK_6 = "🕕"
    CLOCK_7 = "🕖"
    CLOCK_8 = "🕗"
    CLOCK_9 = "🕘"
    CLOCK_10 = "🕙"
    CLOCK_11 = "🕚"
    CLOCK_12 = "🕛"

    ICON_TYPE = "📚"
    ICON_TYPE_SONG = "🎧"
    ICON_TYPE_SCRIPT = "🎙️"
    ICON_TYPE_SELECT = "✔️"
    ICON_TYPE_PICTURE = "🖼"
    ICON_TYPE_OX = "⭕"
    ICON_TYPE_QNA = "👨‍🎓"
    ICON_TYPE_INTRO = "🎶"
    ICON_TYPE_MULTIPLAY = "🛰"
    ALPHABET = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q"
                    , "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
    NUMBER = [ "0️⃣", "1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    OX = ["⭕", "❌"] #ox퀴즈용


def getAlphabetFromIndex(index): 
    return EMOJI_ICON.ALPHABET[index]


def getEmojiFromNumber(index): #정수값에 알맞은 이모지 반환
    return EMOJI_ICON.NUMBER[index]

def getNumberFromEmoji(emoji): #이모지가 숫자 이모지인지 확인
    index = 0
    while index < len(EMOJI_ICON.NUMBER): #이모지에 맞는 번호 반환
        if EMOJI_ICON.NUMBER[index] == emoji:
            return index
        index += 1

    return -1 #-1은 숫자 이모지가 아니라는 뜻

def getRandomWrongIcon():
    return random.choice(EMOJI_ICON.ICON_WRONG)

def getMedalFromNumber(index): #정수값에 알맞은 메달 이모지 반환
    if index >= 0 and index < len(EMOJI_ICON.ICON_MEDAL):
        return EMOJI_ICON.ICON_MEDAL[index]
    else:
        return EMOJI_ICON.ICON_MEDAL[0]

def getRandomHumanIcon():
    return random.choice(EMOJI_ICON.ICON_HUMAN)

