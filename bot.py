import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp
import datetime
import io
from obfuscator import LuaObfuscator

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = "MTQ4NzEyMTkwNjgwODI2MjgyOQ.GdRT-F.s5CQZTlY8wPZBijno-Wz67Pg9o2GOeNFNZ-UA4"          # Token do bot
WEBHOOK_URL  "https://discord.com/api/webhooks/1487156040058273803/qkpXAv7Wn7NannrA0m1q00deI-bZVmrrfFA8LjcrTJUMZ2ijLezeJWNZhQ9SBu7EKlRS"  # URL do webhook para logs
PREFIX = "!"

# ─── BOT SETUP ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)
tree = bot.tree
obf = LuaObfuscator()

# ─── WEBHOOK LOGGER ───────────────────────────────────────────────────────────
async def send_webhook_log(user, guild, level, stats):
    if not WEBHOOK_URL or WEBHOOK_URL == "https://discord.com/api/webhooks/1487156040058273803/qkpXAv7Wn7NannrA0m1q00deI-bZVmrrfFA8LjcrTJUMZ2ijLezeJWNZhQ9SBu7EKlRS":
        return
    nivel_emoji = {1: "🟢", 2: "🟡", 3: "🔴"}
    nivel_nome  = {1: "Leve", 2: "Médio", 3: "Máximo"}
    embed = {
        "title": "🔒 Script Ofuscado",
        "color": 0x00FFFF,
        "fields": [
            {"name": "👤 Usuário",  "value": f"`{user.name}` (`{user.id}`)",            "inline": True},
            {"name": "🏠 Servidor", "value": f"`{guild.name if guild else 'DM'}`",       "inline": True},
            {"name": "📊 Nível",    "value": f"{nivel_emoji[level]} {nivel_nome[level]}","inline": True},
            {"name": "📏 Original", "value": f"`{stats['original_size']} chars`",         "inline": True},
            {"name": "📦 Ofuscado", "value": f"`{stats['obfuscated_size']} chars`",       "inline": True},
            {"name": "🔄 Aumento",  "value": f"`+{stats['increase']}%`",                  "inline": True},
            {"name": "🔤 Vars",     "value": f"`{stats['vars_renamed']}`",                "inline": True},
            {"name": "🔡 Strings",  "value": f"`{stats['strings_encoded']}`",             "inline": True},
            {"name": "🗑️ Junk",    "value": f"`{stats['junk_added']} blocos`",           "inline": True},
        ],
        "footer": {"text": "ULTRAHUB Obfuscator • by guyscript & darkzinlindinn"},
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(WEBHOOK_URL, json={"username": "ULTRAHUB Logger", "embeds": [embed]})
    except Exception as e:
        print(f"[WEBHOOK ERROR] {e}")

# ─── VIEW: BOTÕES DE NÍVEL ────────────────────────────────────────────────────
class NivelView(discord.ui.View):
    def __init__(self, script: str, user_id: int, filename: str):
        super().__init__(timeout=60)
        self.script = script
        self.user_id = user_id
        self.filename = filename

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Apenas quem usou o comando pode escolher!", ephemeral=True)
            return False
        return True

    async def processar(self, interaction: discord.Interaction, nivel: int):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        nivel_nome = {1: "🟢 Leve", 2: "🟡 Médio", 3: "🔴 Máximo"}

        proc_embed = discord.Embed(
            title="⚙️ Ofuscando script...",
            description=f"**Nível:** {nivel_nome[nivel]}\n\n```\n[▓▓▓▓▓▓▓░░░] Processando...\n```",
            color=0xFFAA00
        )
        proc_embed.set_footer(text="ULTRAHUB Obfuscator • by guyscript & darkzinlindinn")
        proc_msg = await interaction.followup.send(embed=proc_embed)
        await asyncio.sleep(1.5)

        try:
            resultado = obf.obfuscate(self.script, level=nivel)
            stats = obf.get_stats(self.script, resultado)

            file = discord.File(
                fp=io.BytesIO(resultado.encode("utf-8")),
                filename="codigo_obfuscado.lua"
            )

            success_embed = discord.Embed(
                title="✅ Ofuscação Concluída!",
                description=f"**Nível aplicado:** {nivel_nome[nivel]}\n📥 Arquivo: `codigo_obfuscado.lua`",
                color=0x00FF88
            )
            success_embed.add_field(name="📏 Original", value=f"`{stats['original_size']} chars`",   inline=True)
            success_embed.add_field(name="📦 Ofuscado", value=f"`{stats['obfuscated_size']} chars`", inline=True)
            success_embed.add_field(name="🔄 Aumento",  value=f"`+{stats['increase']}%`",            inline=True)
            success_embed.add_field(name="🔤 Vars",     value=f"`{stats['vars_renamed']}`",          inline=True)
            success_embed.add_field(name="🔡 Strings",  value=f"`{stats['strings_encoded']}`",       inline=True)
            success_embed.add_field(name="🗑️ Junk",    value=f"`{stats['junk_added']} blocos`",     inline=True)
            success_embed.set_footer(text="ULTRAHUB Obfuscator • by guyscript & darkzinlindinn")

            await proc_msg.delete()
            await interaction.channel.send(embed=success_embed, file=file)
            await send_webhook_log(interaction.user, interaction.guild, nivel, stats)

        except Exception as e:
            err_embed = discord.Embed(
                title="❌ Erro na Ofuscação",
                description=f"```{str(e)[:500]}```",
                color=0xFF4444
            )
            await proc_msg.edit(embed=err_embed)

        self.stop()

    @discord.ui.button(label="🟢 Nível 1 — Leve",   style=discord.ButtonStyle.success, row=0)
    async def nivel1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.processar(interaction, 1)

    @discord.ui.button(label="🟡 Nível 2 — Médio",  style=discord.ButtonStyle.primary, row=0)
    async def nivel2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.processar(interaction, 2)

    @discord.ui.button(label="🔴 Nível 3 — Máximo", style=discord.ButtonStyle.danger,  row=0)
    async def nivel3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.processar(interaction, 3)

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary, row=1)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(title="❌ Cancelado", description="Ofuscação cancelada.", color=0x888888),
            view=self
        )
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

# ─── SLASH COMMAND: /obfuscar ─────────────────────────────────────────────────
@tree.command(name="obfuscar", description="🔒 Envie um arquivo .lua ou .txt para ofuscar")
async def obfuscar(interaction: discord.Interaction):

    pedir_embed = discord.Embed(
        title="🔒 ULTRAHUB Obfuscator",
        description=(
            "📎 **Envie seu arquivo agora!**\n\n"
            "Formatos aceitos: `.lua` `.txt`\n"
            "Tamanho máximo: **50.000 caracteres**\n\n"
            "*Aguardando por 60 segundos...*"
        ),
        color=0x00FFFF
    )
    pedir_embed.set_footer(text="ULTRAHUB Obfuscator • by guyscript & darkzinlindinn")
    await interaction.response.send_message(embed=pedir_embed)

    def check(m: discord.Message):
        return (
            m.author.id == interaction.user.id and
            m.channel.id == interaction.channel.id and
            len(m.attachments) > 0
        )

    try:
        msg = await bot.wait_for("message", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await interaction.followup.send(embed=discord.Embed(
            title="⏰ Tempo esgotado",
            description="Você demorou demais. Use `/obfuscar` novamente.",
            color=0xFF4444
        ))
        return

    attachment = msg.attachments[0]

    if not attachment.filename.endswith((".lua", ".txt")):
        await interaction.followup.send(embed=discord.Embed(
            title="❌ Formato inválido",
            description="Apenas arquivos `.lua` ou `.txt` são aceitos.",
            color=0xFF4444
        ))
        return

    try:
        raw = await attachment.read()
        script = raw.decode("utf-8", errors="ignore").strip()
    except Exception:
        await interaction.followup.send("❌ Não foi possível ler o arquivo.")
        return

    if not script:
        await interaction.followup.send("❌ O arquivo está vazio.")
        return

    if len(script) > 50000:
        await interaction.followup.send("❌ Script muito grande! Máximo: 50.000 caracteres.")
        return

    opcoes_embed = discord.Embed(
        title="⚙️ Escolha o Nível de Ofuscação",
        description=(
            f"📄 **Arquivo:** `{attachment.filename}`\n"
            f"📏 **Tamanho:** `{len(script)} chars`\n\n"
            "🟢 **Nível 1 — Leve**\n"
            "└ Remove comentários, renomeia vars, codifica strings\n\n"
            "🟡 **Nível 2 — Médio**\n"
            "└ Nível 1 + ofusca números + injeta código lixo\n\n"
            "🔴 **Nível 3 — Máximo**\n"
            "└ Nível 2 + encapsula em decoder base64 custom\n\n"
            "*Clique no botão desejado abaixo:*"
        ),
        color=0x00FFFF
    )
    opcoes_embed.set_footer(text="ULTRAHUB Obfuscator • by guyscript & darkzinlindinn")

    view = NivelView(script=script, user_id=interaction.user.id, filename=attachment.filename)
    await interaction.followup.send(embed=opcoes_embed, view=view)

# ─── SLASH COMMAND: /help ─────────────────────────────────────────────────────
@tree.command(name="help", description="📖 Como usar o ULTRAHUB Obfuscator")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔒 ULTRAHUB Obfuscator — Help",
        description="Bot para ofuscação de scripts Lua do Roblox.",
        color=0x00FFFF
    )
    embed.add_field(
        name="</obfuscar:0>",
        value=(
            "1️⃣ Use o comando `/obfuscar`\n"
            "2️⃣ Envie seu arquivo `.lua` ou `.txt`\n"
            "3️⃣ Escolha o nível clicando nos botões\n"
            "4️⃣ Baixe o arquivo `codigo_obfuscado.lua`"
        ),
        inline=False
    )
    embed.add_field(
        name="Níveis",
        value=(
            "🟢 **1 — Leve:** Renomeia vars + hex strings\n"
            "🟡 **2 — Médio:** + números + código lixo\n"
            "🔴 **3 — Máximo:** + wrapper base64 decoder"
        ),
        inline=False
    )
    embed.set_footer(text="ULTRAHUB Obfuscator • by guyscript & darkzinlindinn")
    await interaction.response.send_message(embed=embed)

# ─── EVENTS ───────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await tree.sync()
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="🔒 ULTRAHUB Obfuscator"
        )
    )
    print(f"[ULTRAHUB] Bot online como {bot.user}")
    print(f"[ULTRAHUB] Slash commands sincronizados!")

# ─── RUN ──────────────────────────────────────────────────────────────────────
bot.run(TOKEN)
