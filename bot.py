import os
import time
import datetime
import logging
import asyncio
import aiohttp
import json
from urllib.parse import quote
from config import Config
from database import Database
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

# Create necessary directories
os.makedirs("downloads", exist_ok=True)
os.chmod("downloads", 0o755)
os.makedirs("data/files", exist_ok=True)
os.makedirs("data/thumbnails", exist_ok=True)
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Client(
    "MystreamBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    in_memory=True,
    workers=100
)

db = Database(Config.DATABASE_URL, Config.BOT_USERNAME)

# Global variables
BIN_CHANNEL = Config.BIN_CHANNEL
AUTO_DELETE_TIME = Config.AUTO_DELETE_TIME
ADMINS = Config.ADMINS

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    user_id = message.from_user.id
    if not await db.is_user_exist(user_id):
        await db.add_user(user_id)
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"#NEW_USER: \n\nNew User [{message.from_user.first_name}](tg://user?id={message.from_user.id}) started !!"
            )
        except:
            pass
    
    if len(message.command) > 1:
        if message.command[1] == "plans":
            return await message.reply_text(Config.PLANS_TEXT, quote=True)
        
        if message.command[1].startswith("verify_"):
            user_id = int(message.command[1].split("_", 1)[1])
            if user_id == message.from_user.id:
                await db.update_verified(user_id, True)
                await message.reply_text("✅ You are now verified!", quote=True)
            else:
                await message.reply_text("❌ Invalid verification link!", quote=True)
            return
    
    await message.reply_text(
        text=Config.START_TEXT.format(message.from_user.mention, Config.BOT_USERNAME),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Updates", url=f"https://t.me/{Config.UPDATES_CHANNEL}"),
             InlineKeyboardButton("💬 Support", url=f"https://t.me/{Config.SUPPORT_GROUP}")],
            [InlineKeyboardButton("💰 Premium Plans", callback_data="premium"),
             InlineKeyboardButton("🤖 About", callback_data="about")],
            [InlineKeyboardButton("🔍 How to Use", callback_data="help")]
        ])
    )

@app.on_message(filters.private & (filters.document | filters.video | filters.audio | filters.photo))
async def file_handler(client, message: Message):
    try:
        user_id = message.from_user.id
        if not await db.is_user_exist(user_id):
            await db.add_user(user_id)
        
        # Check if user is banned
        if await db.is_banned(user_id):
            await message.reply_text("❌ You are banned from using this bot!")
            return
        
        # Check premium status for large files
        media = message.document or message.video or message.audio or message.photo
        file_size = media.file_size
        
        if not await db.is_premium(user_id) and file_size > Config.FREE_FILE_SIZE:
            await message.reply_text(
                f"❌ Free users can only upload files up to {humanbytes(Config.FREE_FILE_SIZE)}\n\n"
                f"💎 Upgrade to premium for {humanbytes(Config.MAX_FILE_SIZE)} files!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💰 Premium Plans", callback_data="premium")]
                ])
            )
            return
        
        if file_size > Config.MAX_FILE_SIZE:
            await message.reply_text("❌ File size exceeds maximum limit!")
            return
        
        msg = await message.reply_text("📥 Downloading your file...")
        
        # Download file
        file_name = getattr(media, 'file_name', None) or f"file_{message.id}"
        download_path = os.path.join("downloads", file_name)
        file_path = await message.download(file_name=download_path)
        
        await msg.edit_text("📤 Uploading to storage...")
        
        # Upload to bin channel
        caption = f"📁 {file_name}\n📦 {humanbytes(file_size)}\n👤 User: {user_id}\n🆔 #ID{user_id}"
        
        if message.video:
            bin_message = await app.send_video(
                chat_id=BIN_CHANNEL,
                video=file_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                thumb="assets/thumbnail.jpg" if os.path.exists("assets/thumbnail.jpg") else None
            )
        elif message.audio:
            bin_message = await app.send_audio(
                chat_id=BIN_CHANNEL,
                audio=file_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                thumb="assets/thumbnail.jpg" if os.path.exists("assets/thumbnail.jpg") else None
            )
        elif message.document:
            bin_message = await app.send_document(
                chat_id=BIN_CHANNEL,
                document=file_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                thumb="assets/thumbnail.jpg" if os.path.exists("assets/thumbnail.jpg") else None
            )
        else:
            bin_message = await app.send_photo(
                chat_id=BIN_CHANNEL,
                photo=file_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML
            )
        
        # Generate multiple links
        file_id = bin_message.document.file_id if bin_message.document else bin_message.video.file_id if bin_message.video else bin_message.audio.file_id if bin_message.audio else bin_message.photo.file_id
        
        direct_link = f"{Config.DOWNLOAD_BASE_URL}/file/{file_id}?filename={quote(file_name)}"
        stream_link = f"{Config.STREAM_BASE_URL}/stream/{file_id}"
        embed_link = f"{Config.STREAM_BASE_URL}/embed/{file_id}"
        
        # Save to database
        await db.add_file_record(
            file_id=file_id,
            file_name=file_name,
            file_size=file_size,
            mime_type=media.mime_type if hasattr(media, 'mime_type') else "application/octet-stream",
            bin_message_id=bin_message.id,
            direct_link=direct_link,
            stream_link=stream_link,
            embed_link=embed_link,
            user_id=user_id,
            premium=await db.is_premium(user_id)
        )
        
        # Auto-delete setup
        if AUTO_DELETE_TIME > 0:
            asyncio.create_task(auto_delete_message(bin_message, AUTO_DELETE_TIME))
        
        # Create buttons
        buttons = [
            [InlineKeyboardButton("📥 Direct Download", url=direct_link)],
            [InlineKeyboardButton("🎥 Stream Online", url=stream_link)],
            [InlineKeyboardButton("🔗 Share Links", callback_data=f"share_{file_id}")]
        ]
        
        if "video" in getattr(media, 'mime_type', ''):
            buttons.insert(1, [InlineKeyboardButton("📺 Embed Player", url=embed_link)])
        
        if user_id in ADMINS:
            buttons.append([InlineKeyboardButton("🗑️ Delete File", callback_data=f"delete_{bin_message.id}")])
        
        await msg.edit_text(
            text=f"**✅ File Ready!**\n\n"
                 f"**📁 File:** `{file_name}`\n"
                 f"**📦 Size:** {humanbytes(file_size)}\n"
                 f"**⏰ Auto-delete:** {AUTO_DELETE_TIME//3600} hours\n"
                 f"**👤 Status:** {'💎 Premium' if await db.is_premium(user_id) else '🎫 Free'}\n\n"
                 f"**🔗 Direct Download:**\n`{direct_link}`\n\n"
                 f"**🎬 Stream Link:**\n`{stream_link}`",
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        
        # Log to channel
        try:
            await client.send_message(
                Config.LOG_CHANNEL,
                f"#NEW_FILE: \n\nUser: [{message.from_user.first_name}](tg://user?id={user_id})\nFile: {file_name}\nSize: {humanbytes(file_size)}\nPremium: {await db.is_premium(user_id)}"
            )
        except:
            pass
        
        # Clean up
        os.remove(file_path)
        
    except Exception as e:
        logger.error(f"File handling error: {e}")
        await message.reply_text("❌ Error processing your file.")

@app.on_callback_query(filters.regex("^share_"))
async def share_callback(client, callback_query: CallbackQuery):
    file_id = callback_query.data.split("_", 1)[1]
    file_data = await db.get_file_by_id(file_id)
    
    if not file_data:
        await callback_query.answer("❌ File not found!", show_alert=True)
        return
    
    await callback_query.answer()
    await callback_query.message.reply_text(
        text=f"**🔗 Share Links for {file_data['file_name']}**\n\n"
             f"**📥 Direct Download:**\n`{file_data['direct_link']}`\n\n"
             f"**🎥 Stream Link:**\n`{file_data['stream_link']}`\n\n"
             f"**📺 Embed Link:**\n`{file_data.get('embed_link', 'N/A')}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 Direct", url=file_data['direct_link'])],
            [InlineKeyboardButton("🎥 Stream", url=file_data['stream_link'])],
            [InlineKeyboardButton("📺 Embed", url=file_data.get('embed_link', file_data['stream_link']))],
            [InlineKeyboardButton("🔙 Back", callback_data=f"back_{file_id}")]
        ]),
        disable_web_page_preview=True
    )

@app.on_callback_query(filters.regex("^back_"))
async def back_callback(client, callback_query: CallbackQuery):
    file_id = callback_query.data.split("_", 1)[1]
    file_data = await db.get_file_by_id(file_id)
    
    if not file_data:
        await callback_query.answer("❌ File not found!", show_alert=True)
        return
    
    await callback_query.answer()
    buttons = [
        [InlineKeyboardButton("📥 Direct Download", url=file_data['direct_link'])],
        [InlineKeyboardButton("🎥 Stream Online", url=file_data['stream_link'])],
        [InlineKeyboardButton("🔗 Share Links", callback_data=f"share_{file_id}")]
    ]
    
    if "video" in file_data.get('mime_type', ''):
        buttons.insert(1, [InlineKeyboardButton("📺 Embed Player", url=file_data.get('embed_link', file_data['stream_link']))])
    
    if callback_query.from_user.id in ADMINS:
        buttons.append([InlineKeyboardButton("🗑️ Delete File", callback_data=f"delete_{file_data['bin_message_id']}")])
    
    await callback_query.message.edit_text(
        text=f"**✅ File Ready!**\n\n"
             f"**📁 File:** `{file_data['file_name']}`\n"
             f"**📦 Size:** {humanbytes(file_data['file_size'])}\n"
             f"**⏰ Auto-delete:** {AUTO_DELETE_TIME//3600} hours\n\n"
             f"**🔗 Direct Download:**\n`{file_data['direct_link']}`\n\n"
             f"**🎬 Stream Link:**\n`{file_data['stream_link']}`",
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )

@app.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast_handler(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("❌ Please reply to a message to broadcast.")
        return
    
    all_users = await db.get_all_users()
    total_users = len(all_users)
    success = 0
    
    progress_msg = await message.reply_text(f"📤 Broadcasting to {total_users} users...")
    
    for user_id in all_users:
        try:
            await message.reply_to_message.copy(user_id)
            success += 1
            if success % 100 == 0:
                await progress_msg.edit_text(f"📤 Progress: {success}/{total_users}")
        except Exception as e:
            logger.error(f"Broadcast error for {user_id}: {e}")
    
    await progress_msg.edit_text(f"✅ Broadcast completed!\nSuccess: {success}\nFailed: {total_users - success}")

@app.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats_command(client, message: Message):
    total_users = await db.total_users_count()
    total_files = await db.total_files_count()
    premium_users = await db.premium_users_count()
    
    await message.reply_text(
        f"📊 **Bot Statistics:**\n\n"
        f"👥 Total Users: `{total_users}`\n"
        f"💎 Premium Users: `{premium_users}`\n"
        f"📁 Total Files: `{total_files}`\n"
        f"🆓 Free Limit: `{humanbytes(Config.FREE_FILE_SIZE)}`\n"
        f"💎 Premium Limit: `{humanbytes(Config.MAX_FILE_SIZE)}`"
    )

@app.on_message(filters.command("ban") & filters.user(ADMINS))
async def ban_user(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /ban <user_id>")
        return
    
    try:
        user_id = int(message.command[1])
        await db.ban_user(user_id)
        await message.reply_text(f"✅ User {user_id} has been banned!")
    except:
        await message.reply_text("❌ Invalid user ID!")

@app.on_message(filters.command("unban") & filters.user(ADMINS))
async def unban_user(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("❌ Usage: /unban <user_id>")
        return
    
    try:
        user_id = int(message.command[1])
        await db.unban_user(user_id)
        await message.reply_text(f"✅ User {user_id} has been unbanned!")
    except:
        await message.reply_text("❌ Invalid user ID!")

# ... (Add all other callback handlers: about, help, premium, etc.)

def humanbytes(size):
    if not size:
        return "0 B"
    power = 2**10
    n = 0
    units = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {units[n]}"

if __name__ == "__main__":
    print("🚀 Starting Mystream Bot with All Features...")
    app.run()
