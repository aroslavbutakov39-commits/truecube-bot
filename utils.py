import discord
from datetime import datetime, timezone
import json
import os
import re
import config

# --- Утилиты ---
def load_message_ids():
    if not os.path.exists(config.MESSAGE_STORAGE):
        return {}
    try:
        with open(config.MESSAGE_STORAGE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_message_ids(data):
    try:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        with open(config.MESSAGE_STORAGE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ ID сообщений сохранены в {config.MESSAGE_STORAGE}")
    except (PermissionError, OSError):
        fallback_dir = os.path.join(os.environ.get('TEMP', '/tmp'), 'TrueCubeBot')
        fallback_path = os.path.join(fallback_dir, 'menu_messages.json')
        try:
            os.makedirs(fallback_dir, exist_ok=True)
            with open(fallback_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"⚠️ Использую временное хранилище: {fallback_path}")
        except Exception as e:
            print(f"❌ Не удалось сохранить ID ни в основное, ни во временное хранилище: {e}")
    except Exception as e:
        print(f"❌ Ошибка сохранения ID: {e}")

async def send_or_update_message(bot, channel_id, key, embed=None, view=None):
    data = load_message_ids()
    try:
        channel = await bot.fetch_channel(channel_id)
    except Exception as e:
        print(f"❌ Ошибка получения канала {channel_id}: {e}")
        return

    message_id = data.get(key)
    if message_id:
        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(embed=embed, view=view)
            print(f"✅ Сообщение {key} обновлено в канале {channel.name}")
            return
        except discord.NotFound:
            print(f"⚠️ Сообщение {key} не найдено, отправляем новое.")
        except Exception as e:
            print(f"⚠️ Ошибка при редактировании: {e}, отправляем новое.")

    try:
        msg = await channel.send(embed=embed, view=view)
        data[key] = msg.id
        save_message_ids(data)
        print(f"✅ Новое сообщение {key} отправлено в канал {channel.name} (ID: {msg.id})")
    except Exception as e:
        print(f"❌ Не удалось отправить сообщение в канал {channel_id}: {e}")

async def log_action(bot, title, description, color=None):
    if not config.LOG_CHANNEL_ID:
        return
    if color is None:
        color = config.EMBED_COLOR
    channel = bot.get_channel(config.LOG_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))
        await channel.send(embed=embed)

# --- View и Modals ---
class ConfirmCloseView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(timeout=60)
        self.channel = channel

    @discord.ui.button(label="✅ Да, закрыть", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ Тикет закрыт.", ephemeral=True)
        try:
            await self.channel.delete(reason=f"Тикет закрыт пользователем {interaction.user}")
            await log_action(
                interaction.client,
                "🔒 Тикет закрыт",
                f"Пользователь {interaction.user.mention} закрыл тикет `{self.channel.name}`.",
                config.EMBED_COLOR
            )
        except discord.NotFound:
            pass
        except discord.Forbidden:
            print(f"⚠️ Нет прав для удаления канала {self.channel.id}")

    @discord.ui.button(label="❌ Нет, отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="✖ Закрытие тикета отменено.", view=None)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Закрыть тикет", style=discord.ButtonStyle.danger, custom_id="close_ticket_channel")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ConfirmCloseView(channel=interaction.channel)
        await interaction.response.send_message("❓ Вы точно хотите закрыть тикет?", view=view, ephemeral=True)

class ReplyViaDM(discord.ui.Modal, title="Ответить в ЛС"):
    def __init__(self, user: discord.User, source_channel: discord.TextChannel):
        super().__init__()
        self.user = user
        self.source_channel = source_channel
        self.message = discord.ui.TextInput(
            label="Сообщение",
            placeholder="Введите текст сообщения...",
            style=discord.TextStyle.paragraph,
            max_length=1000
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.user.send(f"**Ответ от поддержки {config.BOT_NAME}:**\n{self.message.value}")
        except discord.Forbidden:
            await interaction.followup.send("Не удалось отправить ЛС: у пользователя закрыты личные сообщения.", ephemeral=True)
            return

        embed = discord.Embed(
            title="💬 Ответ отправлен в ЛС",
            description=f"**От:** {interaction.user.mention}\n**Сообщение:**\n{self.message.value}",
            color=config.EMBED_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        await self.source_channel.send(embed=embed)
        await log_action(
            interaction.client,
            "💬 Ответ в ЛС",
            f"Администратор {interaction.user.mention} ответил пользователю {self.user.mention} в канале {self.source_channel.mention}.",
            config.EMBED_COLOR
        )
        await interaction.followup.send("Сообщение отправлено в ЛС.", ephemeral=True)

class DenyReasonModal(discord.ui.Modal, title="Отклонить заявку"):
    internal_reason = discord.ui.TextInput(
        label="Причина (для журнала)",
        placeholder="Например: не прошёл по возрасту",
        style=discord.TextStyle.short,
        max_length=100,
        required=False
    )
    message_to_user = discord.ui.TextInput(
        label="Сообщение пользователю",
        placeholder="Текст, который увидит заявитель...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )

    def __init__(self, channel: discord.TextChannel, applicant: discord.User):
        super().__init__()
        self.channel = channel
        self.applicant = applicant

    async def on_submit(self, interaction: discord.Interaction):
        user_msg = self.message_to_user.value.strip() or "Без дополнительных комментариев."
        internal_reason = self.internal_reason.value.strip() or "не указана"

        await interaction.response.send_message("✅ Заявка отклонена, канал удалён.", ephemeral=True)

        embed = discord.Embed(
            title="📛 Ваша заявка отклонена",
            description=(
                f"К сожалению, в этот раз вы не прошли отбор. "
                f"Спасибо за проявленный интерес.\n\n"
                f"Сообщение от администрации\n{user_msg}"
            ),
            color=config.EMBED_COLOR
        )
        if config.DENY_ICON_URL:
            embed.set_thumbnail(url=config.DENY_ICON_URL)

        try:
            await self.applicant.send(content=self.applicant.mention, embed=embed)
        except discord.Forbidden:
            pass

        await self.channel.delete(reason=f"Заявка отклонена. Причина: {internal_reason}")
        await log_action(
            interaction.client,
            "❌ Заявка отклонена",
            f"Администратор {interaction.user.mention} отклонил заявку пользователя {self.applicant.mention}. Причина: {internal_reason}",
            config.EMBED_COLOR
        )

class StaffApplicationView(discord.ui.View):
    def __init__(self, applicant: discord.User = None):
        super().__init__(timeout=None)
        self.applicant = applicant

    async def _resolve_applicant(self, interaction: discord.Interaction):
        if self.applicant is not None:
            return self.applicant
        if interaction.message and interaction.message.embeds:
            for field in interaction.message.embeds[0].fields:
                if field.name == "Пользователь":
                    match = re.search(r"\((\d+)\)", field.value)
                    if match:
                        try:
                            self.applicant = await interaction.client.fetch_user(int(match.group(1)))
                            return self.applicant
                        except Exception:
                            pass
        return None

    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success, custom_id="staff_accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id == config.MOD_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
            return

        applicant = await self._resolve_applicant(interaction)
        if not applicant:
            await interaction.response.send_message("Не удалось определить заявителя.", ephemeral=True)
            return

        channel = interaction.channel
        new_name = f"сотрудник-{applicant.name}"
        accepted_category = interaction.guild.get_channel(config.STAFF_ACCEPTED_CATEGORY_ID)

        try:
            await channel.edit(name=new_name, category=accepted_category)
        except Exception as e:
            await interaction.response.send_message(f"Ошибка при перемещении: {e}", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎉 Заявка принята!",
            description=(
                "Поздравляем! Ваша заявка на персонал была **одобрена**.\n"
                f"Теперь вы часть команды {config.BOT_NAME}!\n\n"
                "С вами свяжется администрация для дальнейших инструкций."
            ),
            color=config.EMBED_COLOR
        )
        if config.ACCEPT_ICON_URL:
            embed.set_thumbnail(url=config.ACCEPT_ICON_URL)

        try:
            await applicant.send(embed=embed)
        except discord.Forbidden:
            pass

        await log_action(
            interaction.client,
            "✅ Заявка принята",
            f"Администратор {interaction.user.mention} принял заявку пользователя {applicant.mention}. Канал перемещён в категорию сотрудников.",
            config.EMBED_COLOR
        )
        await interaction.response.send_message("✅ Заявка принята. Канал перемещён в категорию сотрудников.", ephemeral=False)
        await interaction.message.edit(view=None)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger, custom_id="staff_deny")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id == config.MOD_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
            return
        applicant = await self._resolve_applicant(interaction)
        if not applicant:
            await interaction.response.send_message("Не удалось определить заявителя.", ephemeral=True)
            return
        await interaction.response.send_modal(DenyReasonModal(channel=interaction.channel, applicant=applicant))

    @discord.ui.button(label="💬 Ответить в ЛС", style=discord.ButtonStyle.primary, custom_id="staff_reply")
    async def reply_dm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id == config.MOD_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
            return
        applicant = await self._resolve_applicant(interaction)
        if not applicant:
            await interaction.response.send_message("Не удалось определить заявителя.", ephemeral=True)
            return
        await interaction.response.send_modal(ReplyViaDM(user=applicant, source_channel=interaction.channel))

class MenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MenuSelect())

class MenuSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Как зайти на сервер", description="Пошаговая инструкция", emoji="⭐"),
            discord.SelectOption(label="Пожаловаться на игрока", description="Создать анонимно жалобу на игрока", emoji="🔍"),
            discord.SelectOption(label="Задать вопрос", description="Задать вопрос поддержке", emoji="❓"),
            discord.SelectOption(label="Наш телеграм канал", description="Какие либо вопросы через TG", emoji="📶"),
        ]
        super().__init__(
            placeholder="Выберите категорию из меню ниже",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="persistent_menu_select"
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        if selected == "Как зайти на сервер":
            await self.send_how_to_join(interaction)
        elif selected == "Пожаловаться на игрока":
            await interaction.response.send_modal(ReportModal())
        elif selected == "Задать вопрос":
            await interaction.response.send_modal(QuestionModal())
        elif selected == "Наш телеграм канал":
            await self.send_telegram_info(interaction)

    async def send_how_to_join(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Как зайти на сервер?",
            color=config.EMBED_COLOR,
            description=(
                "Все легко и просто! Для начала заходим в Minecraft\n"
                "Подходящие лаунчеры для игры: [TLauncher](https://tlauncher.ru/) / [Legacy Launcher](https://legacylauncher.ru/ru)\n"
                "Далее по желанию регистрируемся в этих лаунчерах.\n\n"
                "На нашем сервере используется версия **Minecraft** 1.21\n\n"
                "Но мы __**рекомендуем**__ играть на версии **1.21.1** для лучшей\n"
                "оптимизации игры\n\n"
                "После чего заходим в сам **Minecraft**:\n"
                "1. Нажимаем на кнопку \"Сетевая игра\"\n"
                "2. Нажимаем на кнопку \"Добавить\"\n"
                "3. Пишем в строчку \"Адрес сервера\" - Можно скопировать **IP**:\n"
                f"   ```{config.SERVER_IP}```\n\n"
                "4. Далее прохождения капчи и регистрации, после всех\n"
                "  процедур можете спокойно начать играть, **Хорошего\n настроения и время провождения!**\n\n"
                "Если есть какие либо вопросы можете обращаться в\n"
                "Поддержку-TG / Выбрать категорию **Задать вопрос**"
            )
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def send_telegram_info(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Наш телеграм канал",
            description=f"Связаться с нами: [{config.TELEGRAM_TAG}]({config.TELEGRAM_URL})",
            color=config.EMBED_COLOR
        )
        embed.add_field(name=config.BOT_NAME.upper(), value="**НАШ ТЕЛЕГРАМ КАНАЛ**", inline=False)
        embed.add_field(name="Ссылка", value=f"[Нажмите, чтобы перейти]({config.TELEGRAM_URL})", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class StaffMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Подать заявку", style=discord.ButtonStyle.success, custom_id="staff_apply_button")
    async def apply_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StaffApplicationModal())

class StaffApplicationModal(discord.ui.Modal, title="Подать заявку"):
    game_nick = discord.ui.TextInput(label="Ник в игре", placeholder="Введите ваш ник в игре", required=True, max_length=32)
    discord_contact = discord.ui.TextInput(label="Discord", placeholder="Укажите ваш Discord (микрофон обязателен!)", required=True, max_length=64)
    age = discord.ui.TextInput(label="Возраст", placeholder="Сколько вам полных лет?", required=True, max_length=3)
    hours = discord.ui.TextInput(label="Часы в день", placeholder="Сколько часов в день вы играете?", required=True, max_length=3)
    about = discord.ui.TextInput(label="О себе", placeholder="Расскажите немного о себе", style=discord.TextStyle.paragraph, required=True, max_length=1000)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category = guild.get_channel(config.STAFF_CATEGORY_ID)
        if not category:
            await interaction.followup.send("Категория для заявок не настроена.", ephemeral=True)
            return

        channel_name = f"заявка-{interaction.user.name}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        mod_role = guild.get_role(config.MOD_ROLE_ID)
        if mod_role:
            overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        try:
            channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        except Exception as e:
            await interaction.followup.send(f"Не удалось создать канал: {e}", ephemeral=True)
            return

        curator_role = guild.get_role(config.CURATOR_ROLE_ID)
        if curator_role:
            await channel.send(curator_role.mention)

        embed = discord.Embed(title="Новая заявка на персонал", color=config.EMBED_COLOR, timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Ник в игре", value=self.game_nick.value, inline=True)
        embed.add_field(name="Discord", value=self.discord_contact.value, inline=True)
        embed.add_field(name="Возраст", value=self.age.value, inline=True)
        embed.add_field(name="Часов в день", value=self.hours.value, inline=True)
        embed.add_field(name="О себе", value=self.about.value, inline=False)
        embed.add_field(name="Пользователь", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)

        view = StaffApplicationView(applicant=interaction.user)
        await channel.send(embed=embed, view=view)

        await log_action(
            interaction.client,
            "📨 Новая заявка на персонал",
            f"Пользователь {interaction.user.mention} подал заявку. Канал: {channel.mention}",
            config.EMBED_COLOR
        )

        response_embed = discord.Embed(
            title="📨 Заявка отправлена",
            description="✅ Ваша заявка на персонал успешно отправлена!\n\n**📢 Ожидайте ответа от бота в ЛС.**",
            color=config.EMBED_COLOR
        )
        await interaction.followup.send(embed=response_embed, ephemeral=True)

class QuestionModal(discord.ui.Modal, title="Задать вопрос"):
    question = discord.ui.TextInput(label="Ваш вопрос", placeholder="Введите свой вопрос", style=discord.TextStyle.paragraph, max_length=1000, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category = guild.get_channel(config.CATEGORY_ID)
        if not category:
            await interaction.followup.send("Категория не настроена.", ephemeral=True)
            return
        channel_name = f"вопрос-{interaction.user.name}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        mod_role = guild.get_role(config.MOD_ROLE_ID)
        if mod_role:
            overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        curator_role = guild.get_role(config.CURATOR_ROLE_ID)
        if curator_role:
            await channel.send(curator_role.mention)
        embed = discord.Embed(
            title="Новый вопрос",
            description="Ожидайте ответа от поддержки",
            color=config.EMBED_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Вопрос", value=self.question.value, inline=False)
        embed.add_field(name="Создано пользователем", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
        view = CloseTicketView()
        await channel.send(embed=embed, view=view)

        await log_action(
            interaction.client,
            "❓ Новый вопрос",
            f"Пользователь {interaction.user.mention} задал вопрос. Канал: {channel.mention}",
            config.EMBED_COLOR
        )

        response_embed = discord.Embed(
            title="Обращение создано",
            description=f"Вы создали обращение в {channel.mention}",
            color=config.EMBED_COLOR
        )
        await interaction.followup.send(embed=response_embed, ephemeral=True)

class ReportModal(discord.ui.Modal, title="Пожаловаться на игрока"):
    player = discord.ui.TextInput(label="Ник нарушителя", placeholder="Введите ник игрока", max_length=16, required=True)
    reason = discord.ui.TextInput(label="Причина жалобы", placeholder="Опишите нарушение", style=discord.TextStyle.paragraph, max_length=1000, required=True)
    proof = discord.ui.TextInput(label="Доказательства (ссылка)", placeholder="https://...", required=False, max_length=200)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category = guild.get_channel(config.CATEGORY_ID)
        if not category:
            await interaction.followup.send("Категория не настроена.", ephemeral=True)
            return
        channel_name = f"жалоба-{interaction.user.name}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        mod_role = guild.get_role(config.MOD_ROLE_ID)
        if mod_role:
            overwrites[mod_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        curator_role = guild.get_role(config.CURATOR_ROLE_ID)
        if curator_role:
            await channel.send(curator_role.mention)
        embed = discord.Embed(
            title="Новая жалоба на игрока",
            description="Ожидайте ответа от поддержки",
            color=config.EMBED_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Нарушитель", value=self.player.value, inline=True)
        embed.add_field(name="Причина", value=self.reason.value, inline=False)
        if self.proof.value:
            embed.add_field(name="Доказательства", value=self.proof.value, inline=False)
        embed.add_field(name="Создано пользователем", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
        view = CloseTicketView()
        await channel.send(embed=embed, view=view)

        await log_action(
            interaction.client,
            "🔍 Новая жалоба",
            f"Пользователь {interaction.user.mention} подал жалобу на игрока **{self.player.value}**. Канал: {channel.mention}",
            config.EMBED_COLOR
        )

        response_embed = discord.Embed(
            title="Жалоба создана",
            description=f"Вы создали жалобу в {channel.mention}",
            color=config.EMBED_COLOR
        )
        await interaction.followup.send(embed=response_embed, ephemeral=True)
