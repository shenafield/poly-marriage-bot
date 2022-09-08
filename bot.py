from distutils.log import debug
from io import BytesIO
from firestore import FirestoreDatabase
from discord.ext import commands
import discord
import visuals
from dotenv import find_dotenv
from dotenv import load_dotenv
import os


class Fetcher:
    def __init__(self, person, direction_children, builder):
        self.person = person
        self.direction_children = direction_children
        self.builder = builder

    async def get_tree(self, ctx):
        await ctx.response.defer(invisible=False)
        image, view = await self.builder.build_tree_and_view_for(
            self.person, direction_children=self.direction_children
        )

        with BytesIO() as image_binary:
            image.save(image_binary, "PNG")
            image_binary.seek(0)
            await ctx.followup.send(
                file=discord.File(fp=image_binary, filename="tree.png"), view=view
            )


class MarriageCog(commands.Cog):
    def __init__(self, bot, credentials_file="credentials.json"):
        self.bot = bot
        self.database = FirestoreDatabase(credentials_file)

    @commands.slash_command(description="Marry a user")
    async def marry(self, ctx, partner: discord.User):
        await self._marry(ctx, partner)

    @commands.user_command(name="Marry them")
    async def marry_user_command(self, ctx, user: discord.Member):
        await self._marry(ctx, user)

    async def _marry(self, ctx, partner: discord.User):
        if ctx.author.id == partner.id:
            await ctx.respond("You can't marry yourself", ephemeral=True)
            return

        me = self.database.get_person(ctx.author.id)
        target = self.database.get_person(partner.id)

        if target.id in me.partners:
            await ctx.respond("You are already married", ephemeral=True)
            return

        congrats_message = (
            f"{ctx.author.mention} is now happily married to {partner.mention}"
        )

        async def marry(ctx):
            if ctx.user.id != partner.id:
                await ctx.response.send_message(
                    "Sorry, we are not asking you -_-", ephemeral=True
                )
                return
            me.add_partner(target)
            await ctx.response.send_message(congrats_message)

        confirm_button = discord.ui.Button(
            label="Marry them", style=discord.ButtonStyle.primary
        )
        confirm_button.callback = marry

        view = discord.ui.View(confirm_button)
        await ctx.respond(
            f"{partner.mention}, it would make {ctx.author.mention} really happy if you married them",
            view=view,
        )

    @commands.slash_command(description="Divorce a user")
    async def divorce(self, ctx, partner: discord.User):
        await self._divorce(ctx, partner)

    @commands.user_command(name="Divorce them")
    async def divorce_user(self, ctx, user: discord.User):
        await self._divorce(ctx, user)

    async def _divorce(self, ctx, partner: discord.User):
        me = self.database.get_person(ctx.author.id)
        target = self.database.get_person(partner.id)
        if target.id not in me.partners:
            await ctx.respond("You are not married", ephemeral=True)
            return
        me.remove_partner(target)
        await ctx.respond(f"{ctx.author.mention} divorced {partner.mention}")

    @commands.slash_command(description="Adopt a user")
    async def adopt(self, ctx, child: discord.User):
        await self._adopt(ctx, child)

    @commands.user_command(name="Adopt them")
    async def adopt_user(self, ctx, user: discord.User):
        await self._adopt(ctx, user)

    async def _adopt(self, ctx, child: discord.User):
        if ctx.author.id == child.id:
            await ctx.respond("You can't adopt yourself", ephemeral=True)
            return

        me = self.database.get_person(ctx.author.id)
        target = self.database.get_person(child.id)

        if target.id in me.children:
            await ctx.respond("You are already their parent", ephemeral=True)
            return

        congrats_message = f"{ctx.author.mention} is now {child.mention}'s parent"

        async def adopt(ctx):
            if ctx.user.id != child.id:
                await ctx.response.send_message(
                    "Sorry, we are not asking you -_-", ephemeral=True
                )
                return
            me.adopt(target)
            await ctx.response.send_message(congrats_message)

        confirm_button = discord.ui.Button(
            label="Become their child", style=discord.ButtonStyle.primary
        )
        confirm_button.callback = adopt

        view = discord.ui.View(confirm_button)
        await ctx.respond(
            f"{child.mention}, {ctx.author.mention} wants to adopt you", view=view
        )

    @commands.slash_command(description="Disown a user")
    async def disown(self, ctx, child: discord.User):
        await self._disown(ctx, child)

    async def _disown(self, ctx, child: discord.User):
        me = self.database.get_person(ctx.author.id)
        target = self.database.get_person(child.id)
        if target.id not in me.children:
            await ctx.respond("They are not your child", ephemeral=True)
            return
        me.disown(target)
        await ctx.respond(f"{child.mention}, {ctx.author.mention} disowned you")

    @commands.slash_command(description="Make a user your parent")
    async def make_parent(self, ctx, parent: discord.User):
        await self._make_parent(ctx, parent)

    @commands.user_command(name="Make them your parent")
    async def make_parent_user(self, ctx, user: discord.User):
        await self._make_parent(ctx, user)

    async def _make_parent(self, ctx, parent: discord.User):
        if ctx.author.id == parent.id:
            await ctx.respond("You can't be your own parent", ephemeral=True)
            return

        me = self.database.get_person(ctx.author.id)
        target = self.database.get_person(parent.id)

        if me.id in target.children:
            await ctx.respond("You are already their child", ephemeral=True)
            return

        congrats_message = f"{parent.mention} is now {ctx.author.mention}'s parent"

        async def adopt(ctx):
            if ctx.user.id != parent.id:
                await ctx.response.send_message(
                    "Sorry, we are not asking you -_-", ephemeral=True
                )
                return
            target.adopt(me)
            await ctx.response.send_message(congrats_message)

        confirm_button = discord.ui.Button(
            label="Become their parent", style=discord.ButtonStyle.primary
        )
        confirm_button.callback = adopt

        view = discord.ui.View(confirm_button)
        await ctx.respond(
            f"{parent.mention}, {ctx.author.mention} wants you to be their parent",
            view=view,
        )

    @commands.slash_command(description="Run away from a parent")
    async def runaway(self, ctx, parent: discord.User):
        await self._runaway(ctx, parent)

    async def _runaway(self, ctx, parent: discord.User):
        me = self.database.get_person(ctx.author.id)
        target = self.database.get_person(parent.id)
        if me.id not in target.children:
            await ctx.respond("You are not their child", ephemeral=True)
            return
        target.disown(me)
        await ctx.respond(f"{parent.mention}, {ctx.author.mention} ran away from you")

    @commands.user_command(name="Remove parent-child link")
    async def disown_user(self, ctx, user: discord.User):
        me = self.database.get_person(ctx.author.id)
        target = self.database.get_person(user.id)
        if me.id in target.children:
            target.disown(me)
            await ctx.respond(f"{user.mention}, {ctx.author.mention} ran away from you")
        elif target.id in me.children:
            me.disown(target)
            await ctx.respond(f"{user.mention}, {ctx.author.mention} disowned you")
        else:
            await ctx.respond("You are not related in that way", ephemeral=True)

    async def build_tree_for(self, id: int, steps=2, direction_children=True):
        generations, positions, links = visuals.person_to_generations_and_coordinates(
            self.database.get_person(id), direction_children, steps
        )
        profile_picture_map = {}
        username_map = {}
        for user_id in positions.keys():
            user = await self.bot.fetch_user(user_id)
            username_map[user_id] = f"{user.name}#{user.discriminator}"
            profile_picture_map[user_id] = user.avatar and user.avatar.url
        return (
            visuals.render(
                positions, links, generations, profile_picture_map, username_map, direction_children
            ),
            generations,
        )

    async def build_tree_and_view_for(self, id: int, steps=2, direction_children=True):
        image, generations = await self.build_tree_for(id, steps, direction_children)
        buttons = []
        for person, gendata in generations.items():
            allowed = False
            for direct, generation in gendata:
                if generation == 1:
                    allowed = True
            if not allowed:
                continue
            user = await self.bot.fetch_user(person)
            button = discord.ui.Button(
                label=f"{user.name}#{user.discriminator}",
            )
            button.callback = Fetcher(person, direction_children, self).get_tree
            buttons.append(button)

        view = discord.ui.View(*buttons)
        return image, view

    @commands.slash_command(description="Show your descendants tree")
    async def descendants(self, ctx, person: discord.User = None, generations: int = 2):
        await ctx.defer()
        image, view = await self.build_tree_and_view_for(ctx.author.id if person is None else person.id, generations)
        with BytesIO() as image_binary:
            image.save(image_binary, "PNG")
            image_binary.seek(0)
            await ctx.followup.send(
                file=discord.File(fp=image_binary, filename="tree.png"), view=view
            )

    @commands.slash_command(description="Show your ancestors tree")
    async def ancestors(self, ctx, person: discord.User = None, generations: int = 2):
        await ctx.defer()
        image, view = await self.build_tree_and_view_for(ctx.author.id if person is None else person.id, generations, False)
        with BytesIO() as image_binary:
            image.save(image_binary, "PNG")
            image_binary.seek(0)
            await ctx.followup.send(
                file=discord.File(fp=image_binary, filename="tree.png"), view=view
            )

    @commands.slash_command(description="Show your partners tree")
    async def partners(self, ctx, person: discord.User = None):
        await ctx.defer()
        image, view = await self.build_tree_and_view_for(ctx.author.id if person is None else person.id, 0, None)
        with BytesIO() as image_binary:
            image.save(image_binary, "PNG")
            image_binary.seek(0)
            await ctx.followup.send(
                file=discord.File(fp=image_binary, filename="tree.png"), view=view
            )


def main():
    load_dotenv(find_dotenv(usecwd=True))
    bot = commands.Bot(
        command_prefix=commands.when_mentioned
    )
    bot.add_cog(MarriageCog(bot))
    bot.run(os.getenv("TOKEN"))


if __name__ == "__main__":
    main()
