import discord
from discord.ext import commands
from .utils import (MenuView, StaffMenuView, CloseTicketView,
                    StaffApplicationView, send_or_update_message)
import config

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        # Установка имени и никнейма бота на TrueCube
        if self.bot.user and self.bot.user.name != config.BOT_NAME:
            try:
                await self.bot.user.edit(username=config.BOT_NAME)
                print(f"✅ Имя бота изменено на {config.BOT_NAME}")
            except Exception as e:
                print(f"⚠️ Не удалось изменить глобальное имя бота (возможно, лимит Discord): {e}")

        guild_id = config.GUILD_ID.id if hasattr(config.GUILD_ID, "id") else config.GUILD_ID
        guild = self.bot.get_guild(guild_id)
        if guild and guild.me and guild.me.display_name != config.BOT_NAME:
            try:
                await guild.me.edit(nick=config.BOT_NAME)
                print(f"✅ Никнейм бота на сервере изменён на {config.BOT_NAME}")
            except Exception as e:
                print(f"⚠️ Не удалось изменить никнейм бота на сервере: {e}")

        print(f"Бот {self.bot.user} готов!")
        await self.bot.change_presence(activity=discord.Game(name=f"Играет на {config.BOT_NAME}"))

        if not self._views_added:
            self.bot.add_view(MenuView())
            self.bot.add_view(StaffMenuView())
            self.bot.add_view(CloseTicketView())
            self.bot.add_view(StaffApplicationView(applicant=None))
            self._views_added = True

        main_embed = discord.Embed(
            title="Информация",
            description="Выберите категорию из меню ниже",
            color=config.EMBED_COLOR
        )
        await send_or_update_message(self.bot, config.MAIN_MENU_CHANNEL_ID, "main_menu", embed=main_embed, view=MenuView())

        staff_embed = discord.Embed(
            title="📋 Подать заявку на персонал",
            description=(
                "Нажмите кнопку ниже, чтобы заполнить анкету и\nподать заявку на персонал.\n\n"
                "Спасибо за интерес к нашей команде!\n\n"
                "📌 **Требования к заявке:**\n"
                "• Знание правил\n"
                "• Адекватное поведение и умение вежливо\nобщаться с игроками\n"
                "• Наличие хорошего микрофона\n\n"
                "**Ждём ваших заявок!**"
            ),
            color=config.EMBED_COLOR
        )
        staff_embed.set_footer(text=config.BOT_NAME)
        await send_or_update_message(self.bot, config.STAFF_MENU_CHANNEL_ID, "staff_menu", embed=staff_embed, view=StaffMenuView())

        await self.bot.tree.sync(guild=discord.Object(id=guild_id))
        print("Команды синхронизированы.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if isinstance(message.channel, discord.DMChannel):
            if config.LOG_CHANNEL_ID:
                log_channel = self.bot.get_channel(config.LOG_CHANNEL_ID)
                if log_channel:
                    embed = discord.Embed(
                        title="📩 Новое личное сообщение",
                        description=message.content,
                        color=config.EMBED_COLOR,
                        timestamp=message.created_at
                    )
                    embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.display_avatar.url)
                    embed.set_footer(text="Чтобы ответить, используйте /reply")
                    await log_channel.send(embed=embed)
            return
        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(Events(bot))
