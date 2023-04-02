import discord
import aiohttp
import asyncio
import datetime
from discord.ext import commands, tasks
from secret import tokenz, header_email, header_platform, header_repo
import pytz


API_URL = "https://d2runewizard.com/api/terror-zone"
CACHE_TTL_MIN = 30
params = {"token": tokenz}
headers = {
    "D2R-Contact": header_email,
    "D2R-Platform": header_platform,
    "D2R-Repo": header_repo,
}


times = []

for hour in range(0, 24):
    times.append(datetime.time(hour=hour, minute=3))


class TerrorZoneCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.cache = {}
        self.last_updated = None
        self.zone.start()

    def cog_unload(self):
        self.zone.cancel()

    def get_cache_ttl(self, zone_info):
        highest_probability_zone = zone_info["terrorZone"]["highestProbabilityZone"]
        if highest_probability_zone["amount"] > 3:
            return highest_probability_zone["amount"] * 60
        elif highest_probability_zone["amount"] > 0:
            return 60
        else:
            tz = pytz.timezone("Europe/Oslo")
            last_update_time = datetime.datetime.fromtimestamp(
                zone_info["terrorZone"]["lastUpdate"]["seconds"], tz
            )
            next_hour = (last_update_time + datetime.timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )
            ttl_max = next_hour - datetime.datetime.now(tz)
            return int(ttl_max.total_seconds())

    async def get_zone_info(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
        return None

    async def get_zone_info_cached(self):
        now = datetime.datetime.utcnow()
        zone_info = self.cache.get("zone_info", None)
        if zone_info is not None:
            expiry = self.cache["expiry"]
            if now < expiry:
                return zone_info
        zone_info = await self.get_zone_info()
        if zone_info is not None:
            ttl = self.get_cache_ttl(zone_info)
            self.cache["zone_info"] = zone_info
            self.cache["expiry"] = now + datetime.timedelta(seconds=ttl)
            self.last_updated = now
            return zone_info
        return None

    @tasks.loop(time=times)
    async def zone(self):
        channel = self.client.get_channel(1075792513727746078)
        zone_info = await self.get_zone_info_cached()
        if zone_info is not None:
            last_updated = self.last_updated + datetime.timedelta(hours=2)
            last_updated = last_updated.strftime("%d-%m-%Y %H:%M:%S")

            highest_probability_zone = zone_info["terrorZone"]["highestProbabilityZone"]
            embed = discord.Embed(
                title=f"Terror Zone",
                colour=discord.Colour.gold(),
            )
            embed.set_footer(text=f"Provided by: {zone_info['providedBy']}")
            embed.add_field(
                name="Terror Zone:",
                value=f"{highest_probability_zone['zone']}",
                inline=True,
            )
            embed.add_field(
                name="Act", value=f"{highest_probability_zone['act']}", inline=True
            )
            embed.add_field(name="Last updated", value=f"{last_updated}", inline=False)
            try:
                await channel.purge(limit=10)
            except discord.errors.NotFound:
                print("Message not found during purge.")
            await channel.send(embed=embed)
        else:
            await channel.send("Failed to fetch zone info.")


async def setup(client):
    await client.add_cog(TerrorZoneCog(client))
    return TerrorZoneCog(client)
