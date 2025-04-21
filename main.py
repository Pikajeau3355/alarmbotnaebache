import asyncio
import aiohttp
import os
from telegram.ext import Application
from datetime import datetime

API_TOKEN = os.getenv("API_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ALERTS_API_URL = f"https://api.alerts.in.ua/v1/alerts/active.json?token={API_TOKEN}"

ALLOWED_UIDS = {
    9: "Дніпропетровська область",
}

ALERT_NAMES = {
    "air_raid": "Повітряна тривога",
    "artillery_shelling": "Артобстріл",
    "urban_fights": "Вуличні бої",
    "chemical": "Хімічна загроза",
    "nuclear": "Ядерна загроза"
}

INTERESTING_TYPES = {"air_raid", "artillery_shelling"}

previous_alerts = set()
air_raid_status = {}

async def check_alerts(application: Application):
    global previous_alerts
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(ALERTS_API_URL) as response:
                    if response.status != 200:
                        print(f"❗ HTTP помилка: {response.status}")
                        await asyncio.sleep(30)
                        continue
                    data = await response.json()

            alerts = data.get("alerts", [])
            current_alerts = set()

            for alert in alerts:
                uid = int(alert.get("location_uid", 0))
                if uid not in ALLOWED_UIDS:
                    continue

                alert_type = alert.get("alert_type", "unknown")
                if alert_type not in INTERESTING_TYPES:
                    continue

                notes = alert.get("notes", "").strip()
                location_name = ALLOWED_UIDS.get(uid)

                key = f"{uid}|{alert_type}|{notes}"
                current_alerts.add(key)

                started_at = datetime.strptime(alert['started_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
                is_active = started_at <= datetime.utcnow() and alert.get("finished_at") is None

                if is_active and alert_type == "air_raid":
                    if not air_raid_status.get(uid):
                        air_raid_status[uid] = True
                        text = f"🚨 {location_name} - повітряна тривога!"
                        if notes:
                            text += f"
📜 Коментар: {notes}"
                        await application.bot.send_message(chat_id=CHAT_ID, text=text)

            for uid in list(air_raid_status.keys()):
                still_active = any(f"{uid}|air_raid" in key for key in current_alerts)
                if air_raid_status[uid] and not still_active:
                    air_raid_status[uid] = False
                    await application.bot.send_message(
                        chat_id=CHAT_ID,
                        text=f"✅ {ALLOWED_UIDS[uid]} - відбій повітряної тривоги!"
                    )

            previous_alerts = current_alerts

        except Exception as e:
            print(f"⚠️ Помилка: {e}")

        await asyncio.sleep(30)

async def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    await application.bot.send_message(chat_id=CHAT_ID, text="🔔 Бот активний. Відстежую тривоги.")
    await check_alerts(application)

if __name__ == "__main__":
    asyncio.run(main())
