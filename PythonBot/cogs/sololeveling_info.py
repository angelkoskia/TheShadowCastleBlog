import discord
from discord.ext import commands
from utils.theme_utils import get_user_theme_colors

class SoloLevelingInfoCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _create_base_embed(self, ctx, title, description=None, color_type='info'):
        user_id = str(ctx.author.id)
        colors = get_user_theme_colors(user_id)
        embed_color = discord.Color(colors.get(color_type, colors['primary']))

        embed = discord.Embed(
            title=title,
            description=description,
            color=embed_color
        )
        embed.set_footer(text="Information from Solo Leveling Wiki | Data may be simplified.")
        return embed

    @commands.command(name='weaponsinfo', aliases=['wepinfo', 'weapon'])
    async def weapons_info(self, ctx):
        """Displays information about weapons in Solo Leveling."""
        embed = self._create_base_embed(ctx, "🗡️ Weapons & Equipment")
        
        embed.add_field(
            name="General Finds",
            value="Hunters typically find equipment like mana crystals, artifacts, and special weapons inside dungeons.",
            inline=False
        )
        embed.add_field(
            name="Notable Drops",
            value=(
                "**Baruka's Dagger:** An S-Rank ice-elf weapon taken from the boss Baruka.\n"
                "[Learn more about Baruka's Dagger](https://solo-leveling.fandom.com/wiki/Baruka%27s_Dagger)"
            ),
            inline=False
        )
        embed.add_field(
            name="Sources",
            value=(
                "[GameFAQs](https://gamefaqs.gamespot.com)\n"
                "[Solo Leveling Wiki - Fandom](https://solo-leveling.fandom.com)\n"
                "[Wikipedia](https://en.wikipedia.org)"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name='bossinfo', aliases=['bosses', 'eventmonsters'])
    async def boss_info(self, ctx):
        """Displays information about Event Monsters and Dungeon Bosses."""
        embed = self._create_base_embed(ctx, "👹 Event Monsters & Dungeon Bosses")
        
        embed.add_field(
            name="Bosses Overview",
            value="Bosses are elite monsters at the end of each dungeon. Defeating one closes the gate.",
            inline=False
        )
        embed.add_field(
            name="Baruka",
            value=(
                "S-Rank Ice-Elf leader and boss of the Red Gate in the training exercise arc. "
                "He engaged Jinwoo and his shadows; despite being individually stronger, he was ultimately defeated through strategic teamwork and shadow extraction.\n"
                "[More on Baruka](https://solo-leveling.fandom.com/wiki/Baruka)"
            ),
            inline=False
        )
        embed.add_field(
            name="Other Bosses",
            value="Include ice bears, ice-elves, yetis, etc., especially inside the Red Gate arc.",
            inline=False
        )
        embed.add_field(
            name="Sources",
            value=(
                "[Solo Leveling Wiki - Fandom](https://solo-leveling.fandom.com)"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name='gatesinfo', aliases=['gateinfo', 'slgates'])
    async def gates_info(self, ctx):
        """Displays information about Normal and Red Gates."""
        embed = self._create_base_embed(ctx, "🚪 Gates")
        
        embed.add_field(
            name="Normal Gates (Blue-colored portals)",
            value=(
                "Ranging from E to S-Rank; spawn randomly and remain open until their boss is defeated.\n"
                "If not cleared in 7 days, a Dungeon Break occurs—monsters flood into human territory, possibly leading to long-lasting 'Field-Type Dungeons'.\n"
                "[Solo Leveling Wiki - Gates](https://solo-leveling.fandom.com/wiki/Gate)"
            ),
            inline=False
        )
        embed.add_field(
            name="Red Gates (Red Portals)",
            value=(
                "Triggered by any B-Rank or higher gate; these turn the gate red and lock visitors inside.\n"
                "**Unique Traits:**\n"
                "- Sealed entrance until the boss is defeated, whole party dies, or a Dungeon Break happens.\n"
                "- Contain harsh environments (desert, freezing tundra); time moves faster inside (1 day inside = 1 hour outside).\n"
                "- Typically start as a normal B-Rank (or higher) but intensify dramatically upon turning red.\n"
                "[Solo Leveling Wiki - Red Gates](https://solo-leveling.fandom.com/wiki/Red_Gate)\n"
                "[GameFAQs - Red Gates](https://gamefaqs.gamespot.com)"
            ),
            inline=False
        )
        embed.add_field(
            name="Historical Incidents",
            value=(
                "**Red Gate Incident (White Tiger Guild training):** Initially a C‑Rank gate but became Red, claimed 9 lives (including A-Rank Kim Chul); only 5 survived. Jinwoo was key to rescuing survivors.\n"
                "**Red Gate Arc:** Jinwoo's team faces off against ice bears, ice elves, yetis, and Baruka. Jinwoo built his shadow army here, showcasing his first real \"shadow extraction\" successes.\n"
                "[Red Gate Incident Details](https://solo-leveling.fandom.com/wiki/Red_Gate_Incident)"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name='dungeonsinfo', aliases=['dungeoninfo', 'sldungeons'])
    async def dungeons_info(self, ctx):
        """Displays information about Dungeons."""
        embed = self._create_base_embed(ctx, "🏰 Dungeons")
        
        embed.add_field(
            name="Overview",
            value=(
                "Created by Gates connecting to the Chaos World; contain mobs and a boss.\n"
                "Rankings (E–S) reflect monster difficulty and loot quality; higher-rank dungeons are larger and deadlier.\n"
                "Dungeons often come as multi-level complexes—caverns, forests, castles, icy terrains.\n"
                "Hunters rely on them for income, titles, and rare loot."
            ),
            inline=False
        )
        embed.add_field(
            name="Sources",
            value=(
                "[Solo Leveling Wiki - Dungeons](https://solo-leveling.fandom.com/wiki/Dungeon)\n"
                "[GameFAQs](https://gamefaqs.gamespot.com)"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name='slquickref', aliases=['quickref', 'slref'])
    async def quick_reference(self, ctx):
        """Provides a quick reference summary of Solo Leveling elements."""
        embed = self._create_base_embed(ctx, "📊 Solo Leveling Quick Reference", color_type='info')

        embed.add_field(name="Type: Normal Gates", value="**Key Traits:** Blue portals, open until boss defeat, rank E–S, avoid Dungeon Breaks", inline=False)
        embed.add_field(name="Type: Dungeon Breaks", value="**Key Traits:** Occur after 7 days, unleash monsters, create Field-Type Dungeons", inline=False)
        embed.add_field(name="Type: Red Gates", value="**Key Traits:** Red portals, trap hunters, harsh conditions, time dilation, must clear boss or break", inline=False)
        embed.add_field(name="Type: Bosses", value="**Key Traits:** Elite monsters (e.g. Baruka, Ice Bear Alpha); strong, trigger gate closure upon defeat", inline=False)
        embed.add_field(name="Type: Event Monsters", value="**Key Traits:** Thematic mobs like ice bears, yetis, ice elves—often environmental flavor", inline=False)

        embed.add_field(
            name="🎯 Narrative Significance",
            value=(
                "Red Gates serve as pivotal arcs:\n"
                "- Demonstrate Jinwoo's tactical growth, shadow army development, and first major boss battle.\n"
                "- Highlight the escalating dangers Hunters face—even in what seem to be routine missions.\n"
                "Dungeons and their bosses are the backbone of the Solo Leveling progression system, allowing Hunters (and especially Jinwoo) to grind, grow, and uncover supernatural threats."
            ),
            inline=False
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SoloLevelingInfoCommands(bot))