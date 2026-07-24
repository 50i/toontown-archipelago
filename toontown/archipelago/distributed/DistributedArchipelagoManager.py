from typing import List, Dict, Union
import math
import time

from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel, DGG
from direct.directnotify import DirectNotifyGlobal
from direct.distributed.DistributedObject import DistributedObject
from direct.task import Task
from panda3d.core import TextNode

from toontown.archipelago.definitions import color_profile
from toontown.archipelago.definitions.color_profile import ColorProfile
from toontown.archipelago.util.HintContainer import HintContainer, HintedItem
from toontown.archipelago.util.archipelago_information import ArchipelagoInformation
from toontown.toon.DistributedToon import DistributedToon

# An array of default defined team colors to use.
# Feel free to dynamically adjust this array however you please
TEAM_COLORS = (
    color_profile.BLUE,
    color_profile.RED,
    color_profile.GREEN,
    color_profile.YELLOW,
    color_profile.CYAN,
    color_profile.MAGENTA,
    color_profile.ORANGE,
    color_profile.PURPLE,
    color_profile.PINK,
    color_profile.MINT_GREEN,
    color_profile.MIDNIGHT_BLUE,
    color_profile.BURGUNDY,
    color_profile.MAUVE,
)

# The color to use when a toon is not on a team. (Not connected to AP)
NO_TEAM_COLOR = color_profile.GRAY


# Basically the "None" to check for when team checking
NO_TEAM = 999

class DistributedArchipelagoManager(DistributedObject):
    notify = DirectNotifyGlobal.directNotify.newCategory("DistributedArchipelagoManager")
    neverDisable = 1

    def __init__(self, cr):
        super().__init__(cr)
        self.notify.debug("DistributedArchipelagoManager starting up....")

        self._ap_info_cache: Dict[int, ArchipelagoInformation] = {}
        self._trade_inventory_cache: Dict[int, List[List[int]]] = {}
        self._tradeDialog = None
        self._tradeRequesterAvId = None
        self._communityPollFrame = None
        self._communityPollId = None
        self._communityPollEndTime = 0

    def generate(self):
        self.notify.debug("DistributedArchipelagoManager generate()")
        base.cr.archipelagoManager = self

    def announceGenerate(self):
        self.notify.debug("DistributedArchipelagoManager announceGenerate()")

    def delete(self):
        self.notify.debug("DistributedArchipelagoManager delete()")
        base.cr.archipelagoManager = None
        self._destroyCommunityPoll()

    def showCommunityPoll(self, pollId, description, duration):
        self._destroyCommunityPoll()
        self._communityPollId = pollId
        self._communityPollEndTime = time.time() + duration
        self._communityPollFrame = DirectFrame(parent=aspect2d, relief=DGG.RIDGE, frameColor=(0.12, 0.2, 0.38, 0.94), frameSize=(-0.5, 0.5, -0.35, 0.35), pos=(1.5, 0, 0.18), scale=0.72, sortOrder=120)
        DirectLabel(parent=self._communityPollFrame, relief=None, text='COMMUNITY POLL', text_scale=0.07, text_fg=(1, 0.9, 0.35, 1), pos=(0, 0, 0.23), text_align=TextNode.ACenter)
        DirectLabel(parent=self._communityPollFrame, relief=None, text=description, text_scale=0.053, text_wordwrap=15, pos=(0, 0, 0.05), text_align=TextNode.ACenter)
        self._communityPollTimerLabel = DirectLabel(parent=self._communityPollFrame, relief=None, text='', text_scale=0.042, pos=(0, 0, -0.13), text_align=TextNode.ACenter)
        self._communityPollAgreeButton = DirectButton(parent=self._communityPollFrame, relief='raised', frameColor=(0.2, 0.7, 0.32, 1), frameSize=(-0.22, 0.22, -0.07, 0.07), text='Agree', text_scale=0.055, pos=(-0.16, 0, -0.25), command=self._agreeCommunityPoll)
        self._communityPollDeclineButton = DirectButton(parent=self._communityPollFrame, relief='raised', frameColor=(0.72, 0.28, 0.28, 1), frameSize=(-0.22, 0.22, -0.07, 0.07), text='Decline', text_scale=0.05, pos=(0.16, 0, -0.25), command=self._declineCommunityPoll)
        taskMgr.add(self._updateCommunityPollTimer, self.uniqueName('community-poll-countdown'))

    def _agreeCommunityPoll(self):
        if self._communityPollId is None:
            return
        self.sendUpdate('voteCommunityPoll', [self._communityPollId])
        self._setCommunityPollResponse('Agreed')

    def _declineCommunityPoll(self):
        if self._communityPollId is None:
            return
        self.sendUpdate('declineCommunityPoll', [self._communityPollId])
        self._setCommunityPollResponse('Declined')

    def _setCommunityPollResponse(self, text):
        self._communityPollAgreeButton['state'] = DGG.DISABLED
        self._communityPollDeclineButton['state'] = DGG.DISABLED
        self._communityPollAgreeButton['text'] = text
        self._communityPollDeclineButton.hide()

    def _updateCommunityPollTimer(self, task):
        if self._communityPollTimerLabel is None:
            return Task.done
        remaining = max(0, int(math.ceil(self._communityPollEndTime - time.time())))
        self._communityPollTimerLabel['text'] = f'Voting closes in {remaining}s'
        return Task.cont

    def clearCommunityPoll(self, pollId):
        if pollId == self._communityPollId:
            self._destroyCommunityPoll()

    def _destroyCommunityPoll(self):
        taskMgr.remove(self.uniqueName('community-poll-countdown'))
        if self._communityPollFrame:
            self._communityPollFrame.destroy()
            self._communityPollFrame = None
        self._communityPollId = None
        self._communityPollTimerLabel = None

    # Called from the AI. Used to update information that we need to know about toons and their sessions.
    # As the client, we are unaware of most Archipelago things being done on the AI so whatever we need to know
    # We receive here.

    # This can probably be improved, but for now we just get something to work.
    # Only called when information updates on the AI that we need to know.
    def sync(self, info_array: List[List[int]]):

        # First convert our astron data back into our dataclass
        tempInfo: List[ArchipelagoInformation] = []
        for info in info_array:
            tempInfo.append(ArchipelagoInformation.from_struct(info))

        # Clear our cache and add the new data we received
        self._ap_info_cache.clear()
        for info in tempInfo:
            self._ap_info_cache[info.avId] = info

        # Now update everyone's colors
        self.syncToonColorProfiles()

        # Debug
        self.notify.debug(f"DistributedArchipelagoManager sync(): {self._ap_info_cache}")

    # Loops through every DistributedToon in the base.cr repository and sets a color profile for them
    # (If we have one)
    def syncToonColorProfiles(self):

        toons: Dict[int, DistributedToon] = base.cr.getObjectsOfExactClass(DistributedToon)
        self.notify.debug(f"Syncing {len(toons)+1} toons color profiles")

        # Loop through every toon in our DO repository and update their color profile.
        # (If they exist)
        for toonId, toon in toons.items():
            newColorProfile = self.getToonColorProfile(toonId)
            toon.setColorProfile(newColorProfile)

        # Now update ours.
        base.localAvatar.setColorProfile(self.getToonColorProfile(base.localAvatar.getDoId()))

    # Given an avId, attempt to find information related to this toon.
    # Returns ArchipelagoInformation dataclass if exists, None otherwise.
    def getInformation(self, avId) -> Union[ArchipelagoInformation, None]:
        return self._ap_info_cache.get(avId, None)

    def getLocalInformation(self) -> ArchipelagoInformation | None:
        """
        Returns the local toon's information. Returns None if local toon is not currently in an Archipelago session
        """
        return self.getInformation(base.localAvatar.getDoId())

    """
    Helper methods to be called throughout the client for game code
    
    Most of these methods are just dupes of the AI versions, but they work with our ArchipelagoInformation
    dataclasses instead of the raw session on the AI.
    """

    # Given an toon ID, return the ID of the team they are on.
    # Returns None if they are either not on a team, or not connected to Archipelago.
    def getToonTeam(self, avId) -> int:

        # See if we have information about this toon
        info = self.getInformation(avId)
        if info is None:
            return NO_TEAM

        # See if we are on a valid team
        teamId = info.teamId
        if teamId == NO_TEAM:
            return NO_TEAM

        # We have a team!
        return teamId

    # Given two toon IDs, return whether or not they are on the same team.
    # This case is ONLY True when both toons are connected to archipelago and have a similar team slot.
    def onSameTeam(self, avId1, avId2) -> bool:
        team1 = self.getToonTeam(avId1)
        team2 = self.getToonTeam(avId2)

        # If either team1 or team2 is not on a team, they cannot be on the same team.
        if NO_TEAM in (team1, team2):
            return False

        # If the teams are equal, they are on the same team
        return team1 == team2

    # Given two toon IDs, return whether or not they are on enemy teams.
    # We define enemy teams as two opposing teams that does not include spectators.
    # This means that if either toon is not on a team, they will not be considered enemies.
    def onEnemyTeams(self, avId1, avId2) -> bool:
        toon1Team = self.getToonTeam(avId1)
        toon2Team = self.getToonTeam(avId2)

        # If either toon1 or toon2 is not on a team, they cannot be enemies.
        if NO_TEAM in (toon1Team, toon2Team):
            return False

        # If the teams are not equal, they are enemies.
        return toon1Team != toon2Team

    # Returns a list of all toon IDs we are enemies with.
    def getAllEnemies(self) -> List[int]:
        enemies: List[int] = []

        # Loop through all of our information, if the two avIds are enemies then add it
        for info in self._ap_info_cache.values():
            if self.onEnemyTeams(info.avId, base.localAvatar.getDoId()):
                enemies.append(info.avId)

        return enemies

    def getAllTradeTargets(self) -> List[int]:
        localAvId = base.localAvatar.getDoId()
        targets = []
        for avId in self._ap_info_cache:
            if avId != localAvId:
                targets.append(avId)
        return targets

    # Given a team ID, (from self.getToonTeam()) return a ColorProfile.
    def getTeamColorProfile(self, teamId: int) -> ColorProfile:

        # If not on a valid team then return gray.
        # This toon is either "spectating" or is not connected to Archipelago currently.
        if teamId < 0 or teamId is None:
            return NO_TEAM_COLOR

        # If on a team that is within bounds return that color
        if teamId < len(TEAM_COLORS):
            return TEAM_COLORS[teamId]

        # Out of bounds color, make a randomly seeded one (lol)
        return color_profile.getRandomColorProfile(teamId)

    # Given a Toon ID, return a color profile we should use for this toon.
    def getToonColorProfile(self, toonId: int) -> ColorProfile:

        info = self.getInformation(toonId)

        # If we don't have information for this toon, we can safely assume they are not on a team.
        if info is None:
            return NO_TEAM_COLOR

        # Extract the toon's team information and find the team's corresponding color.
        teamID = info.teamId
        return self.getTeamColorProfile(teamID)


    """
    Code related to hint management
    """

    def d_requestHints(self):
        self.sendUpdate('requestHints')

    def setHints(self, primitiveHintContainer):
        """
        Called from the AI, updates hint container stored locally
        """
        container = HintContainer.from_struct(base.localAvatar.getDoId(), primitiveHintContainer)
        base.localAvatar.setHintContainer(container)
        messenger.send('archipelago-hint-update')

    def addHint(self, primitiveHint, silent=False) -> bool:
        """
        Called from the AI, contains a single hint to add to our container
        returns true if the hint made a modification
        """
        hint: HintedItem = HintedItem.from_struct(primitiveHint)
        newHint = base.localAvatar.getHintContainer().addHint(hint)
        if not silent and newHint:
            messenger.send('archipelago-hints-updated')
        return newHint

    def addHints(self, primitiveHintList, silent=False):
        """
        Called from the AI, contains a multiple hints to add to our container
        """
        foundNewHint = False
        for hint in primitiveHintList:
            new = self.addHint(hint, silent=True)
            if new:
                foundNewHint = True

        if not silent and foundNewHint:
            messenger.send('archipelago-hints-updated')

    """
    Code related to cross-player AP reward visibility (cosmetic only)
    """

    def receiveAPReward(self, sourceDisplayName, itemName, fromName):
        """
        Called from the AI. Purely cosmetic — displays a toast that another
        AP-connected toon received an item. Does NOT apply any reward locally,
        does NOT touch received items state, and has no effect on our own
        Archipelago session.
        """
        msg = f"{sourceDisplayName} received: {itemName} (found by {fromName})"
        base.localAvatar.sendArchipelagoMessages([msg])

    def receiveAPBroadcast(self, message):
        """Display a cosmetic server-wide Archipelago announcement."""
        base.localAvatar.sendArchipelagoMessages([message])

    """
    Code related to AP trade escrow
    """

    def d_requestTradeInventories(self):
        self.sendUpdate('requestTradeInventories')

    def tradeInventories(self, inventories):
        self._trade_inventory_cache = {avId: items for avId, items in inventories}
        tradeGui = getattr(base.localAvatar, 'tradeGui', None)
        if tradeGui is not None and not tradeGui.isHidden():
            tradeGui.refresh(requestInventories=False)

    def getTradeInventory(self, avId):
        return self._trade_inventory_cache.get(avId, [])

    def hasTradeInventory(self, avId):
        return avId in self._trade_inventory_cache

    def d_requestTrade(self, targetAvId, offerIndex, offerItemId, requestedIndex, requestedItemId):
        self.sendUpdate('requestTrade', [targetAvId, offerIndex, offerItemId, requestedIndex, requestedItemId])

    def d_requestRaidTrade(self, targetAvId, offerIndex, offerItemId, requestedIndex, requestedItemId):
        self.sendUpdate('requestRaidTrade', [targetAvId, offerIndex, offerItemId, requestedIndex, requestedItemId])

    def d_respondTrade(self, requesterAvId, accepted):
        self.sendUpdate('respondTrade', [requesterAvId, 1 if accepted else 0])

    def d_reportMutationResult(self, result):
        self.sendUpdate('reportMutationResult', [result])

    def tradeRequest(self, requesterAvId, requesterName, offerIndex, offerItemId, requestedItemId, offerName, requestedName):
        self._cleanupTradeDialog()
        self._tradeRequesterAvId = requesterAvId
        self._tradeDialog = DirectFrame(
            parent=aspect2dp,
            relief=DGG.RIDGE,
            borderWidth=(0.012, 0.012),
            frameColor=(0.06, 0.075, 0.09, 0.94),
            frameSize=(-0.42, 0.42, -0.18, 0.18),
            pos=(0.62, 0, 0.58)
        )
        DirectFrame(
            parent=self._tradeDialog,
            relief=DGG.FLAT,
            frameColor=(0.45, 0.78, 0.96, 1),
            frameSize=(-0.42, 0.42, 0.155, 0.18)
        )
        DirectLabel(
            parent=self._tradeDialog,
            relief=None,
            text=f"Trade from {requesterName}",
            text_scale=0.036,
            text_fg=(0.94, 0.97, 1, 1),
            text_align=TextNode.ALeft,
            pos=(-0.37, 0, 0.105)
        )
        DirectLabel(
            parent=self._tradeDialog,
            relief=None,
            text=f"They give: {offerName}\nYou give: {requestedName}",
            text_scale=0.03,
            text_fg=(0.82, 0.88, 0.92, 1),
            text_wordwrap=24,
            text_align=TextNode.ALeft,
            pos=(-0.37, 0, 0.02)
        )
        self._makeTradeDialogButton("Accept", (-0.25, 0, -0.115), self._acceptTradeDialog)
        self._makeTradeDialogButton("Counter", (0, 0, -0.115), self._counterTradeDialog)
        self._makeTradeDialogButton("Decline", (0.25, 0, -0.115), self._declineTradeDialog)

    def _makeTradeDialogButton(self, text, pos, command):
        return DirectButton(
            parent=self._tradeDialog,
            relief=DGG.FLAT,
            frameColor=((0.15, 0.20, 0.25, 1), (0.23, 0.31, 0.38, 1), (0.23, 0.31, 0.38, 1), (0.1, 0.1, 0.1, 0.7)),
            frameSize=(-0.095, 0.095, -0.033, 0.033),
            text=text,
            text_fg=(0.94, 0.97, 1, 1),
            text_scale=0.027,
            text_pos=(0, -0.009),
            pos=pos,
            command=command
        )

    def _acceptTradeDialog(self):
        requesterAvId = self._tradeRequesterAvId
        self._cleanupTradeDialog()
        if requesterAvId is not None:
            self.d_respondTrade(requesterAvId, True)

    def _declineTradeDialog(self):
        requesterAvId = self._tradeRequesterAvId
        self._cleanupTradeDialog()
        if requesterAvId is not None:
            self.d_respondTrade(requesterAvId, False)

    def _counterTradeDialog(self):
        requesterAvId = self._tradeRequesterAvId
        self._cleanupTradeDialog()
        if requesterAvId is not None:
            self.d_respondTrade(requesterAvId, False)
            tradeGui = getattr(base.localAvatar, 'tradeGui', None)
            if tradeGui is not None:
                tradeGui.openForTarget(requesterAvId)

    def _cleanupTradeDialog(self):
        if self._tradeDialog is not None:
            self._tradeDialog.destroy()
            self._tradeDialog = None
        self._tradeRequesterAvId = None

    def tradeResult(self, message):
        base.localAvatar.sendArchipelagoMessages([message])
