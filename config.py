import os

class Config:
    # Telegram Configuration
    API_ID = int(os.environ.get("API_ID", "1234567"))
    API_HASH = os.environ.get("API_HASH", "your_api_hash")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "your_bot_username")
    
    # Admins (comma separated user IDs)
    ADMINS = [int(x) for x in os.environ.get("ADMINS", "123456789").split(",")]
    BOT_OWNER = ADMINS[0] if ADMINS else 123456789
    
    # Database
    DATABASE_URL = os.environ.get("DATABASE_URL", "mongodb_url")
    
    # Channel Configuration
    BIN_CHANNEL = int(os.environ.get("BIN_CHANNEL", "-1001234567890"))
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1001234567890"))
    UPDATES_CHANNEL = os.environ.get("UPDATES_CHANNEL", "your_updates_channel")
    SUPPORT_GROUP = os.environ.get("SUPPORT_GROUP", "your_support_group")
    
    # Auto Delete Time (seconds)
    AUTO_DELETE_TIME = int(os.environ.get("AUTO_DELETE_TIME", "43200"))  # 12 hours
    
    # File Size Limits
    FREE_FILE_SIZE = int(os.environ.get("FREE_FILE_SIZE", "1073741824"))  # 1GB for free users
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", "4294967296"))    # 4GB for premium
    
    # CDN/Server URLs
    DOWNLOAD_BASE_URL = os.environ.get("DOWNLOAD_BASE_URL", "https://your-cdn.com")
    STREAM_BASE_URL = os.environ.get("STREAM_BASE_URL", "https://stream.your-domain.com")
    
    # Premium Configuration
    PREMIUM_DAILY_LIMIT = int(os.environ.get("PREMIUM_DAILY_LIMIT", "50"))
    FREE_DAILY_LIMIT = int(os.environ.get("FREE_DAILY_LIMIT", "5"))
    
    # Text Messages
    START_TEXT = """👋 Hello {}, \n\n🤖 **Welcome to {}!** \n\nI'm a powerful file streaming bot with premium features! \n\n**✨ Features:** \n✅ Free: Files up to {free_size} \n✅ Premium: Files up to {premium_size} \n✅ Direct Download Links \n✅ Streaming Links \n✅ Embed Player \n✅ Auto Cleanup \n\n**📤 Just send me any file to get started!**"""
    
    PLANS_TEXT = """💎 **Premium Plans** \n\n**✨ Free Plan:** \n• {free_size} file size limit \n• {free_daily} files per day \n• Basic support \n\n**💎 Premium Plan:** \n• {premium_size} file size limit \n• {premium_daily} files per day \n• Priority support \n• No ads \n• Early access to features \n\n**Contact @{support_group} for premium upgrades!**"""
    
    ABOUT_TEXT = """🤖 **About {}** \n\n**Version:** 2.0 \n**Developer:** @sathishsksk \n**Source:** [GitHub](https://github.com/sathishsksk/Mystream) \n\n**🚀 Features:** \n• Multi-quality streaming \n• Direct download links \n• Embed player support \n• Premium system \n• User management \n• Auto cleanup \n• MongoDB database \n• Admin controls \n• Broadcast system \n• Ban system \n• Usage statistics"""
    
    HELP_TEXT = """📖 **How to Use** \n\n1. **Send any file** (document, video, audio, photo) \n2. **Get multiple links** (direct download, stream, embed) \n3. **Share the links** with anyone \n\n**📁 Supported Files:** \n• Videos (MP4, MKV, AVI) - Up to {premium_size} \n• Audio (MP3, WAV, FLAC) - Up to {premium_size} \n• Documents (PDF, ZIP, etc.) - Up to {premium_size} \n• Images (JPG, PNG, etc.) \n\n**⚡ Commands:** \n/start - Start the bot \n/stats - Bot statistics (admin) \n/broadcast - Broadcast message (admin) \n/ban - Ban user (admin) \n/unban - Unban user (admin) \n\n**Need help?** Join @{support_group}"""
    
    @classmethod
    def format_start_text(cls, name, username):
        return cls.START_TEXT.format(
            name, username,
            free_size=humanbytes(cls.FREE_FILE_SIZE),
            premium_size=humanbytes(cls.MAX_FILE_SIZE)
        )
    
    @classmethod
    def format_plans_text(cls):
        return cls.PLANS_TEXT.format(
            free_size=humanbytes(cls.FREE_FILE_SIZE),
            free_daily=cls.FREE_DAILY_LIMIT,
            premium_size=humanbytes(cls.MAX_FILE_SIZE),
            premium_daily=cls.PREMIUM_DAILY_LIMIT,
            support_group=cls.SUPPORT_GROUP
        )
    
    @classmethod
    def format_about_text(cls, username):
        return cls.ABOUT_TEXT.format(username)
    
    @classmethod
    def format_help_text(cls):
        return cls.HELP_TEXT.format(
            premium_size=humanbytes(cls.MAX_FILE_SIZE),
            support_group=cls.SUPPORT_GROUP
        )

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
