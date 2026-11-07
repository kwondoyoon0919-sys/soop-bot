import json
import os
import time
import discord
from discord.ext import commands, tasks
import requests

# Render 클라우드 서버의 환경변수에서 토큰을 불러옵니다.
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

SOOP_USER_ID = "haejwer0724"
STREAM_URL = f"https://www.sooplive.com/{SOOP_USER_ID}"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "channels.json")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

is_live = False


def load_channels():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"채널 로드 실패: {e}")
            return []
    return []


def save_channels(channels):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(channels, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"채널 저장 실패: {e}")


def check_soop_live(user_id):
    url = "https://live.afreecatv.com/afreeca/get_live_stat.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": f"https://play.afreecatv.com/{user_id}",
    }
    params = {"bjid": user_id}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        if data.get("RESULT") == 1 and data.get("REAL_BROAD_INFO"):
            broad_info = data["REAL_BROAD_INFO"]
            broad_no = broad_info.get("BROAD_NO")
            title = broad_info.get("TITLE", "방송 제목 없음")
            return {
                "is_live": True,
                "title": title,
                "broad_no": broad_no,
                "thumb": (
                    f"https://liveimg.afreecatv.com/m/{broad_no}?{int(time.time())}"
                    if broad_no
                    else ""
                ),
            }
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 통신 오류: {e}")

    return {"is_live": False}


@bot.command(name="알림등록")
async def register_channel(ctx):
    channels = load_channels()
    channel_id = ctx.channel.id

    if channel_id in channels:
        await ctx.send("⚠️ 이 채널은 이미 알림 채널로 등록되어 있습니다.")
    else:
        channels.append(channel_id)
        save_channels(channels)
        await ctx.send(
            f"✅ **{ctx.guild.name}** 서버의 **#{ctx.channel.name}** 채널이 제로! 뱅온 알림 채널로 등록되었습니다!"
        )


@bot.command(name="알림해제")
async def unregister_channel(ctx):
    channels = load_channels()
    channel_id = ctx.channel.id

    if channel_id in channels:
        channels.remove(channel_id)
        save_channels(channels)
        await ctx.send(
            f"🚫 **#{ctx.channel.name}** 채널의 알림 등록이 해제되었습니다."
        )
    else:
        await ctx.send("⚠️ 이 채널은 등록된 알림 채널이 아닙니다.")


@bot.command(name="목록")
async def list_channels(ctx):
    channels = load_channels()
    await ctx.send(
        f"📋 현재 총 **{len(channels)}개**의 채널에 뱅온 알림이 설정되어 있습니다."
    )


@tasks.loop(seconds=60)
async def monitor_stream():
    global is_live
    status = check_soop_live(SOOP_USER_ID)
    channels = load_channels()

    if status["is_live"] and not is_live:
        is_live = True

        embed = discord.Embed(
            title="제로! 뱅온",
            description=f"**[{status['title']}]({STREAM_URL})**",
            color=0x2ECC71,
        )
        if status["thumb"]:
            embed.set_image(url=status["thumb"])

        for channel_id in channels:
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(content="@everyone 뱅온 알림!", embed=embed)
                except Exception as e:
                    print(f"채널({channel_id}) 알림 전송 실패: {e}")

        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 뱅온 알림 전송 완료 ({len(channels)}개 채널)"
        )

    elif not status["is_live"] and is_live:
        is_live = False

        embed = discord.Embed(
            title="제로! 방송 종료",
            color=0x34495E,
        )

        for channel_id in channels:
            channel = bot.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"채널({channel_id}) 방종 알림 전송 실패: {e}")

        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 방송 종료 알림 전송 완료"
        )


@bot.event
async def on_ready():
    print("========================================")
    print(f"다중 알림 봇 접속 완료: {bot.user.name}")
    print(f"모니터링 대상: 제로 ({SOOP_USER_ID})")
    print("========================================")
    if not monitor_stream.is_running():
        monitor_stream.start()


bot.run(DISCORD_BOT_TOKEN)