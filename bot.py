import os
import time
import threading
import yfinance as yf
import pandas as pd
import ta
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

# Telegram token
TOKEN = os.environ.get("TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")  # Your Telegram user/group chat ID
bot = Bot(token=TOKEN)

# Config
PAIRS = ["EURUSD", "GBPUSD", "USDJPY"]
DEFAULT_INTERVAL = 5  # minutes between automatic signals

# Generate signal with description
def generate_signal(pair: str, timeframe: str):
    try:
        data = yf.download(pair + "=X", period="1mo", interval=timeframe)
        rsi = ta.momentum.RSIIndicator(data['Close']).rsi()
        macd = ta.trend.MACD(data['Close'])
        ma50 = data['Close'].rolling(50).mean()
        ma200 = data['Close'].rolling(200).mean()

        last_rsi = rsi.iloc[-1]
        last_macd = macd.macd().iloc[-1]
        last_macd_signal = macd.macd_signal().iloc[-1]
        last_ma50 = ma50.iloc[-1]
        last_ma200 = ma200.iloc[-1]

        # Determine signal
        if last_rsi < 50 and last_macd > last_macd_signal and last_ma50 > last_ma200:
            signal_type = "BUY ✅"
        else:
            signal_type = "SELL ❌"

        # Professional description
        description = (
            f"{pair} | {timeframe} | {signal_type}\n"
            f"Reason: RSI={last_rsi:.2f}, "
            f"MACD={'Bullish' if last_macd > last_macd_signal else 'Bearish'}, "
            f"Trend={'Up' if last_ma50 > last_ma200 else 'Down'}"
        )

        return signal_type, description

    except Exception as e:
        return "ERROR", f"{pair} | Error: {str(e)}"

# Send signal image with description
def send_signal_image(chat_id, pair, timeframe):
    signal_type, description = generate_signal(pair, timeframe)
    if signal_type == "BUY ✅":
        bot.send_photo(chat_id=chat_id, photo=open("buy.png", "rb"), caption=description)
    elif signal_type == "SELL ❌":
        bot.send_photo(chat_id=chat_id, photo=open("sell.png", "rb"), caption=description)
    else:
        bot.send_message(chat_id=chat_id, text=description)

# Manual command
def manual_signal(update: Update, context: CallbackContext):
    if len(context.args) != 2:
        update.message.reply_text("Usage: /signal PAIR TIMEFRAME\nExample: /signal EURUSD 1m")
        return

    pair = context.args[0].upper()
    timeframe = context.args[1]

    if pair not in PAIRS:
        update.message.reply_text(f"Pair not supported: {', '.join(PAIRS)}")
        return

    send_signal_image(update.message.chat_id, pair, timeframe)

# Automatic signals with 1-minute warning
def auto_signals(interval=DEFAULT_INTERVAL):
    while True:
        for pair in PAIRS:
            # 1-minute warning
            bot.send_message(chat_id=CHAT_ID, text=f"⚠️ {pair} | 1-minute warning before signal!")
            time.sleep(60)
            # Send actual signal with professional description
            send_signal_image(CHAT_ID, pair, "1m")
            print(f"Sent automatic signal for {pair}")
        time.sleep((interval - 1) * 60)

# Main function
def main():
    # Start automatic signals in separate thread
    thread = threading.Thread(target=auto_signals)
    thread.daemon = True
    thread.start()

    # Start Telegram bot for manual commands
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("signal", manual_signal))

    print("Bot started. Manual and automatic modes active with images and professional descriptions.")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()