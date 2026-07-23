# Represents logic for what to do when we are given an item from AP
import math
from enum import IntEnum

import random
from typing import List, Tuple

from apworld.toontown import ToontownItemName, get_item_def_from_id
from apworld.toontown.fish import LICENSE_TO_ACCESS_CODE
from apworld.toontown.options import GagTrainingFrameBehavior
from otp.otpbase.OTPLocalizerEnglish import EmoteFuncDict
from toontown.archipelago.util import global_text_properties
from toontown.archipelago.util.global_text_properties import MinimalJsonMessagePart
from toontown.battle import BattleBase

from toontown.building import FADoorCodes
from toontown.coghq.CogDisguiseGlobals import PartsPerSuitBitmasks
from toontown.fishing import FishGlobals
from toontown.toonbase import ToontownBattleGlobals
from toontown.toonbase import ToontownGlobals
from toontown.toon import NPCToons
from toontown.chat import ResistanceChat
from toontown.archipelago.definitions.death_reason import DeathReason

# Typing hack, can remove later
TYPING = False
if TYPING:
    from toontown.toon.DistributedToonAI import DistributedToonAI


class APReward:

    # Return a color formatted header to display in the on screen display, this should be overridden
    def formatted_header(self):
        return f"UNIMPLEMENTED REWARD STR:\n{self.__class__.__name__}"

    # Returns a color formatted footer so we don't have to call this ugly code a million times
    def _formatted_footer(self, player, isSelf=False):
        color = 'yellow' if not isSelf else 'magenta'
        name = player if not isSelf else "You"
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("\n\nFrom: "),
            MinimalJsonMessagePart(f"{name}", color=color)
        ])

    # Override to set an image path to show up on the display, assumes png and square shaped
    # If not overridden, will show the AP logo
    def get_image_path(self) -> str:
        return 'phase_14/maps/ap_icon.png'

    # Override to set the scale of an image you want to show up on the display
    def get_image_scale(self) -> float:
        return .08

    # Override to set the position of an image you want to show up on the display
    def get_image_pos(self):
        return (.12, 0, .1)

    # Returns a string to show on the display when received, should follow the basic format like so:
    # Your x is now y!\n\nFrom: {fromPlayer}
    def get_reward_string(self, fromPlayer: str, isSelf=False) -> str:
        return f"{self.formatted_header()}{self._formatted_footer(fromPlayer, isSelf)}"

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        raise NotImplementedError("Please implement the apply() method!")

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        return False


# Marker mixin. Rewards that inherit this are held instead of auto-applying to the receiver,
# so they can later be fired at an arbitrary target toon (see DistributedToonAI.useHeldTrap).
class TrapReward:
    pass


def get_trap_strength_multiplier(firer: "DistributedToonAI" = None) -> float:
    if firer is None or not hasattr(firer, 'getTrapStrengthPercent'):
        return 1.0
    return 1.0 + (max(0, firer.getTrapStrengthPercent()) / 100.0)


class LaffBoostReward(APReward):
    def __init__(self, amount: int):
        self.amount = amount

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Increased your\nmax laff by "),
            MinimalJsonMessagePart(f"+{self.amount}", color='green'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.b_setMaxHp(av.maxHp + self.amount)
        av.toonUp(self.amount)
        av.checkWinCondition()

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        newMaxHp = max(15, av.getMaxHp() - self.amount)
        av.b_setMaxHp(newMaxHp)
        if av.getHp() > newMaxHp:
            av.b_setHp(newMaxHp)
        return True


class DmgBoostReward(APReward):
    def __init__(self, amount: int):
        self.amount = amount

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Increased your\nGag damage by "),
            MinimalJsonMessagePart(f"+{self.amount}%", color='green'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        old_dmg = av.getDamageMultiplier()
        av.b_setDamageMultiplier(old_dmg + self.amount)


class GagCapacityReward(APReward):

    def __init__(self, amount: int):
        self.amount: int = amount

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Increased your gag\npouch capacity by "),
            MinimalJsonMessagePart(f"+{self.amount}", color='green'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        new_carry = av.maxCarry + self.amount
        av.b_setMaxCarry(new_carry)
        if new_carry >= 75 and av.has75 == 0:
            av.b_setHas75Capacity(1)
            av.d_considerCapacityRewardMessage75()
        if new_carry >= 90 and av.has90 == 0:
            av.b_setHas90Capacity(1)
            av.d_considerCapacityRewardMessage90()

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        newCarry = max(20, av.maxCarry - self.amount)
        av.b_setMaxCarry(newCarry)
        if newCarry < 75 and av.has75:
            av.b_setHas75Capacity(0)
        if newCarry < 90 and av.has90:
            av.b_setHas90Capacity(0)
        return True


class JellybeanJarUpgradeReward(APReward):

    def __init__(self, amount: int):
        self.amount: int = amount

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Increased your jellybean\njar capacity by "),
            MinimalJsonMessagePart(f"+{self.amount}", color='green'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.b_setMaxMoney(av.maxMoney + self.amount)
        av.addMoney(self.amount)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        newMax = max(1000, av.maxMoney - self.amount)
        av.b_setMaxMoney(newMax)
        av.b_setMoney(min(av.getMoney(), newMax))
        return True

class TaskCapacityReward(APReward):
    
        def __init__(self, amount: int):
            self.amount: int = amount
    
        def formatted_header(self) -> str:
            return global_text_properties.get_raw_formatted_string([
                MinimalJsonMessagePart("Increased your task\ncapacity by "),
                MinimalJsonMessagePart(f"+{self.amount}", color='green'),
                MinimalJsonMessagePart("!"),
            ])
    
        def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
            av.b_setQuestCarryLimit(av.getQuestCarryLimit() + self.amount)

        def revoke(self, av: "DistributedToonAI", item_id: int = None):
            av.b_setQuestCarryLimit(max(1, av.getQuestCarryLimit() - self.amount))
            return True

class GagTrainingFrameReward(APReward):
    TOONUP = 0
    TRAP = 1
    LURE = 2
    SOUND = 3
    THROW = 4
    SQUIRT = 5
    DROP = 6

    TRACK_TO_NAME = {
        TOONUP: "Toon-Up",
        TRAP: "Trap",
        LURE: "Lure",
        SOUND: "Sound",
        THROW: "Throw",
        SQUIRT: "Squirt",
        DROP: "Drop",
    }

    TRACK_TO_COLOR = {
        TOONUP: 'plum',
        TRAP: 'yellow',
        LURE: 'green',
        SOUND: 'blue',
        THROW: 'yellow',  #  todo add a gold text property
        SQUIRT: 'slateblue',  # todo add a pinkish text property
        DROP: 'lightblue'
    }

    TRACK_TO_ICON = {
        TOONUP: "toonup_%s",
        TRAP: "trap_%s",
        LURE: "lure_%s",
        SOUND: "sound_%s",
        THROW: "throw_%s",
        SQUIRT: "squirt_%s",
        DROP: "drop_%s",
    }

    def __init__(self, track):
        self.track = track

    # todo: find a way to show dynamic info based on what this reward did for us exactly
    # todo: new system was two steps forward one step back in this regard
    def formatted_header(self) -> str:
        track_name_color = self.TRACK_TO_COLOR.get(self.track)
        level = base.localAvatar.getTrackAccessLevel(self.track)
        # Check for new levels
        if level <= 7:
            return global_text_properties.get_raw_formatted_string([
                MinimalJsonMessagePart("Received a training frame!\nYour "),
                MinimalJsonMessagePart(f"{self.TRACK_TO_NAME[self.track]}".upper(), color=track_name_color),
                MinimalJsonMessagePart(" Gags have more potential!"),
                ])
        else:
            return global_text_properties.get_raw_formatted_string([
                MinimalJsonMessagePart("Received a training frame!\nYour "),
                MinimalJsonMessagePart(f"{self.TRACK_TO_NAME[self.track]}".upper(), color=track_name_color),
                MinimalJsonMessagePart(" experience can now overflow!"),
            ])

    def get_image_path(self) -> str:
        level = base.localAvatar.getTrackAccessLevel(self.track)
        ap_icon = self.TRACK_TO_ICON[(self.track)] % str(min(max(level, 1), 7))
        return f'phase_14/maps/gags/{ap_icon}.png'

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        
        # Store option for behavior
        behaviorMode = av.slotData.get("gag_frame_item_behavior", 0)

        # Increment track access level by 1
        oldLevel = av.getTrackAccessLevel(self.track)
        newLevel = oldLevel + 1

        # Before we do anything, we need to see if they were capped before this so we can award them gags later
        curExp = av.experience.getExp(self.track)
        wasCapped = curExp == av.experience.getExperienceCapForTrack(self.track)

        # Otherwise increment the gag level allowed
        av.setTrackAccessLevel(self.track, newLevel)

        # Edge case, nothing else should happen if we are unlocking the "overflow xp" mechanic
        if newLevel >= 8:
            return

        # Max the gag and give the new gag if the behavior mode is to max gags 
        elif behaviorMode == GagTrainingFrameBehavior.option_trained:
            av.experience.setExp(self.track, av.experience.getExperienceCapForTrack(track=self.track)) # max the gag exp.
            av.ap_setExperience(av.experience.getCurrentExperience())
            av.inventory.addItemsWithListMax([(self.track, newLevel-1)])  # Give the new gags!!
            av.b_setInventory(av.inventory.makeNetString())
        # Consider the case where we just learned a new gag track, we should give them as many of them as possible
        elif newLevel == 1:
            av.inventory.addItemsWithListMax([(self.track, 0)])
            av.b_setInventory(av.inventory.makeNetString())
        # Now consider the case where we were maxed previously and want to upgrade by giving 1 xp and giving new gags
        # This will also trigger the new gag check to unlock :3
        elif (wasCapped and behaviorMode == GagTrainingFrameBehavior.option_vanilla
            or behaviorMode == GagTrainingFrameBehavior.option_unlock):
            toNext = av.experience.getNextExpValue(track=self.track, curSkill=curExp)
            av.experience.setExp(track=self.track, exp=toNext)  # Give them enough xp to learn the gag :)
            av.ap_setExperience(av.experience.getCurrentExperience())
            av.inventory.addItemsWithListMax([(self.track, newLevel-1)])  # Give the new gags!!
            av.b_setInventory(av.inventory.makeNetString())

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        trackArray = getattr(av, 'trackArray', None) or []
        if self.track >= len(trackArray):
            return False
        oldLevel = trackArray[self.track]
        if oldLevel <= 0:
            return False
        newLevel = max(0, oldLevel - 1)
        av.setTrackAccessLevel(self.track, newLevel)

        cap = av.experience.getExperienceCapForTrack(self.track)
        av.experience.setExp(self.track, min(av.experience.getExp(self.track), cap))
        av.ap_setExperience(av.experience.getCurrentExperience())

        if av.inventory is not None:
            firstInvalidGagLevel = min(newLevel, len(ToontownBattleGlobals.Levels[self.track]))
            for gagLevel in range(firstInvalidGagLevel, len(ToontownBattleGlobals.Levels[self.track])):
                av.inventory.inventory[self.track][gagLevel] = 0
            av.inventory.calcTotalProps()
            av.b_setInventory(av.inventory.makeNetString())
        return True

class GagUpgradeReward(APReward):
    TOONUP = 0
    TRAP = 1
    LURE = 2
    SOUND = 3
    THROW = 4
    SQUIRT = 5
    DROP = 6

    TRACK_TO_NAME = {
        TOONUP: "Toon-Up",
        TRAP: "Trap",
        LURE: "Lure",
        SOUND: "Sound",
        THROW: "Throw",
        SQUIRT: "Squirt",
        DROP: "Drop",
    }

    TRACK_TO_COLOR = {
        TOONUP: 'plum',
        TRAP: 'yellow',
        LURE: 'green',
        SOUND: 'blue',
        THROW: 'yellow',  #  todo add a gold text property
        SQUIRT: 'slateblue',  # todo add a pinkish text property
        DROP: 'lightblue'
    }

    TRACK_TO_ICON = {
        TOONUP: "toonup_%s",
        TRAP: "trap_%s",
        LURE: "lure_%s",
        SOUND: "sound_%s",
        THROW: "throw_%s",
        SQUIRT: "squirt_%s",
        DROP: "drop_%s",
    }

    TRACK_TO_UPGRADE_DESC = {
        TOONUP: "now increase defense on use!",
        TRAP: "now further reduce Cog damage!",
        LURE: "have increased accuracy and knockback!",
        SOUND: "deal more damage the higher the Cogs!",
        THROW: "provide self-heal!",
        SQUIRT: "deal increased knockback damage!",
        DROP: "can now hit lured Cogs!",
    }

    def __init__(self, track):
        self.track = track

    # todo: find a way to show dynamic info based on what this reward did for us exactly
    # todo: new system was two steps forward one step back in this regard
    def formatted_header(self) -> str:
        track_name_color = self.TRACK_TO_COLOR.get(self.track)
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Trees planted! Your "),
            MinimalJsonMessagePart(f"{self.TRACK_TO_NAME[self.track]}\n".upper(), color=track_name_color),
            MinimalJsonMessagePart(f" Gags {self.TRACK_TO_UPGRADE_DESC[self.track]}"),
        ])

    def get_image_path(self) -> str:
        level = base.localAvatar.getTrackAccessLevel(self.track)
        if not level:
            level = 1
        ap_icon = self.TRACK_TO_ICON[(self.track)] % str(min(level, 7))
        return f'phase_14/maps/gags/{ap_icon}.png'

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        bonusArray = av.getTrackBonusLevel()
        bonusArray[self.track] = 7
        av.b_setTrackBonusLevel(bonusArray)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        bonusArray = av.getTrackBonusLevel()
        if self.track >= len(bonusArray) or bonusArray[self.track] < 0:
            return False
        bonusArray[self.track] = -1
        av.b_setTrackBonusLevel(bonusArray)
        return True


class GagTrainingMultiplierReward(APReward):

    def __init__(self, amount: int):
        self.amount: int = amount

    # todo, again nice to have this tell us WHAT it is, not what we got
    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Increased your global XP\nmultiplier by "),
            MinimalJsonMessagePart(f"+{self.amount}", color='green'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        oldMultiplier = av.getBaseGagSkillMultiplier()
        newMultiplier = oldMultiplier + self.amount
        av.b_setBaseGagSkillMultiplier(newMultiplier)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        av.b_setBaseGagSkillMultiplier(max(1, av.getBaseGagSkillMultiplier() - self.amount))
        return True


class GolfPutterReward(APReward):

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Get ready to go mini-golfing\nwith your new "),
            MinimalJsonMessagePart("Golf Putter", color='cyan'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.addAccessKey(ToontownGlobals.PUTTER_KEY)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        av.removeAccessKey(ToontownGlobals.PUTTER_KEY)
        return True


class JokeBookReward(APReward):
    TOONTOWN_CENTRAL = ToontownGlobals.ToontownCentral
    DONALDS_DOCK = ToontownGlobals.DonaldsDock
    DAISYS_GARDENS = ToontownGlobals.DaisyGardens
    MINNIES_MELODYLAND = ToontownGlobals.MinniesMelodyland
    THE_BRRRGH = ToontownGlobals.TheBrrrgh
    DONALDS_DREAMLAND = ToontownGlobals.DonaldsDreamland

    ZONE_TO_DISPLAY_NAME = {
        TOONTOWN_CENTRAL: "Toontown Central",
        DONALDS_DOCK: "Donald's Dock",
        DAISYS_GARDENS: "Daisy Gardens",
        MINNIES_MELODYLAND: "Minnie's Melodyland",
        THE_BRRRGH: "The Brrrgh",
        DONALDS_DREAMLAND: "Donald's Dreamland",
    }
    def __init__(self, playground: int):
        self.playground: int = playground

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("You can now laugh at jokes in\n"),
            MinimalJsonMessagePart(f"{self.ZONE_TO_DISPLAY_NAME.get(self.playground, 'unknown zone: ' + str(self.playground))}", color='green'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        if self.playground in list(FADoorCodes.ZONE_TO_JOKE_CODE.keys()):
            key = FADoorCodes.ZONE_TO_JOKE_CODE[self.playground]
            av.addAccessKey(key)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        if self.playground in list(FADoorCodes.ZONE_TO_JOKE_CODE.keys()):
            av.removeAccessKey(FADoorCodes.ZONE_TO_JOKE_CODE[self.playground])
            return True
        return False


class GoKartReward(APReward):

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Get ready to go racing\nwith your new "),
            MinimalJsonMessagePart("Go-Kart", color='cyan'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.b_setKartBodyType(1)
        av.b_setTickets(99999)


class FishingRodUpgradeReward(APReward):

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Your "),
            MinimalJsonMessagePart(f"Fishing Rod", color='plum'),
            MinimalJsonMessagePart("\nhas been upgraded!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        nextRodID = min(av.fishingRod + 1, FishGlobals.MaxRodId)

        av.b_setFishingRod(nextRodID)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        av.b_setFishingRod(max(0, av.getFishingRod() - 1))
        return True


class AccessKeyReward(APReward):
    TOONTOWN_CENTRAL = ToontownGlobals.ToontownCentral
    DONALDS_DOCK = ToontownGlobals.DonaldsDock
    DAISYS_GARDENS = ToontownGlobals.DaisyGardens
    MINNIES_MELODYLAND = ToontownGlobals.MinniesMelodyland
    THE_BRRRGH = ToontownGlobals.TheBrrrgh
    DONALDS_DREAMLAND = ToontownGlobals.DonaldsDreamland

    SELLBOT_HQ = ToontownGlobals.SellbotHQ
    CASHBOT_HQ = ToontownGlobals.CashbotHQ
    LAWBOT_HQ = ToontownGlobals.LawbotHQ
    BOSSBOT_HQ = ToontownGlobals.BossbotHQ

    ACORN_ACRES = ToontownGlobals.OutdoorZone
    GOOFY_SPEEDWAY = ToontownGlobals.GoofySpeedway

    LINKED_PGS = {ACORN_ACRES: [ToontownGlobals.GolfZone]}

    ZONE_TO_DISPLAY_NAME = {
        TOONTOWN_CENTRAL: "Toontown Central",
        DONALDS_DOCK: "Donald's Dock",
        DAISYS_GARDENS: "Daisy Gardens",
        MINNIES_MELODYLAND: "Minnie's Melodyland",
        THE_BRRRGH: "The Brrrgh",
        DONALDS_DREAMLAND: "Donald's Dreamland",
        SELLBOT_HQ: "Sellbot HQ",
        CASHBOT_HQ: "Cashbot HQ",
        LAWBOT_HQ: "Lawbot HQ",
        BOSSBOT_HQ: "Bossbot HQ",
        ACORN_ACRES: "Acorn Acres",
        GOOFY_SPEEDWAY: "Goofy Speedway",
    }

    ZONE_TO_ACCESS_ITEM = {
        TOONTOWN_CENTRAL: ToontownItemName.TTC_ACCESS,
        DONALDS_DOCK: ToontownItemName.DD_ACCESS,
        DAISYS_GARDENS: ToontownItemName.DG_ACCESS,
        MINNIES_MELODYLAND: ToontownItemName.MML_ACCESS,
        THE_BRRRGH: ToontownItemName.TB_ACCESS,
        DONALDS_DREAMLAND: ToontownItemName.DDL_ACCESS,
        SELLBOT_HQ: ToontownItemName.SBHQ_ACCESS,
        CASHBOT_HQ: ToontownItemName.CBHQ_ACCESS,
        LAWBOT_HQ: ToontownItemName.LBHQ_ACCESS,
        BOSSBOT_HQ: ToontownItemName.BBHQ_ACCESS,
        ACORN_ACRES: ToontownItemName.AA_ACCESS,
        GOOFY_SPEEDWAY: ToontownItemName.GS_ACCESS,
    }

    COG_ZONES = (SELLBOT_HQ, CASHBOT_HQ,  LAWBOT_HQ, BOSSBOT_HQ)

    def __init__(self, playground: int):
        self.playground: int = playground

    def formatted_header(self) -> str:
        accessCount = 0
        items = base.localAvatar.getReceivedItems()
        for item in items:
            index_received, item_id = item
            if get_item_def_from_id(item_id).name == self.ZONE_TO_ACCESS_ITEM.get(self.playground, ToontownGlobals.ToontownCentral):
                accessCount += 1
        if accessCount >= 2:
            if self.playground in self.COG_ZONES:
                return global_text_properties.get_raw_formatted_string([
                    MinimalJsonMessagePart("You may now infiltrate facilities\nin "),
                    MinimalJsonMessagePart(f"{self.ZONE_TO_DISPLAY_NAME.get(self.playground, 'unknown zone: ' + str(self.playground))}", color='green'),
                    MinimalJsonMessagePart("!"),
                    ])
            return global_text_properties.get_raw_formatted_string([
                MinimalJsonMessagePart("You may now complete ToonTasks\nin "),
                MinimalJsonMessagePart(f"{self.ZONE_TO_DISPLAY_NAME.get(self.playground, 'unknown zone: ' + str(self.playground))}", color='green'),
                MinimalJsonMessagePart("!"),
            ])
        else:
            return global_text_properties.get_raw_formatted_string([
                MinimalJsonMessagePart("You can now teleport\nto "),
                MinimalJsonMessagePart(f"{self.ZONE_TO_DISPLAY_NAME.get(self.playground, 'unknown zone: ' + str(self.playground))}", color='green'),
                MinimalJsonMessagePart("!"),
            ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        # Apply TP before HQ or facilities
        if not av.hasTeleportAccess(self.playground):
            av.addTeleportAccess(self.playground)
            for pg in self.LINKED_PGS.get(self.playground, []):
                av.addTeleportAccess(pg)
        else:
            # Get the key ID for this playground
            if self.playground in list(FADoorCodes.ZONE_TO_ACCESS_CODE.keys()):
                key = FADoorCodes.ZONE_TO_ACCESS_CODE[self.playground]
                av.addAccessKey(key)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        effectiveCount = av.getEffectiveReceivedItemCount(item_id)
        if self.playground in list(FADoorCodes.ZONE_TO_ACCESS_CODE.keys()) and effectiveCount <= 1:
            av.removeAccessKey(FADoorCodes.ZONE_TO_ACCESS_CODE[self.playground])
        if effectiveCount <= 0:
            av.removeTeleportAccess(self.playground)
            for pg in self.LINKED_PGS.get(self.playground, []):
                av.removeTeleportAccess(pg)
        return True


class FishingLicenseReward(APReward):
    TOONTOWN_CENTRAL = ToontownGlobals.ToontownCentral
    DONALDS_DOCK = ToontownGlobals.DonaldsDock
    DAISYS_GARDENS = ToontownGlobals.DaisyGardens
    MINNIES_MELODYLAND = ToontownGlobals.MinniesMelodyland
    THE_BRRRGH = ToontownGlobals.TheBrrrgh
    DONALDS_DREAMLAND = ToontownGlobals.DonaldsDreamland

    ZONE_TO_DISPLAY_NAME = {
        TOONTOWN_CENTRAL: "Toontown Central",
        DONALDS_DOCK: "Donald's Dock",
        DAISYS_GARDENS: "Daisy Gardens",
        MINNIES_MELODYLAND: "Minnie's Melodyland",
        THE_BRRRGH: "The Brrrgh",
        DONALDS_DREAMLAND: "Donald's Dreamland",
    }

    def __init__(self, playground: int):
        self.playground: int = playground

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("You may now Fish\nin "),
            MinimalJsonMessagePart(f"{self.ZONE_TO_DISPLAY_NAME.get(self.playground, 'unknown zone: ' + str(self.playground))}", color='green'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        # Get the key ID for this playground
        key = LICENSE_TO_ACCESS_CODE[self.playground]
        av.addAccessKey(key)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        av.removeAccessKey(LICENSE_TO_ACCESS_CODE[self.playground])
        return True


class FacilityAccessReward(APReward):
    FACILITY_ID_TO_DISPLAY = {
        FADoorCodes.FRONT_FACTORY_ACCESS_MISSING: "Front Factory",
        FADoorCodes.SIDE_FACTORY_ACCESS_MISSING: "Side Factory",

        FADoorCodes.COIN_MINT_ACCESS_MISSING: "Coin Mint",
        FADoorCodes.DOLLAR_MINT_ACCESS_MISSING: "Dollar Mint",
        FADoorCodes.BULLION_MINT_ACCESS_MISSING: "Bullion Mint",

        FADoorCodes.OFFICE_A_ACCESS_MISSING: "Office A",
        FADoorCodes.OFFICE_B_ACCESS_MISSING: "Office B",
        FADoorCodes.OFFICE_C_ACCESS_MISSING: "Office C",
        FADoorCodes.OFFICE_D_ACCESS_MISSING: "Office D",

        FADoorCodes.FRONT_THREE_ACCESS_MISSING: "Front One",
        FADoorCodes.MIDDLE_SIX_ACCESS_MISSING: "Middle Two",
        FADoorCodes.BACK_NINE_ACCESS_MISSING: "Back Three",
    }

    def __init__(self, key):
        self.key = key

    def formatted_header(self) -> str:
        key_name = self.FACILITY_ID_TO_DISPLAY.get(self.key, f"UNKNOWN-KEY[{self.key}]")
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("You may now infiltrate\nthe "),
            MinimalJsonMessagePart(f"{key_name}", color='salmon'),
            MinimalJsonMessagePart(" facility!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        # Get the key ID for this playground
        av.addAccessKey(self.key)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        av.removeAccessKey(self.key)
        return True


class CogDisguiseReward(APReward):
    BOSSBOT = 0
    LAWBOT = 1
    CASHBOT = 2
    SELLBOT = 3

    ENUM_TO_NAME = {
        BOSSBOT: "Bossbot",
        LAWBOT: "Lawbot",
        CASHBOT: "Cashbot",
        SELLBOT: "Sellbot",
    }

    # When instantiating this, use the attributes defined above, i'm not here to fix shit toontown code
    def __init__(self, dept: int):
        self.dept: int = dept

    def formatted_header(self) -> str:
        dept = self.ENUM_TO_NAME[self.dept]
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("You were given\nyour "),
            MinimalJsonMessagePart(f"{dept} Disguise", color='plum'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        parts = av.getCogParts()
        parts[self.dept] = PartsPerSuitBitmasks[self.dept]
        av.b_setCogParts(parts)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        parts = av.getCogParts()
        parts[self.dept] = 0
        av.b_setCogParts(parts)
        return True


class JellybeanReward(APReward):

    def __init__(self, amount: int):
        self.amount: int = amount

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("You were given\n"),
            MinimalJsonMessagePart(f"+{self.amount} jellybeans", color='cyan'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.addMoney(self.amount)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        av.takeMoney(min(self.amount, av.getMoney()))
        return True


class FishReward(APReward):
    def __init__(self, amount: int):
        self.amount: int = amount

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("You found an\n"),
            MinimalJsonMessagePart("Old Boot", color='cyan'),
            MinimalJsonMessagePart("!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.addMoney(self.amount)
        sounds = ["phase_4/audio/sfx/fish.ogg", "phase_4/audio/sfx/ykwtm.ogg"]
        sound = random.choice(sounds)
        av.playSound(sound)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        av.takeMoney(min(self.amount, av.getMoney()))
        return True


class DamageTrapAward(APReward, TrapReward):

    def __init__(self, amount: int):
        self.amount: int = amount

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart(f"{self.amount}% DAMAGE TRAP\n", color='salmon'),
            MinimalJsonMessagePart(f"That'll leave a mark!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        amountPercent = (self.amount * get_trap_strength_multiplier(firer)) / 100
        # Deal at least 1 damage
        damage = max(1, math.floor(amountPercent * av.getMaxHp()))
        if damage >= av.getHp():
            damage = av.getHp()
        if av.getHp() > 0:
            if damage >= av.getHp():
                av.setDeathReason(DeathReason.DAMAGE_TRAP)
            av.takeDamage(damage)
        av.playSound('phase_4/audio/sfx/oof.ogg')
        av.d_broadcastHpString("EMOTIONAL DAMAGE!", (.78, .29, .29))
        av.d_playEmote(EmoteFuncDict['Banana Peel'], 1)


class UberTrapAward(APReward, TrapReward):

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("UBER TRAP\n", color='salmon'),
            MinimalJsonMessagePart(f"Will you survive?"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        threshold = max(1, math.floor(15 * get_trap_strength_multiplier(firer)))
        newHp = threshold if av.getHp() > threshold else 0
        damage = av.getHp() - newHp
        if av.getHp() > 0:
            if damage >= av.getHp():
                av.setDeathReason(DeathReason.DAMAGE_TRAP)
            av.takeDamage(damage)
        av.inventory.maxInventory(clearFirst=True, restockAmount=20)
        av.b_setInventory(av.inventory.makeNetString())
        if newHp == 1:
            av.playSound('phase_4/audio/sfx/BLACK_KNIGHT.ogg')
        else:
            av.playSound('phase_4/audio/sfx/NO_NO_NO.ogg')
        av.d_broadcastHpString("UBERFIED!", (.35, .7, .35))
        av.d_playEmote(EmoteFuncDict['Cry'], 1)


class ExposeTrapAward(APReward, TrapReward):
    """Doesn't damage/debuff the target at all -- just reports their current
    location (playground / street / interior / cog facility) back to whoever
    fired it. Requires `firer` to be set, since the message goes to them, not
    to the target being exposed."""

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("EXPOSE TRAP\n", color='yellow'),
            MinimalJsonMessagePart("Your location has been revealed!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        if firer is None:
            return  # No one to report back to, nothing to do

        location = self._describeLocation(av)
        msg = global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("[Expose] ", color='yellow'),
            MinimalJsonMessagePart(f"{av.getName()} is currently "),
            MinimalJsonMessagePart(location, color='cyan'),
        ])
        firer.d_sendArchipelagoMessage(msg)

    # NOTE: this relies on ZoneUtil/ToontownGlobals conventions (hoodId == playground
    # zoneId, ZoneUtil.getBranchZone identifying the street) that are standard in most
    # Toontown forks but may not exactly match yours -- double check the labels this
    # produces in-game and adjust HOOD_NAMES/COG_HQ_HOODS below if anything looks off.
    @staticmethod
    def _describeLocation(av: "DistributedToonAI") -> str:
        from toontown.hood import ZoneUtil
        from toontown.toonbase import ToontownGlobals

        zoneId = av.zoneId
        hoodId = ZoneUtil.getHoodId(zoneId)

        HOOD_NAMES = {
            ToontownGlobals.ToontownCentral: "Toontown Central",
            ToontownGlobals.DonaldsDock: "Donald's Dock",
            ToontownGlobals.DaisyGardens: "Daisy Gardens",
            ToontownGlobals.MinniesMelodyland: "Minnie's Melodyland",
            ToontownGlobals.TheBrrrgh: "The Brrrgh",
            ToontownGlobals.DonaldsDreamland: "Donald's Dreamland",
            ToontownGlobals.SellbotHQ: "the Sellbot HQ",
            ToontownGlobals.CashbotHQ: "the Cashbot HQ",
            ToontownGlobals.LawbotHQ: "the Lawbot HQ",
            ToontownGlobals.BossbotHQ: "the Bossbot HQ",
        }
        COG_HQ_HOODS = {
            ToontownGlobals.SellbotHQ,
            ToontownGlobals.CashbotHQ,
            ToontownGlobals.LawbotHQ,
            ToontownGlobals.BossbotHQ,
        }

        hoodName = HOOD_NAMES.get(hoodId, "an unknown area")

        COG_FACILITY_ZONES = {
            ToontownGlobals.SellbotFactoryExt: "at the Sellbot Factory entrance",
            ToontownGlobals.SellbotFactoryInt: "inside the Front Factory",
            ToontownGlobals.SellbotFactoryIntS: "inside the Side Factory",
            ToontownGlobals.CashbotMintIntA: "inside the Coin Mint",
            ToontownGlobals.CashbotMintIntB: "inside the Dollar Mint",
            ToontownGlobals.CashbotMintIntC: "inside the Bullion Mint",
            ToontownGlobals.LawbotOfficeExt: "at the DA Office entrance",
            ToontownGlobals.LawbotOfficeInt: "inside a DA Office",
            ToontownGlobals.BossbotCountryClubIntA: "inside the Front Three golf course",
            ToontownGlobals.BossbotCountryClubIntB: "inside the Middle Six golf course",
            ToontownGlobals.BossbotCountryClubIntC: "inside the Back Nine golf course",
        }
        if zoneId in COG_FACILITY_ZONES:
            return COG_FACILITY_ZONES[zoneId]
        if hoodId == ToontownGlobals.GolfZone:
            return "at the golf course"
        if hoodId in COG_HQ_HOODS and zoneId != hoodId:
            return f"inside a Cog HQ facility in {hoodName}"
        if zoneId == hoodId:
            return f"in the {hoodName} playground"

        branchZone = ZoneUtil.getBranchZone(zoneId)
        if branchZone == zoneId:
            return f"on a street in {hoodName}"

        buildingType = ExposeTrapAward._describeStreetInterior(av, branchZone, zoneId)
        return f"inside {buildingType} in {hoodName}"

    @staticmethod
    def _describeStreetInterior(av: "DistributedToonAI", branchZone: int, zoneId: int) -> str:
        try:
            blockNumber = zoneId % 100
            buildingMgr = av.air.buildingManagers.get(branchZone)
            if buildingMgr is not None and buildingMgr.isValidBlockNumber(blockNumber):
                building = buildingMgr.getBuilding(blockNumber)
                if building.isSuitBuilding():
                    return "a Cog building"
                if getattr(building, 'isCogdo', lambda: False)():
                    return "a Field Office"
        except Exception:
            pass
        return "a toon/NPC building"


class ExposeBeansTrapAward(APReward, TrapReward):
    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("EXPOSE BEANS TRAP\n", color='yellow'),
            MinimalJsonMessagePart("Reveals your opponent's jellybeans."),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        if firer is None:
            return
        beans = av.getTotalMoney()
        msg = global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("[Expose Beans] ", color='yellow'),
            MinimalJsonMessagePart(f"{av.getName()} has "),
            MinimalJsonMessagePart(f"{beans}", color='cyan'),
            MinimalJsonMessagePart(" jellybeans."),
        ])
        firer.d_sendArchipelagoMessage(msg)


class BeanTaxTrapAward(APReward, TrapReward):
    def __init__(self, tax: int):
        self.tax: int = tax

    def formatted_header(self) -> str:
        if base.localAvatar.getHasPaidTaxes():
            return global_text_properties.get_raw_formatted_string([
                MinimalJsonMessagePart("BEAN TAX PAID\n", color='salmon'),
                MinimalJsonMessagePart("You paid the tax for "),
                MinimalJsonMessagePart(f"{self.tax} beans.", color='cyan'),
            ])

        else:
            return global_text_properties.get_raw_formatted_string([
                MinimalJsonMessagePart("BEAN TAX FAILED\n", color='salmon'),
                MinimalJsonMessagePart("You tried evading the tax for "),
                MinimalJsonMessagePart(f"{self.tax} beans.", color='cyan'),
            ])

    def getPassed(self, avMoney):
        if avMoney >= self.tax:
            return True
        else:
            return False

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        avMoney = av.getMoney()
        tax = max(1, math.floor(self.tax * get_trap_strength_multiplier(firer)))

        if avMoney >= tax:
            av.b_setHasPaidTaxes(True)
            av.takeMoney(tax)
            av.playSound('phase_4/audio/sfx/tax_paid.ogg')
            av.d_broadcastHpString("TAXES PAID!", (.35, .7, .35))
            av.d_playEmote(EmoteFuncDict['Happy'], 1)
        else:
            av.b_setHasPaidTaxes(False)
            av.takeMoney(av.getMoney())
            damage = max(0, av.getHp() - 1)
            if av.getHp() > 0:
                av.takeDamage(damage)
            av.playSound('phase_4/audio/sfx/tax_evasion.ogg')
            av.d_broadcastHpString("EVASION ATTEMPTED!", (.3, .5, .8))
            av.d_playEmote(EmoteFuncDict['Belly Flop'], 1)


class DripTrapAward(APReward, TrapReward):

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("DRIP TRAP\n", color='salmon'),
            MinimalJsonMessagePart(f"Did someone say the door to drip?"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.playSound('phase_4/audio/sfx/avatar_emotion_drip.ogg')
        av.b_setShoes(1, random.randint(1, 48), 0)
        av.b_setBackpack(random.randint(1, 24), 0, 0)
        av.b_setGlasses(random.randint(1, 21), 0, 0)
        av.b_setHat(random.randint(1, 56), 0, 0)

        av.d_broadcastHpString("FASHION STATEMENT!", (.9, .8, .2))
        av.d_playEmote(EmoteFuncDict['Surprise'], 1)


class GagShuffleAward(APReward, TrapReward):

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("GAG SHUFFLE TRAP\n", color='salmon'),
            MinimalJsonMessagePart(f"Got gags?")
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        # Let's make sure we aren't already being shuffled
        avId = av.getDoId()
        if av.getBeingShuffled():
            av.playSound('phase_4/audio/sfx/LETS_GO_GAMBLING.ogg')
            av.d_broadcastHpString("GAG SHUFFLE!", (.3, .5, .8))
            av.d_playEmote(EmoteFuncDict['Confused'], 1)
            return

        # Clear inventory, set being shuffled, randomly choose gags and add them until we fill up
        av.setBeingShuffled(True)
        av.inventory.calcTotalProps()  # Might not be necessary, but just to be safe
        target = av.inventory.totalProps
        av.inventory.clearInventory()  # Wipe inventory
        # Get allowed track level pairs
        allowedGags: List[Tuple[int, int]] = av.experience.getAllowedGagsAndLevels()
        # Only do enough attempts to fill us back up to what we were
        for _ in range(target):
            # Randomly select a gag and attempt to add it
            if allowedGags:  # sanity check for possible empty list
                gag: Tuple[int, int] = random.choice(allowedGags)
                track, level = gag
                gagsAdded = av.inventory.addItem(track, level)

                # If this gag failed to add, we can no longer query for this gag. Remove it.
                if gagsAdded <= 0:
                    allowedGags.remove(gag)

                # Edge case, if we are out of gags we need to stop (in theory this should never happen but let's be safe :p)
                if len(allowedGags) <= 0:
                    break
            else:
                print(f"archipelago rewards WARNING: Could not find any allowed gags. For avId: {avId}")
                break
        # We're done shuffling, should be good now
        av.setBeingShuffled(False)
        av.playSound('phase_4/audio/sfx/LETS_GO_GAMBLING.ogg')
        av.b_setInventory(av.inventory.makeNetString())
        av.d_broadcastHpString("GAG SHUFFLE!", (.3, .5, .8))
        av.d_playEmote(EmoteFuncDict['Confused'], 1)


class GagDisableTrapAward(APReward, TrapReward):
    DURATION_SECONDS = 2 * 60

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("GAG DISABLE TRAP\n", color='salmon'),
            MinimalJsonMessagePart("Temporarily disables a random gag track!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        trackArray = getattr(av, 'trackArray', None) or []
        availableTracks = [
            track for track in range(min(len(ToontownBattleGlobals.Tracks), len(trackArray)))
            if trackArray[track] > 0 and not av.isGagTrackDisabled(track)
        ]
        if not availableTracks:
            av.d_sendArchipelagoMessage("A gag disable trap fizzled because you have no gag tracks.")
            return
        track = random.choice(availableTracks)
        duration = max(1, math.floor(self.DURATION_SECONDS * get_trap_strength_multiplier(firer)))
        if not av.activateGagDisableTrap(track, duration) and firer is not None and firer is not av:
            firer.d_sendArchipelagoMessage("Gag Disable Trap fizzled because the target is on cooldown.")


class ActivityTrapAward(APReward, TrapReward):
    """Base behavior for traps that send an opponent into a solo activity."""

    activity_name = "activity"

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart(f"{self.activity_name.upper()} TRAP\n", color='salmon'),
            MinimalJsonMessagePart(f"Sends your opponent to {self.activity_name}!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        # Activity loaders cannot safely pull a Toon out of a battle. The trap is
        # still spent, but neither combatant is changed.
        if ((firer is not None and firer.getBattleId()) or av.getBattleId()):
            if firer is not None:
                firer.d_sendArchipelagoMessage(
                    f"{self.activity_name.title()} Trap was used during a battle and had no effect."
                )
            return

        from toontown.hood import ZoneUtil

        where = ZoneUtil.getWhereName(av.zoneId, True)
        if where not in ('playground', 'street'):
            if firer is not None:
                firer.d_sendArchipelagoMessage(
                    f"{self.activity_name.title()} Trap fizzled: the target is not in a street or playground."
                )
            return

        # Race and golf both return through lastHood. Explicitly refresh it so
        # a player trapped from a street returns to that street's playground.
        hoodId = ZoneUtil.getHoodId(av.zoneId)
        av.setLastHood(hoodId)
        av.sendUpdate('setLastHood', [hoodId])
        self._start_activity(av)

    def _start_activity(self, av: "DistributedToonAI"):
        raise NotImplementedError


class RacingTrapAward(ActivityTrapAward):
    activity_name = "racing"

    def _start_activity(self, av: "DistributedToonAI"):
        from toontown.racing import RaceGlobals

        raceZone = av.air.raceMgr.createRace(
            RaceGlobals.RT_Speedway_1,
            RaceGlobals.Practice,
            1,
            [av.doId],
            circuitLoop=[],
            circuitPoints={},
            circuitTimes={},
        )
        av.sendUpdate('sendToRaceCourse', [raceZone, RaceGlobals.RT_Speedway_1, av.getLastHood()])


class GolfingTrapAward(ActivityTrapAward):
    activity_name = "golfing"

    def _start_activity(self, av: "DistributedToonAI"):
        from toontown.golf import GolfManagerAI

        golfZone = GolfManagerAI.GolfManagerAI().readyGolfCourse([av.doId], courseId=0)
        av.sendUpdate('sendToGolfTrapCourse', [golfZone, av.getLastHood()])


class RaidTrapAward(APReward, TrapReward):
    self_target = True

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("RAID!\n", color='salmon'),
            MinimalJsonMessagePart("Force one trade without approval."),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.authorizeRaidTrade()
        av.d_openRaidTradeGui()
        av.d_sendArchipelagoMessage("RAID! Choose a forced trade.")


class TrapReflectAward(APReward, TrapReward):
    DURATION_SECONDS = 3 * 60
    CHARGES = 2
    self_target = True

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("TRAP REFLECT\n", color='yellow'),
            MinimalJsonMessagePart("Reflects the next 2 traps for 3 minutes!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.activateTrapReflect(math.floor(self.DURATION_SECONDS * get_trap_strength_multiplier(firer)), self.CHARGES)
        av.playSound('phase_4/audio/sfx/SZ_DD_treasure.ogg')
        av.d_broadcastHpString("TRAP REFLECT!", (.95, .85, .2))
        av.d_playEmote(EmoteFuncDict['Resistance Salute'], 1)


class TrapStrengthReward(APReward):
    def __init__(self, percent: int):
        self.percent = percent

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Trap Strength\n", color='yellow'),
            MinimalJsonMessagePart(f"+{self.percent}% stronger", color='cyan'),
            MinimalJsonMessagePart(" forever!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.b_setTrapStrengthPercent(self.percent)


class GagExpBundleAward(APReward):

    def __init__(self, amount: int):
        self.amount: int = amount

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("You were given a fill of\n"),
            MinimalJsonMessagePart(f"{self.amount}% experience", color='cyan'),
            MinimalJsonMessagePart(" in each Gag Track!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        for index, _ in enumerate(ToontownBattleGlobals.Tracks):
            currentCap = min(av.experience.getExperienceCapForTrack(index), ToontownBattleGlobals.regMaxSkill)
            exptoAdd = math.ceil(currentCap * (self.amount/100))
            av.experience.addExp(index, exptoAdd)
        av.ap_setExperience(av.experience.getCurrentExperience())
        # now check for win condition since we have one for maxed gags
        av.checkWinCondition()

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        for index, _ in enumerate(ToontownBattleGlobals.Tracks):
            currentCap = min(av.experience.getExperienceCapForTrack(index), ToontownBattleGlobals.regMaxSkill)
            expToRemove = math.ceil(currentCap * (self.amount / 100))
            currentExp = av.experience.getExp(index)
            av.experience.setExp(index, max(0, currentExp - expToRemove))
        av.ap_setExperience(av.experience.getCurrentExperience())
        return True


class HealAward(APReward):

    def __init__(self, amount: int):
        self.amount: int = amount

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("You were healed for\n"),
            MinimalJsonMessagePart(f"{self.amount}%", color='cyan'),
            MinimalJsonMessagePart(" of your Laff!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        amountPercent = self.amount/100
        heal = math.ceil(amountPercent * av.getMaxHp())
        av.toonUp(heal)

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        return True


class BossRewardAward(APReward):
    SOS = 0
    UNITE = 1
    PINK_SLIP = 2
    SUMMON = 3

    REWARD_TO_DISPLAY_STR = {
        SOS: {3: "3-Star SOS Card",
              4: "4-Star SOS Card",
              5: "5-Star SOS Card"},
        UNITE: {1: "Toon-Up Unite",
                2: "Gag-Up Unite"},
        PINK_SLIP: "Pink Slip",
        SUMMON: "Cog Summon"
    }

    def __init__(self, reward: int, type: int):
        self.reward: int = reward
        self.type: int = type

    def formatted_header(self) -> str:
        if self.reward in [BossRewardAward.SOS, BossRewardAward.UNITE]:
            return global_text_properties.get_raw_formatted_string([
                MinimalJsonMessagePart("You were given a\nrandom "),
                MinimalJsonMessagePart(f"{self.REWARD_TO_DISPLAY_STR[self.reward][self.type]}", color='cyan'),
                MinimalJsonMessagePart("!"),
            ])
        else:
            return global_text_properties.get_raw_formatted_string([
                MinimalJsonMessagePart("You were given\na "),
                MinimalJsonMessagePart(f"{self.REWARD_TO_DISPLAY_STR[self.reward]}", color='cyan'),
                MinimalJsonMessagePart("!"),
            ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        if self.reward == BossRewardAward.SOS:
            if self.type == 3:
                print(NPCToons.npcFriendsWithStars(5))
                av.attemptAddNPCFriend(random.choice(NPCToons.npcFriendsWithStars(3)))
            elif self.type == 4:
                print(NPCToons.npcFriendsWithStars(5))
                av.attemptAddNPCFriend(random.choice(NPCToons.npcFriendsWithStars(4)))
            elif self.type == 5:
                print(NPCToons.npcFriendsWithStars(5))
                av.attemptAddNPCFriend(random.choice(NPCToons.npcFriendsWithStars(5)))
            # This should realistically never happen but, just in case
            else:
                print("This happened.")
                av.attemptAddNPCFriend(random.choice(NPCToons.npcFriendsMinMaxStars(3, 5)))
        elif self.reward == BossRewardAward.UNITE:
            if self.type == 1:
                uniteType = ResistanceChat.RESISTANCE_TOONUP
            elif self.type == 2:
                uniteType = ResistanceChat.RESISTANCE_RESTOCK
            # This should realistically never happen but, just in case
            else:
                uniteType = random.choice([ResistanceChat.RESISTANCE_TOONUP, ResistanceChat.RESISTANCE_RESTOCK])
            uniteChoice = random.choice(ResistanceChat.getItems(uniteType))
            av.addResistanceMessage(ResistanceChat.encodeId(uniteType, uniteChoice))
        elif self.reward == BossRewardAward.PINK_SLIP:
            av.addPinkSlips(1)
        elif self.reward == BossRewardAward.SUMMON:
            av.assignNewCogSummons()

    def revoke(self, av: "DistributedToonAI", item_id: int = None):
        if self.reward == BossRewardAward.SOS:
            return self._removeSOS(av)
        if self.reward == BossRewardAward.UNITE:
            return self._removeUnite(av)
        if self.reward == BossRewardAward.PINK_SLIP:
            if av.getPinkSlips() <= 0:
                return False
            av.removePinkSlips(1)
            return True
        if self.reward == BossRewardAward.SUMMON:
            return self._removeSummon(av)
        return False

    def _removeSOS(self, av: "DistributedToonAI"):
        candidates = NPCToons.npcFriendsWithStars(self.type)
        for npcId in list(av.getNPCFriendsDict().keys()):
            if npcId in candidates:
                return bool(av.attemptSubtractNPCFriend(npcId))
        return False

    def _removeUnite(self, av: "DistributedToonAI"):
        if self.type == 1:
            uniteType = ResistanceChat.RESISTANCE_TOONUP
        elif self.type == 2:
            uniteType = ResistanceChat.RESISTANCE_RESTOCK
        else:
            uniteType = None
        for message in list(av.getResistanceMessages()):
            textId = message[0]
            decodedType = ResistanceChat.decodeId(textId)[0]
            if uniteType is None or decodedType == uniteType:
                av.removeResistanceMessage(textId)
                return True
        return False

    def _removeSummon(self, av: "DistributedToonAI"):
        for suitIndex, summonBits in enumerate(av.getCogSummonsEarned()):
            for summonType, bit in (('single', 1), ('building', 2), ('invasion', 4)):
                if summonBits & bit:
                    return bool(av.removeCogSummonsEarned(suitIndex, summonType))
        return False


class ProofReward(APReward):
    numToBoss = {
        0: "VP",
        1: "CFO",
        2: "CJ",
        3: "CEO"
    }

    def __init__(self, proof: int):
        self.proof = proof

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Proof Obtained!\n", color='green'),
            MinimalJsonMessagePart(f"Proof of the {self.numToBoss[self.proof]}'s defeat!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        # todo keep track of these
        pass


class BountyReward(APReward):

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("Bounty Obtained!\n", color='green'),
            MinimalJsonMessagePart(f"Proof of a difficult task completed!"),
        ])

    def get_image_path(self) -> str:
        return f'phase_14/maps/bounty.png'

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.checkWinCondition()


class VictoryReward(APReward):

    def formatted_header(self) -> str:
        return global_text_properties.get_raw_formatted_string([
            MinimalJsonMessagePart("VICTORY!\n", color='green'),
            MinimalJsonMessagePart(f"You have completed your goal!"),
        ])

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.APVictory()


class UndefinedReward(APReward):

    def __init__(self, desc):
        self.desc = desc

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        av.d_setSystemMessage(0, f"Unknown AP reward: {self.desc}")


class IgnoreReward(APReward):

    def apply(self, av: "DistributedToonAI", firer: "DistributedToonAI" = None):
        pass


ITEM_NAME_TO_AP_REWARD: [str, APReward] = {
    ToontownItemName.LAFF_BOOST_1.value: LaffBoostReward(1),
    ToontownItemName.LAFF_BOOST_2.value: LaffBoostReward(2),
    ToontownItemName.LAFF_BOOST_3.value: LaffBoostReward(3),
    ToontownItemName.LAFF_BOOST_4.value: LaffBoostReward(4),
    ToontownItemName.LAFF_BOOST_5.value: LaffBoostReward(5),
    ToontownItemName.DMG_BOOST_1.value: DmgBoostReward(1),
    ToontownItemName.DMG_BOOST_2.value: DmgBoostReward(2),
    ToontownItemName.DMG_BOOST_3.value: DmgBoostReward(3),
    ToontownItemName.DMG_BOOST_4.value: DmgBoostReward(4),
    ToontownItemName.GAG_CAPACITY_5.value: GagCapacityReward(5),
    ToontownItemName.GAG_CAPACITY_10.value: GagCapacityReward(10),
    ToontownItemName.GAG_CAPACITY_15.value: GagCapacityReward(15),
    ToontownItemName.MONEY_CAP_1000.value: JellybeanJarUpgradeReward(1000),
    ToontownItemName.TASK_CAPACITY.value: TaskCapacityReward(1),
    ToontownItemName.TOONUP_FRAME.value: GagTrainingFrameReward(GagTrainingFrameReward.TOONUP),
    ToontownItemName.TRAP_FRAME.value: GagTrainingFrameReward(GagTrainingFrameReward.TRAP),
    ToontownItemName.LURE_FRAME.value: GagTrainingFrameReward(GagTrainingFrameReward.LURE),
    ToontownItemName.SOUND_FRAME.value: GagTrainingFrameReward(GagTrainingFrameReward.SOUND),
    ToontownItemName.THROW_FRAME.value: GagTrainingFrameReward(GagTrainingFrameReward.THROW),
    ToontownItemName.SQUIRT_FRAME.value: GagTrainingFrameReward(GagTrainingFrameReward.SQUIRT),
    ToontownItemName.DROP_FRAME.value: GagTrainingFrameReward(GagTrainingFrameReward.DROP),
    ToontownItemName.TOONUP_UPGRADE.value: GagUpgradeReward(GagUpgradeReward.TOONUP),
    ToontownItemName.TRAP_UPGRADE.value: GagUpgradeReward(GagUpgradeReward.TRAP),
    ToontownItemName.LURE_UPGRADE.value: GagUpgradeReward(GagUpgradeReward.LURE),
    ToontownItemName.SOUND_UPGRADE.value: GagUpgradeReward(GagUpgradeReward.SOUND),
    ToontownItemName.THROW_UPGRADE.value: GagUpgradeReward(GagUpgradeReward.THROW),
    ToontownItemName.SQUIRT_UPGRADE.value: GagUpgradeReward(GagUpgradeReward.SQUIRT),
    ToontownItemName.DROP_UPGRADE.value: GagUpgradeReward(GagUpgradeReward.DROP),
    ToontownItemName.GAG_MULTIPLIER_1.value: GagTrainingMultiplierReward(1),
    ToontownItemName.GAG_MULTIPLIER_2.value: GagTrainingMultiplierReward(2),
    ToontownItemName.FISHING_ROD_UPGRADE.value: FishingRodUpgradeReward(),
    ToontownItemName.TTC_ACCESS.value: AccessKeyReward(AccessKeyReward.TOONTOWN_CENTRAL),
    ToontownItemName.DD_ACCESS.value: AccessKeyReward(AccessKeyReward.DONALDS_DOCK),
    ToontownItemName.DG_ACCESS.value: AccessKeyReward(AccessKeyReward.DAISYS_GARDENS),
    ToontownItemName.MML_ACCESS.value: AccessKeyReward(AccessKeyReward.MINNIES_MELODYLAND),
    ToontownItemName.TB_ACCESS.value: AccessKeyReward(AccessKeyReward.THE_BRRRGH),
    ToontownItemName.DDL_ACCESS.value: AccessKeyReward(AccessKeyReward.DONALDS_DREAMLAND),
    ToontownItemName.SBHQ_ACCESS.value: AccessKeyReward(AccessKeyReward.SELLBOT_HQ),
    ToontownItemName.CBHQ_ACCESS.value: AccessKeyReward(AccessKeyReward.CASHBOT_HQ),
    ToontownItemName.LBHQ_ACCESS.value: AccessKeyReward(AccessKeyReward.LAWBOT_HQ),
    ToontownItemName.BBHQ_ACCESS.value: AccessKeyReward(AccessKeyReward.BOSSBOT_HQ),
    ToontownItemName.AA_ACCESS.value: AccessKeyReward(AccessKeyReward.ACORN_ACRES),
    ToontownItemName.GS_ACCESS.value: AccessKeyReward(AccessKeyReward.GOOFY_SPEEDWAY),
    ToontownItemName.TTC_JOKE_BOOK.value: JokeBookReward(JokeBookReward.TOONTOWN_CENTRAL),
    ToontownItemName.DD_JOKE_BOOK.value: JokeBookReward(JokeBookReward.DONALDS_DOCK),
    ToontownItemName.DG_JOKE_BOOK.value: JokeBookReward(JokeBookReward.DAISYS_GARDENS),
    ToontownItemName.MML_JOKE_BOOK.value: JokeBookReward(JokeBookReward.MINNIES_MELODYLAND),
    ToontownItemName.TB_JOKE_BOOK.value: JokeBookReward(JokeBookReward.THE_BRRRGH),
    ToontownItemName.DDL_JOKE_BOOK.value: JokeBookReward(JokeBookReward.DONALDS_DREAMLAND),
    ToontownItemName.TTC_FISHING.value: FishingLicenseReward(FishingLicenseReward.TOONTOWN_CENTRAL),
    ToontownItemName.DD_FISHING.value: FishingLicenseReward(FishingLicenseReward.DONALDS_DOCK),
    ToontownItemName.DG_FISHING.value: FishingLicenseReward(FishingLicenseReward.DAISYS_GARDENS),
    ToontownItemName.MML_FISHING.value: FishingLicenseReward(FishingLicenseReward.MINNIES_MELODYLAND),
    ToontownItemName.TB_FISHING.value: FishingLicenseReward(FishingLicenseReward.THE_BRRRGH),
    ToontownItemName.DDL_FISHING.value: FishingLicenseReward(FishingLicenseReward.DONALDS_DREAMLAND),
    ToontownItemName.GOLF_PUTTER.value: GolfPutterReward(),
    ToontownItemName.GO_KART.value: GoKartReward(),
    ToontownItemName.FRONT_FACTORY_ACCESS.value: FacilityAccessReward(FADoorCodes.FRONT_FACTORY_ACCESS_MISSING),
    ToontownItemName.SIDE_FACTORY_ACCESS.value: FacilityAccessReward(FADoorCodes.SIDE_FACTORY_ACCESS_MISSING),
    ToontownItemName.COIN_MINT_ACCESS.value: FacilityAccessReward(FADoorCodes.COIN_MINT_ACCESS_MISSING),
    ToontownItemName.DOLLAR_MINT_ACCESS.value: FacilityAccessReward(FADoorCodes.DOLLAR_MINT_ACCESS_MISSING),
    ToontownItemName.BULLION_MINT_ACCESS.value: FacilityAccessReward(FADoorCodes.BULLION_MINT_ACCESS_MISSING),
    ToontownItemName.A_OFFICE_ACCESS.value: FacilityAccessReward(FADoorCodes.OFFICE_A_ACCESS_MISSING),
    ToontownItemName.B_OFFICE_ACCESS.value: FacilityAccessReward(FADoorCodes.OFFICE_B_ACCESS_MISSING),
    ToontownItemName.C_OFFICE_ACCESS.value: FacilityAccessReward(FADoorCodes.OFFICE_C_ACCESS_MISSING),
    ToontownItemName.D_OFFICE_ACCESS.value: FacilityAccessReward(FADoorCodes.OFFICE_D_ACCESS_MISSING),
    ToontownItemName.FRONT_ONE_ACCESS.value: FacilityAccessReward(FADoorCodes.FRONT_THREE_ACCESS_MISSING),
    ToontownItemName.MIDDLE_TWO_ACCESS.value: FacilityAccessReward(FADoorCodes.MIDDLE_SIX_ACCESS_MISSING),
    ToontownItemName.BACK_THREE_ACCESS.value: FacilityAccessReward(FADoorCodes.BACK_NINE_ACCESS_MISSING),
    ToontownItemName.SELLBOT_DISGUISE.value: CogDisguiseReward(CogDisguiseReward.SELLBOT),
    ToontownItemName.CASHBOT_DISGUISE.value: CogDisguiseReward(CogDisguiseReward.CASHBOT),
    ToontownItemName.LAWBOT_DISGUISE.value: CogDisguiseReward(CogDisguiseReward.LAWBOT),
    ToontownItemName.BOSSBOT_DISGUISE.value: CogDisguiseReward(CogDisguiseReward.BOSSBOT),
    ToontownItemName.MONEY_150.value: JellybeanReward(150),
    ToontownItemName.MONEY_400.value: JellybeanReward(400),
    ToontownItemName.MONEY_700.value: JellybeanReward(700),
    ToontownItemName.MONEY_1000.value: JellybeanReward(1000),
    ToontownItemName.FISH.value: FishReward(1),
    ToontownItemName.XP_10.value: GagExpBundleAward(10),
    ToontownItemName.XP_15.value: GagExpBundleAward(15),
    ToontownItemName.XP_20.value: GagExpBundleAward(20),
    ToontownItemName.SOS_REWARD_3.value: BossRewardAward(BossRewardAward.SOS, 3),
    ToontownItemName.SOS_REWARD_4.value: BossRewardAward(BossRewardAward.SOS, 4),
    ToontownItemName.SOS_REWARD_5.value: BossRewardAward(BossRewardAward.SOS, 5),
    ToontownItemName.UNITE_REWARD_TOONUP.value: BossRewardAward(BossRewardAward.UNITE, 1),
    ToontownItemName.UNITE_REWARD_GAG.value: BossRewardAward(BossRewardAward.UNITE, 2),
    ToontownItemName.PINK_SLIP_REWARD.value: BossRewardAward(BossRewardAward.PINK_SLIP, 0),
    ToontownItemName.SUMMON_REWARD.value: BossRewardAward(BossRewardAward.SUMMON, 0),
    ToontownItemName.HEAL_10.value: HealAward(10),
    ToontownItemName.HEAL_20.value: HealAward(20),
    ToontownItemName.UBER_TRAP.value: UberTrapAward(),
    ToontownItemName.BEAN_TAX_TRAP_750.value: BeanTaxTrapAward(750),
    ToontownItemName.BEAN_TAX_TRAP_1000.value: BeanTaxTrapAward(1000),
    ToontownItemName.BEAN_TAX_TRAP_1250.value: BeanTaxTrapAward(1250),
    ToontownItemName.DRIP_TRAP.value: DripTrapAward(),
    ToontownItemName.GAG_SHUFFLE_TRAP.value: GagShuffleAward(),
    ToontownItemName.EXPOSE_TRAP.value: ExposeTrapAward(),
    ToontownItemName.EXPOSE_BEANS_TRAP.value: ExposeBeansTrapAward(),
    ToontownItemName.GAG_DISABLE_TRAP.value: GagDisableTrapAward(),
    ToontownItemName.RACING_TRAP.value: RacingTrapAward(),
    ToontownItemName.GOLFING_TRAP.value: GolfingTrapAward(),
    ToontownItemName.RAID_TRAP.value: RaidTrapAward(),
    ToontownItemName.TRAP_REFLECT.value: TrapReflectAward(),
    ToontownItemName.DAMAGE_15.value: DamageTrapAward(15),
    ToontownItemName.DAMAGE_25.value: DamageTrapAward(25),
    ToontownItemName.VP.value: ProofReward(0),
    ToontownItemName.CFO.value: ProofReward(1),
    ToontownItemName.CJ.value: ProofReward(2),
    ToontownItemName.CEO.value: ProofReward(3),
    ToontownItemName.BOUNTY.value: BountyReward(),
}


def get_ap_reward_from_name(name: str) -> APReward:
    return ITEM_NAME_TO_AP_REWARD.get(name, UndefinedReward(name))


# The id we are given from a packet from archipelago
def get_ap_reward_from_id(_id: int) -> APReward:
    definition = get_item_def_from_id(_id)

    if not definition:
        return UndefinedReward(_id)

    ap_reward: APReward = ITEM_NAME_TO_AP_REWARD.get(definition.name.value)

    if not ap_reward:
        ap_reward = UndefinedReward(definition.name.value)

    return ap_reward


# Wrapper class for APReward that holds not only the APReward, but also additional attributes such as:
# - index reward was received
# - item ID of the Archipelago item
# - Name of the player who got this reward for us
class EarnedAPReward:

    def __init__(self, av, reward: APReward, rewardIndex: int, itemId: int, fromName: str, isLocal: bool, firer=None):
        self.av = av
        self.reward = reward
        self.rewardIndex = rewardIndex
        self.itemId = itemId
        self.fromName = fromName
        self.isLocal = isLocal
        self.firer = firer  # The toon that fired this (only set for manually-fired held traps)

    def apply(self):
        self.reward.apply(self.av, firer=self.firer)  # Actually give the effects
        self.av.d_showReward(self.itemId, self.fromName, self.isLocal)  # Display the popup to the client
