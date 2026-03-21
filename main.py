import discord
from discord.ext import commands
import os
import requests
from dotenv import load_dotenv
import asyncio
import yt_dlp as youtube_dl
import subprocess
import random
import json
from aiohttp import web
import aiohttp
import threading

# ДОБАВЛЯЕМ ПУТЬ К FFMPEG
os.environ["PATH"] += os.pathsep + "C:\\ffmpeg\\bin"

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
BRIDGE_URL = "http://localhost:3001/control"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ========== HTTP СЕРВЕР ДЛЯ ПИНГОВ ==========
async def handle_ping(request):
    return web.Response(text="I'm alive!")

async def start_http_server():
    app = web.Application()
    app.router.add_get('/ping', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("✅ HTTP сервер запущен на порту 8080 (для пингов)")

# ========== АВТОПИНГ (чтобы бот не засыпал) ==========
async def self_ping():
    """Каждые 10 минут отправляет запрос к самому себе"""
    while True:
        await asyncio.sleep(600)  # 10 минут = 600 секунд
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8080/ping') as resp:
                    if resp.status == 200:
                        print("✅ Self-ping успешен")
                    else:
                        print(f"⚠️ Self-ping вернул {resp.status}")
        except Exception as e:
            print(f"❌ Ошибка self-ping: {e}")

# ========== ПЕРЕВОДЫ ==========
LANGUAGES = {
    'ru': {
        'name': 'Русский',
        'not_in_voice': '❌ Ты не в голосовом канале',
        'not_in_channel': '❌ Бот не в голосовом канале',
        'nothing_playing': '❌ Ничего не играет',
        'already_playing': '❌ Ничего не играет',
        'track_added': '✅ Добавлен в очередь: **{}**',
        'now_playing': '▶️ Сейчас играет: **{}**',
        'track_not_found': '❌ Трек не найден',
        'queue_empty': '❌ Очередь пуста',
        'queue_cleared': '✅ Очередь очищена',
        'shuffled': '🔀 Очередь перемешана!',
        'not_enough_tracks': '❌ В очереди слишком мало треков для перемешивания',
        'loop_mode': '🔄 Режим повтора: {}',
        'loop_off': 'выключен',
        'loop_one': 'один трек',
        'loop_all': 'вся очередь',
        'history_empty': '❌ История пуста',
        'volume_set': '🔊 Громкость: {}%',
        'volume_error': '❌ Громкость от 0 до 200',
        'joined': '✅ Зашёл в {}',
        'left': '👋 Пока!',
        'previous_error': '❌ Нет предыдущих треков',
        'paused': '⏸️ Пауза',
        'resumed': '▶️ Продолжаем',
        'skipped': '⏭️ Трек пропущен',
        'stopped': '👋 Остановлено и отключено',
        'language_set': '🌐 Язык изменён на: **{}**',
        'source': '⚙️ Источник',
        'repeat_mode': '🔄 Режим повтора',
        'queue_length': '📊 {} треков в очереди',
        'history_title': '📜 История',
        'queue_title': '📋 Очередь',
        'now_title': '🎵 Сейчас играет',
        'duration': '🔒 {}',
        'requested_by': 'По запросу @{}',
        'already_connected': '❌ Я уже в голосовом канале',
        'connect_error': '❌ Не удалось подключиться: {}',
        'error': '❌ Ошибка: {}',
        'track_not_found_sc': 'Трек не найден на SoundCloud, ищу на YouTube...',
    },
    'ua': {
        'name': 'Українська',
        'not_in_voice': '❌ Ти не в голосовому каналі',
        'not_in_channel': '❌ Бот не в голосовому каналі',
        'nothing_playing': '❌ Нічого не грає',
        'already_playing': '❌ Нічого не грає',
        'track_added': '✅ Додано в чергу: **{}**',
        'now_playing': '▶️ Зараз грає: **{}**',
        'track_not_found': '❌ Трек не знайдено',
        'queue_empty': '❌ Черга пуста',
        'queue_cleared': '✅ Чергу очищено',
        'shuffled': '🔀 Чергу перемішано!',
        'not_enough_tracks': '❌ У черзі занадто мало треків для перемішування',
        'loop_mode': '🔄 Режим повтору: {}',
        'loop_off': 'вимкнено',
        'loop_one': 'один трек',
        'loop_all': 'вся черга',
        'history_empty': '❌ Історія пуста',
        'volume_set': '🔊 Гучність: {}%',
        'volume_error': '❌ Гучність від 0 до 200',
        'joined': '✅ Зайшов у {}',
        'left': '👋 Бувай!',
        'previous_error': '❌ Немає попередніх треків',
        'paused': '⏸️ Пауза',
        'resumed': '▶️ Продовжуємо',
        'skipped': '⏭️ Трек пропущено',
        'stopped': '👋 Зупинено та відключено',
        'language_set': '🌐 Мову змінено на: **{}**',
        'source': '⚙️ Джерело',
        'repeat_mode': '🔄 Режим повтору',
        'queue_length': '📊 {} треків у черзі',
        'history_title': '📜 Історія',
        'queue_title': '📋 Черга',
        'now_title': '🎵 Зараз грає',
        'duration': '🔒 {}',
        'requested_by': 'На замовлення @{}',
        'already_connected': '❌ Я вже в голосовому каналі',
        'connect_error': '❌ Не вдалося підключитися: {}',
        'error': '❌ Помилка: {}',
        'track_not_found_sc': 'Трек не знайдено на SoundCloud, шукаю на YouTube...',
    },
    'en': {
        'name': 'English',
        'not_in_voice': '❌ You are not in a voice channel',
        'not_in_channel': '❌ Bot is not in a voice channel',
        'nothing_playing': '❌ Nothing is playing',
        'already_playing': '❌ Nothing is playing',
        'track_added': '✅ Added to queue: **{}**',
        'now_playing': '▶️ Now playing: **{}**',
        'track_not_found': '❌ Track not found',
        'queue_empty': '❌ Queue is empty',
        'queue_cleared': '✅ Queue cleared',
        'shuffled': '🔀 Queue shuffled!',
        'not_enough_tracks': '❌ Not enough tracks in queue to shuffle',
        'loop_mode': '🔄 Loop mode: {}',
        'loop_off': 'off',
        'loop_one': 'one track',
        'loop_all': 'all queue',
        'history_empty': '❌ History is empty',
        'volume_set': '🔊 Volume: {}%',
        'volume_error': '❌ Volume must be between 0 and 200',
        'joined': '✅ Joined {}',
        'left': '👋 Bye!',
        'previous_error': '❌ No previous tracks',
        'paused': '⏸️ Paused',
        'resumed': '▶️ Resumed',
        'skipped': '⏭️ Track skipped',
        'stopped': '👋 Stopped and disconnected',
        'language_set': '🌐 Language changed to: **{}**',
        'source': '⚙️ Source',
        'repeat_mode': '🔄 Repeat mode',
        'queue_length': '📊 {} tracks in queue',
        'history_title': '📜 History',
        'queue_title': '📋 Queue',
        'now_title': '🎵 Now playing',
        'duration': '🔒 {}',
        'requested_by': 'Requested by @{}',
        'already_connected': '❌ I am already in a voice channel',
        'connect_error': '❌ Failed to connect: {}',
        'error': '❌ Error: {}',
        'track_not_found_sc': 'Track not found on SoundCloud, searching on YouTube...',
    }
}

# ========== ХРАНЕНИЕ ЯЗЫКОВ ПОЛЬЗОВАТЕЛЕЙ ==========
user_languages = {}

def get_lang(user_id):
    return user_languages.get(user_id, 'ru')

def t(user_id, key, *args):
    lang = get_lang(user_id)
    text = LANGUAGES[lang].get(key, key)
    if args:
        return text.format(*args)
    return text

# ========== КНОПКИ ДЛЯ ВЫБОРА ЯЗЫКА ==========
class LanguageSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Русский", value="ru", description="Русский язык", emoji="🐷"),
            discord.SelectOption(label="Українська", value="ua", description="Українська мова", emoji="🇺🇦"),
            discord.SelectOption(label="English", value="en", description="English language", emoji="🇺🇸"),
        ]
        super().__init__(placeholder="Выберите язык / Виберіть мову / Choose language", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_languages[interaction.user.id] = self.values[0]
        await interaction.response.send_message(t(interaction.user.id, 'language_set', LANGUAGES[self.values[0]]['name']), ephemeral=True)

class LanguageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(LanguageSelect())

# ========== НАСТРОЙКИ ДЛЯ YOUTUBE-DL ==========
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'writethumbnail': True,
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title', 'Unknown track')
        self.url = data.get('webpage_url', data.get('url', ''))
        self.source_name = data.get('extractor', 'unknown')
        self.thumbnail = data.get('thumbnail')
        duration = data.get('duration')
        self.duration = duration if duration is not None else 0

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        
        ytdl_opts = ytdl_format_options.copy()
        ytdl_opts['format'] = 'bestaudio'
        ytdl_temp = youtube_dl.YoutubeDL(ytdl_opts)
        
        try:
            data = await loop.run_in_executor(None, lambda: ytdl_temp.extract_info(url, download=not stream))
        except Exception as e:
            print(f"Error extracting: {e}")
            ytdl_temp = youtube_dl.YoutubeDL({'format': 'bestaudio', 'quiet': True, 'no_warnings': True})
            data = await loop.run_in_executor(None, lambda: ytdl_temp.extract_info(f"ytsearch:{url}", download=False))
            if 'entries' in data and data['entries']:
                data = data['entries'][0]
            else:
                raise Exception("Track not found")
        
        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data.get('url') if stream else ytdl_temp.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
    
    def format_duration(self):
        if not self.duration or self.duration <= 0:
            return "0:00"
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        return f"{minutes}:{seconds:02d}"
    # ========== КНОПКИ УПРАВЛЕНИЯ МУЗЫКОЙ ==========
class MusicControls(discord.ui.View):
    def __init__(self, bot, guild_id, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your music!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label='⏮️', style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        music_cog = self.bot.get_cog('Music')
        if music_cog:
            await music_cog.previous(interaction)

    @discord.ui.button(label='⏯️', style=discord.ButtonStyle.primary)
    async def play_pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        music_cog = self.bot.get_cog('Music')
        if music_cog:
            await music_cog.play_pause(interaction)

    @discord.ui.button(label='⏭️', style=discord.ButtonStyle.secondary)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        music_cog = self.bot.get_cog('Music')
        if music_cog:
            await music_cog.skip(interaction)

    @discord.ui.button(label='⏹️', style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        music_cog = self.bot.get_cog('Music')
        if music_cog:
            await music_cog.stop(interaction)

# ========== ПАНЕЛЬ УПРАВЛЕНИЯ ТВОИМ ПРИЛОЖЕНИЕМ ==========
class PlayerView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.guild_id = guild_id

    async def send_command(self, command: str):
        try:
            response = requests.post(BRIDGE_URL, json={'command': command}, timeout=1.5)
            return response.status_code == 200
        except:
            return False

    @discord.ui.button(label='⏮️', style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if await self.send_command('previous'):
            await interaction.followup.send("✅ Предыдущий трек", ephemeral=True)
        else:
            await interaction.followup.send("❌ Приложение не запущено", ephemeral=True)

    @discord.ui.button(label='⏯️', style=discord.ButtonStyle.primary)
    async def play_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if await self.send_command('play'):
            await interaction.followup.send("✅ Play/Pause", ephemeral=True)
        else:
            await interaction.followup.send("❌ Приложение не запущено", ephemeral=True)

    @discord.ui.button(label='⏭️', style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if await self.send_command('next'):
            await interaction.followup.send("✅ Следующий трек", ephemeral=True)
        else:
            await interaction.followup.send("❌ Приложение не запущено", ephemeral=True)

# ========== ПОИСК ==========
class SearchService:
    async def detect_source(self, query):
        if 'soundcloud.com' in query:
            return 'soundcloud_link'
        elif 'youtube.com' in query or 'youtu.be' in query:
            return 'youtube_link'
        else:
            return 'search'
    
    async def resolve_query(self, query):
        source_type = await self.detect_source(query)
        
        if source_type == 'soundcloud_link':
            return query
        if source_type == 'youtube_link':
            return query
        if source_type == 'search':
            return f"scsearch:{query}"

# ========== МУЗЫКАЛЬНЫЙ МОДУЛЬ ==========
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.players = {}
        self.current_track = {}
        self.history = {}
        self.loop_mode = {}
        self.search_service = SearchService()
        self.control_messages = {}

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    def get_history(self, guild_id):
        if guild_id not in self.history:
            self.history[guild_id] = []
        return self.history[guild_id]

    def get_loop_mode(self, guild_id):
        return self.loop_mode.get(guild_id, 'off')

    def get_loop_text(self, user_id, mode):
        if mode == 'off':
            return t(user_id, 'loop_off')
        elif mode == 'one':
            return t(user_id, 'loop_one')
        else:
            return t(user_id, 'loop_all')

    async def send_controls(self, interaction: discord.Interaction, source: YTDLSource):
        loop_emoji = "🔁" if self.get_loop_mode(interaction.guild.id) == 'all' else "🔂" if self.get_loop_mode(interaction.guild.id) == 'one' else "➡️"
        
        embed = discord.Embed(
            title=t(interaction.user.id, 'now_title'),
            description=f"**{source.title}**",
            color=0xff5500
        )
        embed.add_field(name=t(interaction.user.id, 'source'), value=source.source_name.capitalize(), inline=True)
        embed.add_field(name=t(interaction.user.id, 'repeat_mode'), value=loop_emoji, inline=True)
        embed.set_footer(text=f"{t(interaction.user.id, 'duration', source.format_duration())} | {t(interaction.user.id, 'queue_length', len(self.get_queue(interaction.guild.id)))}")
        if source.thumbnail:
            embed.set_thumbnail(url=source.thumbnail)
        
        view = MusicControls(self.bot, interaction.guild.id, interaction.user.id)
        
        msg = await interaction.followup.send(embed=embed, view=view)
        self.control_messages[interaction.guild.id] = msg

    async def update_controls(self, interaction: discord.Interaction, source: YTDLSource):
        if interaction.guild.id in self.control_messages:
            msg = self.control_messages[interaction.guild.id]
            loop_emoji = "🔁" if self.get_loop_mode(interaction.guild.id) == 'all' else "🔂" if self.get_loop_mode(interaction.guild.id) == 'one' else "➡️"
            
            embed = discord.Embed(
                title=t(interaction.user.id, 'now_title'),
                description=f"**{source.title}**",
                color=0xff5500
            )
            embed.add_field(name=t(interaction.user.id, 'source'), value=source.source_name.capitalize(), inline=True)
            embed.add_field(name=t(interaction.user.id, 'repeat_mode'), value=loop_emoji, inline=True)
            embed.set_footer(text=f"{t(interaction.user.id, 'duration', source.format_duration())} | {t(interaction.user.id, 'queue_length', len(self.get_queue(interaction.guild.id)))}")
            if source.thumbnail:
                embed.set_thumbnail(url=source.thumbnail)
            
            try:
                await msg.edit(embed=embed)
            except:
                pass

    async def play_next(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild.id)
        history = self.get_history(interaction.guild.id)
        loop_mode = self.get_loop_mode(interaction.guild.id)
        
        if interaction.guild.id in self.current_track:
            history.append(self.current_track[interaction.guild.id])
        
        if queue:
            next_track = queue.pop(0)
            player = interaction.guild.voice_client
            source = await YTDLSource.from_url(next_track, loop=self.bot.loop, stream=True)
            player.play(source, after=lambda e: self.bot.loop.create_task(self.play_next(interaction)))
            self.players[interaction.guild.id] = player
            self.current_track[interaction.guild.id] = source
            await self.update_controls(interaction, source)
        elif loop_mode == 'one' and interaction.guild.id in self.current_track:
            source = self.current_track[interaction.guild.id]
            player = interaction.guild.voice_client
            new_source = await YTDLSource.from_url(source.url, loop=self.bot.loop, stream=True)
            player.play(new_source, after=lambda e: self.bot.loop.create_task(self.play_next(interaction)))
            self.current_track[interaction.guild.id] = new_source
            await self.update_controls(interaction, new_source)
        elif loop_mode == 'all' and history:
            self.queues[interaction.guild.id] = [track.url for track in history]
            self.history[interaction.guild.id] = []
            await self.play_next(interaction)

    @discord.app_commands.command(name="play", description="Воспроизвести трек")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        
        if not interaction.user.voice:
            return await interaction.followup.send(t(interaction.user.id, 'not_in_voice'), ephemeral=True)
        
        if not interaction.guild.voice_client:
            try:
                await interaction.user.voice.channel.connect()
            except Exception as e:
                return await interaction.followup.send(t(interaction.user.id, 'connect_error', str(e)), ephemeral=True)
        
        player = interaction.guild.voice_client
        queue = self.get_queue(interaction.guild.id)
        
        try:
            search_query = await self.search_service.resolve_query(query)
            
            try:
                source = await YTDLSource.from_url(search_query, loop=self.bot.loop, stream=True)
            except Exception as e:
                print(f"SoundCloud not found: {e}")
                await interaction.followup.send(t(interaction.user.id, 'track_not_found_sc'), ephemeral=True)
                source = await YTDLSource.from_url(f"ytsearch:{query}", loop=self.bot.loop, stream=True)
            
            if player.is_playing():
                queue.append(search_query)
                await interaction.followup.send(t(interaction.user.id, 'track_added', source.title), ephemeral=True)
            else:
                player.play(source, after=lambda e: self.bot.loop.create_task(self.play_next(interaction)))
                self.players[interaction.guild.id] = player
                self.current_track[interaction.guild.id] = source
                await self.send_controls(interaction, source)
                
        except Exception as e:
            await interaction.followup.send(t(interaction.user.id, 'error', str(e)), ephemeral=True)

    @discord.app_commands.command(name="queue", description="Показать очередь")
    async def queue_cmd(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild.id)
        if not queue:
            return await interaction.response.send_message(t(interaction.user.id, 'queue_empty'), ephemeral=True)
        
        embed = discord.Embed(title=t(interaction.user.id, 'queue_title'), color=0xff5500)
        for i, track in enumerate(queue[:10], 1):
            embed.add_field(name=f"{i}.", value=track, inline=False)
        
        if len(queue) > 10:
            embed.set_footer(text=f"{t(interaction.user.id, 'queue_length', len(queue))}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="clear", description="Очистить очередь")
    async def clear(self, interaction: discord.Interaction):
        self.queues[interaction.guild.id] = []
        await interaction.response.send_message(t(interaction.user.id, 'queue_cleared'), ephemeral=True)

    @discord.app_commands.command(name="shuffle", description="Перемешать очередь")
    async def shuffle(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild.id)
        if len(queue) < 2:
            return await interaction.response.send_message(t(interaction.user.id, 'not_enough_tracks'), ephemeral=True)
        
        random.shuffle(queue)
        await interaction.response.send_message(t(interaction.user.id, 'shuffled'), ephemeral=True)

    @discord.app_commands.command(name="loop", description="Режим повтора (off/one/all)")
    async def loop(self, interaction: discord.Interaction, mode: str):
        if mode not in ['off', 'one', 'all']:
            return await interaction.response.send_message("❌ Режимы: off, one, all", ephemeral=True)
        
        self.loop_mode[interaction.guild.id] = mode
        await interaction.response.send_message(t(interaction.user.id, 'loop_mode', self.get_loop_text(interaction.user.id, mode)), ephemeral=True)
        
        if interaction.guild.id in self.current_track:
            await self.update_controls(interaction, self.current_track[interaction.guild.id])

    @discord.app_commands.command(name="history", description="Показать историю")
    async def history_cmd(self, interaction: discord.Interaction):
        history = self.get_history(interaction.guild.id)
        if not history:
            return await interaction.response.send_message(t(interaction.user.id, 'history_empty'), ephemeral=True)
        
        embed = discord.Embed(title=t(interaction.user.id, 'history_title'), color=0xff5500)
        for i, track in enumerate(history[-10:], 1):
            embed.add_field(name=f"{i}.", value=track.title, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="now", description="Показать текущий трек")
    async def now(self, interaction: discord.Interaction):
        if interaction.guild.id not in self.current_track:
            return await interaction.response.send_message(t(interaction.user.id, 'nothing_playing'), ephemeral=True)
        
        source = self.current_track[interaction.guild.id]
        embed = discord.Embed(
            title=t(interaction.user.id, 'now_title'),
            description=f"**{source.title}**",
            color=0xff5500
        )
        embed.add_field(name=t(interaction.user.id, 'source'), value=source.source_name.capitalize(), inline=True)
        embed.set_footer(text=t(interaction.user.id, 'duration', source.format_duration()))
        if source.thumbnail:
            embed.set_thumbnail(url=source.thumbnail)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="volume", description="Изменить громкость (0-200)")
    async def volume(self, interaction: discord.Interaction, level: int):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message(t(interaction.user.id, 'not_in_channel'), ephemeral=True)
        
        if level < 0 or level > 200:
            return await interaction.response.send_message(t(interaction.user.id, 'volume_error'), ephemeral=True)
        
        player = interaction.guild.voice_client
        player.source.volume = level / 100
        await interaction.response.send_message(t(interaction.user.id, 'volume_set', level), ephemeral=True)

    @discord.app_commands.command(name="join", description="Зайти в голосовой канал")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message(t(interaction.user.id, 'not_in_voice'), ephemeral=True)
        
        if interaction.guild.voice_client:
            return await interaction.response.send_message(t(interaction.user.id, 'already_connected'), ephemeral=True)
        
        await interaction.user.voice.channel.connect()
        await interaction.response.send_message(t(interaction.user.id, 'joined', interaction.user.voice.channel.name), ephemeral=True)

    @discord.app_commands.command(name="leave", description="Выйти из голосового канала")
    async def leave(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message(t(interaction.user.id, 'not_in_channel'), ephemeral=True)
        
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(t(interaction.user.id, 'left'), ephemeral=True)

    async def play_pause(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message(t(interaction.user.id, 'not_in_channel'), ephemeral=True)
        
        player = interaction.guild.voice_client
        if player.is_playing():
            player.pause()
            await interaction.response.send_message(t(interaction.user.id, 'paused'), ephemeral=True)
        elif player.is_paused():
            player.resume()
            await interaction.response.send_message(t(interaction.user.id, 'resumed'), ephemeral=True)
        else:
            await interaction.response.send_message(t(interaction.user.id, 'nothing_playing'), ephemeral=True)

    async def skip(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message(t(interaction.user.id, 'not_in_channel'), ephemeral=True)
        
        player = interaction.guild.voice_client
        if player.is_playing():
            player.stop()
            await interaction.response.send_message(t(interaction.user.id, 'skipped'), ephemeral=True)
        else:
            await interaction.response.send_message(t(interaction.user.id, 'nothing_playing'), ephemeral=True)

    async def stop(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message(t(interaction.user.id, 'not_in_channel'), ephemeral=True)
        
        player = interaction.guild.voice_client
        self.queues[interaction.guild.id] = []
        self.players[interaction.guild.id] = None
        self.current_track[interaction.guild.id] = None
        player.stop()
        await player.disconnect()
        if interaction.guild.id in self.control_messages:
            await self.control_messages[interaction.guild.id].delete()
            del self.control_messages[interaction.guild.id]
        await interaction.response.send_message(t(interaction.user.id, 'stopped'), ephemeral=True)

    async def previous(self, interaction: discord.Interaction):
        history = self.get_history(interaction.guild.id)
        if not history:
            return await interaction.response.send_message(t(interaction.user.id, 'previous_error'), ephemeral=True)
        
        previous_track = history.pop()
        queue = self.get_queue(interaction.guild.id)
        queue.insert(0, previous_track.url)
        await self.skip(interaction)

# ========== ЗАПУСК ==========
async def main():
    # Запускаем HTTP сервер для пингов
    await start_http_server()
    
    # Запускаем self-ping в фоне
    asyncio.create_task(self_ping())
    
    # Запускаем бота
    await bot.start(TOKEN)

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    await bot.add_cog(Music(bot))
    try:
        synced = await bot.tree.sync()
        print(f"✅ Синхронизировано {len(synced)} команд")
        for cmd in synced:
            print(f"   /{cmd.name}")
    except Exception as e:
        print(f"❌ Ошибка синхронизации: {e}")

@bot.tree.command(name="player", description="Показать панель управления плеером")
async def player(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎵 SoundCloud Remote",
        description="Управляй плеером через кнопки",
        color=0xff5500
    )
    await interaction.response.send_message(
        embed=embed,
        view=PlayerView(bot, interaction.guild.id),
        ephemeral=True
    )

@bot.tree.command(name="language", description="Выбрать язык / Choose language / Обрати мову")
async def language(interaction: discord.Interaction):
    view = LanguageView()
    await interaction.response.send_message("🌐 Выберите язык / Choose language / Виберіть мову:", view=view, ephemeral=True)

if __name__ == "__main__":
    # Запускаем всё вместе
    asyncio.run(main())