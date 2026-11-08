import os

TOKEN = "MTIyNDAwODg5NDI2MzU5MDk2Mg.G6EkWa.G8i-88HCk6RlUF_nZOAE2xLWEPWJLVUE4AUuFo"

GUILD_ID = 1001741324061528064

CATEGORY_ID = 1492211550193455204                # Категория для вопросов/жалоб
STAFF_CATEGORY_ID = 1492211550193455204          # Категория для заявок персонала (можно ту же)
STAFF_ACCEPTED_CATEGORY_ID = STAFF_CATEGORY_ID   # Категория для принятых заявок

MOD_ROLE_ID = 1007659142552494143
CURATOR_ROLE_ID = 1007656280447520881

# ID каналов для постоянных меню
MAIN_MENU_CHANNEL_ID = 1492262926797770923       # Канал для главного меню (вопросы/жалобы)
STAFF_MENU_CHANNEL_ID = 1492264834408910940      # Канал для меню набора персонала

# Канал для логов и пересылки ЛС бота (укажите ID канала при необходимости)
LOG_CHANNEL_ID = None

# Настройки проекта TrueCube
BOT_NAME = "TrueCube"
SERVER_IP = "mc.truecube.ru"
TELEGRAM_URL = "https://t.me/truecubeM"
TELEGRAM_TAG = "@truecubeM"
EMBED_COLOR = 0xC400FF

ACCEPT_ICON_URL = "https://emoji.gg/assets/emoji/7425-classic-check-mark.png"
DENY_ICON_URL = "https://cdn-icons-png.flaticon.com/512/753/753345.png"

# Абсолютный путь к папке data, расположенной рядом с ботом
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MESSAGE_STORAGE = os.path.join(DATA_DIR, "menu_messages.json")
