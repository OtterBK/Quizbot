
# 개발자 페이지에서 봇에 대한 토큰 텍스트를 가져온 뒤, TOKEN에 대입하자
TOKEN = "ODA1MjE1NjU5NjMzOTM0NTE3.YBXphQ.aRZPxSMFofc7F1L1NdzL58o5sxQ"

BOT_PREFIX = "^" #명령어 prefix

QUIZ_PATH = "F:/quizbot/gameData/"  # 게임 소스폴더
BGM_PATH = "F:/quizbot/bgm/"  # 효과음 폴더
SAVE_PATH = "F:/quizbot/download/"
TMP_PATH = "F:/quizbot/tmp/" #임시폴더
DATA_PATH = "F:/quizbot/savedata/" #데이터 저장 폴더


#이모지 아이콘
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
    ALPHABET = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q"
                    , "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
    NUMBER = [ "0️⃣", "1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    OX = ["⭕", "❌"] #ox퀴즈용