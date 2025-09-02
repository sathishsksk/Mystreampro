import motor.motor_asyncio
import datetime
from typing import List, Dict, Any

class Database:
    def __init__(self, uri: str, database_name: str):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.users = self.db.users
        self.files = self.db.files
        self.premium = self.db.premium
    
    # User Management
    async def add_user(self, id: int):
        user = {
            "id": id,
            "join_date": datetime.datetime.utcnow(),
            "last_active": datetime.datetime.utcnow(),
            "is_banned": False,
            "is_verified": False,
            "is_premium": False,
            "premium_until": None,
            "daily_usage": 0,
            "last_reset": datetime.datetime.utcnow().date()
        }
        await self.users.insert_one(user)
    
    async def is_user_exist(self, id: int) -> bool:
        user = await self.users.find_one({'id': id})
        return bool(user)
    
    async def get_all_users(self) -> List[int]:
        users = []
        async for user in self.users.find({}):
            users.append(user['id'])
        return users
    
    async def total_users_count(self) -> int:
        return await self.users.count_documents({})
    
    async def ban_user(self, user_id: int):
        await self.users.update_one(
            {'id': user_id},
            {'$set': {'is_banned': True}}
        )
    
    async def unban_user(self, user_id: int):
        await self.users.update_one(
            {'id': user_id},
            {'$set': {'is_banned': False}}
        )
    
    async def is_banned(self, user_id: int) -> bool:
        user = await self.users.find_one({'id': user_id})
        return user.get('is_banned', False) if user else False
    
    # Premium Management
    async def upgrade_premium(self, user_id: int, days: int):
        premium_until = datetime.datetime.utcnow() + datetime.timedelta(days=days)
        await self.users.update_one(
            {'id': user_id},
            {'$set': {
                'is_premium': True,
                'premium_until': premium_until
            }}
        )
    
    async def is_premium(self, user_id: int) -> bool:
        user = await self.users.find_one({'id': user_id})
        if not user:
            return False
        
        if user.get('is_premium', False) and user.get('premium_until'):
            if user['premium_until'] > datetime.datetime.utcnow():
                return True
            else:
                # Premium expired
                await self.users.update_one(
                    {'id': user_id},
                    {'$set': {'is_premium': False}}
                )
                return False
        return False
    
    async def premium_users_count(self) -> int:
        return await self.users.count_documents({'is_premium': True})
    
    # File Management
    async def add_file_record(self, file_id: str, file_name: str, file_size: int, mime_type: str,
                            bin_message_id: int, direct_link: str, stream_link: str, embed_link: str, 
                            user_id: int, premium: bool):
        file_record = {
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "mime_type": mime_type,
            "bin_message_id": bin_message_id,
            "direct_link": direct_link,
            "stream_link": stream_link,
            "embed_link": embed_link,
            "user_id": user_id,
            "is_premium": premium,
            "upload_date": datetime.datetime.utcnow(),
            "access_count": 0,
            "last_accessed": datetime.datetime.utcnow()
        }
        await self.files.insert_one(file_record)
        
        # Update user daily usage
        await self.users.update_one(
            {'id': user_id},
            {'$inc': {'daily_usage': 1}}
        )
    
    async def get_file_by_id(self, file_id: str):
        return await self.files.find_one({'file_id': file_id})
    
    async def get_user_files(self, user_id: int, limit: int = 50):
        files = []
        async for file in self.files.find({'user_id': user_id}).sort('upload_date', -1).limit(limit):
            files.append(file)
        return files
    
    async def total_files_count(self) -> int:
        return await self.files.count_documents({})
    
    async def increment_access_count(self, file_id: str):
        await self.files.update_one(
            {'file_id': file_id},
            {'$inc': {'access_count': 1}, '$set': {'last_accessed': datetime.datetime.utcnow()}}
        )
    
    async def delete_file(self, bin_message_id: int):
        await self.files.delete_one({'bin_message_id': bin_message_id})
    
    # Usage Management
    async def reset_daily_usage(self):
        """Reset daily usage for all users (run daily via cron)"""
        await self.users.update_many(
            {},
            {'$set': {'daily_usage': 0, 'last_reset': datetime.datetime.utcnow().date()}}
        )
    
    async def get_daily_usage(self, user_id: int) -> int:
        user = await self.users.find_one({'id': user_id})
        if user and user.get('last_reset') == datetime.datetime.utcnow().date():
            return user.get('daily_usage', 0)
        return 0
    
    async def can_upload(self, user_id: int) -> bool:
        user = await self.users.find_one({'id': user_id})
        if not user:
            return False
        
        is_premium = await self.is_premium(user_id)
        daily_limit = Config.PREMIUM_DAILY_LIMIT if is_premium else Config.FREE_DAILY_LIMIT
        daily_usage = await self.get_daily_usage(user_id)
        
        return daily_usage < daily_limit
