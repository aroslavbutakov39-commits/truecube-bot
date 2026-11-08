import discord
from discord.ext import commands
from discord import app_commands
from .utils import log_action, MenuView, StaffMenuView, send_or_update_message
import config

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reply", description="Ответить пользователю в ЛС (администратор)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(user_id="ID пользователя", text="Текст сообщения")
    async def reply(self, interaction: discord.Interaction, user_id: str, text: str):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await user.send(f"**Ответ от поддержки {config.BOT_NAME}:**\n{text}")
            await interaction.response.send_message(f"✅ Сообщение отправлено пользователю {user.mention}.", ephemeral=True)
            await log_action(
                self.bot,
                "💬 Ответ в ЛС",
                f"Администратор {interaction.user.mention} ответил пользователю {user.mention} через команду /reply.",
                config.EMBED_COLOR
            )
        except ValueError:
            await interaction.response.send_message("❌ Неверный ID пользователя.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Не удалось отправить сообщение: у пользователя закрыты ЛС.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

    @app_commands.command(name="setup", description="Обновить меню вручную (админ)")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
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
        await interaction.followup.send("✅ Меню обновлены!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(General(bot))
