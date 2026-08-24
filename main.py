import os
import asyncio
from aiohttp import web
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Environment Variables
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", 0))
PORT = int(os.environ.get("PORT", 8080))
FQDN = os.environ.get("FQDN", "").rstrip('/')

bot = Client(
    "StreamLinkBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Web Stream Route Handler
async def stream_handler(request):
    try:
        msg_id = int(request.match_info['msg_id'])
        msg = await bot.get_messages(BIN_CHANNEL, msg_id)
        if not msg or not (msg.video or msg.document or msg.photo or msg.audio):
            return web.Response(status=404, text="File Not Found")

        media = msg.video or msg.document or msg.photo or msg.audio
        file_size = getattr(media, 'file_size', 0)
        mime_type = getattr(media, 'mime_type', 'application/octet-stream')
        if msg.photo:
            mime_type = 'image/jpeg'

        headers = {
            "Content-Type": mime_type,
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="{getattr(media, "file_name", "file")}"'
        }

        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)

        async for chunk in bot.stream_media(msg, limit=0):
            await response.write(chunk)

        await response.write_eof()
        return response
    except Exception as e:
        return web.Response(status=500, text=str(e))

# Health Check Route
async def ping(request):
    return web.Response(text="Bot & Server Active 🚀")

# Telegram Bot Message Listener
@bot.on_message(filters.private & (filters.video | filters.document | filters.photo | filters.audio))
async def generate_links(client: Client, message: Message):
    status_msg = await message.reply_text("⚡ Processing file & generating fast links...")
    try:
        forwarded = await message.copy(chat_id=BIN_CHANNEL)
        msg_id = forwarded.id
        
        base_url = FQDN if FQDN else f"http://localhost:{PORT}"
        direct_link = f"{base_url}/dl/{msg_id}"

        if message.video:
            text = (
                f"🎬 **Direct MP4 Stream Link Generated!**\n\n"
                f"🔗 **Web Player URL:**\n`{direct_link}`\n\n"
                f"💡 *මෙම Link එක App Hub එකේ 'Preview Video URL' එකට Paste කරන්න.*"
            )
        elif message.photo:
            text = (
                f"🖼️ **Direct Cover Image Link Generated!**\n\n"
                f"🔗 **Image URL:**\n`{direct_link}`\n\n"
                f"💡 *මෙම Link එක 'Cover Image URL' එකට Paste කරන්න.*"
            )
        else:
            text = (
                f"📦 **Direct Fast Zip / File Download Link Generated!**\n\n"
                f"🔗 **Download URL:**\n`{direct_link}`\n\n"
                f"💡 *මෙම Link එක 'Full Video Zip Pack URL' එකට Paste කරන්න.*"
            )

        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Direct Link Open", url=direct_link)]
        ])

        await status_msg.edit_text(text, reply_markup=btn, disable_web_page_preview=True)
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

# Web Server & Bot Startup
async def start_services():
    await bot.start()
    app = web.Application()
    app.router.add_get('/', ping)
    app.router.add_get('/dl/{msg_id}', stream_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"Bot and Streaming Server running on port {PORT}...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(start_services())
